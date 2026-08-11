"""Tests for file_io module — validates correct UTF-8 buffer handling.

Covers the fix for issue #820: segfault when saving files >64KB
containing UTF-8 multibyte characters.
"""

import os
import tempfile

from file_io import save_file


def _temp_path(tmp_dir, name="test_output.txt"):
    return os.path.join(tmp_dir, name)


def test_save_small_file_with_emoji():
    """Save <64KB file with emoji chars — should succeed."""
    # 63KB of emoji (each emoji is 4 bytes in UTF-8)
    content = "\U0001f600" * (63 * 1024 // 4)
    with tempfile.TemporaryDirectory() as tmp:
        path = _temp_path(tmp)
        save_file(path, content)
        with open(path, "r", encoding="utf-8") as f:
            assert f.read() == content


def test_save_large_file_with_emoji():
    """Save >64KB file with emoji chars — the crash scenario from #820."""
    # 65KB worth of emoji bytes (each emoji is 4 bytes in UTF-8)
    content = "\U0001f600" * (65 * 1024 // 4)
    with tempfile.TemporaryDirectory() as tmp:
        path = _temp_path(tmp)
        save_file(path, content)
        with open(path, "r", encoding="utf-8") as f:
            assert f.read() == content


def test_save_large_file_with_cjk():
    """Save 128KB file with mixed ASCII/CJK — should succeed."""
    # CJK chars are 3 bytes each in UTF-8
    ascii_part = "Hello " * 1000
    cjk_part = "世界" * (128 * 1024 // 6)
    content = ascii_part + cjk_part
    with tempfile.TemporaryDirectory() as tmp:
        path = _temp_path(tmp)
        save_file(path, content)
        with open(path, "r", encoding="utf-8") as f:
            assert f.read() == content


def test_save_large_ascii_file():
    """Save >64KB ASCII-only file — control case, should succeed."""
    content = "A" * (65 * 1024)
    with tempfile.TemporaryDirectory() as tmp:
        path = _temp_path(tmp)
        save_file(path, content)
        with open(path, "r", encoding="utf-8") as f:
            assert f.read() == content


def test_saved_content_integrity():
    """Verify no truncated multibyte sequences in saved output."""
    # Mix of 1-byte, 2-byte, 3-byte, and 4-byte UTF-8 characters
    chars = "Aé世\U0001f600"  # A, e-acute, CJK, emoji
    # Repeat enough to exceed 64KB in byte length
    content = chars * (65 * 1024 // len(chars.encode("utf-8")) + 1)
    with tempfile.TemporaryDirectory() as tmp:
        path = _temp_path(tmp)
        save_file(path, content)
        with open(path, "rb") as f:
            raw = f.read()
        # Decoding should succeed without errors — no truncated sequences
        decoded = raw.decode("utf-8")
        assert decoded == content


def test_save_rejects_non_string():
    """Passing non-string content raises TypeError."""
    with tempfile.TemporaryDirectory() as tmp:
        path = _temp_path(tmp)
        try:
            save_file(path, 12345)
            assert False, "Expected TypeError"
        except TypeError:
            pass


def test_save_empty_file():
    """Saving empty content should create an empty file."""
    with tempfile.TemporaryDirectory() as tmp:
        path = _temp_path(tmp)
        save_file(path, "")
        with open(path, "rb") as f:
            assert f.read() == b""
