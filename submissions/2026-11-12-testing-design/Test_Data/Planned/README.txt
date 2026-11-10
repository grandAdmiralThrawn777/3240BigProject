DESIGN INPUTS ONLY - NOT EXECUTED FIRMWARE TESTS

These files define inputs for unfinished tank/sensor/serial/authentication
features. The executable host suite does not run them or count them as passes.
The PDF defines the expected outcomes, parameters, timing, and justifications.

tank_runs.json: T01-T06 initial conditions and run lengths. Unspecified run
fields inherit the top-level default. T06 runs each sample_ms_values entry.
tank_events.csv: profile,time_ms,event,value. Apply matching profile events
before sampling at the named timestamp. Missing events mean keep the current
parameter. Model output must distinguish actual valve from commanded valve.

sensor_events.csv: test_id,time_ms,level_bp,valid,sample_time_ms,expected_open,
expected_fault. Reset between IDs; default low/high 3000/7000, valve closed.
S02 intentionally holds the t=0 sample across intermediate control ticks.
Freshness validation and periodic ticks are not present in the C prototype.

auth_valid.txt: correctly tagged SET,3500,6500 command.
auth_modified.txt: changed low threshold with the original tag; reject.
auth_wrong_key.txt: a tag made with a different key; reject.
auth_missing_tag.txt, auth_short_tag.txt, auth_long_tag.txt,
auth_nonhex_tag.txt: malformed authentication field; reject.
auth_bad_range.txt: authentic but reversed thresholds; reject.
auth_overflow.txt: authentic but value 65536; reject before narrowing.
auth_replay.txt: A, B, A. Final settings may return to A because replay
protection is not in scope; record the limitation, not a replay-test pass.

test_key.hex: PUBLIC deterministic fixture, bytes 00 through 1f. Not a secret.
hmac_vectors.json: independent RFC 4231 case 1/2 digests. Compare the future
C library output against these, not just against its own generated tags.

serial_partial.bin: valid command without LF; timeout at age >500 ms.
serial_nul.bin: embedded NUL; reject without changing settings.
serial_length_127/128/129/1024.bin: that many X bytes followed by LF.
All have invalid grammar; the last two also exceed the 128-byte limit.
serial_flood.bin: exactly 10000 bytes; inject at 1000 bytes/s from t=20 s
through t=30 s in L01. Do not inject the entire file as one instantaneous burst.

The proposed protocol uses ASCII, canonical decimal fields, 64 lowercase
hex tag characters, and LF only. Host CSV CRLF support is separate from
this proposed serial wire grammar. Read byte fixtures in binary mode.

Additional scenarios in the PDF (restart, age/timeout boundaries, fragmented
commands, equal/excessive thresholds, and recovery) require the planned
adapter. These files are a starting data set, not a claim of complete coverage.
