"""Tests for terminal image protocol support."""

from __future__ import annotations

import os
import pytest
from unittest.mock import patch, MagicMock

from ralph_agi.vision.terminal import (
    TerminalImageProtocol,
    detect_terminal_protocol,
    is_image_protocol_supported,
    display_image_in_terminal,
    get_protocol_info,
    clear_image,
)
from ralph_agi.vision.image import ImageData


class TestTerminalImageProtocol:
    """Tests for TerminalImageProtocol enum."""

    def test_protocol_values(self):
        """Test all protocol values exist."""
        assert TerminalImageProtocol.ITERM2.value == "iterm2"
        assert TerminalImageProtocol.KITTY.value == "kitty"
        assert TerminalImageProtocol.SIXEL.value == "sixel"
        assert TerminalImageProtocol.NONE.value == "none"


class TestDetectTerminalProtocol:
    """Tests for detect_terminal_protocol function."""

    def test_detect_iterm2(self):
        """Test detecting iTerm2."""
        with patch.dict(os.environ, {"TERM_PROGRAM": "iTerm.app"}):
            assert detect_terminal_protocol() == TerminalImageProtocol.ITERM2

    def test_detect_kitty_by_window_id(self):
        """Test detecting Kitty by KITTY_WINDOW_ID."""
        with patch.dict(os.environ, {"KITTY_WINDOW_ID": "1", "TERM_PROGRAM": ""}, clear=True):
            assert detect_terminal_protocol() == TerminalImageProtocol.KITTY

    def test_detect_kitty_by_term(self):
        """Test detecting Kitty by TERM."""
        with patch.dict(os.environ, {"TERM": "xterm-kitty", "TERM_PROGRAM": ""}, clear=True):
            assert detect_terminal_protocol() == TerminalImageProtocol.KITTY

    def test_detect_wezterm(self):
        """Test detecting WezTerm (uses iTerm2 protocol)."""
        with patch.dict(os.environ, {"TERM_PROGRAM": "WezTerm"}):
            assert detect_terminal_protocol() == TerminalImageProtocol.ITERM2

    def test_detect_none(self):
        """Test detecting no support."""
        with patch.dict(os.environ, {"TERM_PROGRAM": "", "TERM": "xterm"}, clear=True):
            assert detect_terminal_protocol() == TerminalImageProtocol.NONE


class TestIsImageProtocolSupported:
    """Tests for is_image_protocol_supported function."""

    def test_supported_iterm2(self):
        """Test that iTerm2 is supported."""
        with patch.dict(os.environ, {"TERM_PROGRAM": "iTerm.app"}):
            assert is_image_protocol_supported() is True

    def test_supported_kitty(self):
        """Test that Kitty is supported."""
        with patch.dict(os.environ, {"KITTY_WINDOW_ID": "1", "TERM_PROGRAM": ""}, clear=True):
            assert is_image_protocol_supported() is True

    def test_not_supported(self):
        """Test that unsupported terminals return False."""
        with patch.dict(os.environ, {"TERM_PROGRAM": "", "TERM": "xterm"}, clear=True):
            assert is_image_protocol_supported() is False


class TestDisplayImageInTerminal:
    """Tests for display_image_in_terminal function."""

    @pytest.fixture
    def mock_image(self):
        """Create a mock ImageData."""
        return ImageData(
            data=b"PNG data here",
            format="png",
            width=100,
            height=100,
            size_bytes=13,
        )

    def test_display_no_protocol(self, mock_image):
        """Test display returns False when no protocol."""
        with patch.dict(os.environ, {"TERM_PROGRAM": "", "TERM": "xterm"}, clear=True):
            result = display_image_in_terminal(mock_image)
            assert result is False

    def test_display_iterm2(self, mock_image):
        """Test display with iTerm2 protocol."""
        with patch.dict(os.environ, {"TERM_PROGRAM": "iTerm.app"}):
            with patch("sys.stdout") as mock_stdout:
                mock_stdout.write = MagicMock()
                mock_stdout.flush = MagicMock()
                result = display_image_in_terminal(mock_image)
                # Should attempt to write escape sequence
                assert mock_stdout.write.called

    def test_display_kitty(self, mock_image):
        """Test display with Kitty protocol."""
        with patch.dict(os.environ, {"KITTY_WINDOW_ID": "1", "TERM_PROGRAM": ""}, clear=True):
            with patch("sys.stdout") as mock_stdout:
                mock_stdout.write = MagicMock()
                mock_stdout.flush = MagicMock()
                result = display_image_in_terminal(mock_image)
                # Should attempt to write escape sequence
                assert mock_stdout.write.called

    def test_force_protocol(self, mock_image):
        """Test forcing a specific protocol."""
        with patch("sys.stdout") as mock_stdout:
            mock_stdout.write = MagicMock()
            mock_stdout.flush = MagicMock()

            # Force iTerm2 even if not detected
            display_image_in_terminal(
                mock_image,
                protocol=TerminalImageProtocol.ITERM2,
            )
            assert mock_stdout.write.called


class TestGetProtocolInfo:
    """Tests for get_protocol_info function."""

    def test_info_structure(self):
        """Test that info has expected keys."""
        info = get_protocol_info()

        assert "protocol" in info
        assert "supported" in info
        assert "term_program" in info
        assert "term" in info
        assert "pixel_width" in info
        assert "pixel_height" in info

    def test_info_iterm2(self):
        """Test info when iTerm2 detected."""
        with patch.dict(os.environ, {"TERM_PROGRAM": "iTerm.app"}):
            info = get_protocol_info()
            assert info["protocol"] == "iterm2"
            assert info["supported"] is True
            assert info["term_program"] == "iTerm.app"

    def test_info_none(self):
        """Test info when no protocol detected."""
        with patch.dict(os.environ, {"TERM_PROGRAM": "", "TERM": "xterm"}, clear=True):
            info = get_protocol_info()
            assert info["protocol"] == "none"
            assert info["supported"] is False


class TestClearImage:
    """Tests for clear_image function."""

    def test_clear_kitty(self):
        """Test clearing images in Kitty."""
        with patch.dict(os.environ, {"KITTY_WINDOW_ID": "1", "TERM_PROGRAM": ""}, clear=True):
            with patch("sys.stdout") as mock_stdout:
                mock_stdout.write = MagicMock()
                mock_stdout.flush = MagicMock()
                clear_image()
                # Should write delete sequence
                assert mock_stdout.write.called
                call_args = str(mock_stdout.write.call_args)
                assert "Ga=d" in call_args  # Kitty delete command

    def test_clear_no_protocol(self):
        """Test clearing when no protocol (should not error)."""
        with patch.dict(os.environ, {"TERM_PROGRAM": "", "TERM": "xterm"}, clear=True):
            # Should not raise
            clear_image()
