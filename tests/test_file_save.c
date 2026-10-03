#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "../src/file_save.h"

#define TEST_FILE "/tmp/test_file_save_output.bin"

/* Helper: build a string of `n` repetitions of `pattern`. */
static char *repeat(const char *pattern, size_t n) {
    size_t plen = strlen(pattern);
    char *buf = malloc(plen * n + 1);
    assert(buf);
    for (size_t i = 0; i < n; i++) {
        memcpy(buf + i * plen, pattern, plen);
    }
    buf[plen * n] = '\0';
    return buf;
}

/* Helper: read entire file into a malloc'd buffer; sets *out_len. */
static char *read_file(const char *path, size_t *out_len) {
    FILE *fp = fopen(path, "rb");
    assert(fp);
    fseek(fp, 0, SEEK_END);
    long len = ftell(fp);
    assert(len >= 0);
    fseek(fp, 0, SEEK_SET);
    char *buf = malloc((size_t)len + 1);
    assert(buf);
    size_t rd = fread(buf, 1, (size_t)len, fp);
    assert(rd == (size_t)len);
    buf[len] = '\0';
    fclose(fp);
    *out_len = (size_t)len;
    return buf;
}

/* ------------------------------------------------------------------ */

static void test_save_small_ascii(void) {
    const char *content = "Hello, world!\n";
    assert(save_file(TEST_FILE, content) == SAVE_OK);

    size_t len;
    char *got = read_file(TEST_FILE, &len);
    assert(len == strlen(content));
    assert(memcmp(got, content, len) == 0);
    free(got);
    remove(TEST_FILE);
    printf("  PASS  test_save_small_ascii\n");
}

static void test_save_null_args(void) {
    assert(save_file(NULL, "data") == SAVE_ERR_NULL_ARG);
    assert(save_file(TEST_FILE, NULL) == SAVE_ERR_NULL_ARG);
    printf("  PASS  test_save_null_args\n");
}

static void test_save_empty_content(void) {
    assert(save_file(TEST_FILE, "") == SAVE_ERR_EMPTY);
    printf("  PASS  test_save_empty_content\n");
}

/*
 * Regression test for #1759: saving >64 KB of multibyte UTF-8 content
 * must not crash (segfault) or corrupt data.
 *
 * The emoji U+1F600 (😀) is encoded as 4 bytes in UTF-8 (f0 9f 98 80).
 * 17000 repetitions = 68000 bytes > 64 KB.
 */
static void test_save_large_utf8(void) {
    /* 4-byte emoji repeated to exceed 64 KB */
    char *content = repeat("\xf0\x9f\x98\x80", 17000);
    size_t expected_bytes = 4 * 17000; /* 68000 */

    assert(save_file(TEST_FILE, content) == SAVE_OK);

    size_t len;
    char *got = read_file(TEST_FILE, &len);
    assert(len == expected_bytes);
    assert(memcmp(got, content, len) == 0);

    free(got);
    free(content);
    remove(TEST_FILE);
    printf("  PASS  test_save_large_utf8\n");
}

/*
 * Mixed 1/2/3/4-byte UTF-8 sequences crossing the 64 KB boundary.
 * ASCII 'A' = 1 byte, '¢' (U+00A2) = 2 bytes, '€' (U+20AC) = 3 bytes,
 * '😀' (U+1F600) = 4 bytes.  Pattern = 10 bytes per unit.
 */
static void test_save_large_mixed_utf8(void) {
    /* 10-byte pattern: A(1) + ¢(2) + €(3) + 😀(4) = 10 */
    const char *pattern = "A\xc2\xa2\xe2\x82\xac\xf0\x9f\x98\x80";
    size_t pattern_len = strlen(pattern);
    assert(pattern_len == 10);

    size_t reps = 7000; /* 70000 bytes > 64 KB */
    char *content = repeat(pattern, reps);

    assert(save_file(TEST_FILE, content) == SAVE_OK);

    size_t len;
    char *got = read_file(TEST_FILE, &len);
    assert(len == pattern_len * reps);
    assert(memcmp(got, content, len) == 0);

    free(got);
    free(content);
    remove(TEST_FILE);
    printf("  PASS  test_save_large_mixed_utf8\n");
}

/* Large ASCII (>64 KB) must still work (regression guard). */
static void test_save_large_ascii(void) {
    char *content = repeat("ABCDEFGHIJ", 7000); /* 70000 bytes */

    assert(save_file(TEST_FILE, content) == SAVE_OK);

    size_t len;
    char *got = read_file(TEST_FILE, &len);
    assert(len == 70000);
    assert(memcmp(got, content, len) == 0);

    free(got);
    free(content);
    remove(TEST_FILE);
    printf("  PASS  test_save_large_ascii\n");
}

/* Just under 64 KB with multibyte chars — should always have worked. */
static void test_save_under_64kb_utf8(void) {
    /* 3-byte CJK character U+4E16 (世) repeated 21000 times = 63000 bytes */
    char *content = repeat("\xe4\xb8\x96", 21000);

    assert(save_file(TEST_FILE, content) == SAVE_OK);

    size_t len;
    char *got = read_file(TEST_FILE, &len);
    assert(len == 63000);
    assert(memcmp(got, content, len) == 0);

    free(got);
    free(content);
    remove(TEST_FILE);
    printf("  PASS  test_save_under_64kb_utf8\n");
}

/* ------------------------------------------------------------------ */

int main(void) {
    printf("Running file save tests...\n");
    test_save_small_ascii();
    test_save_null_args();
    test_save_empty_content();
    test_save_large_utf8();
    test_save_large_mixed_utf8();
    test_save_large_ascii();
    test_save_under_64kb_utf8();
    printf("All tests passed.\n");
    return 0;
}
