#include <stdint.h>

extern uint32_t _sidata, _sdata, _edata, _sbss, _ebss;

int main(void);
void Reset_Handler(void);

void Reset_Handler(void) {
    uint32_t *src = &_sidata;
    for (uint32_t *dst = &_sdata; dst < &_edata; ++dst) {
        *dst = *src++;
    }
    for (uint32_t *dst = &_sbss; dst < &_ebss; ++dst) {
        *dst = 0U;
    }
    (void)main();
    for (;;) {
        __asm volatile ("wfi");
    }
}
