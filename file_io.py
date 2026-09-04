"""File I/O module with correct UTF-8 buffer handling.

This module provides file save functionality that correctly handles
UTF-8 multibyte characters by using byte length (not character count)
for buffer allocation.
"""

import os

# Maximum buffer size in bytes. Files larger than this are written
# in chunks to avoid allocating a single oversized buffer.
MAX_BUFFER_SIZE = 65536  # 64 KB


def save_file(path, content):
    """Save content to a file, handling UTF-8 multibyte characters correctly.

    Uses byte length (len(encoded)) for buffer sizing instead of character
    count (len(content)), which would under-allocate for multibyte UTF-8
    sequences and cause data corruption or crashes for files over 64KB.

    Args:
        path: Filesystem path to write to.
        content: String content to save (may contain multibyte UTF-8 chars).

    Raises:
        OSError: If the file cannot be written.
        TypeError: If content is not a string.
    """
    if not isinstance(content, str):
        raise TypeError("content must be a string")

    encoded = content.encode("utf-8")
    byte_length = len(encoded)

    # Write in chunks when the encoded byte length exceeds the buffer size.
    # The key fix: we measure byte_length (encoded bytes), NOT len(content)
    # (character count). For multibyte UTF-8 characters, len(content) can
    # be much smaller than byte_length, causing buffer overrun when the
    # character count fits in 64KB but the byte length does not.
    dir_name = os.path.dirname(path)
    if dir_name:
        os.makedirs(dir_name, exist_ok=True)

    with open(path, "wb") as f:
        offset = 0
        while offset < byte_length:
            chunk = encoded[offset : offset + MAX_BUFFER_SIZE]
            f.write(chunk)
            offset += len(chunk)
