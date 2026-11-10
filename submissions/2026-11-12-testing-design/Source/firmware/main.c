#include <stdbool.h>
#include <stdint.h>
#include "controller.h"

// Register addresses come from the STM32F407 reference manual, RM0090.
// This setup uses the default 16 MHz HSI clock.
#define REG32(address) (*(volatile uint32_t *)(uintptr_t)(address))
#define RCC_AHB1ENR REG32(0x40023830U)
#define RCC_APB1ENR REG32(0x40023840U)
#define GPIOA_MODER REG32(0x40020000U)
#define GPIOA_AFRL  REG32(0x40020020U)
#define GPIOD_MODER REG32(0x40020C00U)
#define GPIOD_BSRR  REG32(0x40020C18U)
#define USART2_SR   REG32(0x40004400U)
#define USART2_DR   REG32(0x40004404U)
#define USART2_BRR  REG32(0x40004408U)
#define USART2_CR1  REG32(0x4000440CU)

static void board_init(void) {
    RCC_AHB1ENR |= (1U << 0) | (1U << 3); /* GPIOA, GPIOD */
    RCC_APB1ENR |= 1U << 17;              /* USART2 */
    (void)RCC_AHB1ENR;
    GPIOA_MODER = (GPIOA_MODER & ~(3U << 4)) | (2U << 4); /* PA2 AF */
    GPIOA_AFRL = (GPIOA_AFRL & ~(15U << 8)) | (7U << 8); /* USART2 TX */
    GPIOD_MODER = (GPIOD_MODER & ~(3U << 24)) | (1U << 24); /* PD12 */
    GPIOD_BSRR = 1U << 28; /* Closed on startup */
    USART2_BRR = 139U;     /* 16 MHz / 115200, rounded; oversampling by 16 */
    USART2_CR1 = (1U << 13) | (1U << 3);
}

static bool uart_write(const char *text) {
    while (*text != '\0') {
        uint32_t remaining = 100000U;
        while ((USART2_SR & (1U << 7)) == 0U) {
            if (--remaining == 0U) {
                return false;
            }
        }
        USART2_DR = (uint32_t)(unsigned char)*text++;
    }
    return true;
}

int main(void) {
    board_init();
    if (!uart_write("C_RENODE_SETUP_OK\r\n")) {
        return 1;
    }
    // Use a fixed 25% reading for this firmware test.
    const tank_config config = {3000U, 7000U};
    tank_state state = {false, false};
    tank_step(&state, config, 2500U, true);
    if (state.valve_open && !state.fault) {
        GPIOD_BSRR = 1U << 12;
        if (!uart_write("C_CONTROL_LOW_OPEN_OK\r\n")) {
            return 1;
        }
    }
    for (;;) {
        __asm volatile ("wfi");
    }
}
