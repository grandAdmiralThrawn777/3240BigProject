"""Close the loop through the emulated ARM firmware and the separate C tank model."""
import argparse
import csv
from fractions import Fraction
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
import time
from build import ROOT
from renode_session import Renode
from test_tank import Program


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--renode', default='renode')
    parser.add_argument('--nm', default='arm-none-eabi-nm')
    parser.add_argument('--model', type=Path, required=True)
    parser.add_argument('--seconds', type=int, default=600)
    args = parser.parse_args()
    if not 1 <= args.seconds <= 3600:
        parser.error('--seconds must be 1..3600')
    elf = ROOT/'Build/cortex-m4/controller.elf'
    symbols = subprocess.check_output([args.nm, str(elf)], text=True)
    address = int(re.search(r'^([0-9a-fA-F]+)\s+\w\s+observed$', symbols, re.M).group(1), 16)
    folder = Path(tempfile.mkdtemp(prefix='renode-tank-', dir=ROOT/'Runs'))
    report = {'status': 'INCOMPLETE', 'target': 'Actual Cortex-M4 ELF in Renode with C model feedback',
              'elf_sha256': hashlib.sha256(elf.read_bytes()).hexdigest(), 'duration_s': args.seconds,
              'steps': 0}
    session = Renode(args.renode, folder/'monitor.log')
    model = Program(args.model)
    volume = 50000000
    reference = Fraction(volume)
    expected_open = False
    minimum = 10000
    maximum = 0
    start = time.monotonic()
    try:
        session.command('mach create "tank"; emulation SetGlobalAdvanceImmediately true')
        session.command('machine LoadPlatformDescription @' + (ROOT/'Source/emulation/tank.repl').as_posix().replace(' ', '\\ '))
        session.command('sysbus LoadELF @' + elf.as_posix().replace(' ', '\\ '))
        settings = json.loads((ROOT/'Test_Data/Runtime/tank.json').read_text())['runs'][0]
        inlet = settings['inlet_ul_s']
        demand = settings['demand_ul_s']
        with (folder/'samples.csv').open('w', newline='') as stream:
            writer = csv.writer(stream)
            writer.writerow(['sample','firmware_ms','volume_ul','level_bp','gpio_open','fault'])
            for step in range(args.seconds * 10 + 1):
                level = volume * 10000 // 100000000
                timestamp = step * 100
                commands = [f'sysbus WriteDoubleWord 0x20000000 {step * 2 + 1}',
                    f'sysbus WriteDoubleWord 0x20000004 {level}',
                    'sysbus WriteDoubleWord 0x20000008 1',
                    f'sysbus WriteDoubleWord 0x2000000c {timestamp}',
                    f'sysbus WriteDoubleWord 0x20000000 {step * 2 + 2}',
                    'emulation RunFor "' + ('0.11' if step == 0 else '0.1') + '"',
                    'sysbus ReadDoubleWord 0x40020C14',
                    f'sysbus ReadDoubleWord {hex(address + 8)}',
                    f'sysbus ReadDoubleWord {hex(address)}']
                output = session.command('; '.join(commands))
                values = [int(value, 16) for value in re.findall(r'^0x([0-9a-fA-F]+)\s*$', output, re.M)]
                assert len(values) == 3, values
                opened = bool(values[0] & (1 << 12))
                if level < 3000:
                    expected_open = True
                elif level > 7000:
                    expected_open = False
                assert opened == expected_open and values[1] == 0, (step, values, expected_open)
                assert values[2] == (step + 1) * 100, (step, values)
                assert volume == int(reference), (step, volume, reference)
                minimum = min(minimum, level)
                maximum = max(maximum, level)
                writer.writerow([step, values[2], volume, level, int(opened), values[1]])
                report['steps'] += 1
                if step < args.seconds * 10:
                    result = model.step([100, 100000000, volume if step == 0 else 'continue',
                                         inlet, demand, int(opened)])
                    reference += Fraction((int(opened) * inlet - demand) * 100, 1000)
                    assert result['underflow'] == result['overflow'] == 0
                    volume = result['volume']
                if step and step % 1000 == 0:
                    print('ARM feedback:', step // 10, 'simulated seconds', flush=True)
        assert minimum >= 2980 and maximum <= 7020
        report.update(status='PASS', minimum_bp=minimum, maximum_bp=maximum, final_ul=volume)
    except (AssertionError, OSError, RuntimeError) as error:
        report['status'] = 'FAIL'
        report['error'] = str(error)
    finally:
        session.close()
        model.close()
        report['wall_seconds'] = time.monotonic() - start
        (folder/'summary.json').write_text(json.dumps(report, indent=2) + '\n')
    print(report['status'], folder)
    if report['status'] != 'PASS':
        print(report['error'])
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
