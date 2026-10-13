# ESP32 e-reader lab

Run embedded firmware tests before moving to real hardware. This repository
packages Espressif QEMU and esp-emulator with reproducible setup, CrossPoint
board adapters, disposable SD fixtures, bounded tests, and recorded results.
It complements the [CrossPoint Simulator](https://github.com/lpla/crosspoint-simulator):
the simulator is fast for UI work; these tests execute the guest allocator,
FreeRTOS, filesystem and supported networking code.

## Quick start

Requirements: Python 3.12+, Docker running Linux containers, and PlatformIO CLI
for guest builds. The container uses Linux x86_64; Intel macOS is the tested host.

```sh
git clone https://github.com/lpla/esp32-ereader-lab.git
cd esp32-ereader-lab
python3 lab.py setup --engine esp-emu
python3 lab.py doctor
python3 lab.py build --profile ap
python3 lab.py doctor --profile ap
python3 lab.py run --profile ap --name first-ap
```

The AP test checks six uploads over three hotspot starts, including payload
checksums and guest heap integrity. See `results/first-ap/result.json` and
`uart.log`. Use a new name for each run: existing evidence is preserved.

The default is SHA256-pinned **esp-emulator 0.49.0**, the latest release checked
on October 13, 2026. QEMU is pinned to **esp-develop-9.2.2-20260417**.
`setup --engine all` installs both; `--esp-version 0.48.0` or `0.45.0` selects an
older control explicitly. Setup does not download stock firmware.

## Choose a workflow

| Workflow | Command | What it validates | Current limit |
|---|---|---|---|
| Embedded AP | `lab.py run --profile ap` | Guest HTTP uploads, AP restart, heap integrity | Standalone component, no CrossPoint activity |
| CrossPoint reading | `lab.py run --profile reader --card …` | Guest SD/EPUB, page turn, Home paint | Verified X4/C3 control and ABI; QEMU preferred |
| CrossPoint transfer | `lab.py run --profile file-transfer --card …` | Hotspot upload/download through guest SD | Observes restart request; does not execute reset |
| Your test firmware | `lab.py firmware --image … --expect …` | Explicit serial assertion in your own merged image | No SD, input or display board adapter |

`python3 lab.py profiles --json` exposes workflow descriptions and limits to
agents. `doctor --json` returns readiness, errors and suggested fixes with a
nonzero exit status when prerequisites are missing. Both work without a guest run.

## Test your own code

```sh
python3 lab.py build --project /path/to/your/project --environment your-test-env
python3 lab.py firmware --image /path/to/merged-flash.bin \
  --source /path/to/your/project --name candidate-heap \
  --chip esp32c3 --expect TEST_PASS --seconds 60
```

Your test must emit the marker only after its assertions pass. The runner checks
the chip and merged-image layout, copies the image, verifies the engine, and
records logs and a semantic result. A normal exit without the marker fails.
See [testing your code](docs/TESTING_YOUR_CODE.md) for image requirements,
base/candidate comparisons and the distinction between component tests and full
CrossPoint integration. ESP32-S3 selection is available but not validated here.

## Documentation and repository layout

- [Developer guide](docs/DEVELOPER_GUIDE.md): installation, full reader/SD test,
  file transfer, result inspection and troubleshooting.
- [Testing your code](docs/TESTING_YOUR_CODE.md): custom builds and tests for humans
  and agents.
- [Architecture and extension points](docs/ARCHITECTURE.md): CLI, profiles,
  engine pins, adapters and evidence.
- [Emulation roadmap](docs/ROADMAP.md): remaining limitations and useful next work.
- [Documentation index](docs/README.md): current guidance and historical reports.
- [Contributing](CONTRIBUTING.md) and [agent instructions](AGENTS.md).

`lab.py` is the public entry point; `config/` describes workflows, `adapters/`
defines verified engine/board contracts, `probes/` holds buildable guest tests,
`scripts/` implements the runners, and `tests/` checks host behavior. Generated
packages, builds, cards and complete results are ignored by Git. Selected
reviewable evidence belongs in `evidence/`.

## Validation boundaries

Full reader runs currently use CrossPoint
`223c20b4864da9e7ee400d8234f7544fbbe54b62` and FreeInk SDK
`aef1a6c89e36f331b2e1aacbbf7ce0debdeb732a`, not latest develop. Arbitrary firmware
cannot use that adapter without ABI verification. Large SD/EPUB workloads are
more practical in QEMU; esp-emulator supplies useful guest Wi-Fi tests.

Neither engine establishes device speed, RF behavior, SD timing, e-paper optical
output, power consumption or reset/RTC retention. Screenshots capture firmware
display requests. A completed component test is evidence for that component,
not a pass for an unexecuted PR or a physical device.

The lab adds harnesses and adapters; it does not fork either emulator core.
Closed-stock feature research is stopped; its [historical reports](docs/README.md#historical-reports)
remain available separately. Harness code and docs are MIT licensed; see
[NOTICE.md](NOTICE.md) for third-party material.
