"""Tests for file_saver module.

Verifies correct handling of UTF-8 multibyte characters at and around
the 64KB buffer boundary, as reported in issue #1698.
"""

import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from file_saver import BUFFER_SIZE, calculate_buffer_size, save_file


def test_save_file_under_64kb_with_emoji():
    """File just under 64KB with emoji content saves successfully."""
    # Each emoji is 4 bytes in UTF-8; fill to just under 64KB
    char_count = (BUFFER_SIZE // 4) - 10
    content = "\U0001f600" * char_count  # grinning face emoji
    byte_len = len(content.encode("utf-8"))
    assert byte_len < BUFFER_SIZE

    with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as tmp:
        path = tmp.name
    try:
        save_file(path, content)
        with open(path, "rb") as f:
            saved = f.read()
        assert saved == content.encode("utf-8")
    finally:
        os.unlink(path)


def test_save_file_over_64kb_with_emoji():
    """File over 64KB with emoji content saves successfully (#1698)."""
    # Each emoji is 4 bytes in UTF-8; create content well over 64KB
    char_count = (BUFFER_SIZE // 4) + 5000  # ~70KB of emoji
    content = "\U0001f600" * char_count
    byte_len = len(content.encode("utf-8"))
    assert byte_len > BUFFER_SIZE

    with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as tmp:
        path = tmp.name
    try:
        save_file(path, content)
        with open(path, "rb") as f:
            saved = f.read()
        assert saved == content.encode("utf-8")
    finally:
        os.unlink(path)


def test_save_file_over_64kb_with_cjk():
    """File over 64KB with CJK characters saves successfully (#1698)."""
    # CJK characters are 3 bytes in UTF-8
    char_count = (BUFFER_SIZE // 3) + 5000
    content = "世" * char_count  # 世
    byte_len = len(content.encode("utf-8"))
    assert byte_len > BUFFER_SIZE

    with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as tmp:
        path = tmp.name
    try:
        save_file(path, content)
        with open(path, "rb") as f:
            saved = f.read()
        assert saved == content.encode("utf-8")
    finally:
        os.unlink(path)


def test_save_file_over_64kb_mixed_ascii_and_multibyte():
    """File over 64KB with mixed ASCII + CJK saves successfully (#1698)."""
    # Mix of ASCII (1 byte) and CJK (3 bytes)
    unit = "hello世界"  # "hello世界" = 5 + 6 = 11 bytes
    repeat_count = (BUFFER_SIZE // len(unit.encode("utf-8"))) + 1000
    content = unit * repeat_count
    byte_len = len(content.encode("utf-8"))
    assert byte_len > BUFFER_SIZE

    with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as tmp:
        path = tmp.name
    try:
        save_file(path, content)
        with open(path, "rb") as f:
            saved = f.read()
        assert saved == content.encode("utf-8")
    finally:
        os.unlink(path)


def test_round_trip_preserves_content():
    """Saved content matches original exactly after round-trip."""
    content = "Hello \U0001f600 World 世界 \U0001f389" * 10000
    byte_len = len(content.encode("utf-8"))
    assert byte_len > BUFFER_SIZE

    with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as tmp:
        path = tmp.name
    try:
        save_file(path, content)
        with open(path, "r", encoding="utf-8") as f:
            loaded = f.read()
        assert loaded == content
    finally:
        os.unlink(path)


def test_calculate_buffer_size_multibyte():
    """calculate_buffer_size returns byte length, not character count."""
    # 10 emoji characters = 10 chars but 40 bytes in UTF-8
    content = "\U0001f600" * 10
    assert len(content) == 10
    assert calculate_buffer_size(content) == 40


def test_calculate_buffer_size_ascii():
    """calculate_buffer_size matches len() for pure ASCII."""
    content = "a" * 100
    assert calculate_buffer_size(content) == len(content)


def test_save_file_over_64kb_ascii():
    """Large ASCII-only file saves successfully (regression check)."""
    content = "a" * (BUFFER_SIZE + 10000)

    with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as tmp:
        path = tmp.name
    try:
        save_file(path, content)
        with open(path, "r", encoding="utf-8") as f:
            loaded = f.read()
        assert loaded == content
    finally:
        os.unlink(path)


def test_save_file_rejects_non_string():
    """save_file raises TypeError for non-string content."""
    with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as tmp:
        path = tmp.name
    try:
        raised = False
        try:
            save_file(path, b"bytes content")
        except TypeError:
            raised = True
        assert raised, "Expected TypeError for bytes content"
    finally:
        os.unlink(path)


if __name__ == "__main__":
    tests = [
        test_save_file_under_64kb_with_emoji,
        test_save_file_over_64kb_with_emoji,
        test_save_file_over_64kb_with_cjk,
        test_save_file_over_64kb_mixed_ascii_and_multibyte,
        test_round_trip_preserves_content,
        test_calculate_buffer_size_multibyte,
        test_calculate_buffer_size_ascii,
        test_save_file_over_64kb_ascii,
        test_save_file_rejects_non_string,
    ]
    failed = 0
    for test in tests:
        try:
            test()
            print(f"PASS: {test.__name__}")
        except Exception as e:
            print(f"FAIL: {test.__name__}: {e}")
            failed += 1
    if failed:
        print(f"\n{failed} test(s) failed")
        sys.exit(1)
    else:
        print(f"\nAll {len(tests)} tests passed")
