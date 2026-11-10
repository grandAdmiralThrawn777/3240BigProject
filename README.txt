Secure Embedded Water Tank Controller
Finley Burns - CYCS 3240

I am building a C17 controller for one simulated tank, sensor and inlet valve.
The valve opens below the low threshold, closes above the high threshold,
and keeps its previous state between them and at either endpoint.

Submissions
  November 12: submissions/2026-11-12-testing-design
  November 17: submissions/2026-11-17-design-presentation
  November 19: submissions/2026-11-19-comprehensive-design
  December final report: drafts/final-report (unfinished)

The three November deliverables are ready. Each report has one PDF plus its
supporting files. Presentation slides are editable PPTX with speaking notes.
Download packages/ for the organized submission ZIPs.

Implementation
  implementation/Source: shared C code, host programs, ARM firmware
  implementation/Test_Data: inputs read from files
  implementation/Scripts: portable build and test commands
  implementation/Evidence: recorded local results
  implementation/PORTABILITY.txt: OS and processor instructions

Host builds target x86-64 and ARM64 on Windows, macOS and Linux. The separate
embedded target is Cortex-M4 ARM in Renode. The Actions workflow checks each
host OS/processor pair. Read the actual job results before calling a platform
verified. Windows x86-64 tests passed locally; ARM firmware compiled and its
first GPIO test ran in Renode. System integration is still in progress.

The November submissions are milestone snapshots. The final implementation
directory contains later work and may be ahead of those documents. The final
report and presentation remain open goals until testing and analysis finish.

The HMAC key is public demonstration data. Commands are authenticated but not
encrypted, and replay is not prevented. Private handoff and chat files are
excluded from this repository.
