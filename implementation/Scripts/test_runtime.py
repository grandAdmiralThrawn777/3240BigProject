"""Run file-driven security, timing and integer-model checks on the native host."""
import argparse
import csv
import io
import json
import os
from pathlib import Path
import platform
import subprocess
import tempfile
from datetime import datetime, timezone
from build import ROOT, build


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cc')
    parser.add_argument('--sanitize', action='store_true')
    args = parser.parse_args()
    folder = build(args.cc, sanitize=args.sanitize)
    results = ROOT / 'Runs'
    results.mkdir(exist_ok=True)
    evidence = Path(tempfile.mkdtemp(prefix='runtime-', dir=results))
    report = {'status': 'INCOMPLETE', 'date': datetime.now(timezone.utc).isoformat(),
              'platform': platform.platform(), 'architecture': platform.machine(), 'checks': []}

    def run(program, fixture, name, expected=0):
        exe = folder / (program + ('.exe' if os.name == 'nt' else ''))
        command = [str(exe), str(fixture)]
        result = subprocess.run(command, capture_output=True, text=True, timeout=30)
        (evidence / (name + '.stdout.txt')).write_text(result.stdout)
        (evidence / (name + '.stderr.txt')).write_text(result.stderr)
        report['checks'].append({'id': name, 'command': command, 'exit': result.returncode,
                                 'expected_exit': expected, 'passed': False})
        assert result.returncode == expected, name + ': wrong exit status'
        return result.stdout

    try:
        data = ROOT / 'Test_Data/Runtime'
        for case in json.loads((data / 'manifest.json').read_text()):
            output = run('runtime_runner', data / case['file'], case['name'], case['expected_exit'])
            rows = list(csv.DictReader(io.StringIO(output)))
            for index, fields in case['checks'].items():
                for name, value in fields.items():
                    assert int(rows[int(index)][name]) == value, f"{case['name']} row {index} {name}: {rows[int(index)][name]} != {value}"
            previous = 0
            for row in rows:
                assert int(row['bytes']) <= 32
                assert 0 <= int(row['auth']) - previous <= 1
                previous = int(row['auth'])
            report['checks'][-1]['passed'] = True
        actual = run('hmac_runner', data / 'hmac.csv', 'hmac_vectors').splitlines()
        expected = [value['sha256'] for value in json.loads((data / 'hmac_expected.json').read_text())]
        assert actual == expected, 'HMAC mismatch'
        report['checks'][-1]['passed'] = True
        model_data = data / 'model.csv'
        model_data.write_text('100,100000000,50000000,2000000,1000000,1\n'
                              '100,100000000,continue,2000000,1000000,0\n'
                              '100,100000000,0,2000000,3000000,0\n'
                              '100,100000000,100000000,2000000,1000000,1\n'
                              '50,100000000,0,1,0,1\n' +
                              '50,100000000,continue,1,0,1\n' * 19)
        rows = list(csv.DictReader(io.StringIO(run('tank_model', model_data, 'model_units'))))
        assert [int(row['volume']) for row in rows[:4]] == [50100000, 50000000, 0, 100000000]
        assert int(rows[2]['raw']) == -300000 and rows[2]['underflow'] == '1'
        assert int(rows[3]['raw']) == 100100000 and rows[3]['overflow'] == '1'
        assert rows[-1]['volume'] == '1' and rows[-1]['remainder'] == '0'
        report['checks'][-1]['passed'] = True
        report['status'] = 'PASS'
    except (AssertionError, OSError, subprocess.TimeoutExpired) as error:
        report['status'] = 'FAIL'
        report['error'] = str(error)
    (evidence / 'summary.json').write_text(json.dumps(report, indent=2) + '\n')
    print(report['status'], evidence)
    if report['status'] != 'PASS':
        print(report['error'])
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
