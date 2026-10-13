# Public developer workflows — 2026-10-13

The lab now exposes `lab.py` for setup, prerequisite checks, workflow discovery,
guest builds, disposable cards, bounded runs, serial test firmware and matched
engine controls. esp-emulator 0.49.0 is the verified default. No emulator-core
or shipped CrossPoint firmware source was changed.

## Executed checks

| Check | Result and scope |
|---|---|
| `lab.py setup --engine all` | Selected QEMU/0.49.0 archives verified and extracted; Linux/amd64 Docker build completed using the existing layer cache. No stock download. |
| Custom build | `lab.py build --project probes/wifi-ap --environment c3` completed. An invalid environment returned failure with a complete retained log. |
| Built-in AP build | `lab.py build --profile ap` built and packaged the probe. Image/ELF hashes remained equal to the existing control. |
| AP CLI | Six checked uploads across three AP starts, matching guest upload records and valid teardown heap integrity. No reported bus fault or panic. |
| Reader CLI | QEMU on a fresh ALPHA SD image completed two renders and Home paint. Page 2/9 content was inspected; heap samples and logical SD counts match the earlier guide control. |
| Transfer CLI | esp-emulator 0.49.0 ran the full CrossPoint hotspot activity: identical 2,074-byte upload/download through guest SD, followed by the observed silent restart request. Reset was not executed. |
| Custom-image runner | The existing AP probe merged image reached `AP_READY` with normal exit and clean modeled execution. This validates startup and the runner, not the full AP workflow or an arbitrary candidate. Original image unchanged. |
| Negative custom-image run | With an impossible marker and three-second budget, the emulator exited 0 but the runner exited 1 and recorded `passed: false`. |
| Host checks | 35 regressions passed, Python compilation and whitespace checks passed, and current local documentation links resolved. |

Full-reader inputs remain the older control CrossPoint
`223c20b4864da9e7ee400d8234f7544fbbe54b62` / SDK
`aef1a6c89e36f331b2e1aacbbf7ce0debdeb732a`. The transfer run retains one
startup debugger read warning at `0x3ffffffc`; packet attribution is recorded.
No guest panic or unexplained bus fault was reported. Its final heap observation
precedes AP teardown; this does not prove post-reset or post-Wi-Fi recovery.

## Evidence

- [AP CLI](../evidence/2026-10-13/developer-cli-ap)
- [Reader CLI](../evidence/2026-10-13/developer-cli-reader)
- [Reader/control comparison](../evidence/2026-10-13/developer-cli-reader-comparison.json)
- [CrossPoint transfer CLI](../evidence/2026-10-13/developer-cli-transfer)
- [Custom-image startup](../evidence/2026-10-13/developer-firmware)
- [Missing-marker failure](../evidence/2026-10-13/developer-firmware-negative)

Archives omit binaries, SD images and raw RAM. The transfer's complete 3 MB
debugger trace remains local; the archive records its hash and startup-read
packet rather than including the entire trace.

## Publication and remaining coverage

These checks were recorded locally before publication. GitHub host CI and the
manual AP guest workflow are separate checks; consult the
[Actions runs](https://github.com/lpla/esp32-ereader-lab/actions) for their status.
A workflow definition alone is not executed CI evidence. No new physical-device
result is claimed.

Publication follow-up: source commit
`d31bfc4a5b4685d0d32a5ffcdc3cf591ccc6200c` passed
[host CI](https://github.com/lpla/esp32-ereader-lab/actions/runs/38422547708) and
[fresh AP guest CI](https://github.com/lpla/esp32-ereader-lab/actions/runs/38422604704).
The fresh Linux runner downloaded/verified 0.49.0, built the container and guest,
and completed six matching transfers across three AP starts with valid guest
heap integrity and no reported bus fault/panic. The downloaded result was also
checked locally with the AP validator. [Preserved CI evidence](../evidence/2026-10-13/github-ap-smoke)
includes input/engine hashes, build logs, UART and semantic results. This is the
standalone component, not full CrossPoint or physical-device validation.

Custom component firmware can now be supplied directly. Arbitrary latest-develop
full-reader builds still need verified ABI adapters; S3 device workflows,
reset/RTC recovery, physical timing/RF/e-paper and ARM/WSL end-to-end runs remain
unvalidated. See [testing your code](TESTING_YOUR_CODE.md) for exact scope.
