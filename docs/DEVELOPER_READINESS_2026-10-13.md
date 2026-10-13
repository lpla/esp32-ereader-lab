# Developer readiness — 2026-10-13

This report preserves the first setup audit. The subsequent public CLI update
made the verified 0.49.0 release the default; use the [developer guide](DEVELOPER_GUIDE.md)
for current commands. The guest results below retain their original inputs.

## Device audit

CrossPoint develop `c1a62f663172af69eda49e774c82ec7600836d01` pins SDK
`7fcd3b34c108f28c086ade3b433924022dbc0998`. Its build environments enable
eight device families: X3, X4, X4 Pro, X4 Classic, Sticky, PaperMono, Metalio
E-Ink 4 and EEGO A4. Simulator main
`1915ee0a15564c3f49d74fa2334f773f282c5364` covers all eight. PR #44 merged
on October 8. There is no new device profile gap in firmware-supported models.

Sources: [firmware environments](https://github.com/crosspoint-reader/crosspoint-reader/blob/c1a62f663172af69eda49e774c82ec7600836d01/platformio.ini#L266),
[simulator profiles](https://github.com/crosspoint-reader/crosspoint-simulator/blob/1915ee0a15564c3f49d74fa2334f773f282c5364/src/BoardConfig.h#L222)
and [merged EEGO PR](https://github.com/crosspoint-reader/crosspoint-simulator/pull/44).
[Recorded flags and revisions](../evidence/2026-10-13/device-audit.json).

The SDK has additional profiles, but an SDK flag alone is not a CrossPoint build
environment. This is a device-coverage audit, not new physical validation or a
claim that the latest full application has built in every simulator environment.

## Setup improvements

- `download.py` and `prepare.py` share `--engine` selection. Developers can
  install one engine or the default pair without stock firmware, WASM or
  historical packages. Preparation rejects hash mismatches even under `python -O`.
- `doctor.py` reports missing prerequisites and next commands, with JSON and a
  meaningful exit status. It checks Docker's Linux x86_64 execution, engine
  hashes and the selected guest package; it does not execute guest tests.
- Full-machine runs report missing/stale packages, missing cards and reused
  result names before creating run artifacts.
- The README and [developer guide](DEVELOPER_GUIDE.md) start with CrossPoint
  controls and explicit pinned-build limits. Archived stock setup is separate.

Host checks cover a fresh isolated selected-package extraction, corrupt-package
rejection, a Docker-free failure path and stale guest-source detection.

## esp-emulator 0.49.0

[Espressif released 0.49.0](https://github.com/espressif/esp-emulator/releases/tag/v0.49.0)
on October 13. It adds C3/S3 permission-monitor support and console fixes, among
other changes. The lab pins its Linux x86_64 package and executable. The initial
audit retained 0.48.0; the [public CLI update](DEVELOPER_WORKFLOWS_2026-10-13.md)
now makes 0.49.0 the default. No CrossPoint speedup claim is made from the
release's interpreter benchmark.

Executed with the same older CrossPoint/SDK control documented in the guide:

| Test | Result |
|---|---|
| Standalone AP server | Three AP starts, six checked uploads and teardown/integrity samples passed. No bus warnings or guest panic. |
| Full CrossPoint AP/SD activity | Uploaded and downloaded identical 2,074-byte EPUB content; reached the real silent-restart request. Reset remains unexecuted. |
| Full 6,001-entry shared-payload XTCH | Two renders and Home paint completed. Heap samples and logical SD counts match the existing 0.48.0 control. |
| 3,001-chapter EPUB | Incomplete: bounded run ended with GDB reporting `Remote connection closed`, after logs recorded 3,001 spine/TOC entries. No reader checkpoint; no guest panic or unexplained bus fault recorded. Do not call it a pass or infer an OOM cause. |
| Fresh generated ALPHA card, QEMU | Guide's reader workflow completed two renders and Home paint; screenshots checked for ALPHA page content. |

The full 0.49.0 machine runs retain one attributed startup GDB read warning at
`0x3ffffffc`. Their logs are not described as fault-free memory-safety proof.
SD sectors, GPIO/ADC and display transport still use the lab adapter; the guest
allocator, filesystem, parser and application code execute. Emulated timing is
not physical device timing.

Evidence: [standalone AP](../evidence/2026-10-13/ap49-developer),
[CrossPoint AP](../evidence/2026-10-13/developer49-crosspoint-ap),
[XTCH comparison](../evidence/2026-10-13/xtch49-comparison.json),
[incomplete large EPUB](../evidence/2026-10-13/developer49-3001-incomplete),
[fresh QEMU reader](../evidence/2026-10-13/developer-guide-reader).

Still pending: general candidate-build ABI derivation, full reset/RTC recovery,
post-Wi-Fi reader allocations, guest workloads in CI, broader S3 device tests
and end-to-end verification on ARM/WSL hosts. Host readiness checks do not prove
those workflows. Physical device validation belongs to the human tester.
