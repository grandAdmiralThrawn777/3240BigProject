"""Build portable C17 host programs or Cortex-M4 firmware. No shell required."""
import argparse
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]
MBED = ROOT / 'Third_Party/mbedtls'
LIBS = ['md', 'sha256', 'constant_time', 'platform', 'platform_util', 'memory_buffer_alloc']


def build(cc=None, firmware=False, sanitize=False):
    compiler = cc or os.environ.get('TANK_ARM_CC' if firmware else 'CC')
    compiler = compiler or ('arm-none-eabi-gcc' if firmware else 'gcc')
    compiler = shutil.which(compiler)
    if not compiler:
        raise RuntimeError('Compiler not found; supply --cc with a GCC/Clang executable path.')
    target = 'cortex-m4' if firmware else platform.machine().lower()
    folder = ROOT / 'Build' / (target + ('-sanitized' if sanitize else ''))
    folder.mkdir(parents=True, exist_ok=True)
    common = ['-std=c17', '-O2', '-g', '-ffunction-sections', '-fdata-sections',
              '-ISource/include', '-IThird_Party/mbedtls/include',
              '-IThird_Party/mbedtls/library', '-DMBEDTLS_CONFIG_FILE="tank_mbed_config.h"']
    if os.name == 'nt' and not firmware:
        common += ['-D_CRT_SECURE_NO_WARNINGS']
    strict = ['-Wall', '-Wextra', '-Werror', '-Wconversion', '-Wshadow', '-Wstrict-prototypes', '-Wpedantic']
    if firmware:
        common += ['-mcpu=cortex-m4', '-mthumb', '-mfloat-abi=soft', '-ffreestanding', '-fno-common']
    if sanitize:
        common += ['-fsanitize=address,undefined', '-fno-sanitize-recover=all', '-fno-omit-frame-pointer']
    log = []

    def run(command):
        result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=120)
        log.append({'command': command, 'exit': result.returncode,
                    'stdout': result.stdout, 'stderr': result.stderr})
        (folder / 'build.json').write_text(json.dumps(log, indent=2) + '\n')
        if result.returncode:
            raise RuntimeError(result.stderr)
        return result.stdout

    run([compiler, '--version'])
    triple = run([compiler, '-dumpmachine']).strip()
    objects = []
    sources = ['Source/src/controller.c', 'Source/src/runtime.c']
    if firmware:
        sources += ['Source/firmware/main.c', 'Source/firmware/startup.c', 'Source/firmware/startup.S']
    for source in sources + ['Third_Party/mbedtls/library/' + name + '.c' for name in LIBS]:
        obj = folder / (source.replace('/', '_') + '.o')
        warnings = strict if source.startswith('Source/') and source.endswith('.c') else []
        run([compiler] + common + warnings + ['-c', source, '-o', str(obj)])
        objects.append(str(obj))
    programs = ['controller'] if firmware else ['runtime_runner', 'hmac_runner', 'tank_model']
    for name in programs:
        output = folder / (name + ('.elf' if firmware else '.exe' if os.name == 'nt' else ''))
        options = []
        if firmware:
            options = ['-nostartfiles', '--specs=nosys.specs', '-TSource/firmware/linker.ld',
                       '-Wl,--gc-sections,-Map=' + str(folder / 'controller.map')]
        else:
            options = strict + ['Source/host/' + name + '.c']
        run([compiler] + common + options + objects + ['-o', str(output)])
    (folder / 'target.json').write_text(json.dumps({'host_os': platform.system(),
        'host_arch': platform.machine(), 'compiler_target': triple, 'firmware': firmware,
        'sanitizers': sanitize}, indent=2) + '\n')
    print('Built:', folder, 'Compiler target:', triple)
    return folder


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cc')
    parser.add_argument('--firmware', action='store_true')
    parser.add_argument('--sanitize', action='store_true')
    options = parser.parse_args()
    build(options.cc, options.firmware, options.sanitize)
