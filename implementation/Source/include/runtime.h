#ifndef TANK_RUNTIME_H
#define TANK_RUNTIME_H

#include "controller.h"
#include <stddef.h>

#define TANK_RX_CAPACITY 256U
#define TANK_LINE_CAPACITY 128U
#define TANK_RX_BUDGET 32U
#define TANK_SAMPLE_MAX_AGE 300U
#define TANK_LINE_TIMEOUT 500U

typedef struct {
    uint32_t level;
    uint32_t timestamp;
    bool valid;
} tank_sample;

typedef struct {
    tank_config config;
    tank_state state;
    uint8_t queue[TANK_RX_CAPACITY];
    size_t head;
    size_t count;
    bool overflow;
    char line[TANK_LINE_CAPACITY + 1U];
    size_t length;
    bool discard;
    uint32_t started;
    uint32_t period;
    uint32_t last_tick;
    uint32_t accepted;
    uint32_t rejected;
    uint32_t overflows;
    uint32_t deadlines;
    uint32_t auth_attempts;
    uint32_t last_bytes;
} tank_runtime;

/* Call queue functions with interrupts masked on the single-core firmware. */
void tank_runtime_init(tank_runtime *runtime, uint32_t period);
bool tank_receive(tank_runtime *runtime, uint8_t byte);
bool tank_cycle(tank_runtime *runtime, uint32_t now, tank_sample sample);
void tank_crypto_init(void);
bool tank_hmac(const uint8_t *key, size_t key_length, const uint8_t *message,
               size_t length, uint8_t tag[32]);

#endif
