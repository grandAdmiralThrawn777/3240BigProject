#ifndef TANK_MBED_CONFIG_H
#define TANK_MBED_CONFIG_H
#define MBEDTLS_MD_C
#define MBEDTLS_SHA256_C
#define MBEDTLS_PLATFORM_C
#define MBEDTLS_PLATFORM_MEMORY
#define MBEDTLS_PLATFORM_NO_STD_FUNCTIONS
#define MBEDTLS_MEMORY_BUFFER_ALLOC_C
/* MinGW's compatibility wrapper needs the standard declarations. */
#include <stdio.h>
#endif
