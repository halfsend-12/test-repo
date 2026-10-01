"""Tests for the file-save buffer fix (issue #1680).

Verifies that files larger than 64 KiB containing UTF-8 multibyte
characters are saved and loaded correctly without data loss or crash.
"""

import os
import tempfile

import pytest

from filesaver import BUFFER_SIZE, load_file, save_file


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _round_trip(content: str) -> str:
    """Save *content* to a temp file and load it back."""
    with tempfile.NamedTemporaryFile(
        delete=False, suffix=".txt"
    ) as tmp:
        path = tmp.name
    try:
        save_file(path, content)
        return load_file(path)
    finally:
        os.unlink(path)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestSaveFileMultibyteAbove64KB:
    """Core regression tests from the triage proposed test cases."""

    def test_emoji_text_above_64kb(self):
        """~70 KiB of emoji text round-trips correctly."""
        # Each emoji is 4 bytes in UTF-8; we need > 64 KiB of bytes.
        emoji = "\U0001f389\U0001f680\U0001f30d"  # 🎉🚀🌍
        repeat_count = (70 * 1024) // (len(emoji) * 4) + 1
        content = emoji * repeat_count
        assert len(content.encode("utf-8")) > BUFFER_SIZE
        result = _round_trip(content)
        assert result == content

    def test_cjk_text_above_64kb(self):
        """~70 KiB of CJK characters round-trips correctly."""
        # CJK characters are 3 bytes each in UTF-8.
        cjk = "世界你好"  # 世界你好
        repeat_count = (70 * 1024) // (len(cjk) * 3) + 1
        content = cjk * repeat_count
        assert len(content.encode("utf-8")) > BUFFER_SIZE
        result = _round_trip(content)
        assert result == content

    def test_mixed_ascii_multibyte_above_64kb(self):
        """~70 KiB of mixed ASCII and multibyte round-trips correctly."""
        mixed = "Hello \U0001f30d world 世界 "
        repeat_count = (70 * 1024) // len(mixed.encode("utf-8")) + 1
        content = mixed * repeat_count
        assert len(content.encode("utf-8")) > BUFFER_SIZE
        result = _round_trip(content)
        assert result == content

    def test_boundary_64kb_last_char_4byte_emoji(self):
        """Exactly 64 KiB where the last character is a 4-byte emoji."""
        # Fill to just under 64 KiB with ASCII, then append a 4-byte emoji.
        filler = "A" * (BUFFER_SIZE - 4)
        content = filler + "\U0001f600"  # 😀
        assert len(content.encode("utf-8")) == BUFFER_SIZE
        result = _round_trip(content)
        assert result == content


class TestSaveFileBasicBehavior:
    """Sanity checks for basic save/load functionality."""

    def test_ascii_under_64kb(self):
        """Small ASCII file saves correctly (baseline)."""
        content = "Hello, world!\n" * 100
        assert len(content.encode("utf-8")) < BUFFER_SIZE
        result = _round_trip(content)
        assert result == content

    def test_ascii_above_64kb(self):
        """Large ASCII-only file saves correctly."""
        content = "A" * (BUFFER_SIZE + 1024)
        result = _round_trip(content)
        assert result == content

    def test_empty_file(self):
        """Empty content saves and loads as empty string."""
        result = _round_trip("")
        assert result == ""

    def test_exact_buffer_boundary(self):
        """Content whose byte length is exactly BUFFER_SIZE."""
        content = "B" * BUFFER_SIZE
        result = _round_trip(content)
        assert result == content
