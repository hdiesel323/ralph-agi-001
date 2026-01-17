"""Tests for vision image handling."""

from __future__ import annotations

import base64
import io
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

# Check if PIL is available
try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

from ralph_agi.vision.image import (
    ImageData,
    load_image,
    encode_for_claude,
    compress_image,
    get_image_info,
    is_supported_format,
    create_thumbnail,
    SUPPORTED_FORMATS,
    MIME_TYPES,
)


def create_test_image(
    width: int = 100,
    height: int = 100,
    color: tuple = (255, 0, 0),
    format: str = "PNG",
) -> bytes:
    """Create a test image and return as bytes."""
    if not HAS_PIL:
        pytest.skip("PIL not available")

    img = Image.new("RGB", (width, height), color)
    buffer = io.BytesIO()
    img.save(buffer, format=format)
    return buffer.getvalue()


class TestImageData:
    """Tests for ImageData dataclass."""

    def test_image_data_creation(self):
        """Test creating ImageData."""
        data = b"test data"
        img = ImageData(
            data=data,
            format="png",
            width=100,
            height=200,
            size_bytes=len(data),
            source="test.png",
        )
        assert img.data == data
        assert img.format == "png"
        assert img.width == 100
        assert img.height == 200
        assert img.size_bytes == len(data)
        assert img.source == "test.png"

    def test_mime_type(self):
        """Test MIME type property."""
        img = ImageData(data=b"", format="png", width=0, height=0, size_bytes=0)
        assert img.mime_type == "image/png"

        img = ImageData(data=b"", format="jpeg", width=0, height=0, size_bytes=0)
        assert img.mime_type == "image/jpeg"

        img = ImageData(data=b"", format="gif", width=0, height=0, size_bytes=0)
        assert img.mime_type == "image/gif"

    def test_aspect_ratio(self):
        """Test aspect ratio calculation."""
        img = ImageData(data=b"", format="png", width=200, height=100, size_bytes=0)
        assert img.aspect_ratio == 2.0

        img = ImageData(data=b"", format="png", width=100, height=200, size_bytes=0)
        assert img.aspect_ratio == 0.5

        img = ImageData(data=b"", format="png", width=100, height=0, size_bytes=0)
        assert img.aspect_ratio == 0.0  # Avoid division by zero

    def test_to_base64(self):
        """Test base64 encoding."""
        data = b"hello world"
        img = ImageData(data=data, format="png", width=0, height=0, size_bytes=len(data))
        encoded = img.to_base64()
        assert encoded == base64.b64encode(data).decode("utf-8")

    def test_to_data_url(self):
        """Test data URL generation."""
        data = b"hello"
        img = ImageData(data=data, format="png", width=0, height=0, size_bytes=len(data))
        url = img.to_data_url()
        assert url.startswith("data:image/png;base64,")
        assert base64.b64encode(data).decode("utf-8") in url


@pytest.mark.skipif(not HAS_PIL, reason="PIL not available")
class TestLoadImage:
    """Tests for load_image function."""

    def test_load_from_bytes(self):
        """Test loading image from bytes."""
        data = create_test_image(50, 50)
        img = load_image(data)

        assert img.width == 50
        assert img.height == 50
        assert img.format == "png"
        assert img.source == "<bytes>"

    def test_load_from_file(self, tmp_path):
        """Test loading image from file."""
        # Create test image file
        img_path = tmp_path / "test.png"
        img_data = create_test_image(100, 80)
        img_path.write_bytes(img_data)

        img = load_image(img_path)

        assert img.width == 100
        assert img.height == 80
        assert img.format == "png"
        assert str(img_path) in img.source

    def test_load_from_string_path(self, tmp_path):
        """Test loading image from string path."""
        img_path = tmp_path / "test.png"
        img_data = create_test_image()
        img_path.write_bytes(img_data)

        img = load_image(str(img_path))
        assert img.width == 100

    def test_load_jpeg(self, tmp_path):
        """Test loading JPEG image."""
        img_path = tmp_path / "test.jpg"
        img_data = create_test_image(format="JPEG")
        img_path.write_bytes(img_data)

        img = load_image(img_path)
        assert img.format == "jpeg"

    def test_load_nonexistent_file(self):
        """Test loading from nonexistent file."""
        with pytest.raises(FileNotFoundError):
            load_image("/nonexistent/path/image.png")


@pytest.mark.skipif(not HAS_PIL, reason="PIL not available")
class TestEncodeForClaude:
    """Tests for encode_for_claude function."""

    def test_encode_basic(self):
        """Test basic encoding for Claude."""
        data = create_test_image()
        img = load_image(data)
        encoded = encode_for_claude(img)

        assert encoded["type"] == "image"
        assert encoded["source"]["type"] == "base64"
        assert encoded["source"]["media_type"] == "image/png"
        assert len(encoded["source"]["data"]) > 0

    def test_encode_jpeg(self, tmp_path):
        """Test encoding JPEG for Claude."""
        img_path = tmp_path / "test.jpg"
        img_data = create_test_image(format="JPEG")
        img_path.write_bytes(img_data)

        img = load_image(img_path)
        encoded = encode_for_claude(img)

        assert encoded["source"]["media_type"] == "image/jpeg"


@pytest.mark.skipif(not HAS_PIL, reason="PIL not available")
class TestCompressImage:
    """Tests for compress_image function."""

    def test_no_compression_needed(self):
        """Test that small images aren't compressed."""
        data = create_test_image(50, 50)
        img = load_image(data)
        original_size = img.size_bytes

        compressed = compress_image(img)
        # Small image should not be modified much
        assert compressed.width == 50
        assert compressed.height == 50

    def test_resize_large_image(self):
        """Test resizing large image."""
        data = create_test_image(5000, 5000)
        img = load_image(data)

        compressed = compress_image(img, max_dimension=1000)

        assert compressed.width <= 1000
        assert compressed.height <= 1000

    def test_preserve_aspect_ratio(self):
        """Test that aspect ratio is preserved."""
        data = create_test_image(2000, 1000)  # 2:1 aspect ratio
        img = load_image(data)

        compressed = compress_image(img, max_dimension=500)

        # Should maintain approximately 2:1 ratio
        ratio = compressed.width / compressed.height
        assert 1.9 < ratio < 2.1


@pytest.mark.skipif(not HAS_PIL, reason="PIL not available")
class TestGetImageInfo:
    """Tests for get_image_info function."""

    def test_info_from_bytes(self):
        """Test getting info from bytes."""
        data = create_test_image(150, 100)
        info = get_image_info(data)

        assert info["width"] == 150
        assert info["height"] == 100
        assert info["format"] == "png"
        assert info["size_bytes"] == len(data)

    def test_info_from_file(self, tmp_path):
        """Test getting info from file."""
        img_path = tmp_path / "test.png"
        img_data = create_test_image(200, 150)
        img_path.write_bytes(img_data)

        info = get_image_info(img_path)

        assert info["width"] == 200
        assert info["height"] == 150
        assert info["path"] == str(img_path)


class TestIsSupportedFormat:
    """Tests for is_supported_format function."""

    def test_supported_formats(self):
        """Test all supported formats."""
        assert is_supported_format("image.png") is True
        assert is_supported_format("image.jpg") is True
        assert is_supported_format("image.jpeg") is True
        assert is_supported_format("image.gif") is True
        assert is_supported_format("image.webp") is True

    def test_unsupported_formats(self):
        """Test unsupported formats."""
        assert is_supported_format("image.bmp") is False
        assert is_supported_format("image.tiff") is False
        assert is_supported_format("document.pdf") is False

    def test_case_insensitive(self):
        """Test case insensitivity."""
        assert is_supported_format("image.PNG") is True
        assert is_supported_format("image.JPG") is True

    def test_path_object(self):
        """Test with Path object."""
        assert is_supported_format(Path("image.png")) is True
        assert is_supported_format(Path("/path/to/image.jpeg")) is True


@pytest.mark.skipif(not HAS_PIL, reason="PIL not available")
class TestCreateThumbnail:
    """Tests for create_thumbnail function."""

    def test_thumbnail_size(self):
        """Test thumbnail is created at correct size."""
        data = create_test_image(500, 500)
        img = load_image(data)

        thumb = create_thumbnail(img, max_width=100, max_height=100)

        assert thumb.width <= 100
        assert thumb.height <= 100

    def test_thumbnail_preserves_aspect(self):
        """Test thumbnail preserves aspect ratio."""
        data = create_test_image(400, 200)  # 2:1 ratio
        img = load_image(data)

        thumb = create_thumbnail(img, max_width=100, max_height=100)

        # Width should be limiting factor
        assert thumb.width == 100
        assert thumb.height == 50

    def test_thumbnail_source(self):
        """Test thumbnail source is marked."""
        data = create_test_image()
        img = load_image(data)
        img.source = "original.png"

        thumb = create_thumbnail(img)

        assert "thumbnail:" in thumb.source


class TestConstants:
    """Tests for module constants."""

    def test_supported_formats(self):
        """Test SUPPORTED_FORMATS contains expected values."""
        assert "png" in SUPPORTED_FORMATS
        assert "jpeg" in SUPPORTED_FORMATS
        assert "jpg" in SUPPORTED_FORMATS
        assert "gif" in SUPPORTED_FORMATS
        assert "webp" in SUPPORTED_FORMATS

    def test_mime_types(self):
        """Test MIME_TYPES mapping."""
        assert MIME_TYPES["png"] == "image/png"
        assert MIME_TYPES["jpeg"] == "image/jpeg"
        assert MIME_TYPES["jpg"] == "image/jpeg"
        assert MIME_TYPES["gif"] == "image/gif"
        assert MIME_TYPES["webp"] == "image/webp"
