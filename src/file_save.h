#ifndef FILE_SAVE_H
#define FILE_SAVE_H

#define SAVE_OK        0
#define SAVE_ERR_NULL_ARG -1
#define SAVE_ERR_EMPTY    -2
#define SAVE_ERR_ALLOC    -3
#define SAVE_ERR_OPEN     -4
#define SAVE_ERR_WRITE    -5
#define SAVE_ERR_CLOSE    -6

/*
 * save_file - Write content to a file.
 *
 * Allocates a buffer using the byte length of content (not character
 * count) to handle multibyte UTF-8 sequences correctly for any size.
 *
 * Returns SAVE_OK on success, or a negative error code on failure.
 */
int save_file(const char *path, const char *content);

#endif /* FILE_SAVE_H */
