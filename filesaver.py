"""File save module with correct UTF-8 buffer allocation.

Prior to this fix (v2.3.1 regression), the write buffer was allocated
based on the number of *characters* (``len(text)``) rather than the
number of *bytes* (``len(text.encode('utf-8'))``).  For ASCII-only
content the two values are identical, so the bug only manifested when
multibyte characters pushed the byte count past the 64 KiB buffer
boundary while the character count remained below it.
"""

BUFFER_SIZE = 65536  # 64 KiB


def save_file(path: str, content: str) -> None:
    """Write *content* to *path* using chunked I/O.

    The content is encoded to UTF-8 and written in chunks of at most
    ``BUFFER_SIZE`` bytes.  The chunking previously used character
    offsets, which caused a buffer overrun (segfault) when multibyte
    characters made the encoded chunk larger than the buffer.

    Args:
        path: Destination file path.
        content: The text to save.

    Raises:
        OSError: If the file cannot be opened or written.
    """
    encoded = content.encode("utf-8")
    with open(path, "wb") as fh:
        offset = 0
        while offset < len(encoded):
            chunk = encoded[offset : offset + BUFFER_SIZE]
            fh.write(chunk)
            offset += len(chunk)


def load_file(path: str) -> str:
    """Read a UTF-8 encoded file and return its content as a string.

    Args:
        path: Source file path.

    Returns:
        The decoded text content.

    Raises:
        OSError: If the file cannot be opened or read.
    """
    with open(path, "rb") as fh:
        return fh.read().decode("utf-8")
