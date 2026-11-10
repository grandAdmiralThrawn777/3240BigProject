"""Create deterministic file-driven cases and explicit expected observations."""
from pathlib import Path
import hashlib
import hmac
import json

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'Test_Data/Runtime'
DATA.mkdir(parents=True, exist_ok=True)
KEY = bytes(range(32))
manifest = []


def signed(message, key=KEY):
    return message + b',' + hmac.new(key, message, hashlib.sha256).hexdigest().encode() + b'\n'


def row(now, level=2500, timestamp=None, valid=1, period=100, rx=b''):
    return [now, level, now if timestamp is None else timestamp, valid, period, rx.hex() or '-']


def case(name, rows, checks, exit_code=0):
    path = DATA / (name + '.csv')
    path.write_text('# now,level,sample_ms,valid,period,rx_hex\n' +
                    ''.join(','.join(map(str, value)) + '\n' for value in rows))
    manifest.append({'name': name, 'file': path.name, 'expected_exit': exit_code, 'checks': checks})


case('age_and_recovery', [row(100), row(200, timestamp=0), row(300, timestamp=0),
    row(400, timestamp=99), row(500), row(600, valid=0), row(700, level=10001),
    row(800, timestamp=801), row(900), row(1000, level=7000), row(1100, level=7001)],
    {str(i): {'open': value, 'fault': fault} for i, (value, fault) in enumerate([
        (1, 0), (1, 0), (1, 0), (0, 1), (1, 0), (0, 1), (0, 1), (0, 1), (1, 0), (1, 0), (0, 0)])})
case('deadline', [row(100), row(299), row(499), row(599)],
    {'0': {'open': 1}, '1': {'open': 1, 'deadlines': 0},
     '2': {'open': 0, 'fault': 1, 'deadlines': 1}, '3': {'open': 1, 'fault': 0}})
case('wrap', [row(4294967200), row(4, timestamp=4294967200), row(104, timestamp=4294967200),
    row(204, timestamp=4294967200), row(304, timestamp=4294967200)],
    {'1': {'open': 1, 'fault': 0}, '2': {'open': 1}, '3': {'open': 1}, '4': {'fault': 1, 'open': 0}})
case('periods', [row(50, period=50), row(100, period=50), row(200), row(700, period=500)],
    {str(i): {'ran': 1, 'open': 1, 'deadlines': 0} for i in range(4)})

commands = {
    'valid': signed(b'SET,2000,8000'),
    'wrong_key': signed(b'SET,2000,8000', b'wrong'),
    'modified': signed(b'SET,2000,8000').replace(b'2000', b'2001'),
    'equal': signed(b'SET,3000,3000'),
    'reversed': signed(b'SET,8000,2000'),
    'range': signed(b'SET,0,10001'),
    'uint_overflow': signed(b'SET,65536,7000'),
    'huge_integer': b'SET,' + b'9' * 150 + b',7000,' + b'0' * 64 + b'\n',
    'leading_zero': signed(b'SET,02000,8000'),
    'negative': signed(b'SET,-1,8000'),
    'plus': signed(b'SET,+1,8000'),
    'space': signed(b'SET, 1,8000'),
    'nul': b'SET,20\x000,8000,' + b'0' * 64 + b'\n',
    'nonhex': b'SET,2000,8000,' + b'z' * 64 + b'\n',
    'uppercase': signed(b'SET,2000,8000').upper(),
    'short_tag': b'SET,2000,8000,' + b'0' * 63 + b'\n',
    'long_tag': b'SET,2000,8000,' + b'0' * 65 + b'\n',
    'missing_tag': b'SET,2000,8000\n',
    'extra_field': signed(b'SET,2000,8000').rstrip(b'\n') + b',1\n',
    'crlf': signed(b'SET,2000,8000').replace(b'\n', b'\r\n'),
}
for name, command in commands.items():
    rows = [row(100 * (i + 1), rx=command if i == 0 else b'') for i in range(9)]
    if name == 'valid':
        expected = {'accepted': 1, 'low': 2000, 'high': 8000, 'auth': 1}
    else:
        expected = {'accepted': 0, 'low': 3000, 'high': 7000}
    case('command_' + name, rows, {'8': expected})

valid = signed(b'SET,2000,8000')
case('apply_next_tick', [row(100, rx=valid), row(200), row(300), row(400, level=1500)],
    {'2': {'accepted': 1, 'low': 2000, 'open': 1}, '3': {'open': 1}})
case('replay', [row(100 * (i + 1), rx=command) for i, command in enumerate(
    [valid, b'', b'', signed(b'SET,3500,6500'), b'', b'', valid, b'', b''])],
    {'8': {'accepted': 3, 'low': 2000, 'high': 8000}})
case('timeout_recovery', [row(100, rx=b'SET,'), row(200), row(300), row(400), row(500), row(600),
    row(700, rx=valid), row(800), row(900)],
    {'5': {'rejected': 0}, '8': {'accepted': 1, 'rejected': 1}})
case('overflow_recovery', [row(100, rx=b'x' * 257), row(200, rx=b'\n'),
    row(300, rx=valid), row(400), row(500)],
    {'0': {'queued': 0, 'overflows': 1, 'accepted': 0}, '4': {'accepted': 1}})
case('queue_256', [row(1, rx=b'x' * 256), row(100)],
    {'0': {'queued': 256, 'overflows': 0}, '1': {'queued': 224, 'bytes': 32}})
case('flood_safety', [row(100 * (i + 1), valid=0 if i == 5 else 1, rx=b'x' * 100) for i in range(10)],
    {'5': {'open': 0, 'fault': 1}, '9': {'deadlines': 0}})

(DATA / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
vectors = json.loads((ROOT / 'Test_Data/Planned/hmac_vectors.json').read_text())
# A long key exercises the hash-key branch, checked against Python's separate library.
for key, message in [(b'\xaa' * 131, b'Test Using Larger Than Block-Size Key - Hash Key First'),
                     (b'', b''), (bytes(range(256)), bytes(range(256)))]:
    vectors.append({'source': 'Python hmac reference', 'key_hex': key.hex(),
        'data_hex': message.hex(), 'sha256': hmac.new(key, message, hashlib.sha256).hexdigest()})
(DATA / 'hmac.csv').write_text(''.join(v['key_hex'] + ',' + v['data_hex'] + '\n' for v in vectors))
(DATA / 'hmac_expected.json').write_text(json.dumps(vectors, indent=2) + '\n')
print('Created', len(manifest), 'runtime files and', len(vectors), 'HMAC vectors.')
