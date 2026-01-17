"""Tests for FileSystemTools."""

from __future__ import annotations

import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import pytest

from ralph_agi.tools.filesystem import (
    BinaryFileError,
    FileInfo,
    FileSystemError,
    FileSystemTools,
    FileTooLargeError,
    PathSecurityError,
)


class TestFileInfo:
    """Tests for FileInfo dataclass."""

    def test_from_path_file(self, tmp_path: Path) -> None:
        """Test creating FileInfo from a file."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("hello")

        info = FileInfo.from_path(test_file)

        assert info.name == "test.txt"
        assert info.is_file is True
        assert info.is_directory is False
        assert info.size == 5
        assert info.extension == "txt"
        assert isinstance(info.modified, datetime)

    def test_from_path_directory(self, tmp_path: Path) -> None:
        """Test creating FileInfo from a directory."""
        test_dir = tmp_path / "subdir"
        test_dir.mkdir()

        info = FileInfo.from_path(test_dir)

        assert info.name == "subdir"
        assert info.is_file is False
        assert info.is_directory is True
        assert info.size == 0
        assert info.extension is None

    def test_from_path_no_extension(self, tmp_path: Path) -> None:
        """Test file without extension."""
        test_file = tmp_path / "Makefile"
        test_file.write_text("all:")

        info = FileInfo.from_path(test_file)

        assert info.name == "Makefile"
        assert info.extension is None

    def test_from_path_not_found(self, tmp_path: Path) -> None:
        """Test FileInfo from non-existent path."""
        with pytest.raises(FileNotFoundError):
            FileInfo.from_path(tmp_path / "nonexistent")

    def test_to_dict(self, tmp_path: Path) -> None:
        """Test converting FileInfo to dictionary."""
        test_file = tmp_path / "test.py"
        test_file.write_text("# code")

        info = FileInfo.from_path(test_file)
        d = info.to_dict()

        assert d["name"] == "test.py"
        assert d["is_file"] is True
        assert d["extension"] == "py"
        assert "modified" in d


class TestFileSystemToolsInit:
    """Tests for FileSystemTools initialization."""

    def test_default_root(self) -> None:
        """Test default root is current directory."""
        fs = FileSystemTools()
        assert Path.cwd().resolve() in fs.allowed_roots

    def test_custom_roots(self, tmp_path: Path) -> None:
        """Test custom allowed roots."""
        root1 = tmp_path / "root1"
        root2 = tmp_path / "root2"
        root1.mkdir()
        root2.mkdir()

        fs = FileSystemTools(allowed_roots=[root1, root2])

        assert len(fs.allowed_roots) == 2
        assert root1.resolve() in fs.allowed_roots
        assert root2.resolve() in fs.allowed_roots

    def test_max_file_size(self, tmp_path: Path) -> None:
        """Test custom max file size."""
        fs = FileSystemTools(
            allowed_roots=[tmp_path],
            max_file_size=100,
        )

        # Create large file
        large_file = tmp_path / "large.txt"
        large_file.write_text("x" * 200)

        with pytest.raises(FileTooLargeError) as exc:
            fs.read_file(large_file)

        assert exc.value.size == 200
        assert exc.value.limit == 100


class TestPathValidation:
    """Tests for path validation and security."""

    def test_valid_path_within_root(self, tmp_path: Path) -> None:
        """Test valid path within allowed root."""
        fs = FileSystemTools(allowed_roots=[tmp_path])
        test_file = tmp_path / "test.txt"
        test_file.write_text("content")

        content = fs.read_file(test_file)
        assert content == "content"

    def test_path_traversal_blocked(self, tmp_path: Path) -> None:
        """Test path traversal is blocked."""
        sandbox = tmp_path / "sandbox"
        sandbox.mkdir()

        # Create file outside sandbox
        outside = tmp_path / "secret.txt"
        outside.write_text("secret")

        fs = FileSystemTools(allowed_roots=[sandbox])

        # Try to escape with ..
        with pytest.raises(PathSecurityError) as exc:
            fs.read_file(sandbox / ".." / "secret.txt")

        assert "outside allowed roots" in str(exc.value)

    def test_absolute_path_outside_root(self, tmp_path: Path) -> None:
        """Test absolute path outside root is blocked."""
        sandbox = tmp_path / "sandbox"
        sandbox.mkdir()

        outside = tmp_path / "outside.txt"
        outside.write_text("data")

        fs = FileSystemTools(allowed_roots=[sandbox])

        with pytest.raises(PathSecurityError):
            fs.read_file(outside)

    def test_relative_path_resolved(self, tmp_path: Path) -> None:
        """Test relative paths are resolved correctly."""
        fs = FileSystemTools(allowed_roots=[tmp_path])

        subdir = tmp_path / "sub"
        subdir.mkdir()
        test_file = subdir / "test.txt"
        test_file.write_text("hello")

        # Read with relative path from cwd
        content = fs.read_file(test_file)
        assert content == "hello"

    @pytest.mark.skipif(os.name == "nt", reason="Symlinks need admin on Windows")
    def test_symlink_target_validated(self, tmp_path: Path) -> None:
        """Test symlink targets are validated."""
        sandbox = tmp_path / "sandbox"
        sandbox.mkdir()

        outside = tmp_path / "outside.txt"
        outside.write_text("secret")

        # Create symlink inside sandbox pointing outside
        link = sandbox / "link.txt"
        link.symlink_to(outside)

        fs = FileSystemTools(allowed_roots=[sandbox])

        with pytest.raises(PathSecurityError):
            fs.read_file(link)


class TestReadFile:
    """Tests for read_file operation."""

    def test_read_utf8(self, tmp_path: Path) -> None:
        """Test reading UTF-8 file."""
        fs = FileSystemTools(allowed_roots=[tmp_path])

        test_file = tmp_path / "utf8.txt"
        test_file.write_text("Hello, 世界! 🌍", encoding="utf-8")

        content = fs.read_file(test_file)
        assert "Hello" in content
        assert "世界" in content

    def test_read_latin1(self, tmp_path: Path) -> None:
        """Test reading Latin-1 encoded file."""
        fs = FileSystemTools(allowed_roots=[tmp_path])

        test_file = tmp_path / "latin1.txt"
        test_file.write_bytes(b"caf\xe9")

        content = fs.read_file(test_file)
        assert "caf" in content

    def test_read_empty_file(self, tmp_path: Path) -> None:
        """Test reading empty file."""
        fs = FileSystemTools(allowed_roots=[tmp_path])

        test_file = tmp_path / "empty.txt"
        test_file.write_text("")

        content = fs.read_file(test_file)
        assert content == ""

    def test_read_not_found(self, tmp_path: Path) -> None:
        """Test reading non-existent file."""
        fs = FileSystemTools(allowed_roots=[tmp_path])

        with pytest.raises(FileNotFoundError):
            fs.read_file(tmp_path / "missing.txt")

    def test_read_directory_fails(self, tmp_path: Path) -> None:
        """Test reading a directory fails."""
        fs = FileSystemTools(allowed_roots=[tmp_path])

        subdir = tmp_path / "subdir"
        subdir.mkdir()

        with pytest.raises(FileSystemError) as exc:
            fs.read_file(subdir)

        assert "Not a file" in str(exc.value)

    def test_read_binary_detection(self, tmp_path: Path) -> None:
        """Test binary file detection."""
        fs = FileSystemTools(allowed_roots=[tmp_path])

        binary_file = tmp_path / "binary.bin"
        binary_file.write_bytes(b"\x00\x01\x02\x03")

        with pytest.raises(BinaryFileError):
            fs.read_file(binary_file)

    def test_read_file_too_large(self, tmp_path: Path) -> None:
        """Test size limit enforcement."""
        fs = FileSystemTools(allowed_roots=[tmp_path], max_file_size=10)

        large_file = tmp_path / "large.txt"
        large_file.write_text("x" * 100)

        with pytest.raises(FileTooLargeError) as exc:
            fs.read_file(large_file)

        assert exc.value.size == 100
        assert exc.value.limit == 10


class TestReadFileBytes:
    """Tests for read_file_bytes operation."""

    def test_read_bytes(self, tmp_path: Path) -> None:
        """Test reading file as bytes."""
        fs = FileSystemTools(allowed_roots=[tmp_path])

        test_file = tmp_path / "data.bin"
        test_file.write_bytes(b"\x00\x01\x02\x03")

        content = fs.read_file_bytes(test_file)
        assert content == b"\x00\x01\x02\x03"

    def test_read_bytes_not_found(self, tmp_path: Path) -> None:
        """Test reading non-existent file as bytes."""
        fs = FileSystemTools(allowed_roots=[tmp_path])

        with pytest.raises(FileNotFoundError):
            fs.read_file_bytes(tmp_path / "missing.bin")


class TestWriteFile:
    """Tests for write_file operation."""

    def test_write_new_file(self, tmp_path: Path) -> None:
        """Test writing a new file."""
        fs = FileSystemTools(allowed_roots=[tmp_path])

        result = fs.write_file(tmp_path / "new.txt", "hello world")

        assert result.exists()
        assert result.read_text() == "hello world"

    def test_write_overwrites(self, tmp_path: Path) -> None:
        """Test overwriting existing file."""
        fs = FileSystemTools(allowed_roots=[tmp_path])

        test_file = tmp_path / "existing.txt"
        test_file.write_text("old content")

        fs.write_file(test_file, "new content")

        assert test_file.read_text() == "new content"

    def test_write_creates_dirs(self, tmp_path: Path) -> None:
        """Test parent directory creation."""
        fs = FileSystemTools(allowed_roots=[tmp_path])

        deep_file = tmp_path / "a" / "b" / "c" / "deep.txt"
        result = fs.write_file(deep_file, "deep content")

        assert result.exists()
        assert result.read_text() == "deep content"

    def test_write_no_create_dirs(self, tmp_path: Path) -> None:
        """Test write without creating directories."""
        fs = FileSystemTools(allowed_roots=[tmp_path])

        with pytest.raises(FileNotFoundError):
            fs.write_file(
                tmp_path / "missing" / "file.txt",
                "content",
                create_dirs=False,
            )

    def test_write_atomic(self, tmp_path: Path) -> None:
        """Test atomic write behavior."""
        fs = FileSystemTools(allowed_roots=[tmp_path])

        test_file = tmp_path / "atomic.txt"
        test_file.write_text("original")

        # Write new content
        fs.write_file(test_file, "new")

        # Verify no temp files left
        assert len(list(tmp_path.glob(".atomic.*"))) == 0
        assert test_file.read_text() == "new"

    def test_write_utf8_content(self, tmp_path: Path) -> None:
        """Test writing UTF-8 content."""
        fs = FileSystemTools(allowed_roots=[tmp_path])

        content = "Hello, 世界! 🌍"
        result = fs.write_file(tmp_path / "utf8.txt", content)

        assert result.read_text(encoding="utf-8") == content

    def test_write_outside_root_blocked(self, tmp_path: Path) -> None:
        """Test write outside root is blocked."""
        sandbox = tmp_path / "sandbox"
        sandbox.mkdir()

        fs = FileSystemTools(allowed_roots=[sandbox])

        with pytest.raises(PathSecurityError):
            fs.write_file(tmp_path / "outside.txt", "blocked")

    def test_write_to_directory_blocked(self, tmp_path: Path) -> None:
        """Test write to directory path is blocked with clear error."""
        fs = FileSystemTools(allowed_roots=[tmp_path])

        # Create a directory
        subdir = tmp_path / "mydir"
        subdir.mkdir()

        # Attempting to write to a directory should fail clearly
        with pytest.raises(FileSystemError) as exc_info:
            fs.write_file(subdir, "content")

        assert "is a directory" in str(exc_info.value).lower()
        assert "file path" in str(exc_info.value).lower()


class TestWriteFileBytes:
    """Tests for write_file_bytes operation."""

    def test_write_bytes(self, tmp_path: Path) -> None:
        """Test writing bytes to file."""
        fs = FileSystemTools(allowed_roots=[tmp_path])

        result = fs.write_file_bytes(tmp_path / "data.bin", b"\x00\x01\x02")

        assert result.read_bytes() == b"\x00\x01\x02"


class TestGlobFiles:
    """Tests for glob_files operation."""

    def test_glob_py_files(self, tmp_path: Path) -> None:
        """Test globbing Python files."""
        fs = FileSystemTools(allowed_roots=[tmp_path])

        # Create test structure
        (tmp_path / "main.py").write_text("# main")
        (tmp_path / "test.py").write_text("# test")
        (tmp_path / "readme.md").write_text("# readme")

        result = fs.glob_files("*.py")

        assert len(result) == 2
        names = {p.name for p in result}
        assert "main.py" in names
        assert "test.py" in names

    def test_glob_recursive(self, tmp_path: Path) -> None:
        """Test recursive globbing."""
        fs = FileSystemTools(allowed_roots=[tmp_path])

        # Create nested structure
        (tmp_path / "root.py").write_text("")
        subdir = tmp_path / "sub"
        subdir.mkdir()
        (subdir / "nested.py").write_text("")
        deep = subdir / "deep"
        deep.mkdir()
        (deep / "deeper.py").write_text("")

        result = fs.glob_files("**/*.py")

        assert len(result) == 3

    def test_glob_custom_root(self, tmp_path: Path) -> None:
        """Test globbing with custom root."""
        fs = FileSystemTools(allowed_roots=[tmp_path])

        subdir = tmp_path / "src"
        subdir.mkdir()
        (subdir / "code.py").write_text("")
        (tmp_path / "other.py").write_text("")

        result = fs.glob_files("*.py", root=subdir)

        assert len(result) == 1
        assert result[0].name == "code.py"

    def test_glob_no_matches(self, tmp_path: Path) -> None:
        """Test glob with no matches."""
        fs = FileSystemTools(allowed_roots=[tmp_path])

        (tmp_path / "file.txt").write_text("")

        result = fs.glob_files("*.py")

        assert result == []

    def test_glob_empty_dir(self, tmp_path: Path) -> None:
        """Test globbing empty directory."""
        fs = FileSystemTools(allowed_roots=[tmp_path])

        result = fs.glob_files("*")

        assert result == []


class TestListDirectory:
    """Tests for list_directory operation."""

    def test_list_directory(self, tmp_path: Path) -> None:
        """Test listing directory contents."""
        fs = FileSystemTools(allowed_roots=[tmp_path])

        (tmp_path / "file1.txt").write_text("1")
        (tmp_path / "file2.txt").write_text("2")
        subdir = tmp_path / "subdir"
        subdir.mkdir()

        result = fs.list_directory(tmp_path)

        assert len(result) == 3
        names = [e.name for e in result]
        assert "file1.txt" in names
        assert "file2.txt" in names
        assert "subdir" in names

    def test_list_directory_sorted(self, tmp_path: Path) -> None:
        """Test directory listing is sorted."""
        fs = FileSystemTools(allowed_roots=[tmp_path])

        (tmp_path / "c.txt").write_text("")
        (tmp_path / "a.txt").write_text("")
        (tmp_path / "b.txt").write_text("")

        result = fs.list_directory(tmp_path)

        names = [e.name for e in result]
        assert names == ["a.txt", "b.txt", "c.txt"]

    def test_list_directory_not_found(self, tmp_path: Path) -> None:
        """Test listing non-existent directory."""
        fs = FileSystemTools(allowed_roots=[tmp_path])

        with pytest.raises(FileNotFoundError):
            fs.list_directory(tmp_path / "missing")

    def test_list_directory_on_file(self, tmp_path: Path) -> None:
        """Test listing a file fails."""
        fs = FileSystemTools(allowed_roots=[tmp_path])

        test_file = tmp_path / "file.txt"
        test_file.write_text("")

        with pytest.raises(FileSystemError) as exc:
            fs.list_directory(test_file)

        assert "Not a directory" in str(exc.value)

    def test_list_directory_empty(self, tmp_path: Path) -> None:
        """Test listing empty directory."""
        fs = FileSystemTools(allowed_roots=[tmp_path])

        result = fs.list_directory(tmp_path)

        assert result == []


class TestFileExists:
    """Tests for file_exists operation."""

    def test_exists_file(self, tmp_path: Path) -> None:
        """Test file exists."""
        fs = FileSystemTools(allowed_roots=[tmp_path])

        test_file = tmp_path / "exists.txt"
        test_file.write_text("")

        assert fs.file_exists(test_file) is True

    def test_exists_directory(self, tmp_path: Path) -> None:
        """Test directory exists."""
        fs = FileSystemTools(allowed_roots=[tmp_path])

        subdir = tmp_path / "subdir"
        subdir.mkdir()

        assert fs.file_exists(subdir) is True

    def test_not_exists(self, tmp_path: Path) -> None:
        """Test file does not exist."""
        fs = FileSystemTools(allowed_roots=[tmp_path])

        assert fs.file_exists(tmp_path / "missing.txt") is False


class TestGetFileInfo:
    """Tests for get_file_info operation."""

    def test_get_file_info(self, tmp_path: Path) -> None:
        """Test getting file info."""
        fs = FileSystemTools(allowed_roots=[tmp_path])

        test_file = tmp_path / "test.py"
        test_file.write_text("# code")

        info = fs.get_file_info(test_file)

        assert info.name == "test.py"
        assert info.is_file is True
        assert info.extension == "py"

    def test_get_file_info_not_found(self, tmp_path: Path) -> None:
        """Test getting info for non-existent file."""
        fs = FileSystemTools(allowed_roots=[tmp_path])

        with pytest.raises(FileNotFoundError):
            fs.get_file_info(tmp_path / "missing.txt")


class TestDeleteFile:
    """Tests for delete_file operation."""

    def test_delete_file(self, tmp_path: Path) -> None:
        """Test deleting a file."""
        fs = FileSystemTools(allowed_roots=[tmp_path])

        test_file = tmp_path / "delete_me.txt"
        test_file.write_text("bye")

        result = fs.delete_file(test_file)

        assert result is True
        assert not test_file.exists()

    def test_delete_nonexistent(self, tmp_path: Path) -> None:
        """Test deleting non-existent file."""
        fs = FileSystemTools(allowed_roots=[tmp_path])

        result = fs.delete_file(tmp_path / "missing.txt")

        assert result is False

    def test_delete_directory_fails(self, tmp_path: Path) -> None:
        """Test deleting directory fails."""
        fs = FileSystemTools(allowed_roots=[tmp_path])

        subdir = tmp_path / "subdir"
        subdir.mkdir()

        with pytest.raises(FileSystemError) as exc:
            fs.delete_file(subdir)

        assert "Cannot delete directory" in str(exc.value)


class TestCreateDirectory:
    """Tests for create_directory operation."""

    def test_create_directory(self, tmp_path: Path) -> None:
        """Test creating a directory."""
        fs = FileSystemTools(allowed_roots=[tmp_path])

        new_dir = tmp_path / "new_dir"
        result = fs.create_directory(new_dir)

        assert result.exists()
        assert result.is_dir()

    def test_create_nested_directory(self, tmp_path: Path) -> None:
        """Test creating nested directories."""
        fs = FileSystemTools(allowed_roots=[tmp_path])

        deep_dir = tmp_path / "a" / "b" / "c"
        result = fs.create_directory(deep_dir)

        assert result.exists()
        assert result.is_dir()

    def test_create_existing_directory(self, tmp_path: Path) -> None:
        """Test creating existing directory with exist_ok=True."""
        fs = FileSystemTools(allowed_roots=[tmp_path])

        existing = tmp_path / "existing"
        existing.mkdir()

        result = fs.create_directory(existing, exist_ok=True)

        assert result.exists()

    def test_create_existing_directory_fail(self, tmp_path: Path) -> None:
        """Test creating existing directory with exist_ok=False."""
        fs = FileSystemTools(allowed_roots=[tmp_path])

        existing = tmp_path / "existing"
        existing.mkdir()

        with pytest.raises(FileExistsError):
            fs.create_directory(existing, exist_ok=False)


class TestCopyFile:
    """Tests for copy_file operation."""

    def test_copy_file(self, tmp_path: Path) -> None:
        """Test copying a file."""
        fs = FileSystemTools(allowed_roots=[tmp_path])

        src = tmp_path / "source.txt"
        src.write_text("content")
        dst = tmp_path / "dest.txt"

        result = fs.copy_file(src, dst)

        assert result.exists()
        assert result.read_text() == "content"
        assert src.exists()  # Source still exists

    def test_copy_file_not_found(self, tmp_path: Path) -> None:
        """Test copying non-existent file."""
        fs = FileSystemTools(allowed_roots=[tmp_path])

        with pytest.raises(FileNotFoundError):
            fs.copy_file(tmp_path / "missing.txt", tmp_path / "dest.txt")


class TestMoveFile:
    """Tests for move_file operation."""

    def test_move_file(self, tmp_path: Path) -> None:
        """Test moving a file."""
        fs = FileSystemTools(allowed_roots=[tmp_path])

        src = tmp_path / "source.txt"
        src.write_text("content")
        dst = tmp_path / "dest.txt"

        result = fs.move_file(src, dst)

        assert result.exists()
        assert result.read_text() == "content"
        assert not src.exists()  # Source removed

    def test_move_file_not_found(self, tmp_path: Path) -> None:
        """Test moving non-existent file."""
        fs = FileSystemTools(allowed_roots=[tmp_path])

        with pytest.raises(FileNotFoundError):
            fs.move_file(tmp_path / "missing.txt", tmp_path / "dest.txt")


class TestWalk:
    """Tests for walk operation."""

    def test_walk_all_files(self, tmp_path: Path) -> None:
        """Test walking all files."""
        fs = FileSystemTools(allowed_roots=[tmp_path])

        # Create structure
        (tmp_path / "root.txt").write_text("")
        subdir = tmp_path / "sub"
        subdir.mkdir()
        (subdir / "nested.txt").write_text("")

        result = list(fs.walk())

        assert len(result) == 2
        names = {f.name for f in result}
        assert "root.txt" in names
        assert "nested.txt" in names

    def test_walk_with_pattern(self, tmp_path: Path) -> None:
        """Test walking with filename pattern."""
        fs = FileSystemTools(allowed_roots=[tmp_path])

        (tmp_path / "code.py").write_text("")
        (tmp_path / "readme.md").write_text("")

        result = list(fs.walk(pattern="*.py"))

        assert len(result) == 1
        assert result[0].name == "code.py"

    def test_walk_custom_root(self, tmp_path: Path) -> None:
        """Test walking from custom root."""
        fs = FileSystemTools(allowed_roots=[tmp_path])

        subdir = tmp_path / "src"
        subdir.mkdir()
        (subdir / "code.py").write_text("")
        (tmp_path / "other.txt").write_text("")

        result = list(fs.walk(path=subdir))

        assert len(result) == 1
        assert result[0].name == "code.py"


class TestEditFile:
    """Tests for edit_file method."""

    def test_edit_file_simple_replace(self, tmp_path: Path) -> None:
        """Test simple content replacement."""
        fs = FileSystemTools(allowed_roots=[tmp_path])
        test_file = tmp_path / "test.py"
        test_file.write_text("def hello():\n    return 'hello'\n")

        path, count = fs.edit_file(test_file, "return 'hello'", "return 'world'")

        assert count == 1
        assert test_file.read_text() == "def hello():\n    return 'world'\n"

    def test_edit_file_content_not_found(self, tmp_path: Path) -> None:
        """Test error when old_content not found."""
        fs = FileSystemTools(allowed_roots=[tmp_path])
        test_file = tmp_path / "test.py"
        test_file.write_text("def hello():\n    pass\n")

        with pytest.raises(ValueError, match="Content to replace not found"):
            fs.edit_file(test_file, "nonexistent", "new")

    def test_edit_file_blocks_destructive(self, tmp_path: Path) -> None:
        """Test that massive shrinkage is blocked."""
        fs = FileSystemTools(allowed_roots=[tmp_path])
        test_file = tmp_path / "test.py"
        # Create a file with 50 lines
        content = "\n".join([f"line {i}" for i in range(50)])
        test_file.write_text(content)

        # Try to replace everything with just 2 lines
        with pytest.raises(ValueError, match="looks destructive"):
            fs.edit_file(test_file, content, "just\ntwo")

    def test_edit_file_preserves_surrounding(self, tmp_path: Path) -> None:
        """Test that surrounding content is preserved."""
        fs = FileSystemTools(allowed_roots=[tmp_path])
        test_file = tmp_path / "test.py"
        original = "# Header\ndef old():\n    pass\n# Footer\n"
        test_file.write_text(original)

        fs.edit_file(test_file, "def old():\n    pass", "def new():\n    return 42")

        result = test_file.read_text()
        assert "# Header" in result
        assert "# Footer" in result
        assert "def new():" in result
        assert "def old():" not in result


class TestInsertInFile:
    """Tests for insert_in_file method."""

    def test_insert_after(self, tmp_path: Path) -> None:
        """Test inserting after a line."""
        fs = FileSystemTools(allowed_roots=[tmp_path])
        test_file = tmp_path / "test.py"
        test_file.write_text("import os\n\ndef main():\n    pass\n")

        fs.insert_in_file(test_file, "import sys", after="import os")

        result = test_file.read_text()
        lines = result.split('\n')
        assert lines[0] == "import os"
        assert lines[1] == "import sys"

    def test_insert_before(self, tmp_path: Path) -> None:
        """Test inserting before a line."""
        fs = FileSystemTools(allowed_roots=[tmp_path])
        test_file = tmp_path / "test.py"
        test_file.write_text("def main():\n    pass\n")

        fs.insert_in_file(test_file, "# Main function", before="def main():")

        result = test_file.read_text()
        assert result.startswith("# Main function\ndef main():")

    def test_insert_at_line(self, tmp_path: Path) -> None:
        """Test inserting at specific line number."""
        fs = FileSystemTools(allowed_roots=[tmp_path])
        test_file = tmp_path / "test.py"
        test_file.write_text("line1\nline2\nline3\n")

        fs.insert_in_file(test_file, "inserted", at_line=2)

        lines = test_file.read_text().split('\n')
        assert lines[1] == "inserted"
        assert lines[2] == "line2"


class TestAppendToFile:
    """Tests for append_to_file method."""

    def test_append_to_existing(self, tmp_path: Path) -> None:
        """Test appending to existing file."""
        fs = FileSystemTools(allowed_roots=[tmp_path])
        test_file = tmp_path / "test.py"
        test_file.write_text("# Original\n")

        fs.append_to_file(test_file, "# Appended\n")

        assert test_file.read_text() == "# Original\n# Appended\n"

    def test_append_creates_file(self, tmp_path: Path) -> None:
        """Test append creates file if doesn't exist."""
        fs = FileSystemTools(allowed_roots=[tmp_path])
        test_file = tmp_path / "new.py"

        fs.append_to_file(test_file, "# New file\n")

        assert test_file.exists()
        assert test_file.read_text() == "# New file\n"

    def test_append_adds_newline(self, tmp_path: Path) -> None:
        """Test append adds newline if missing."""
        fs = FileSystemTools(allowed_roots=[tmp_path])
        test_file = tmp_path / "test.py"
        test_file.write_text("no newline at end")

        fs.append_to_file(test_file, "appended")

        result = test_file.read_text()
        assert result == "no newline at end\nappended"
