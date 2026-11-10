#include "runtime.h"
#include "file_input.h"
#include <errno.h>
#include <inttypes.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

/* Each row supplies dt, capacity, starting volume, inlet, demand, actual valve.
 * The runner also accepts 'continue' volume to carry fractional flow forward. */
int main(int argc, char **argv) {
    if (argc != 2) {
        return 2;
    }
    FILE *input = strcmp(argv[1], "-") == 0 ? stdin : fopen(argv[1], "rb");
    if (input == NULL) {
        return 2;
    }
    char line[256];
    int64_t volume = 0, remainder = 0;
    puts("volume,raw,underflow,overflow,level,remainder");
    (void)fflush(stdout);
    int record;
    while ((record = read_record(input, line, sizeof line)) > 0) {
        if (has_empty_field(line)) {
            (void)fclose(input);
            return 2;
        }
        int64_t values[6];
        size_t count = 0U;
        char *field = strtok(line, ",");
        bool continued = false;
        while (field != NULL && count < 6U) {
            if (count == 2U && strcmp(field, "continue") == 0) {
                values[count++] = volume;
                continued = true;
            } else {
                char *end;
                errno = 0;
                if (*field < '0' || *field > '9') {
                    (void)fclose(input);
                    return 2;
                }
                int64_t value = strtoll(field, &end, 10);
                if (errno != 0 || *end != '\0') {
                    (void)fclose(input);
                    return 2;
                }
                values[count++] = value;
            }
            field = strtok(NULL, ",");
        }
        if (count != 6U || field != NULL || values[0] < 1 || values[0] > 500 ||
            values[1] < 1 || values[1] > 100000000 || values[2] > values[1] ||
            values[3] > 3000000 || values[4] > 3000000 || values[5] > 1) {
            (void)fclose(input);
            return 2;
        }
        if (!continued) {
            remainder = 0;
        }
        int64_t change = (values[3] * values[5] - values[4]) * values[0] + remainder;
        remainder = change % 1000;
        int64_t raw = values[2] + change / 1000;
        volume = raw < 0 ? 0 : raw > values[1] ? values[1] : raw;
        if (raw < 0 || raw > values[1]) {
            remainder = 0;
        }
        printf("%" PRId64 ",%" PRId64 ",%u,%u,%" PRId64 ",%" PRId64 "\n",
            volume, raw, (unsigned int)(raw < 0), (unsigned int)(raw > values[1]),
            volume * 10000 / values[1], remainder);
        (void)fflush(stdout);
    }
    bool failed = record < 0;
    return fclose(input) != 0 || failed ? 2 : 0;
}
