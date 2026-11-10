#include "runtime.h"
#include "mbedtls/constant_time.h"
#include "mbedtls/md.h"
#include "mbedtls/memory_buffer_alloc.h"
#include "mbedtls/platform_util.h"
#include <string.h>

/* Public demonstration key. This is not a provisioned production secret. */
static const uint8_t demo_key[32] = {
    0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15,
    16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31
};
static unsigned char crypto_memory[4096];

void tank_crypto_init(void) {
    mbedtls_memory_buffer_alloc_init(crypto_memory, sizeof crypto_memory);
}

bool tank_hmac(const uint8_t *key, size_t key_length, const uint8_t *message,
               size_t length, uint8_t tag[32]) {
    const mbedtls_md_info_t *info = mbedtls_md_info_from_type(MBEDTLS_MD_SHA256);
    return mbedtls_md_hmac(info, key, key_length, message, length, tag) == 0;
}

void tank_runtime_init(tank_runtime *runtime, uint32_t period) {
    memset(runtime, 0, sizeof *runtime);
    runtime->config = (tank_config){3000U, 7000U};
    runtime->state.fault = true;
    if (period == 50U || period == 100U || period == 500U) {
        runtime->period = period;
    }
}

bool tank_receive(tank_runtime *runtime, uint8_t byte) {
    if (runtime->count == TANK_RX_CAPACITY) {
        runtime->overflow = true;
        runtime->overflows++;
        return false;
    }
    size_t tail = (runtime->head + runtime->count) % TANK_RX_CAPACITY;
    runtime->queue[tail] = byte;
    runtime->count++;
    return true;
}

static bool decimal(const char *line, size_t *position, uint16_t *value) {
    size_t start = *position;
    uint32_t number = 0U;
    while (line[*position] >= '0' && line[*position] <= '9') {
        uint32_t digit = (uint32_t)(line[*position] - '0');
        if (number > (UINT16_MAX - digit) / 10U) {
            return false;
        }
        number = number * 10U + digit;
        (*position)++;
    }
    if (*position == start || line[*position] != ',' ||
        (*position - start > 1U && line[start] == '0')) {
        return false;
    }
    *value = (uint16_t)number;
    (*position)++;
    return true;
}

static int hex_digit(char c) {
    if (c >= '0' && c <= '9') {
        return c - '0';
    }
    if (c >= 'a' && c <= 'f') {
        return c - 'a' + 10;
    }
    return -1;
}

static bool command(tank_runtime *runtime) {
    if (runtime->length < 4U || memcmp(runtime->line, "SET,", 4U) != 0) {
        return false;
    }
    size_t position = 4U;
    tank_config proposed;
    if (!decimal(runtime->line, &position, &proposed.low) ||
        !decimal(runtime->line, &position, &proposed.high) ||
        runtime->length - position != 64U) {
        return false;
    }
    uint8_t supplied[32];
    uint8_t calculated[32];
    for (size_t i = 0U; i < sizeof supplied; i++) {
        int high = hex_digit(runtime->line[position + i * 2U]);
        int low = hex_digit(runtime->line[position + i * 2U + 1U]);
        if (high < 0 || low < 0) {
            return false;
        }
        supplied[i] = (uint8_t)((unsigned int)high * 16U + (unsigned int)low);
    }
    runtime->auth_attempts++;
    bool valid = tank_hmac(demo_key, sizeof demo_key,
                          (const uint8_t *)runtime->line, position - 1U, calculated);
    valid = valid && mbedtls_ct_memcmp(supplied, calculated, sizeof supplied) == 0;
    mbedtls_platform_zeroize(calculated, sizeof calculated);
    if (!valid || !tank_config_valid(proposed)) {
        return false;
    }
    runtime->config = proposed;
    return true;
}

static void serial_step(tank_runtime *runtime, uint32_t now) {
    runtime->last_bytes = 0U;
    if (runtime->overflow) {
        /* Drop all queued bytes: a dropped newline could join two commands. */
        runtime->head = 0U;
        runtime->count = 0U;
        runtime->overflow = false;
        runtime->length = 0U;
        runtime->discard = true;
        runtime->rejected++;
    }
    if (runtime->length != 0U && now - runtime->started > TANK_LINE_TIMEOUT) {
        runtime->length = 0U;
        runtime->rejected++;
    }
    while (runtime->count != 0U && runtime->last_bytes < TANK_RX_BUDGET) {
        uint8_t byte = runtime->queue[runtime->head];
        runtime->head = (runtime->head + 1U) % TANK_RX_CAPACITY;
        runtime->count--;
        runtime->last_bytes++;
        if (runtime->discard) {
            if (byte == (uint8_t)'\n') {
                runtime->discard = false;
            }
            continue;
        }
        if (byte == (uint8_t)'\n') {
            runtime->line[runtime->length] = '\0';
            if (command(runtime)) {
                runtime->accepted++;
            } else {
                runtime->rejected++;
            }
            runtime->length = 0U;
            /* At most one completed line and one authentication per cycle. */
            break;
        }
        if (byte < 32U || byte > 126U || runtime->length == TANK_LINE_CAPACITY) {
            runtime->discard = true;
            runtime->length = 0U;
            runtime->rejected++;
            continue;
        }
        if (runtime->length == 0U) {
            runtime->started = now;
        }
        runtime->line[runtime->length++] = (char)byte;
    }
}

bool tank_cycle(tank_runtime *runtime, uint32_t now, tank_sample sample) {
    uint32_t elapsed = now - runtime->last_tick;
    if (runtime->period == 0U || elapsed < runtime->period) {
        return false;
    }
    runtime->last_tick = now;
    if (elapsed >= 2U * runtime->period) {
        runtime->state = (tank_state){false, true};
        runtime->deadlines++;
    } else {
        bool valid = sample.valid && sample.level <= TANK_LEVEL_MAX &&
                     now - sample.timestamp <= TANK_SAMPLE_MAX_AGE;
        tank_step(&runtime->state, runtime->config,
                  valid ? (uint16_t)sample.level : 0U, valid);
    }
    serial_step(runtime, now);
    return true;
}
