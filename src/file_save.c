#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "file_save.h"

/*
 * save_file - Write content to a file safely.
 *
 * Prior to v2.3.1, the buffer size was calculated using the character
 * count (via wcslen or equivalent) rather than the actual byte length.
 * For ASCII-only content, character count == byte count, so the bug was
 * latent.  For multibyte UTF-8 content (emoji, CJK, etc.) the byte
 * length can be up to 4x the character count, causing a heap buffer
 * overflow when the encoded size exceeds 64 KB.
 *
 * Fix: allocate the write buffer using the byte length of the content
 * (strlen), not the character count.
 */
int save_file(const char *path, const char *content) {
    if (!path || !content) {
        return SAVE_ERR_NULL_ARG;
    }

    /* Use byte length, not character count, for buffer allocation. */
    size_t byte_len = strlen(content);
    if (byte_len == 0) {
        return SAVE_ERR_EMPTY;
    }

    char *buf = malloc(byte_len + 1);
    if (!buf) {
        return SAVE_ERR_ALLOC;
    }
    memcpy(buf, content, byte_len + 1);

    FILE *fp = fopen(path, "wb");
    if (!fp) {
        free(buf);
        return SAVE_ERR_OPEN;
    }

    size_t written = fwrite(buf, 1, byte_len, fp);
    free(buf);

    if (fclose(fp) != 0) {
        return SAVE_ERR_CLOSE;
    }

    if (written != byte_len) {
        return SAVE_ERR_WRITE;
    }

    return SAVE_OK;
}
