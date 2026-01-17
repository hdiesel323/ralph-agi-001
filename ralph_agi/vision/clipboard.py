"""Clipboard image support for RALPH-AGI.

Provides functions to check for and retrieve images from the system clipboard.
Supports macOS, Linux (X11/Wayland), and Windows.
"""

from __future__ import annotations

import io
import logging
import subprocess
import sys
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


def has_clipboard_image() -> bool:
    """Check if the clipboard contains an image.

    Returns:
        True if clipboard has image data.
    """
    if sys.platform == "darwin":
        return _has_clipboard_image_macos()
    elif sys.platform == "win32":
        return _has_clipboard_image_windows()
    else:
        return _has_clipboard_image_linux()


def get_clipboard_image() -> Optional[bytes]:
    """Get image data from the clipboard.

    Returns:
        Raw image bytes (PNG format) or None if no image found.
    """
    if sys.platform == "darwin":
        return _get_clipboard_image_macos()
    elif sys.platform == "win32":
        return _get_clipboard_image_windows()
    else:
        return _get_clipboard_image_linux()


def _has_clipboard_image_macos() -> bool:
    """Check clipboard on macOS using osascript."""
    try:
        result = subprocess.run(
            [
                "osascript",
                "-e",
                'clipboard info for (clipboard info) contains {«class PNGf»}',
            ],
            capture_output=True,
            text=True,
            timeout=5,
        )
        # This returns "true" or "false"
        return "true" in result.stdout.lower()
    except Exception as e:
        logger.debug(f"Error checking macOS clipboard: {e}")
        return False


def _get_clipboard_image_macos() -> Optional[bytes]:
    """Get image from macOS clipboard using osascript and pbpaste."""
    try:
        # Try using pngpaste if available (faster)
        try:
            result = subprocess.run(
                ["pngpaste", "-"],
                capture_output=True,
                timeout=10,
            )
            if result.returncode == 0 and result.stdout:
                return result.stdout
        except FileNotFoundError:
            pass

        # Fall back to AppleScript approach
        # Use osascript to write clipboard to temp file
        import tempfile

        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            tmp_path = tmp.name

        script = f'''
        set theFile to POSIX file "{tmp_path}"
        try
            set imageData to the clipboard as «class PNGf»
            set fileRef to open for access theFile with write permission
            write imageData to fileRef
            close access fileRef
            return "success"
        on error errMsg
            return "error: " & errMsg
        end try
        '''

        result = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True,
            text=True,
            timeout=10,
        )

        if "success" in result.stdout:
            path = Path(tmp_path)
            if path.exists():
                data = path.read_bytes()
                path.unlink()
                return data

        # Clean up temp file
        Path(tmp_path).unlink(missing_ok=True)

    except Exception as e:
        logger.debug(f"Error getting macOS clipboard image: {e}")

    return None


def _has_clipboard_image_linux() -> bool:
    """Check clipboard on Linux using xclip or wl-paste."""
    try:
        # Try wl-paste first (Wayland)
        try:
            result = subprocess.run(
                ["wl-paste", "--list-types"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                return "image/png" in result.stdout or "image/" in result.stdout
        except FileNotFoundError:
            pass

        # Try xclip (X11)
        try:
            result = subprocess.run(
                ["xclip", "-selection", "clipboard", "-t", "TARGETS", "-o"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                return "image/png" in result.stdout
        except FileNotFoundError:
            pass

    except Exception as e:
        logger.debug(f"Error checking Linux clipboard: {e}")

    return False


def _get_clipboard_image_linux() -> Optional[bytes]:
    """Get image from Linux clipboard using xclip or wl-paste."""
    try:
        # Try wl-paste first (Wayland)
        try:
            result = subprocess.run(
                ["wl-paste", "--type", "image/png"],
                capture_output=True,
                timeout=10,
            )
            if result.returncode == 0 and result.stdout:
                return result.stdout
        except FileNotFoundError:
            pass

        # Try xclip (X11)
        try:
            result = subprocess.run(
                ["xclip", "-selection", "clipboard", "-t", "image/png", "-o"],
                capture_output=True,
                timeout=10,
            )
            if result.returncode == 0 and result.stdout:
                return result.stdout
        except FileNotFoundError:
            pass

    except Exception as e:
        logger.debug(f"Error getting Linux clipboard image: {e}")

    return None


def _has_clipboard_image_windows() -> bool:
    """Check clipboard on Windows using win32clipboard."""
    try:
        import win32clipboard
        import win32con

        win32clipboard.OpenClipboard()
        try:
            # Check for DIB format (standard Windows image format)
            return win32clipboard.IsClipboardFormatAvailable(win32con.CF_DIB)
        finally:
            win32clipboard.CloseClipboard()
    except ImportError:
        # Try PowerShell fallback
        try:
            result = subprocess.run(
                [
                    "powershell",
                    "-Command",
                    "[Windows.Forms.Clipboard]::ContainsImage()",
                ],
                capture_output=True,
                text=True,
                timeout=5,
            )
            return "True" in result.stdout
        except Exception:
            pass
    except Exception as e:
        logger.debug(f"Error checking Windows clipboard: {e}")

    return False


def _get_clipboard_image_windows() -> Optional[bytes]:
    """Get image from Windows clipboard."""
    try:
        import win32clipboard
        import win32con

        win32clipboard.OpenClipboard()
        try:
            if win32clipboard.IsClipboardFormatAvailable(win32con.CF_DIB):
                data = win32clipboard.GetClipboardData(win32con.CF_DIB)
                # Convert DIB to PNG
                return _dib_to_png(data)
        finally:
            win32clipboard.CloseClipboard()
    except ImportError:
        # Try PowerShell fallback
        try:
            import tempfile

            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
                tmp_path = tmp.name

            script = f'''
            Add-Type -AssemblyName System.Windows.Forms
            $img = [Windows.Forms.Clipboard]::GetImage()
            if ($img -ne $null) {{
                $img.Save("{tmp_path}")
                Write-Output "success"
            }}
            '''

            result = subprocess.run(
                ["powershell", "-Command", script],
                capture_output=True,
                text=True,
                timeout=10,
            )

            if "success" in result.stdout:
                path = Path(tmp_path)
                if path.exists():
                    data = path.read_bytes()
                    path.unlink()
                    return data

            Path(tmp_path).unlink(missing_ok=True)

        except Exception as e:
            logger.debug(f"Error with PowerShell clipboard: {e}")

    except Exception as e:
        logger.debug(f"Error getting Windows clipboard image: {e}")

    return None


def _dib_to_png(dib_data: bytes) -> Optional[bytes]:
    """Convert Windows DIB (Device Independent Bitmap) to PNG.

    Args:
        dib_data: Raw DIB data from clipboard.

    Returns:
        PNG image bytes.
    """
    try:
        from PIL import Image

        # DIB format: BITMAPINFOHEADER + color table + pixel data
        # We need to add the BITMAPFILEHEADER
        import struct

        # Parse BITMAPINFOHEADER
        header_size, width, height, planes, bpp = struct.unpack("<IIIHI", dib_data[:14])

        # Create BITMAPFILEHEADER
        file_size = 14 + len(dib_data)  # 14 bytes for file header
        offset = 14 + header_size
        if bpp <= 8:
            # Add color table size
            offset += (1 << bpp) * 4

        file_header = struct.pack("<2sIHHI", b"BM", file_size, 0, 0, offset)

        # Combine headers and data
        bmp_data = file_header + dib_data

        # Convert to PNG using PIL
        img = Image.open(io.BytesIO(bmp_data))
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        return buffer.getvalue()

    except Exception as e:
        logger.debug(f"Error converting DIB to PNG: {e}")
        return None


def capture_screen_region(
    x: int = 0,
    y: int = 0,
    width: Optional[int] = None,
    height: Optional[int] = None,
) -> Optional[bytes]:
    """Capture a region of the screen.

    Args:
        x: X coordinate of top-left corner.
        y: Y coordinate of top-left corner.
        width: Width of region (None for full screen).
        height: Height of region (None for full screen).

    Returns:
        PNG image bytes or None on failure.
    """
    if sys.platform == "darwin":
        return _capture_screen_macos(x, y, width, height)
    elif sys.platform == "win32":
        return _capture_screen_windows(x, y, width, height)
    else:
        return _capture_screen_linux(x, y, width, height)


def _capture_screen_macos(
    x: int,
    y: int,
    width: Optional[int],
    height: Optional[int],
) -> Optional[bytes]:
    """Capture screen on macOS using screencapture."""
    try:
        import tempfile

        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            tmp_path = tmp.name

        cmd = ["screencapture", "-x"]  # -x for silent (no sound)

        if width is not None and height is not None:
            cmd.extend(["-R", f"{x},{y},{width},{height}"])

        cmd.append(tmp_path)

        result = subprocess.run(cmd, timeout=10)

        if result.returncode == 0:
            path = Path(tmp_path)
            if path.exists():
                data = path.read_bytes()
                path.unlink()
                return data

        Path(tmp_path).unlink(missing_ok=True)

    except Exception as e:
        logger.debug(f"Error capturing macOS screen: {e}")

    return None


def _capture_screen_linux(
    x: int,
    y: int,
    width: Optional[int],
    height: Optional[int],
) -> Optional[bytes]:
    """Capture screen on Linux using scrot or import."""
    try:
        import tempfile

        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            tmp_path = tmp.name

        # Try gnome-screenshot
        try:
            result = subprocess.run(
                ["gnome-screenshot", "-f", tmp_path],
                timeout=10,
            )
            if result.returncode == 0:
                path = Path(tmp_path)
                if path.exists():
                    data = path.read_bytes()
                    path.unlink()
                    return data
        except FileNotFoundError:
            pass

        # Try scrot
        try:
            result = subprocess.run(
                ["scrot", tmp_path],
                timeout=10,
            )
            if result.returncode == 0:
                path = Path(tmp_path)
                if path.exists():
                    data = path.read_bytes()
                    path.unlink()
                    return data
        except FileNotFoundError:
            pass

        # Try import (ImageMagick)
        try:
            cmd = ["import", "-window", "root"]
            if width is not None and height is not None:
                cmd.extend(["-crop", f"{width}x{height}+{x}+{y}"])
            cmd.append(tmp_path)

            result = subprocess.run(cmd, timeout=10)
            if result.returncode == 0:
                path = Path(tmp_path)
                if path.exists():
                    data = path.read_bytes()
                    path.unlink()
                    return data
        except FileNotFoundError:
            pass

        Path(tmp_path).unlink(missing_ok=True)

    except Exception as e:
        logger.debug(f"Error capturing Linux screen: {e}")

    return None


def _capture_screen_windows(
    x: int,
    y: int,
    width: Optional[int],
    height: Optional[int],
) -> Optional[bytes]:
    """Capture screen on Windows using PowerShell."""
    try:
        import tempfile

        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            tmp_path = tmp.name

        # Use PowerShell to capture screen
        script = f'''
        Add-Type -AssemblyName System.Windows.Forms
        Add-Type -AssemblyName System.Drawing
        $screen = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds
        $bitmap = New-Object System.Drawing.Bitmap($screen.Width, $screen.Height)
        $graphics = [System.Drawing.Graphics]::FromImage($bitmap)
        $graphics.CopyFromScreen($screen.Location, [System.Drawing.Point]::Empty, $screen.Size)
        $bitmap.Save("{tmp_path}")
        $graphics.Dispose()
        $bitmap.Dispose()
        Write-Output "success"
        '''

        result = subprocess.run(
            ["powershell", "-Command", script],
            capture_output=True,
            text=True,
            timeout=10,
        )

        if "success" in result.stdout:
            path = Path(tmp_path)
            if path.exists():
                data = path.read_bytes()
                path.unlink()
                return data

        Path(tmp_path).unlink(missing_ok=True)

    except Exception as e:
        logger.debug(f"Error capturing Windows screen: {e}")

    return None
