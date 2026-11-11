.syntax unified
.cpu cortex-m4
.thumb
.section .isr_vector,"a",%progbits
.global vector_table
vector_table:
.word _estack
.word Reset_Handler
.rept 13
.word Default_Handler
.endr
.word SysTick_Handler
.rept 38
.word Default_Handler
.endr
.word USART2_Handler
.rept 43
.word Default_Handler
.endr
.section .text.Default_Handler,"ax",%progbits
.thumb_func
Default_Handler:
    b .
