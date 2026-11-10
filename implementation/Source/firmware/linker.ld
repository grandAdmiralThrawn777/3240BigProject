ENTRY(Reset_Handler)
MEMORY {
    FLASH (rx) : ORIGIN = 0x08000000, LENGTH = 1024K
    SENSOR (rw) : ORIGIN = 0x20000000, LENGTH = 32
    RAM (rwx)  : ORIGIN = 0x20000020, LENGTH = 128K - 32
}
_estack = ORIGIN(RAM) + LENGTH(RAM);
SECTIONS {
    .sensor (NOLOAD) : { . += 32; } > SENSOR
    .isr_vector : { KEEP(*(.isr_vector)) } > FLASH
    .text : { *(.text*) *(.rodata*) . = ALIGN(4); } > FLASH
    .ARM.exidx : { *(.ARM.exidx*) } > FLASH
    .data : {
        . = ALIGN(4); _sdata = .; *(.data*) . = ALIGN(4); _edata = .;
    } > RAM AT > FLASH
    _sidata = LOADADDR(.data);
    .bss (NOLOAD) : {
        . = ALIGN(4); _sbss = .; *(.bss*) *(COMMON) . = ALIGN(4); _ebss = .;
    } > RAM
    ASSERT(_ebss <= _estack - 4096, "Keep at least 4 KiB for stack")
}
