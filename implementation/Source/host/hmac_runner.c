#include "runtime.h"
#include "file_input.h"
#include <stdio.h>
#include <string.h>

static int hex(char c) {
    if (c >= '0' && c <= '9') {
        return c - '0';
    }
    if (c >= 'a' && c <= 'f') {
        return c - 'a' + 10;
    }
    return -1;
}

static bool decode(const char *text, uint8_t *bytes, size_t *length) {
    size_t size = strlen(text);
    if (size % 2U != 0U || size > 2048U) {
        return false;
    }
    for (size_t i = 0U; i < size; i += 2U) {
        int a = hex(text[i]);
        int b = hex(text[i + 1U]);
        if (a < 0 || b < 0) {
            return false;
        }
        bytes[i / 2U] = (uint8_t)((unsigned int)a * 16U + (unsigned int)b);
    }
    *length = size / 2U;
    return true;
}

int main(int argc, char **argv) {
    if (argc != 2) {
        return 2;
    }
    FILE *input = fopen(argv[1], "rb");
    if (input == NULL) {
        return 2;
    }
    tank_crypto_init();
    char line[4200];
    int record;
    while ((record = read_record(input, line, sizeof line)) > 0) {
        char *split = strchr(line, ',');
        if (split == NULL) {
            (void)fclose(input);
            return 2;
        }
        *split++ = '\0';
        uint8_t key[1024], message[1024], tag[32];
        size_t key_length, message_length;
        if (!decode(line, key, &key_length) || !decode(split, message, &message_length) ||
            !tank_hmac(key, key_length, message, message_length, tag)) {
            (void)fclose(input);
            return 2;
        }
        for (size_t i = 0U; i < sizeof tag; i++) {
            printf("%02x", (unsigned int)tag[i]);
        }
        putchar('\n');
    }
    bool failed = record < 0;
    return fclose(input) != 0 || failed ? 2 : 0;
}
