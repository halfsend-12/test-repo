"""File saving module with chunked write support.

Handles saving files of arbitrary size, including content with
multibyte UTF-8 characters (emoji, CJK, etc.).
"""

BUFFER_SIZE = 65536  # 64KB


def _compute_chunks(data: bytes, chunk_size: int) -> list[bytes]:
    """Split *data* into chunks of at most *chunk_size* bytes."""
    return [
        data[i : i + chunk_size]
        for i in range(0, len(data), chunk_size)
    ]


def save_file(path: str, content: str) -> int:
    """Save *content* to *path* using chunked writes.

    The content is encoded to UTF-8 and the resulting **byte length**
    is used for buffer/chunk calculations.  Previous versions
    incorrectly used ``len(content)`` (character count), which
    under-allocated the buffer when multibyte characters caused the
    byte length to exceed BUFFER_SIZE.

    Returns the number of bytes written.
    """
    encoded = content.encode("utf-8")
    chunks = _compute_chunks(encoded, BUFFER_SIZE)

    bytes_written = 0
    with open(path, "wb") as fh:
        for chunk in chunks:
            fh.write(chunk)
            bytes_written += len(chunk)

    return bytes_written
