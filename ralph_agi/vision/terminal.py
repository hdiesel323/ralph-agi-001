"""Terminal image protocol support for RALPH-AGI.

Supports displaying images in terminals that implement:
- iTerm2 inline images protocol
- Kitty graphics protocol
- Sixel graphics (limited support)
"""

from __future__ import annotations

import base64
import os
import sys
from enum import Enum
from typing import Optional

from ralph_agi.vision.image import ImageData


class TerminalImageProtocol(str, Enum):
    """Supported terminal image protocols."""

    ITERM2 = "iterm2"
    KITTY = "kitty"
    SIXEL = "sixel"
    NONE = "none"


def detect_terminal_protocol() -> TerminalImageProtocol:
    """Detect which terminal image protocol is supported.

    Detection is based on environment variables and terminal capabilities.

    Returns:
        The detected protocol, or NONE if no image support found.
    """
    # Check for iTerm2
    term_program = os.environ.get("TERM_PROGRAM", "")
    if term_program == "iTerm.app":
        return TerminalImageProtocol.ITERM2

    # Check for Kitty
    if os.environ.get("KITTY_WINDOW_ID"):
        return TerminalImageProtocol.KITTY

    # Check for terminals that support Kitty protocol
    term = os.environ.get("TERM", "")
    if "kitty" in term.lower():
        return TerminalImageProtocol.KITTY

    # Check for WezTerm (supports iTerm2 protocol)
    if term_program == "WezTerm":
        return TerminalImageProtocol.ITERM2

    # Check for Mintty (supports sixel)
    if os.environ.get("MSYSTEM"):
        # Could be MSYS2/Git Bash - limited sixel support
        pass

    # Check for sixel support via TERM
    if any(x in term.lower() for x in ["sixel", "mlterm", "xterm-256color"]):
        # Note: xterm-256color doesn't always mean sixel support
        # Would need capability query for proper detection
        pass

    return TerminalImageProtocol.NONE


def is_image_protocol_supported() -> bool:
    """Check if any terminal image protocol is supported.

    Returns:
        True if images can be displayed in the terminal.
    """
    return detect_terminal_protocol() != TerminalImageProtocol.NONE


def display_image_in_terminal(
    image: ImageData,
    width: Optional[int] = None,
    height: Optional[int] = None,
    preserve_aspect_ratio: bool = True,
    protocol: Optional[TerminalImageProtocol] = None,
) -> bool:
    """Display an image in the terminal using the appropriate protocol.

    Args:
        image: ImageData to display.
        width: Display width (cells or pixels depending on protocol).
        height: Display height.
        preserve_aspect_ratio: Whether to maintain aspect ratio.
        protocol: Force a specific protocol. Auto-detects if None.

    Returns:
        True if image was displayed successfully.
    """
    if protocol is None:
        protocol = detect_terminal_protocol()

    if protocol == TerminalImageProtocol.NONE:
        return False

    if protocol == TerminalImageProtocol.ITERM2:
        return _display_iterm2(image, width, height, preserve_aspect_ratio)
    elif protocol == TerminalImageProtocol.KITTY:
        return _display_kitty(image, width, height, preserve_aspect_ratio)
    elif protocol == TerminalImageProtocol.SIXEL:
        return _display_sixel(image, width, height, preserve_aspect_ratio)

    return False


def _display_iterm2(
    image: ImageData,
    width: Optional[int],
    height: Optional[int],
    preserve_aspect_ratio: bool,
) -> bool:
    """Display image using iTerm2 inline images protocol.

    iTerm2 protocol uses OSC 1337 escape sequence with base64 encoded data.
    See: https://iterm2.com/documentation-images.html
    """
    # Build arguments
    args = []

    if width is not None:
        args.append(f"width={width}")
    if height is not None:
        args.append(f"height={height}")
    if preserve_aspect_ratio:
        args.append("preserveAspectRatio=1")

    # Add size
    args.append(f"size={image.size_bytes}")

    # Encode image
    encoded = image.to_base64()

    # Build escape sequence
    # OSC 1337 ; File=[args]:base64_data BEL
    args_str = ";".join(args) if args else ""
    sequence = f"\033]1337;File={args_str}:{encoded}\a"

    try:
        sys.stdout.write(sequence)
        sys.stdout.flush()
        return True
    except Exception:
        return False


def _display_kitty(
    image: ImageData,
    width: Optional[int],
    height: Optional[int],
    preserve_aspect_ratio: bool,
) -> bool:
    """Display image using Kitty graphics protocol.

    Kitty protocol uses APC escape sequences with chunked transfer.
    See: https://sw.kovidgoyal.net/kitty/graphics-protocol/
    """
    # Encode image
    encoded = image.to_base64()

    # Build control data
    # a=T (transmit), f=100 (PNG) or f=32 (RGBA), t=d (direct)
    fmt = 100 if image.format == "png" else 32

    # Chunk size (4096 bytes recommended)
    chunk_size = 4096

    try:
        # Send chunks
        for i in range(0, len(encoded), chunk_size):
            chunk = encoded[i : i + chunk_size]
            is_last = i + chunk_size >= len(encoded)

            # m=1 means more chunks coming, m=0 means last chunk
            m = 0 if is_last else 1

            if i == 0:
                # First chunk includes metadata
                ctrl = f"a=T,f={fmt},m={m}"
            else:
                # Subsequent chunks
                ctrl = f"m={m}"

            # APC escape sequence: \033_G...;\033\\
            sequence = f"\033_G{ctrl};{chunk}\033\\"
            sys.stdout.write(sequence)

        sys.stdout.flush()
        return True
    except Exception:
        return False


def _display_sixel(
    image: ImageData,
    width: Optional[int],
    height: Optional[int],
    preserve_aspect_ratio: bool,
) -> bool:
    """Display image using Sixel graphics protocol.

    Sixel is an older protocol supported by some terminals.
    Requires conversion to sixel format which is complex.
    """
    # Sixel conversion is complex and typically requires a library
    # For now, return False as it's not commonly used
    return False


def get_terminal_size_pixels() -> tuple[int, int]:
    """Get terminal size in pixels (if available).

    Returns:
        Tuple of (width_pixels, height_pixels) or (0, 0) if unavailable.
    """
    # Try TIOCGWINSZ ioctl
    try:
        import fcntl
        import struct
        import termios

        # Query window size
        result = fcntl.ioctl(
            sys.stdout.fileno(),
            termios.TIOCGWINSZ,
            b"\x00" * 8,
        )
        rows, cols, xpixel, ypixel = struct.unpack("HHHH", result)
        if xpixel > 0 and ypixel > 0:
            return (xpixel, ypixel)
    except Exception:
        pass

    return (0, 0)


def clear_image() -> None:
    """Clear any displayed images from the terminal.

    This sends appropriate escape sequences to clear inline images.
    """
    protocol = detect_terminal_protocol()

    if protocol == TerminalImageProtocol.KITTY:
        # Kitty: delete all images
        sys.stdout.write("\033_Ga=d\033\\")
        sys.stdout.flush()


def get_protocol_info() -> dict:
    """Get information about terminal image protocol support.

    Returns:
        Dictionary with protocol details.
    """
    protocol = detect_terminal_protocol()
    term_program = os.environ.get("TERM_PROGRAM", "unknown")
    term = os.environ.get("TERM", "unknown")
    pixel_size = get_terminal_size_pixels()

    return {
        "protocol": protocol.value,
        "supported": protocol != TerminalImageProtocol.NONE,
        "term_program": term_program,
        "term": term,
        "pixel_width": pixel_size[0],
        "pixel_height": pixel_size[1],
    }
