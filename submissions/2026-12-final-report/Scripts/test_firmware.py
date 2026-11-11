"""Run the actual Cortex-M4 ELF with file-driven sensor and UART cases in Renode."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import tempfile
from build import ROOT
from renode_session import Renode


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--renode', default='renode')
    parser.add_argument('--nm', default='arm-none-eabi-nm')
    args = parser.parse_args()
    elf = ROOT/'Build/cortex-m4/controller.elf'
    symbols = subprocess.check_output([args.nm, str(elf)], text=True)
    address = int(re.search(r'^([0-9a-fA-F]+)\s+\w\s+observed$', symbols, re.M).group(1), 16)
    directory = Path(tempfile.mkdtemp(prefix='firmware-', dir=ROOT/'Runs'))
    report = {'status': 'INCOMPLETE', 'elf_sha256': hashlib.sha256(elf.read_bytes()).hexdigest(),
              'target': 'ARM Cortex-M4 / STM32F4, Renode emulation', 'checks': []}
    session = Renode(args.renode, directory/'monitor.log')

    def numbers(command):
        output = session.command(command)
        return [int(value, 16) for value in re.findall(r'^0x([0-9a-fA-F]+)\s*$', output, re.M)]

    def status():
        commands = ['sysbus ReadDoubleWord ' + hex(address + i * 4) for i in range(12)]
        commands.append('sysbus ReadDoubleWord 0x40020C14')
        values = numbers('; '.join(commands))
        assert len(values) == 13, values
        keys = ['now', 'open', 'fault', 'low', 'high', 'accepted', 'rejected',
                'overflows', 'deadlines', 'auth', 'bytes', 'ticks', 'gpio']
        return dict(zip(keys, values))

    try:
        session.command('mach create "tank"')
        session.command('emulation SetGlobalAdvanceImmediately true')
        session.command('machine LoadPlatformDescription @' + (ROOT/'Source/emulation/tank.repl').as_posix().replace(' ', '\\ '))
        session.command('sysbus LoadELF @' + elf.as_posix().replace(' ', '\\ '))
        for index, case in enumerate(json.loads((ROOT/'Test_Data/Runtime/firmware.json').read_text())):
            writes = [(0x20000000, index * 2 + 1), (0x20000004, case['level']),
                      (0x20000008, case.get('valid', 1)), (0x2000000c, case['timestamp']),
                      (0x20000000, index * 2 + case.get('sequence_parity', 2))]
            session.command('; '.join(f'sysbus WriteDoubleWord {hex(location)} {value}' for location, value in writes))
            if case.get('rx_hex'):
                session.command('; '.join('sysbus.usart2 WriteChar ' + str(byte) for byte in bytes.fromhex(case['rx_hex'])))
            session.command('emulation RunFor "' + str(case.get('run_seconds', 0.1)) + '"')
            observed = status()
            ok = all(observed[key] == value for key, value in case['expected'].items())
            ok = ok and ((observed['gpio'] >> 12) & 1) == observed['open']
            report['checks'].append({'name': case['name'], 'expected': case['expected'], 'observed': observed, 'passed': ok})
            assert ok, case['name'] + ': ' + str(observed)
        report['status'] = 'PASS'
    except (AssertionError, OSError, RuntimeError) as error:
        report['status'] = 'FAIL'
        report['error'] = str(error)
    finally:
        session.close()
        (directory/'summary.json').write_text(json.dumps(report, indent=2) + '\n')
    print(report['status'], directory)
    if report['status'] != 'PASS':
        print(report['error'])
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
