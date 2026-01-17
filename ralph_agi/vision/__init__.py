"""Vision module for RALPH-AGI.

Provides image handling, encoding, and terminal image protocol support
for Claude's vision capabilities.
"""

from ralph_agi.vision.image import (
    ImageData,
    load_image,
    encode_for_claude,
    compress_image,
    get_image_info,
)
from ralph_agi.vision.terminal import (
    TerminalImageProtocol,
    detect_terminal_protocol,
    display_image_in_terminal,
    is_image_protocol_supported,
)
from ralph_agi.vision.clipboard import (
    get_clipboard_image,
    has_clipboard_image,
)

__all__ = [
    # Image handling
    "ImageData",
    "load_image",
    "encode_for_claude",
    "compress_image",
    "get_image_info",
    # Terminal protocol
    "TerminalImageProtocol",
    "detect_terminal_protocol",
    "display_image_in_terminal",
    "is_image_protocol_supported",
    # Clipboard
    "get_clipboard_image",
    "has_clipboard_image",
]
