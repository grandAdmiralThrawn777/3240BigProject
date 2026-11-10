#include "controller.h"

bool tank_config_valid(tank_config config) {
    return config.low < config.high && config.high <= TANK_LEVEL_MAX;
}

void tank_step(tank_state *state, tank_config config, uint16_t level, bool sample_valid) {
    if (state == 0) {
        return;
    }
    if (!tank_config_valid(config) || !sample_valid || level > TANK_LEVEL_MAX) {
        state->valve_open = false;
        state->fault = true;
        return;
    }
    state->fault = false;
    if (level < config.low) {
        state->valve_open = true;
    } else if (level > config.high) {
        state->valve_open = false;
    }
    // Keep the previous valve state between the thresholds, including their endpoints.
}
