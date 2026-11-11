"""Recreate the supplied fixtures. These files contain test inputs, not results."""
from pathlib import Path
import csv
import hashlib
import hmac
import json

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'Test_Data'


def write_csv(path, header, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', newline='', encoding='ascii') as stream:
        stream.write('# ' + ','.join(header) + '\n')
        writer = csv.writer(stream, lineterminator='\n')
        writer.writerows(rows)


def main():
    for part in ['Control', 'Parser', 'Planned']:
        (DATA / part).mkdir(parents=True, exist_ok=True)
    rows = []
    # Expectations are grouped by the stated boundary rules.
    for level in [0, 2999, 3000, 3001, 5000, 6999, 7000, 7001, 10000]:
        for previous in [0, 1]:
            expected = 1 if level < 3000 else 0 if level > 7000 else previous
            rows.append([level, 1, 3000, 7000, previous, expected, 0])
    for level in [10001, 65535]:
        for previous in [0, 1]:
            rows.append([level, 1, 3000, 7000, previous, 0, 1])
    for level in [0, 5000, 10000]:
        for previous in [0, 1]:
            rows.append([level, 0, 3000, 7000, previous, 0, 1])
    for low, high in [(7000, 3000), (3000, 3000), (3000, 10001), (0, 0), (65535, 65535)]:
        for previous in [0, 1]:
            rows.append([5000, 1, low, high, previous, 0, 1])
    for low, high in [(0, 10000), (0, 1), (9999, 10000)]:
        for level in sorted({0, low, high, 10000}):
            for previous in [0, 1]:
                expected = 1 if level < low else 0 if level > high else previous
                rows.append([level, 1, low, high, previous, expected, 0])
    header = ['level_bp', 'valid', 'low', 'high', 'previous_open', 'expected_open', 'expected_fault']
    write_csv(DATA / 'Control/boundaries.csv', header, rows)
    # Literal expectations make the stateful regression independent of tank_step.
    sequence = [
        [1,2500,1,3000,7000,0,1,0], [0,3000,1,3000,7000,0,1,0],
        [0,5000,1,3000,7000,0,1,0], [0,7000,1,3000,7000,0,1,0],
        [0,7001,1,3000,7000,0,0,0], [0,7000,1,3000,7000,0,0,0],
        [0,5000,1,3000,7000,0,0,0], [0,3000,1,3000,7000,0,0,0],
        [0,2999,1,3000,7000,0,1,0], [0,5000,0,3000,7000,0,0,1],
        [0,5000,1,3000,7000,0,0,0], [0,2500,1,3000,7000,0,1,0],
        [0,2500,1,7000,3000,0,0,1], [0,7000,1,3000,7000,0,0,0],
        [1,5000,1,3000,7000,1,1,0], [0,10001,1,3000,7000,0,0,1],
        [0,7500,1,3000,7000,0,0,0], [0,2500,1,3000,7000,0,1,0],
    ]
    write_csv(DATA / 'Control/sequence.csv', ['reset','level_bp','valid','low','high','start_open','expected_open','expected_fault'], sequence)
    record = b'2500,1,3000,7000,0,1,0'
    files = {
        'truncated.csv': record.rsplit(b',',1)[0]+b'\n',
        'overflow.csv': b'65536,1,3000,7000,0,1,0\n',
        'huge_integer.csv': b'9'*100+b',1,3000,7000,0,1,0\n',
        'extra.csv': record+b',9\n', 'oversized.csv': b'1'*300+b'\n',
        'empty.csv': b'', 'embedded_nul.csv': record+b'\0extra\n',
        'negative.csv': b'-1,1,3000,7000,0,1,0\n',
        'nonnumeric.csv': b'abc,1,3000,7000,0,1,0\n',
        'plus.csv': b'+'+record+b'\n', 'space.csv': b' '+record+b'\n',
        'boolean.csv': b'2500,2,3000,7000,0,1,0\n',
        'empty_field.csv': b'2500,,3000,7000,0,1,0\n',
        'trailing_text.csv': record+b'garbage\n', 'comments_only.csv': b'# no data\n',
        'ctrl_z.csv': record+b'\n\x1aextra\n',
        'too_long_256.csv': b'0'*(255-len(record))+record+b'\n',
        'nul_in_comment.csv': b'# comment\0hidden\n'+record+b'\n',
        'lf.csv': record+b'\n', 'crlf.csv': b'\r\n'+record+b'\r\n',
        'no_final_newline.csv': record,
        'limit_255.csv': b'0'*(254-len(record))+record+b'\n',
        'wrong_expectation.csv': b'2500,1,3000,7000,0,0,0\n',
    }
    manifest = []
    accepted = {'lf.csv','crlf.csv','no_final_newline.csv','limit_255.csv'}
    for name, data in files.items():
        (DATA/'Parser'/name).write_bytes(data)
        code = 0 if name in accepted else 1 if name == 'wrong_expectation.csv' else 2
        manifest.append({'file':name, 'expected_exit':code, 'bytes':len(data)})
    (DATA/'Parser/manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    # Planned integration data are intentionally kept out of the executable host suite.
    plan = {
        'status':'DESIGN ONLY - no tank model or Renode adapter implemented',
        'capacity_l':100, 'initial_l':50, 'initial_valve_open':False,
        'low_bp':3000, 'high_bp':7000, 'sample_ms':100,
        'max_sample_age_ms':300, 'sensor_quantization_bp':1,
        'rounding':'floor(10000 * volume_l / capacity_l)',
        'event_order':'apply events; sample; controller; advance volume using actual valve',
        'event_file':'tank_events.csv',
        'runs':[
            {'id':'T01','profile':'normal','duration_s':600,'inlet_lps':2,'drain_lps':1,'repetitions':3},
            {'id':'T02','profile':'demand','duration_s':600,'inlet_lps':2,'drain_lps':1,'repetitions':3},
            {'id':'T03','profile':'shortage','duration_s':600,'inlet_lps':2,'drain_lps':3,'repetitions':1},
            {'id':'T04','profile':'stuck_open','duration_s':120,'inlet_lps':2,'drain_lps':1,'repetitions':1},
            {'id':'T05','profile':'normal','duration_s':3600,'inlet_lps':2,'drain_lps':1,'repetitions':1},
            {'id':'T06','profile':'normal','duration_s':600,'sample_ms_values':[50,100,500],'inlet_lps':2,'drain_lps':1,'repetitions':3},
        ]
    }
    (DATA/'Planned/tank_runs.json').write_text(json.dumps(plan,indent=2)+'\n')
    write_csv(DATA/'Planned/tank_events.csv', ['profile','time_ms','event','value'], [
        ['demand',200000,'drain_lps',0.5], ['demand',400000,'drain_lps',1.5],
        ['stuck_open',10000,'force_valve_open',1],
    ])
    write_csv(DATA/'Planned/sensor_events.csv', ['test_id','time_ms','level_bp','valid','sample_time_ms','expected_open','expected_fault'], [
        ['S01',0,2500,1,0,1,0], ['S01',100,2500,0,100,0,1], ['S01',200,5000,1,200,0,0],
        ['S02',0,2500,1,0,1,0], ['S02',300,2500,1,0,1,0], ['S02',400,2500,1,0,0,1],
        ['S03',0,2500,1,0,1,0], ['S03',100,65535,1,100,0,1], ['S03',200,2500,1,200,1,0],
    ])
    key = bytes(range(32))
    payload = b'SET,3500,6500'
    tag = hmac.new(key,payload,hashlib.sha256).hexdigest().encode('ascii')
    command = payload+b','+tag+b'\n'
    (DATA/'Planned/test_key.hex').write_text(key.hex()+'\n')
    (DATA/'Planned/auth_valid.txt').write_bytes(command)
    (DATA/'Planned/auth_modified.txt').write_bytes(command.replace(b'SET,3500',b'SET,3501',1))
    other = b'SET,3000,7000'
    other_command = other+b','+hmac.new(key,other,hashlib.sha256).hexdigest().encode()+b'\n'
    (DATA/'Planned/auth_replay.txt').write_bytes(command+other_command+command)
    bad_range = b'SET,7000,3000'
    (DATA/'Planned/auth_bad_range.txt').write_bytes(bad_range+b','+hmac.new(key,bad_range,hashlib.sha256).hexdigest().encode()+b'\n')
    (DATA/'Planned/auth_wrong_key.txt').write_bytes(payload+b','+hmac.new(b'wrong-test-key',payload,hashlib.sha256).hexdigest().encode()+b'\n')
    (DATA/'Planned/auth_missing_tag.txt').write_bytes(payload+b'\n')
    (DATA/'Planned/auth_short_tag.txt').write_bytes(payload+b','+tag[:-2]+b'\n')
    (DATA/'Planned/auth_long_tag.txt').write_bytes(payload+b','+tag+b'00\n')
    (DATA/'Planned/auth_nonhex_tag.txt').write_bytes(payload+b',z'+tag[1:]+b'\n')
    overflow = b'SET,65536,7000'
    (DATA/'Planned/auth_overflow.txt').write_bytes(overflow+b','+hmac.new(key,overflow,hashlib.sha256).hexdigest().encode()+b'\n')
    (DATA/'Planned/serial_partial.bin').write_bytes(command[:-1])
    (DATA/'Planned/serial_nul.bin').write_bytes(payload+b'\0,'+tag+b'\n')
    (DATA/'Planned/serial_flood.bin').write_bytes((b'X'*99+b'\n')*100)
    for length in [127,128,129,1024]:
        (DATA/f'Planned/serial_length_{length}.bin').write_bytes(b'X'*length+b'\n')
    (DATA/'Planned/hmac_vectors.json').write_text(json.dumps([
        {'source':'RFC 4231 test case 1','key_hex':'0b'*20,'data_hex':b'Hi There'.hex(), 'sha256':'b0344c61d8db38535ca8afceaf0bf12b881dc200c9833da726e9376c2e32cff7'},
        {'source':'RFC 4231 test case 2','key_hex':b'Jefe'.hex(),'data_hex':b'what do ya want for nothing?'.hex(), 'sha256':'5bdcc146bf60754e6a042426089575c75a003f089d2739839dec58b964ec3843'}
    ],indent=2)+'\n')
    print(f'Created {len(rows)} boundary cases, {len(sequence)} sequence steps, {len(manifest)} parser files.')


if __name__ == '__main__':
    main()
