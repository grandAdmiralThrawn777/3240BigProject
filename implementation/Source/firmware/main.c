#include "runtime.h"

/* STM32F407 RM0090 registers; the board starts on its 16 MHz HSI clock. */
#define REG32(address) (*(volatile uint32_t *)(uintptr_t)(address))
#define RCC_AHB1ENR REG32(0x40023830U)
#define RCC_APB1ENR REG32(0x40023840U)
#define GPIOA_MODER REG32(0x40020000U)
#define GPIOA_AFRL REG32(0x40020020U)
#define GPIOD_MODER REG32(0x40020C00U)
#define GPIOD_BSRR REG32(0x40020C18U)
#define USART2_SR REG32(0x40004400U)
#define USART2_DR REG32(0x40004404U)
#define USART2_BRR REG32(0x40004408U)
#define USART2_CR1 REG32(0x4000440CU)
#define SYST_CSR REG32(0xE000E010U)
#define SYST_RVR REG32(0xE000E014U)
#define SYST_CVR REG32(0xE000E018U)
#define NVIC_ISER1 REG32(0xE000E104U)

static volatile uint32_t milliseconds;
static tank_runtime runtime;
volatile uint32_t observed[12];

void SysTick_Handler(void);
void USART2_Handler(void);
int main(void);

void SysTick_Handler(void) {
    milliseconds++;
}

void USART2_Handler(void) {
    uint32_t status = USART2_SR;
    if ((status & ((1U << 5) | (1U << 3))) != 0U) {
        uint8_t byte = (uint8_t)USART2_DR;
        if ((status & (1U << 3)) != 0U) {
            runtime.overflow = true;
            runtime.overflows++;
        } else {
            (void)tank_receive(&runtime, byte);
        }
    }
}

static tank_sample sensor_read(void) {
    uint32_t first = REG32(0x20000000U);
    uint32_t level = REG32(0x20000004U);
    uint32_t valid = REG32(0x20000008U);
    uint32_t timestamp = REG32(0x2000000CU);
    uint32_t last = REG32(0x20000000U);
    tank_sample sample = {level, timestamp,
        first == last && (first & 1U) == 0U && valid == 1U};
    return sample;
}

static void board_init(void) {
    RCC_AHB1ENR |= (1U << 0) | (1U << 3);
    RCC_APB1ENR |= 1U << 17;
    (void)RCC_AHB1ENR;
    GPIOA_MODER = (GPIOA_MODER & ~((3U << 4) | (3U << 6))) | (2U << 4) | (2U << 6);
    GPIOA_AFRL = (GPIOA_AFRL & ~((15U << 8) | (15U << 12))) | (7U << 8) | (7U << 12);
    GPIOD_MODER = (GPIOD_MODER & ~(3U << 24)) | (1U << 24);
    GPIOD_BSRR = 1U << 28;
    USART2_BRR = 139U;
    USART2_CR1 = (1U << 13) | (1U << 5) | (1U << 3) | (1U << 2);
    NVIC_ISER1 = 1U << 6;
    SYST_RVR = 15999U;
    SYST_CVR = 0U;
    SYST_CSR = 7U;
}

int main(void) {
    tank_crypto_init();
    tank_runtime_init(&runtime, 100U);
    board_init();
    for (;;) {
        __asm volatile ("cpsid i" ::: "memory");
        uint32_t now = milliseconds;
        if (tank_cycle(&runtime, now, sensor_read())) {
            GPIOD_BSRR = runtime.state.valve_open ? 1U << 12 : 1U << 28;
            observed[0] = now;
            observed[1] = runtime.state.valve_open;
            observed[2] = runtime.state.fault;
            observed[3] = runtime.config.low;
            observed[4] = runtime.config.high;
            observed[5] = runtime.accepted;
            observed[6] = runtime.rejected;
            observed[7] = runtime.overflows;
            observed[8] = runtime.deadlines;
            observed[9] = runtime.auth_attempts;
            observed[10] = runtime.last_bytes;
            observed[11]++;
        }
        __asm volatile ("cpsie i" ::: "memory");
        __asm volatile ("wfi");
    }
}
