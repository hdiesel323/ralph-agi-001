"""Image handling utilities for RALPH-AGI vision capabilities.

Provides loading, encoding, and compression of images for use with
Claude's vision API.
"""

from __future__ import annotations

import base64
import io
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Optional, Union

logger = logging.getLogger(__name__)

# Maximum image size for Claude vision (approximately 20MB base64)
MAX_IMAGE_SIZE_BYTES = 20 * 1024 * 1024

# Supported image formats
SUPPORTED_FORMATS = {"png", "jpeg", "jpg", "gif", "webp"}

# MIME types for image formats
MIME_TYPES = {
    "png": "image/png",
    "jpeg": "image/jpeg",
    "jpg": "image/jpeg",
    "gif": "image/gif",
    "webp": "image/webp",
}

ImageFormat = Literal["png", "jpeg", "gif", "webp"]


@dataclass
class ImageData:
    """Container for image data and metadata.

    Attributes:
        data: Raw image bytes.
        format: Image format (png, jpeg, gif, webp).
        width: Image width in pixels.
        height: Image height in pixels.
        size_bytes: Size of image data in bytes.
        source: Optional source path or description.
    """

    data: bytes
    format: ImageFormat
    width: int
    height: int
    size_bytes: int
    source: Optional[str] = None

    @property
    def mime_type(self) -> str:
        """Get MIME type for this image format."""
        return MIME_TYPES.get(self.format, "application/octet-stream")

    @property
    def aspect_ratio(self) -> float:
        """Get aspect ratio (width/height)."""
        if self.height == 0:
            return 0.0
        return self.width / self.height

    def to_base64(self) -> str:
        """Encode image data to base64 string."""
        return base64.b64encode(self.data).decode("utf-8")

    def to_data_url(self) -> str:
        """Get data URL for this image."""
        return f"data:{self.mime_type};base64,{self.to_base64()}"


def load_image(source: Union[str, Path, bytes]) -> ImageData:
    """Load an image from file path or bytes.

    Args:
        source: File path (str or Path) or raw image bytes.

    Returns:
        ImageData containing the loaded image.

    Raises:
        FileNotFoundError: If file path doesn't exist.
        ValueError: If image format is not supported.
        RuntimeError: If PIL/Pillow is not available.
    """
    try:
        from PIL import Image
    except ImportError:
        raise RuntimeError(
            "PIL/Pillow is required for image processing. "
            "Install with: pip install Pillow"
        )

    if isinstance(source, bytes):
        # Load from bytes
        data = source
        img = Image.open(io.BytesIO(data))
        source_str = "<bytes>"
    else:
        # Load from file
        path = Path(source)
        if not path.exists():
            raise FileNotFoundError(f"Image file not found: {path}")

        with open(path, "rb") as f:
            data = f.read()
        img = Image.open(io.BytesIO(data))
        source_str = str(path)

    # Get format
    fmt = img.format.lower() if img.format else "png"
    if fmt == "jpeg":
        fmt = "jpeg"
    elif fmt not in SUPPORTED_FORMATS:
        # Convert to PNG if format not supported
        logger.debug(f"Converting unsupported format {fmt} to PNG")
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        data = buffer.getvalue()
        fmt = "png"

    return ImageData(
        data=data,
        format=fmt,  # type: ignore
        width=img.width,
        height=img.height,
        size_bytes=len(data),
        source=source_str,
    )


def encode_for_claude(image: ImageData) -> dict:
    """Encode image for Claude vision API.

    Args:
        image: ImageData to encode.

    Returns:
        Dictionary formatted for Claude's vision message content.

    Example:
        >>> img = load_image("screenshot.png")
        >>> content = encode_for_claude(img)
        >>> # Use in messages:
        >>> message = {"role": "user", "content": [content, {"type": "text", "text": "What's in this image?"}]}
    """
    return {
        "type": "image",
        "source": {
            "type": "base64",
            "media_type": image.mime_type,
            "data": image.to_base64(),
        },
    }


def compress_image(
    image: ImageData,
    max_size_bytes: int = MAX_IMAGE_SIZE_BYTES,
    max_dimension: int = 4096,
    quality: int = 85,
) -> ImageData:
    """Compress image to fit within size and dimension limits.

    Args:
        image: ImageData to compress.
        max_size_bytes: Maximum size in bytes.
        max_dimension: Maximum width or height.
        quality: JPEG quality (0-100, only for JPEG output).

    Returns:
        Compressed ImageData (may be same object if no compression needed).
    """
    try:
        from PIL import Image
    except ImportError:
        raise RuntimeError(
            "PIL/Pillow is required for image processing. "
            "Install with: pip install Pillow"
        )

    # Check if compression needed
    needs_resize = image.width > max_dimension or image.height > max_dimension
    needs_compress = image.size_bytes > max_size_bytes

    if not needs_resize and not needs_compress:
        return image

    img = Image.open(io.BytesIO(image.data))

    # Resize if needed
    if needs_resize:
        ratio = min(max_dimension / image.width, max_dimension / image.height)
        new_size = (int(image.width * ratio), int(image.height * ratio))
        img = img.resize(new_size, Image.Resampling.LANCZOS)
        logger.debug(f"Resized image from {image.width}x{image.height} to {new_size}")

    # Determine output format (use JPEG for smaller size if not transparent)
    if img.mode == "RGBA" or image.format == "png":
        output_format = "PNG"
        fmt = "png"
    else:
        output_format = "JPEG"
        fmt = "jpeg"

    # Save with compression
    buffer = io.BytesIO()
    save_kwargs = {"format": output_format}
    if output_format == "JPEG":
        save_kwargs["quality"] = quality
        save_kwargs["optimize"] = True
        # Convert RGBA to RGB for JPEG
        if img.mode == "RGBA":
            img = img.convert("RGB")

    img.save(buffer, **save_kwargs)
    data = buffer.getvalue()

    # If still too large and using PNG, try JPEG
    if len(data) > max_size_bytes and output_format == "PNG":
        buffer = io.BytesIO()
        if img.mode == "RGBA":
            img = img.convert("RGB")
        img.save(buffer, format="JPEG", quality=quality, optimize=True)
        data = buffer.getvalue()
        fmt = "jpeg"
        logger.debug("Converted PNG to JPEG for smaller size")

    # If still too large, reduce quality
    current_quality = quality
    while len(data) > max_size_bytes and current_quality > 20:
        current_quality -= 10
        buffer = io.BytesIO()
        if img.mode == "RGBA":
            img = img.convert("RGB")
        img.save(buffer, format="JPEG", quality=current_quality, optimize=True)
        data = buffer.getvalue()
        fmt = "jpeg"
        logger.debug(f"Reduced quality to {current_quality}, size: {len(data)}")

    return ImageData(
        data=data,
        format=fmt,  # type: ignore
        width=img.width,
        height=img.height,
        size_bytes=len(data),
        source=image.source,
    )


def get_image_info(source: Union[str, Path, bytes]) -> dict:
    """Get image metadata without loading full image data.

    Args:
        source: File path or bytes.

    Returns:
        Dictionary with image info (format, width, height, size).
    """
    try:
        from PIL import Image
    except ImportError:
        raise RuntimeError(
            "PIL/Pillow is required for image processing. "
            "Install with: pip install Pillow"
        )

    if isinstance(source, bytes):
        img = Image.open(io.BytesIO(source))
        size_bytes = len(source)
        path_str = None
    else:
        path = Path(source)
        img = Image.open(path)
        size_bytes = path.stat().st_size
        path_str = str(path)

    fmt = img.format.lower() if img.format else "unknown"

    return {
        "format": fmt,
        "width": img.width,
        "height": img.height,
        "size_bytes": size_bytes,
        "path": path_str,
        "mode": img.mode,
    }


def is_supported_format(path: Union[str, Path]) -> bool:
    """Check if a file has a supported image format.

    Args:
        path: File path to check.

    Returns:
        True if format is supported.
    """
    path = Path(path)
    suffix = path.suffix.lower().lstrip(".")
    return suffix in SUPPORTED_FORMATS


def create_thumbnail(
    image: ImageData,
    max_width: int = 200,
    max_height: int = 200,
) -> ImageData:
    """Create a thumbnail of an image.

    Args:
        image: ImageData to create thumbnail from.
        max_width: Maximum thumbnail width.
        max_height: Maximum thumbnail height.

    Returns:
        Thumbnail ImageData.
    """
    try:
        from PIL import Image
    except ImportError:
        raise RuntimeError(
            "PIL/Pillow is required for image processing. "
            "Install with: pip install Pillow"
        )

    img = Image.open(io.BytesIO(image.data))
    img.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)

    buffer = io.BytesIO()
    output_format = "PNG" if img.mode == "RGBA" else "JPEG"
    fmt = "png" if output_format == "PNG" else "jpeg"

    if output_format == "JPEG" and img.mode == "RGBA":
        img = img.convert("RGB")

    img.save(buffer, format=output_format, quality=85)
    data = buffer.getvalue()

    return ImageData(
        data=data,
        format=fmt,  # type: ignore
        width=img.width,
        height=img.height,
        size_bytes=len(data),
        source=f"thumbnail:{image.source}",
    )
