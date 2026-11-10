"""Build the unchanged fixed-reading firmware with GNU Arm GCC on any host OS."""
import argparse
import os
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cc', default=os.environ.get('TANK_ARM_CC','arm-none-eabi-gcc'))
    args = parser.parse_args()
    cc = shutil.which(args.cc)
    if not cc:
        parser.error('Install GNU Arm Embedded GCC and supply --cc if it is not on PATH.')
    output = ROOT/'Source/build/c'
    output.mkdir(parents=True,exist_ok=True)
    command = [cc,'-std=c17','-Wall','-Wextra','-Werror','-Wconversion','-Wshadow',
        '-Wstrict-prototypes','-Wpedantic','-ISource/include','-mcpu=cortex-m4','-mthumb',
        '-mfloat-abi=soft','-ffreestanding','-fno-builtin','-fno-common','-ffunction-sections',
        '-fdata-sections','-Os','-g3','-nostdlib','Source/firmware/startup.S',
        'Source/firmware/startup.c','Source/firmware/main.c','Source/src/controller.c',
        '-T','Source/firmware/linker.ld','-Wl,--gc-sections,-Map=Source/build/c/controller.map',
        '-o','Source/build/c/controller.elf']
    subprocess.run(command,cwd=ROOT,check=True,timeout=120)
    print('Built '+str(output/'controller.elf'))
    print('Firmware compilation only; Renode was not run.')


if __name__ == '__main__':
    main()
