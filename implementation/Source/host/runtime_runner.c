#include "runtime.h"
#include "file_input.h"
#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static bool number(const char *text, uint32_t *result) {
    if (*text < '0' || *text > '9') {
        return false;
    }
    char *end;
    errno = 0;
    unsigned long long value = strtoull(text, &end, 10);
    if (errno != 0 || *end != '\0' || value > UINT32_MAX) {
        return false;
    }
    *result = (uint32_t)value;
    return true;
}

static int hex(char c) {
    if (c >= '0' && c <= '9') {
        return c - '0';
    }
    if (c >= 'a' && c <= 'f') {
        return c - 'a' + 10;
    }
    return -1;
}

int main(int argc, char **argv) {
    if (argc != 2) {
        return 2;
    }
    FILE *input = strcmp(argv[1], "-") == 0 ? stdin : fopen(argv[1], "rb");
    if (input == NULL) {
        return 2;
    }
    tank_crypto_init();
    tank_runtime runtime;
    tank_runtime_init(&runtime, 100U);
    char line[4096];
    (void)setvbuf(stdout, NULL, _IOLBF, 0U);
    puts("now,ran,open,fault,low,high,accepted,rejected,overflows,deadlines,auth,bytes,queued");
    (void)fflush(stdout);
    int record;
    while ((record = read_record(input, line, sizeof line)) > 0) {
        if (line[0] == '#' || line[0] == '\0') {
            continue;
        }
        if (has_empty_field(line)) {
            (void)fclose(input);
            return 2;
        }
        char *fields[6];
        size_t count = 0U;
        char *token = strtok(line, ",");
        while (token != NULL && count < 6U) {
            fields[count++] = token;
            token = strtok(NULL, ",");
        }
        uint32_t values[5];
        if (count != 6U || token != NULL) {
            (void)fclose(input);
            return 2;
        }
        for (size_t i = 0U; i < 5U; i++) {
            if (!number(fields[i], &values[i])) {
                (void)fclose(input);
                return 2;
            }
        }
        if (values[3] > 1U ||
            !(values[4] == 50U || values[4] == 100U || values[4] == 500U)) {
            (void)fclose(input);
            return 2;
        }
        runtime.period = values[4];
        if (strcmp(fields[5], "-") != 0) {
            size_t bytes = strlen(fields[5]);
            if (bytes % 2U != 0U) {
                (void)fclose(input);
                return 2;
            }
            for (size_t i = 0U; i < bytes; i += 2U) {
                int a = hex(fields[5][i]);
                int b = hex(fields[5][i + 1U]);
                if (a < 0 || b < 0) {
                    (void)fclose(input);
                    return 2;
                }
                (void)tank_receive(&runtime, (uint8_t)((unsigned int)a * 16U + (unsigned int)b));
            }
        }
        tank_sample sample = {values[1], values[2], values[3] != 0U};
        bool ran = tank_cycle(&runtime, values[0], sample);
        printf("%lu,%u,%u,%u,%u,%u,%lu,%lu,%lu,%lu,%lu,%lu,%zu\n",
            (unsigned long)values[0], (unsigned int)ran, (unsigned int)runtime.state.valve_open,
            (unsigned int)runtime.state.fault, (unsigned int)runtime.config.low,
            (unsigned int)runtime.config.high, (unsigned long)runtime.accepted,
            (unsigned long)runtime.rejected, (unsigned long)runtime.overflows,
            (unsigned long)runtime.deadlines, (unsigned long)runtime.auth_attempts,
            (unsigned long)runtime.last_bytes, runtime.count);
        (void)fflush(stdout);
    }
    bool failed = record < 0;
    return fclose(input) != 0 || failed ? 2 : 0;
}
