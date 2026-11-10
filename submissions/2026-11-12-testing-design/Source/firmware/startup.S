.syntax unified
.cpu cortex-m4
.thumb
.section .isr_vector,"a",%progbits
.global vector_table
vector_table:
.word _estack
.word Reset_Handler
.rept 14
.word Default_Handler
.endr
.rept 82
.word Default_Handler
.endr
.section .text.Default_Handler,"ax",%progbits
.thumb_func
Default_Handler:
    b .
