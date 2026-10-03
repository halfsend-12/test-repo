"""File saving module with proper UTF-8 buffer handling.

Allocates write buffers based on byte length rather than character count
to prevent buffer overflows when saving files containing multibyte
UTF-8 characters (emoji, CJK, etc.) that exceed 64KB.
"""

import os

# Buffer size constant in bytes
BUFFER_SIZE = 65536  # 64KB


def save_file(filepath, content):
    """Save content to a file using a byte-length-aware buffer.

    Args:
        filepath: Path to the output file.
        content: String content to write.

    Raises:
        OSError: If the file cannot be written.
        TypeError: If content is not a string.
    """
    if not isinstance(content, str):
        raise TypeError("content must be a string")

    encoded = content.encode("utf-8")
    byte_length = len(encoded)

    with open(filepath, "wb") as f:
        offset = 0
        while offset < byte_length:
            chunk = encoded[offset : offset + BUFFER_SIZE]
            f.write(chunk)
            offset += len(chunk)


def calculate_buffer_size(content):
    """Return the byte length needed to store content as UTF-8.

    This replaces the previous implementation that returned len(content)
    (character count), which caused buffer overflows for multibyte
    characters when the byte length exceeded 64KB.

    Args:
        content: String content to measure.

    Returns:
        Byte length of the UTF-8 encoded content.
    """
    return len(content.encode("utf-8"))
