"""File system tools for RALPH-AGI.

Provides secure file system operations with path validation,
atomic writes, and configurable sandboxing.
"""

from __future__ import annotations

import fnmatch
import logging
import os
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

logger = logging.getLogger(__name__)


class PathSecurityError(Exception):
    """Raised when a path violates security constraints."""

    def __init__(self, path: str, reason: str):
        self.path = path
        self.reason = reason
        super().__init__(f"Path security error for '{path}': {reason}")


class FileSystemError(Exception):
    """Base exception for file system operations."""

    pass


class FileTooLargeError(FileSystemError):
    """Raised when file exceeds size limit."""

    def __init__(self, path: str, size: int, limit: int):
        self.path = path
        self.size = size
        self.limit = limit
        super().__init__(
            f"File '{path}' is {size} bytes, exceeds limit of {limit} bytes"
        )


class BinaryFileError(FileSystemError):
    """Raised when attempting to read binary file as text."""

    def __init__(self, path: str):
        self.path = path
        super().__init__(f"File '{path}' appears to be binary")


@dataclass
class FileInfo:
    """File metadata.

    Attributes:
        path: Absolute path to file
        name: File name (basename)
        is_file: True if regular file
        is_directory: True if directory
        size: Size in bytes (0 for directories)
        modified: Last modification time (UTC)
        extension: File extension (without dot) or None
    """

    path: Path
    name: str
    is_file: bool
    is_directory: bool
    size: int
    modified: datetime
    extension: str | None

    @classmethod
    def from_path(cls, path: Path) -> FileInfo:
        """Create FileInfo from a path.

        Args:
            path: Path to inspect

        Returns:
            FileInfo with metadata

        Raises:
            FileNotFoundError: If path doesn't exist
        """
        stat = path.stat()
        extension = path.suffix[1:] if path.suffix else None

        return cls(
            path=path.resolve(),
            name=path.name,
            is_file=path.is_file(),
            is_directory=path.is_dir(),
            size=stat.st_size if path.is_file() else 0,
            modified=datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc),
            extension=extension,
        )

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "path": str(self.path),
            "name": self.name,
            "is_file": self.is_file,
            "is_directory": self.is_directory,
            "size": self.size,
            "modified": self.modified.isoformat(),
            "extension": self.extension,
        }


class FileSystemTools:
    """Secure file system operations.

    Provides read, write, glob, and directory listing with security
    constraints including path validation and sandboxing.

    Usage:
        # Create with default (cwd) sandbox
        fs = FileSystemTools()

        # Read a file
        content = fs.read_file("src/main.py")

        # Write a file
        fs.write_file("output.txt", "Hello world")

        # Find Python files
        files = fs.glob_files("**/*.py")

        # List directory
        entries = fs.list_directory("src/")

    Security:
        - All paths validated against allowed_roots
        - Path traversal (../) detected after resolution
        - Symlinks resolved and validated
        - Atomic writes prevent corruption
        - Size limits prevent memory exhaustion
    """

    # Default maximum file size (10 MB)
    DEFAULT_MAX_FILE_SIZE = 10 * 1024 * 1024

    # Binary detection: check first N bytes for null bytes
    BINARY_CHECK_SIZE = 8192

    def __init__(
        self,
        allowed_roots: list[Path] | None = None,
        max_file_size: int = DEFAULT_MAX_FILE_SIZE,
        follow_symlinks: bool = True,
    ):
        """Initialize file system tools.

        Args:
            allowed_roots: Directories that can be accessed.
                          If None, uses current working directory.
            max_file_size: Maximum file size to read in bytes
            follow_symlinks: Whether to follow symbolic links
        """
        if allowed_roots is None:
            allowed_roots = [Path.cwd()]

        # Resolve all roots to absolute paths
        self._allowed_roots = [root.resolve() for root in allowed_roots]
        self._max_file_size = max_file_size
        self._follow_symlinks = follow_symlinks

        logger.debug(
            f"FileSystemTools initialized with roots: {self._allowed_roots}"
        )

    @property
    def allowed_roots(self) -> list[Path]:
        """Get allowed root directories."""
        return self._allowed_roots.copy()

    def _validate_path(self, path: str | Path) -> Path:
        """Validate and resolve a path.

        Args:
            path: Path to validate (relative or absolute)

        Returns:
            Resolved absolute path

        Raises:
            PathSecurityError: If path is outside allowed roots
        """
        # Convert to Path
        if isinstance(path, str):
            path = Path(path)

        # Resolve to absolute (follows symlinks if enabled)
        if self._follow_symlinks:
            resolved = path.resolve()
        else:
            # Resolve without following final symlink
            resolved = path.absolute()
            # But still need to check parent resolution
            if path.is_symlink():
                # Check the symlink target is within bounds
                target = path.resolve()
                if not self._is_within_roots(target):
                    raise PathSecurityError(
                        str(path), "Symlink target outside allowed roots"
                    )

        # Check if within allowed roots
        if not self._is_within_roots(resolved):
            raise PathSecurityError(
                str(path),
                f"Path resolves outside allowed roots: {self._allowed_roots}",
            )

        return resolved

    def _is_within_roots(self, path: Path) -> bool:
        """Check if path is within any allowed root."""
        for root in self._allowed_roots:
            try:
                path.relative_to(root)
                return True
            except ValueError:
                continue
        return False

    def read_file(self, path: str | Path) -> str:
        """Read text file contents.

        Args:
            path: File path (relative or absolute)

        Returns:
            File contents as string

        Raises:
            PathSecurityError: Path outside allowed roots
            FileNotFoundError: File doesn't exist
            FileTooLargeError: File exceeds size limit
            BinaryFileError: File appears to be binary
        """
        resolved = self._validate_path(path)

        if not resolved.exists():
            raise FileNotFoundError(f"File not found: {path}")

        if not resolved.is_file():
            raise FileSystemError(f"Not a file: {path}")

        # Check size
        size = resolved.stat().st_size
        if size > self._max_file_size:
            raise FileTooLargeError(str(path), size, self._max_file_size)

        # Read and detect encoding
        content = self._read_with_encoding(resolved)

        logger.debug(f"Read file: {resolved} ({len(content)} chars)")
        return content

    def _read_with_encoding(self, path: Path) -> str:
        """Read file with encoding detection.

        Tries UTF-8 first, then falls back to other encodings.
        """
        # Try UTF-8 first (most common)
        try:
            content = path.read_text(encoding="utf-8")
            # Check for binary content (null bytes in text is suspicious)
            if "\x00" in content[:self.BINARY_CHECK_SIZE]:
                raise BinaryFileError(str(path))
            return content
        except UnicodeDecodeError:
            pass

        # Try UTF-16 (with BOM)
        try:
            content = path.read_text(encoding="utf-16")
            return content
        except (UnicodeDecodeError, UnicodeError):
            pass

        # Try Latin-1 (never fails, but might be wrong)
        try:
            content = path.read_text(encoding="latin-1")
            # Check for binary
            if "\x00" in content[:self.BINARY_CHECK_SIZE]:
                raise BinaryFileError(str(path))
            return content
        except Exception:
            raise BinaryFileError(str(path))

    def read_file_bytes(self, path: str | Path) -> bytes:
        """Read file as bytes.

        Args:
            path: File path

        Returns:
            File contents as bytes

        Raises:
            PathSecurityError: Path outside allowed roots
            FileNotFoundError: File doesn't exist
            FileTooLargeError: File exceeds size limit
        """
        resolved = self._validate_path(path)

        if not resolved.exists():
            raise FileNotFoundError(f"File not found: {path}")

        if not resolved.is_file():
            raise FileSystemError(f"Not a file: {path}")

        size = resolved.stat().st_size
        if size > self._max_file_size:
            raise FileTooLargeError(str(path), size, self._max_file_size)

        return resolved.read_bytes()

    def write_file(
        self,
        path: str | Path,
        content: str,
        create_dirs: bool = True,
        encoding: str = "utf-8",
    ) -> Path:
        """Write content to file atomically.

        Uses write-to-temp-then-rename pattern to prevent corruption
        on crash or interrupt.

        Args:
            path: Target file path
            content: Content to write
            create_dirs: Create parent directories if needed
            encoding: Text encoding (default: utf-8)

        Returns:
            Absolute path to written file

        Raises:
            PathSecurityError: Path outside allowed roots
        """
        resolved = self._validate_path(path)

        # Create parent directories if needed
        if create_dirs:
            resolved.parent.mkdir(parents=True, exist_ok=True)

        # Atomic write: temp file in same directory, then rename
        temp_fd, temp_path = tempfile.mkstemp(
            dir=resolved.parent,
            prefix=f".{resolved.name}.",
            suffix=".tmp",
        )

        try:
            # Write to temp file
            with os.fdopen(temp_fd, "w", encoding=encoding) as f:
                f.write(content)

            # Rename to target (atomic on POSIX)
            os.replace(temp_path, resolved)

            logger.debug(f"Wrote file: {resolved} ({len(content)} chars)")
            return resolved

        except Exception:
            # Clean up temp file on error
            try:
                os.unlink(temp_path)
            except OSError:
                pass
            raise

    def write_file_bytes(
        self,
        path: str | Path,
        content: bytes,
        create_dirs: bool = True,
    ) -> Path:
        """Write bytes to file atomically.

        Args:
            path: Target file path
            content: Bytes to write
            create_dirs: Create parent directories if needed

        Returns:
            Absolute path to written file
        """
        resolved = self._validate_path(path)

        if create_dirs:
            resolved.parent.mkdir(parents=True, exist_ok=True)

        temp_fd, temp_path = tempfile.mkstemp(
            dir=resolved.parent,
            prefix=f".{resolved.name}.",
            suffix=".tmp",
        )

        try:
            with os.fdopen(temp_fd, "wb") as f:
                f.write(content)

            os.replace(temp_path, resolved)
            return resolved

        except Exception:
            try:
                os.unlink(temp_path)
            except OSError:
                pass
            raise

    def glob_files(
        self,
        pattern: str,
        root: str | Path | None = None,
    ) -> list[Path]:
        """Find files matching glob pattern.

        Args:
            pattern: Glob pattern (e.g., "**/*.py", "*.txt")
            root: Root directory for search (default: first allowed root)

        Returns:
            List of matching file paths (sorted)

        Raises:
            PathSecurityError: Root outside allowed roots
        """
        if root is None:
            root = self._allowed_roots[0]
        else:
            root = self._validate_path(root)

        if not root.is_dir():
            return []

        # Use pathlib glob
        matches = list(root.glob(pattern))

        # Filter to files only and validate paths
        result = []
        for match in matches:
            if match.is_file():
                try:
                    self._validate_path(match)
                    result.append(match)
                except PathSecurityError:
                    # Skip files outside allowed roots (e.g., symlinks)
                    continue

        return sorted(result)

    def list_directory(self, path: str | Path) -> list[FileInfo]:
        """List directory contents.

        Args:
            path: Directory path

        Returns:
            List of FileInfo for each entry (sorted by name)

        Raises:
            PathSecurityError: Path outside allowed roots
            FileNotFoundError: Directory doesn't exist
            FileSystemError: Path is not a directory
        """
        resolved = self._validate_path(path)

        if not resolved.exists():
            raise FileNotFoundError(f"Directory not found: {path}")

        if not resolved.is_dir():
            raise FileSystemError(f"Not a directory: {path}")

        entries = []
        for entry in resolved.iterdir():
            try:
                # Validate each entry
                self._validate_path(entry)
                entries.append(FileInfo.from_path(entry))
            except (PathSecurityError, PermissionError):
                # Skip entries we can't access
                continue

        return sorted(entries, key=lambda e: e.name)

    def file_exists(self, path: str | Path) -> bool:
        """Check if file or directory exists.

        Args:
            path: Path to check

        Returns:
            True if exists, False otherwise

        Raises:
            PathSecurityError: Path outside allowed roots
        """
        resolved = self._validate_path(path)
        return resolved.exists()

    def get_file_info(self, path: str | Path) -> FileInfo:
        """Get file metadata.

        Args:
            path: File path

        Returns:
            FileInfo with metadata

        Raises:
            PathSecurityError: Path outside allowed roots
            FileNotFoundError: Path doesn't exist
        """
        resolved = self._validate_path(path)

        if not resolved.exists():
            raise FileNotFoundError(f"Path not found: {path}")

        return FileInfo.from_path(resolved)

    def delete_file(self, path: str | Path) -> bool:
        """Delete a file.

        Args:
            path: File path to delete

        Returns:
            True if deleted, False if didn't exist

        Raises:
            PathSecurityError: Path outside allowed roots
            FileSystemError: Path is a directory
        """
        resolved = self._validate_path(path)

        if not resolved.exists():
            return False

        if resolved.is_dir():
            raise FileSystemError(f"Cannot delete directory with delete_file: {path}")

        resolved.unlink()
        logger.debug(f"Deleted file: {resolved}")
        return True

    def create_directory(self, path: str | Path, exist_ok: bool = True) -> Path:
        """Create a directory.

        Args:
            path: Directory path
            exist_ok: Don't error if directory exists

        Returns:
            Absolute path to directory

        Raises:
            PathSecurityError: Path outside allowed roots
        """
        resolved = self._validate_path(path)
        resolved.mkdir(parents=True, exist_ok=exist_ok)
        logger.debug(f"Created directory: {resolved}")
        return resolved

    def copy_file(self, src: str | Path, dst: str | Path) -> Path:
        """Copy a file.

        Args:
            src: Source file path
            dst: Destination file path

        Returns:
            Absolute path to destination file

        Raises:
            PathSecurityError: Path outside allowed roots
            FileNotFoundError: Source doesn't exist
        """
        src_resolved = self._validate_path(src)
        dst_resolved = self._validate_path(dst)

        if not src_resolved.exists():
            raise FileNotFoundError(f"Source not found: {src}")

        if not src_resolved.is_file():
            raise FileSystemError(f"Source is not a file: {src}")

        # Read and write (using atomic write)
        content = src_resolved.read_bytes()
        return self.write_file_bytes(dst_resolved, content)

    def move_file(self, src: str | Path, dst: str | Path) -> Path:
        """Move/rename a file.

        Args:
            src: Source file path
            dst: Destination file path

        Returns:
            Absolute path to destination file

        Raises:
            PathSecurityError: Path outside allowed roots
            FileNotFoundError: Source doesn't exist
        """
        src_resolved = self._validate_path(src)
        dst_resolved = self._validate_path(dst)

        if not src_resolved.exists():
            raise FileNotFoundError(f"Source not found: {src}")

        # Create parent directories for destination
        dst_resolved.parent.mkdir(parents=True, exist_ok=True)

        # Use rename (atomic if same filesystem)
        src_resolved.rename(dst_resolved)
        logger.debug(f"Moved file: {src_resolved} -> {dst_resolved}")
        return dst_resolved

    def walk(
        self,
        path: str | Path | None = None,
        pattern: str | None = None,
    ) -> Iterator[FileInfo]:
        """Walk directory tree yielding file info.

        Args:
            path: Root directory (default: first allowed root)
            pattern: Optional filename pattern to match

        Yields:
            FileInfo for each file found
        """
        if path is None:
            path = self._allowed_roots[0]
        else:
            path = self._validate_path(path)

        for root, dirs, files in os.walk(path):
            root_path = Path(root)

            for filename in files:
                if pattern and not fnmatch.fnmatch(filename, pattern):
                    continue

                file_path = root_path / filename
                try:
                    self._validate_path(file_path)
                    yield FileInfo.from_path(file_path)
                except (PathSecurityError, PermissionError, FileNotFoundError):
                    continue
