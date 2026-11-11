Secure Embedded Water Tank Controller
Finley Burns - CYCS 3240

All five assignment goals are complete.

SUBMISSIONS
November 12 testing design: submissions/2026-11-12-testing-design
November 17 design presentation: submissions/2026-11-17-design-presentation
November 19 comprehensive design: submissions/2026-11-19-comprehensive-design
December final report: submissions/2026-12-final-report
December final presentation: submissions/2026-12-final-presentation

Download packages/ for the submission ZIPs. Each written assignment has one
PDF plus supporting files. Presentations have editable PPTX and speaking notes.

IMPLEMENTATION
implementation/ contains C17 source, Python build/test scripts, file inputs,
Mbed TLS source and its license. Read USER_GUIDE.txt and PORTABILITY.txt.
Native host tests passed on Windows, macOS and Linux on both x86-64 and ARM64.
Cortex-M4 ARM firmware separately passed sensor, serial and closed-loop tests
in Renode. The final report explains the measured results and their limits.

EVIDENCE
The final report submission includes raw traces, 18 native tank runs, 1815
ARM sensor/serial observations, 6001 ARM feedback samples, six-platform CI
artifacts and a fresh-extraction verification. Every package has file hashes.
November documents preserve their design-stage scope; the final report
describes the later implementation. The public key is demonstration data.
HMAC does not encrypt commands or prevent replay. Physical hardware was not
tested. Private handoff files and conversation history are not included.
