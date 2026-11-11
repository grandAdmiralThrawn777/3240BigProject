// Run independent control cases from a file.
// Other runners cover the tank model, serial commands, and authentication.
#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include "controller.h"

// Return 1 for a record, 0 at the end of the file, or -1 for an input error.
// Reject NUL bytes so a record cannot be cut short without an error.
static int read_record(FILE *input, char line[256]) {
    size_t used = 0U;
    int ch;
    while ((ch = fgetc(input)) != EOF) {
        if (ch == 0 || used >= 255U) {
            return -1;
        }
        line[used++] = (char)ch;
        if (ch == '\n') {
            break;
        }
    }
    if (ferror(input) != 0) {
        return -1;
    }
    line[used] = '\0';
    return used == 0U ? 0 : 1;
}

static bool fields(char *line, unsigned long out[7]) {
    char *cursor = line;
    for (size_t i = 0U; i < 7U; ++i) {
        if (*cursor < '0' || *cursor > '9') {
            return false;
        }
        errno = 0;
        char *end = NULL;
        unsigned long v = strtoul(cursor, &end, 10);
        if (errno != 0 || end == cursor || v > UINT16_MAX) {
            return false;
        }
        out[i] = v;
        if (i < 6U) {
            if (*end != ',') {
                return false;
            }
            cursor = end + 1;
        } else {
            if (*end == '\r') {
                ++end;
            }
            if (*end == '\n') {
                ++end;
            }
            if (*end != '\0') {
                return false;
            }
        }
    }
    return out[1] <= 1UL && out[4] <= 1UL && out[5] <= 1UL && out[6] <= 1UL;
}

int main(int argc, char *argv[]) {
    if (argc != 2) {
        fputs("usage: scenario-runner CASES.csv\n", stderr);
        return 2;
    }
    FILE *input = fopen(argv[1], "rb");
    if (input == NULL) {
        perror("scenario file");
        return 2;
    }
    char line[256];
    size_t count = 0U, line_number = 0U;
    int result = 0;
    int read_status;
    while ((read_status = read_record(input, line)) > 0) {
        ++line_number;
        if (line[0] == '#' || line[0] == '\n' ||
            (line[0] == '\r' && line[1] == '\n' && line[2] == '\0')) {
            continue;
        }
        unsigned long v[7];
        if (!fields(line, v)) {
            fprintf(stderr, "line %zu: invalid record\n", line_number);
            result = 2;
            break;
        }
        tank_config config = {(uint16_t)v[2], (uint16_t)v[3]};
        tank_state state = {v[4] != 0UL, false};
        tank_step(&state, config, (uint16_t)v[0], v[1] != 0UL);
        if (state.valve_open != (v[5] != 0UL) || state.fault != (v[6] != 0UL)) {
            fprintf(stderr, "line %zu: unexpected controller result\n", line_number);
            result = 1;
            break;
        }
        ++count;
    }
    if (read_status < 0) {
        fputs("invalid or oversized record\n", stderr);
        result = 2;
    }
    if (fclose(input) != 0) {
        result = 2;
    }
    if (count == 0U && result == 0) {
        fputs("no cases\n", stderr);
        result = 2;
    }
    if (result == 0) {
        printf("PASS: %zu file-driven C control cases\n", count);
    }
    return result;
}
