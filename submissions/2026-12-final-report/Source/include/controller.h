#ifndef TANK_CONTROLLER_H
#define TANK_CONTROLLER_H

#include <stdbool.h>
#include <stdint.h>

// Level uses basis points: 0 is empty and 10000 is full.
#define TANK_LEVEL_MAX UINT16_C(10000)

typedef struct {
    uint16_t low;
    uint16_t high;
} tank_config;

typedef struct {
    bool valve_open;
    bool fault;
} tank_state;

bool tank_config_valid(tank_config config);
void tank_step(tank_state *state, tank_config config, uint16_t level, bool sample_valid);

#endif
