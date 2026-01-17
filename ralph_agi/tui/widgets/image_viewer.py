"""Image viewer widget for RALPH-AGI TUI.

Displays images in the terminal with fallback for unsupported terminals.
"""

from __future__ import annotations

from pathlib import Path
from typing import ClassVar, Optional, Union

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.message import Message
from textual.reactive import reactive
from textual.widgets import Static

from ralph_agi.vision.image import ImageData, load_image, create_thumbnail
from ralph_agi.vision.terminal import (
    TerminalImageProtocol,
    detect_terminal_protocol,
    display_image_in_terminal,
    is_image_protocol_supported,
)


class ImagePreview(Static):
    """Widget showing an image preview with metadata.

    If the terminal supports image display (iTerm2/Kitty), shows inline image.
    Otherwise shows image metadata and ASCII placeholder.
    """

    DEFAULT_CSS = """
    ImagePreview {
        width: auto;
        height: auto;
        min-height: 3;
        padding: 1;
        border: solid $primary;
        background: $surface;
    }

    ImagePreview.has-image {
        border: solid $success;
    }

    ImagePreview.no-protocol {
        border: dashed $warning;
    }

    ImagePreview .image-info {
        color: $text-muted;
    }

    ImagePreview .image-name {
        color: $text;
        text-style: bold;
    }

    ImagePreview .image-size {
        color: $text-disabled;
    }
    """

    image: reactive[Optional[ImageData]] = reactive(None)

    def __init__(
        self,
        image: Optional[ImageData] = None,
        show_inline: bool = True,
        **kwargs,
    ) -> None:
        """Initialize the image preview.

        Args:
            image: Initial image to display.
            show_inline: Whether to show inline image (if terminal supports).
            **kwargs: Widget arguments.
        """
        super().__init__(**kwargs)
        self._show_inline = show_inline
        if image:
            self.image = image

    def compose(self) -> ComposeResult:
        """Compose the widget content."""
        yield Static("No image", id="preview-content")

    def watch_image(self, image: Optional[ImageData]) -> None:
        """React to image changes."""
        self._update_display()

    def _update_display(self) -> None:
        """Update the display based on current image."""
        try:
            content = self.query_one("#preview-content", Static)
        except Exception:
            return

        if self.image is None:
            content.update("[dim]No image attached[/dim]")
            self.remove_class("has-image")
            return

        self.add_class("has-image")

        # Get protocol info
        protocol = detect_terminal_protocol()

        # Build display text
        lines = []

        # Image info header
        name = Path(self.image.source).name if self.image.source else "Image"
        lines.append(f"[bold]{name}[/bold]")
        lines.append(
            f"[dim]{self.image.width}x{self.image.height} | "
            f"{self._format_size(self.image.size_bytes)} | "
            f"{self.image.format.upper()}[/dim]"
        )

        # Show inline image if supported
        if self._show_inline and protocol != TerminalImageProtocol.NONE:
            # Note: Textual doesn't directly support inline images
            # The actual image display happens via escape sequences
            # which work outside the Textual rendering
            lines.append("")
            lines.append(f"[green]Inline image ({protocol.value})[/green]")
            # Trigger image display
            self.call_later(self._display_inline)
        else:
            # Show ASCII placeholder
            if protocol == TerminalImageProtocol.NONE:
                self.add_class("no-protocol")
                lines.append("")
                lines.append("[yellow]Terminal doesn't support inline images[/yellow]")

            lines.append("")
            lines.append(self._get_ascii_placeholder())

        content.update("\n".join(lines))

    def _display_inline(self) -> None:
        """Display the image inline using terminal protocol."""
        if self.image and is_image_protocol_supported():
            # Create thumbnail for display
            thumb = create_thumbnail(self.image, max_width=400, max_height=300)
            display_image_in_terminal(thumb)

    def _format_size(self, size_bytes: int) -> str:
        """Format size in human-readable form."""
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        else:
            return f"{size_bytes / (1024 * 1024):.1f} MB"

    def _get_ascii_placeholder(self) -> str:
        """Get ASCII placeholder for image."""
        if self.image is None:
            return ""

        # Simple ASCII box representing image
        lines = []
        width = min(30, self.image.width // 20)
        height = min(10, self.image.height // 40)

        lines.append("+" + "-" * width + "+")
        for i in range(height):
            if i == height // 2:
                label = f" {self.image.format.upper()} "
                padding = width - len(label)
                line = "|" + " " * (padding // 2) + label + " " * (padding - padding // 2) + "|"
            else:
                line = "|" + " " * width + "|"
            lines.append(line)
        lines.append("+" + "-" * width + "+")

        return "\n".join(lines)

    def set_image(self, image: ImageData) -> None:
        """Set the displayed image.

        Args:
            image: Image to display.
        """
        self.image = image

    def clear(self) -> None:
        """Clear the displayed image."""
        self.image = None
        self.remove_class("has-image")
        self.remove_class("no-protocol")


class ImageAttachment(Vertical):
    """Widget for managing image attachments in conversations.

    Provides UI for:
    - Dropping/selecting image files
    - Pasting from clipboard
    - Capturing screenshots
    - Managing attached images
    """

    DEFAULT_CSS = """
    ImageAttachment {
        width: 100%;
        height: auto;
        min-height: 5;
        max-height: 20;
        padding: 1;
        border: solid $surface-lighten-2;
        background: $surface;
    }

    ImageAttachment.has-images {
        border: solid $success;
    }

    ImageAttachment .attachment-header {
        text-style: bold;
        margin-bottom: 1;
    }

    ImageAttachment .attachment-count {
        color: $text-muted;
    }

    ImageAttachment .attachment-help {
        color: $text-disabled;
    }
    """

    BINDINGS: ClassVar[list[Binding]] = [
        Binding("ctrl+v", "paste_image", "Paste Image", show=False),
        Binding("ctrl+shift+s", "screenshot", "Screenshot", show=False),
        Binding("delete", "remove_selected", "Remove", show=False),
    ]

    class ImageAdded(Message):
        """Sent when an image is added."""

        def __init__(self, image: ImageData) -> None:
            super().__init__()
            self.image = image

    class ImageRemoved(Message):
        """Sent when an image is removed."""

        def __init__(self, index: int) -> None:
            super().__init__()
            self.index = index

    class ImagesCleared(Message):
        """Sent when all images are cleared."""

        pass

    # Track attached images
    image_count: reactive[int] = reactive(0)

    def __init__(self, **kwargs) -> None:
        """Initialize image attachment widget."""
        super().__init__(**kwargs)
        self._images: list[ImageData] = []
        self._selected_index: Optional[int] = None

    def compose(self) -> ComposeResult:
        """Compose the widget."""
        yield Static("[bold]Images[/bold]", classes="attachment-header")
        yield Static("[dim]No images attached[/dim]", id="attachment-status")
        yield Static(
            "[dim]Ctrl+V: Paste | Ctrl+Shift+S: Screenshot | Drop file[/dim]",
            classes="attachment-help",
        )

    def watch_image_count(self, count: int) -> None:
        """React to image count changes."""
        self._update_status()

    def _update_status(self) -> None:
        """Update status display."""
        try:
            status = self.query_one("#attachment-status", Static)
        except Exception:
            return

        if not self._images:
            status.update("[dim]No images attached[/dim]")
            self.remove_class("has-images")
        else:
            total_size = sum(img.size_bytes for img in self._images)
            size_str = self._format_size(total_size)
            status.update(
                f"[green]{len(self._images)} image(s)[/green] "
                f"[dim]({size_str} total)[/dim]"
            )
            self.add_class("has-images")

    def _format_size(self, size_bytes: int) -> str:
        """Format size in human-readable form."""
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        else:
            return f"{size_bytes / (1024 * 1024):.1f} MB"

    def add_image(self, source: Union[str, Path, bytes, ImageData]) -> bool:
        """Add an image to attachments.

        Args:
            source: File path, bytes, or ImageData.

        Returns:
            True if image was added successfully.
        """
        try:
            if isinstance(source, ImageData):
                image = source
            else:
                image = load_image(source)

            self._images.append(image)
            self.image_count = len(self._images)
            self.post_message(self.ImageAdded(image))
            return True
        except Exception as e:
            self.log.error(f"Failed to add image: {e}")
            return False

    def remove_image(self, index: int) -> bool:
        """Remove an image by index.

        Args:
            index: Index of image to remove.

        Returns:
            True if image was removed.
        """
        if 0 <= index < len(self._images):
            self._images.pop(index)
            self.image_count = len(self._images)
            self.post_message(self.ImageRemoved(index))
            return True
        return False

    def clear_images(self) -> None:
        """Remove all attached images."""
        self._images.clear()
        self.image_count = 0
        self.post_message(self.ImagesCleared())

    def get_images(self) -> list[ImageData]:
        """Get all attached images.

        Returns:
            List of ImageData objects.
        """
        return list(self._images)

    def action_paste_image(self) -> None:
        """Handle paste action."""
        from ralph_agi.vision.clipboard import get_clipboard_image, has_clipboard_image

        if has_clipboard_image():
            data = get_clipboard_image()
            if data:
                self.add_image(data)
                self.notify("Image pasted from clipboard")
            else:
                self.notify("Failed to get clipboard image", severity="error")
        else:
            self.notify("No image in clipboard", severity="warning")

    def action_screenshot(self) -> None:
        """Handle screenshot action."""
        from ralph_agi.vision.clipboard import capture_screen_region

        data = capture_screen_region()
        if data:
            self.add_image(data)
            self.notify("Screenshot captured")
        else:
            self.notify("Failed to capture screenshot", severity="error")

    def action_remove_selected(self) -> None:
        """Remove the selected image."""
        if self._selected_index is not None:
            self.remove_image(self._selected_index)
            self._selected_index = None


def images_to_claude_content(images: list[ImageData]) -> list[dict]:
    """Convert images to Claude message content format.

    Args:
        images: List of ImageData objects.

    Returns:
        List of content blocks for Claude message.
    """
    from ralph_agi.vision.image import encode_for_claude

    return [encode_for_claude(img) for img in images]
