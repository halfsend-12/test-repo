"""Tests for the file_saver module.

Covers the fix for issue #28: segfault when saving files >64KB
containing multibyte UTF-8 characters.
"""

import os
import tempfile

from src.file_saver import BUFFER_SIZE, _compute_chunks, save_file


class TestComputeChunks:
    """Unit tests for _compute_chunks."""

    def test_empty(self):
        assert _compute_chunks(b"", BUFFER_SIZE) == []

    def test_single_chunk(self):
        data = b"hello"
        chunks = _compute_chunks(data, BUFFER_SIZE)
        assert chunks == [data]

    def test_exact_boundary(self):
        data = b"x" * BUFFER_SIZE
        chunks = _compute_chunks(data, BUFFER_SIZE)
        assert len(chunks) == 1
        assert chunks[0] == data

    def test_multiple_chunks(self):
        data = b"x" * (BUFFER_SIZE + 1)
        chunks = _compute_chunks(data, BUFFER_SIZE)
        assert len(chunks) == 2
        assert len(chunks[0]) == BUFFER_SIZE
        assert len(chunks[1]) == 1


class TestSaveFile:
    """Integration tests for save_file."""

    def test_small_ascii(self, tmp_path):
        path = str(tmp_path / "small.txt")
        content = "hello world"
        written = save_file(path, content)
        assert written == len(content.encode("utf-8"))
        assert open(path, "rb").read() == content.encode("utf-8")

    def test_large_ascii_over_64kb(self, tmp_path):
        """ASCII content >64KB should save correctly."""
        path = str(tmp_path / "large_ascii.txt")
        content = "A" * (BUFFER_SIZE + 1024)
        written = save_file(path, content)
        assert written == len(content.encode("utf-8"))
        with open(path, "r", encoding="utf-8") as fh:
            assert fh.read() == content

    def test_large_multibyte_over_64kb(self, tmp_path):
        """Multibyte UTF-8 content >64KB — the exact crash scenario
        from issue #28.  Emoji are 4 bytes each in UTF-8, so ~17K
        emoji characters produce ~68KB of encoded data."""
        path = str(tmp_path / "large_emoji.txt")
        emoji = "\U0001F600"  # 😀 — 4 bytes in UTF-8
        count = (BUFFER_SIZE // len(emoji.encode("utf-8"))) + 1024
        content = emoji * count
        byte_length = len(content.encode("utf-8"))
        assert byte_length > BUFFER_SIZE  # precondition

        written = save_file(path, content)
        assert written == byte_length
        with open(path, "r", encoding="utf-8") as fh:
            assert fh.read() == content

    def test_mixed_ascii_and_multibyte_crossing_boundary(self, tmp_path):
        """Mixed content where the 64KB boundary falls inside a
        multibyte sequence."""
        path = str(tmp_path / "mixed.txt")
        # Fill most of the buffer with ASCII, then add emoji to cross
        ascii_part = "A" * (BUFFER_SIZE - 10)
        emoji_part = "\U0001F600" * 100  # 400 bytes of emoji
        content = ascii_part + emoji_part
        byte_length = len(content.encode("utf-8"))
        assert byte_length > BUFFER_SIZE

        written = save_file(path, content)
        assert written == byte_length
        with open(path, "r", encoding="utf-8") as fh:
            assert fh.read() == content

    def test_exactly_64kb_multibyte(self, tmp_path):
        """Edge case: exactly 64KB of multibyte-encoded content."""
        path = str(tmp_path / "exact.txt")
        emoji = "\U0001F600"  # 4 bytes
        count = BUFFER_SIZE // 4  # exactly 64KB when encoded
        content = emoji * count
        assert len(content.encode("utf-8")) == BUFFER_SIZE

        written = save_file(path, content)
        assert written == BUFFER_SIZE
        with open(path, "r", encoding="utf-8") as fh:
            assert fh.read() == content

    def test_cjk_characters_over_64kb(self, tmp_path):
        """CJK characters (3 bytes each in UTF-8) over 64KB."""
        path = str(tmp_path / "cjk.txt")
        char = "\u4e16"  # 世 — 3 bytes in UTF-8
        count = (BUFFER_SIZE // 3) + 1024
        content = char * count
        byte_length = len(content.encode("utf-8"))
        assert byte_length > BUFFER_SIZE

        written = save_file(path, content)
        assert written == byte_length
        with open(path, "r", encoding="utf-8") as fh:
            assert fh.read() == content
