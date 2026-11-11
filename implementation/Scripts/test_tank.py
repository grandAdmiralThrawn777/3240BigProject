"""Connect the C tank model to the native C controller; compare every sample."""
import argparse
import csv
from fractions import Fraction
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import tempfile
from build import ROOT, build


class Program:
    def __init__(self, executable):
        self.process = subprocess.Popen([str(executable), '-'], stdin=subprocess.PIPE,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, bufsize=1)
        self.fields = self.process.stdout.readline().strip().split(',')

    def step(self, row):
        self.process.stdin.write(','.join(map(str, row)) + '\n')
        self.process.stdin.flush()
        line = self.process.stdout.readline()
        if not line:
            raise RuntimeError('C program stopped: ' + self.process.stderr.read())
        return dict(zip(self.fields, map(int, line.strip().split(','))))

    def close(self):
        self.process.stdin.close()
        self.process.wait(timeout=10)
        if self.process.returncode:
            raise RuntimeError(self.process.stderr.read())


def scenario(specification, events, folder, build_folder):
    suffix = '.exe' if os.name == 'nt' else ''
    controller = Program(build_folder/('runtime_runner' + suffix))
    model = Program(build_folder/('tank_model' + suffix))
    dt = specification['period_ms']
    duration = specification['duration_ms']
    capacity = 100000000
    volume = 50000000
    reference = Fraction(volume)
    previous = False
    forced = False
    demand = specification['demand_ul_s']
    minimum = 10000
    maximum = 0
    underflows = 0
    overflows = 0
    samples = 0
    trace = folder/(specification['name'] + '.csv')
    try:
        with trace.open('w', newline='') as stream:
            writer = csv.writer(stream)
            writer.writerow(['time_ms','volume_ul','level_bp','command_open','actual_open','fault',
                             'low','high','raw_next_ul','underflow','overflow'])
            for now in range(0, duration + 1, dt):
                for event in events:
                    if event['profile'] == specification['profile'] and event['time_ms'] == now:
                        if event['event'] == 'drain_ul_s':
                            demand = event['value']
                        else:
                            forced = bool(event['value'])
                level = volume * 10000 // capacity
                state = controller.step([now, level, now, 1, dt, '-'])
                if now:
                    if level < 3000:
                        previous = True
                    elif level > 7000:
                        previous = False
                assert state['open'] == int(previous), (now, state, previous)
                assert state['fault'] == int(now == 0), (now, state)
                assert state['deadlines'] == 0
                assert volume == int(reference), (now, volume, reference)
                actual = previous or forced
                current_volume = volume
                minimum = min(minimum, level)
                maximum = max(maximum, level)
                if now < duration:
                    result = model.step([dt, capacity, volume if now == 0 else 'continue',
                                         specification['inlet_ul_s'], demand, int(actual)])
                    reference += Fraction((int(actual) * specification['inlet_ul_s'] - demand) * dt, 1000)
                    reference = min(Fraction(capacity), max(Fraction(0), reference))
                    volume = result['volume']
                    underflows += result['underflow']
                    overflows += result['overflow']
                    raw = result['raw']
                else:
                    result = {'underflow': 0, 'overflow': 0}
                    raw = volume
                writer.writerow([now, current_volume,
                    level, state['open'], int(actual), state['fault'], state['low'], state['high'],
                    raw, result['underflow'], result['overflow']])
                samples += 1
        if specification['profile'] in ['normal', 'demand']:
            bound = (200 * dt + 999) // 1000 + 1
            assert minimum >= 3000 - bound and maximum <= 7000 + bound
            assert not underflows and not overflows
        if specification['profile'] == 'shortage':
            assert volume == 0 and underflows and previous
        if specification['profile'] == 'stuck_open':
            assert volume == capacity and overflows and not previous
        return {'name': specification['name'], 'samples': samples, 'minimum_bp': minimum,
            'maximum_bp': maximum, 'final_ul': volume, 'underflows': underflows,
            'overflows': overflows, 'sha256': hashlib.sha256(trace.read_bytes()).hexdigest(), 'passed': True}
    finally:
        controller.close()
        model.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cc')
    args = parser.parse_args()
    build_folder = build(args.cc)
    directory = Path(tempfile.mkdtemp(prefix='tank-', dir=ROOT/'Runs'))
    data = json.loads((ROOT/'Test_Data/Runtime/tank.json').read_text())
    for specification in data['runs']:
        duration = specification['duration_ms']
        period = specification['period_ms']
        if type(duration) is not int or type(period) is not int or period not in [50, 100, 500] or not 0 < duration <= 3600000 or duration % period:
            raise ValueError('Invalid tank duration or sample period')
        for field in ['inlet_ul_s', 'demand_ul_s']:
            if type(specification[field]) is not int or not 0 <= specification[field] <= 3000000:
                raise ValueError('Invalid tank flow rate')
        if specification['profile'] not in ['normal', 'demand', 'shortage', 'stuck_open']:
            raise ValueError('Unknown tank profile')
        if not specification['name'].replace('_', '').isalnum():
            raise ValueError('Invalid output name')
    for event in data['events']:
        if type(event['time_ms']) is not int or not 0 <= event['time_ms'] <= 3600000 or event['time_ms'] % 500:
            raise ValueError('Invalid event time')
        if event['event'] not in ['drain_ul_s', 'force_open'] or type(event['value']) is not int:
            raise ValueError('Invalid event')
        if not 0 <= event['value'] <= (3000000 if event['event'] == 'drain_ul_s' else 1):
            raise ValueError('Invalid event value')
    report = {'status': 'INCOMPLETE', 'platform': platform.platform(), 'architecture': platform.machine(),
              'execution': 'Native C closed-loop simulation, not Renode', 'runs': []}
    try:
        for specification in data['runs']:
            report['runs'].append(scenario(specification, data['events'], directory, build_folder))
        for name in ['T01', 'T02', 'T06_50', 'T06_100', 'T06_500']:
            hashes = {value['sha256'] for value in report['runs'] if value['name'].startswith(name + '_')}
            assert len(hashes) == 1, 'Nonrepeatable: ' + name
        report['status'] = 'PASS'
    except (AssertionError, OSError, RuntimeError) as error:
        report['status'] = 'FAIL'
        report['error'] = str(error)
    (directory/'summary.json').write_text(json.dumps(report, indent=2) + '\n')
    print(report['status'], directory)
    if report['status'] != 'PASS':
        print(report['error'])
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
