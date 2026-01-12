"""JSONL backup store for crash-safe memory persistence.

This module provides a simple append-only JSONL backup that runs
in parallel with Memvid. If Memvid fails, the JSONL can be used
as a fallback for searching historical data.

Design Principles:
- Append-only (crash-safe)
- File locking for concurrent access safety
- Simple grep-based search fallback
- Zero dependencies beyond stdlib
"""

from __future__ import annotations

import fcntl
import json
import logging
import os
import re
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    from .store import MemoryFrame

logger = logging.getLogger(__name__)


class JSONLBackupStore:
    """Append-only JSONL backup for memory frames.

    Provides crash-safe persistence that doesn't depend on Memvid.
    Each line is a complete JSON object representing a MemoryFrame.

    Attributes:
        backup_path: Path to the .jsonl backup file.

    Example:
        >>> backup = JSONLBackupStore("ralph_memory.jsonl")
        >>> backup.append({
        ...     "id": "abc123",
        ...     "content": "Task completed",
        ...     "frame_type": "result",
        ...     "timestamp": "2026-01-11T12:00:00Z"
        ... })
    """

    def __init__(self, backup_path: str | Path = "ralph_memory.jsonl"):
        """Initialize the JSONL backup store.

        Args:
            backup_path: Path to the .jsonl file. Will be created if
                        it doesn't exist.
        """
        self.backup_path = Path(backup_path)

    def append(self, frame_data: dict[str, Any]) -> bool:
        """Append a frame to the backup file.

        Uses file locking to ensure safe concurrent writes.

        Args:
            frame_data: Dictionary with frame data (id, content, frame_type, etc.)

        Returns:
            True if write succeeded, False otherwise.
        """
        try:
            # Ensure parent directory exists
            self.backup_path.parent.mkdir(parents=True, exist_ok=True)

            # Add backup timestamp
            frame_data = {
                **frame_data,
                "_backup_timestamp": datetime.now(timezone.utc).isoformat(),
            }

            # Serialize to JSON
            line = json.dumps(frame_data, default=str) + "\n"

            # Append with file locking
            with open(self.backup_path, "a", encoding="utf-8") as f:
                # Acquire exclusive lock
                fcntl.flock(f.fileno(), fcntl.LOCK_EX)
                try:
                    f.write(line)
                    f.flush()
                    os.fsync(f.fileno())  # Ensure data hits disk
                finally:
                    # Release lock
                    fcntl.flock(f.fileno(), fcntl.LOCK_UN)

            return True

        except Exception as e:
            logger.error(f"Failed to write JSONL backup: {e}")
            return False

    def search(
        self,
        query: str,
        frame_type: Optional[str] = None,
        limit: int = 10,
        case_insensitive: bool = True,
    ) -> list[dict[str, Any]]:
        """Search the backup file using simple text matching.

        This is a fallback search that doesn't require Memvid.
        It's slower than Memvid but guaranteed to work.

        Args:
            query: Text to search for in content field.
            frame_type: Optional filter by frame type.
            limit: Maximum number of results.
            case_insensitive: Whether to ignore case in search.

        Returns:
            List of matching frame dictionaries, most recent first.
        """
        if not self.backup_path.exists():
            return []

        try:
            matches = []
            pattern = re.compile(
                re.escape(query), re.IGNORECASE if case_insensitive else 0
            )

            with open(self.backup_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue

                    try:
                        frame = json.loads(line)

                        # Filter by type if specified
                        if frame_type and frame.get("frame_type") != frame_type:
                            continue

                        # Search in content
                        content = frame.get("content", "")
                        if query == "*" or pattern.search(content):
                            matches.append(frame)

                    except json.JSONDecodeError:
                        continue  # Skip malformed lines

            # Return most recent first
            matches.reverse()

            # Apply limit
            return matches[:limit]

        except Exception as e:
            logger.error(f"Failed to search JSONL backup: {e}")
            return []

    def get_recent(self, n: int = 10) -> list[dict[str, Any]]:
        """Get the most recent N frames from the backup.

        Args:
            n: Maximum number of frames to return.

        Returns:
            List of frame dictionaries, most recent first.
        """
        if not self.backup_path.exists():
            return []

        try:
            # Read all lines (could be optimized with tail-like behavior for large files)
            with open(self.backup_path, "r", encoding="utf-8") as f:
                lines = f.readlines()

            # Parse from end
            frames = []
            for line in reversed(lines):
                line = line.strip()
                if not line:
                    continue
                try:
                    frames.append(json.loads(line))
                    if len(frames) >= n:
                        break
                except json.JSONDecodeError:
                    continue

            return frames

        except Exception as e:
            logger.error(f"Failed to get recent from JSONL backup: {e}")
            return []

    def count(self) -> int:
        """Count total frames in the backup file.

        Returns:
            Number of valid JSON lines in the file.
        """
        if not self.backup_path.exists():
            return 0

        try:
            count = 0
            with open(self.backup_path, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        try:
                            json.loads(line)
                            count += 1
                        except json.JSONDecodeError:
                            pass
            return count
        except Exception as e:
            logger.error(f"Failed to count JSONL backup: {e}")
            return 0

    def exists(self) -> bool:
        """Check if the backup file exists.

        Returns:
            True if the backup file exists.
        """
        return self.backup_path.exists()


def frame_to_dict(frame: "MemoryFrame") -> dict[str, Any]:
    """Convert a MemoryFrame to a dictionary for JSONL serialization.

    Args:
        frame: MemoryFrame object to convert.

    Returns:
        Dictionary representation of the frame.
    """
    return asdict(frame)


def dict_to_frame(data: dict[str, Any]) -> "MemoryFrame":
    """Convert a dictionary to a MemoryFrame.

    Args:
        data: Dictionary with frame data.

    Returns:
        MemoryFrame object.
    """
    from .store import MemoryFrame

    return MemoryFrame(
        id=data.get("id", ""),
        content=data.get("content", ""),
        frame_type=data.get("frame_type", "unknown"),
        metadata=data.get("metadata", {}),
        timestamp=data.get("timestamp", ""),
        session_id=data.get("session_id"),
        tags=data.get("tags", []),
        score=data.get("score"),
    )
