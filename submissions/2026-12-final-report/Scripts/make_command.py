"""Write one demonstration command using the public 00..1f test key."""
import argparse
import hashlib
import hmac
from pathlib import Path

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('low', type=int)
parser.add_argument('high', type=int)
parser.add_argument('output', type=Path)
args = parser.parse_args()
if not 0 <= args.low < args.high <= 10000:
    parser.error('Require 0 <= low < high <= 10000.')
message = f'SET,{args.low},{args.high}'.encode('ascii')
tag = hmac.new(bytes(range(32)), message, hashlib.sha256).hexdigest().encode('ascii')
with args.output.open('xb') as stream:
    stream.write(message + b',' + tag + b'\n')
print('Wrote demonstration command:', args.output)
