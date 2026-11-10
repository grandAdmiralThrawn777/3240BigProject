#ifndef TANK_FILE_INPUT_H
#define TANK_FILE_INPUT_H

#include <stdio.h>
#include <string.h>

/* 1 = record, 0 = clean EOF, -1 = invalid input or I/O error. */
static inline int read_record(FILE *input, char *line, size_t capacity) {
    size_t length = 0U;
    int byte;
    while ((byte = fgetc(input)) != EOF) {
        if (byte == '\n') {
            break;
        }
        if (byte == 0 || length + 1U >= capacity) {
            return -1;
        }
        line[length++] = (char)(unsigned char)byte;
    }
    if (ferror(input) != 0) {
        return -1;
    }
    if (length == 0U && byte == EOF) {
        return 0;
    }
    if (length != 0U && line[length - 1U] == '\r') {
        length--;
    }
    line[length] = '\0';
    return 1;
}

static inline int has_empty_field(const char *line) {
    size_t length = strlen(line);
    return length == 0U || line[0] == ',' || line[length - 1U] == ',' ||
           strstr(line, ",,") != NULL;
}

#endif
