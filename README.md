# ESP32 e-reader lab

Run CrossPoint's embedded firmware and focused regression probes in Espressif
QEMU and esp-emulator. Guest tests add the C3 allocator, 32-bit ABI, FreeRTOS and
Wi-Fi/lwIP behavior to the native simulator's fast UI coverage.

Current work is emulator reliability and reproducing CrossPoint problems.
Closed-stock feature comparisons stopped on 2026-10-08; the earlier experiments
remain archived in [SOURCE_FEATURES.md](docs/SOURCE_FEATURES.md) and
[FEATURE_SCOPE.md](docs/FEATURE_SCOPE.md).

Start with [the current runner improvements and evidence](docs/REGRESSION_RUNNERS.md).
The default newer engine is hash-pinned esp-emulator **0.48.0**. QEMU remains
`esp-develop-9.2.2-20260417`; 0.45.0 stays available for explicit engine-version
controls. These are harness and adapter improvements, not emulator-core forks.

A firmware-created AP now supports automated host uploads and real guest AP
teardown/restart. The full CrossPoint web activity also uploads/downloads an
EPUB through its actual SD filesystem and reaches the AP-exit restart request.
Full-reader checkpoints require a paint from the current
activity, and debugger register handling avoids speculative zero-address reads.
See [older issue/PR results and feedback decisions](docs/REGRESSION_RUNNERS.md#older-work-and-feedback).

Download engines without closed firmware:

```sh
python3 scripts/download.py --emulators-only
python3 scripts/prepare.py --emulators-only
docker build -t crosspoint-esp-emulation-lab:2026-10-04 .
pio run -d probes/wifi-ap
python3 scripts/prepare_ap.py
docker run --rm --network none -v "$PWD:/work" \
  crosspoint-esp-emulation-lab:2026-10-04 \
  python3 scripts/probe_ap.py --name my-ap-test
```

## Earlier coverage (0.45.0; historical)

| Capability | QEMU | esp-emulator v0.45.0 |
|---|---|---|
| X4 home screen, scripted Right/Select | Verified | Verified |
| Settings screen | Verified | Verified |
| Partial display update composition | Verified | Verified |
| Change displayed language | Observed; persistence unverified | Not validated |
| Stock SD-backed EPUB reading and page turn | Verified via sector adapter | First-page render observed; full case incomplete |
| EPUB chapter/menu/bookmark/reopen probes | Verified with diagnostic reader-clock offset | Not validated |
| Guest C3 allocator fragmentation/recovery control | Verified with UART transport observer | Verified in independent IDF/Arduino probe |
| Guest Wi-Fi/DHCP/HTTP, isolated PR #3612 TCP DF A/B | Wi-Fi unsupported by documented model | Verified; full CrossPoint integration/carrier behavior untested |
| X4 Pro stock/Licorice usable reader | Not attempted | Blocked during bring-up |
| Full CrossPoint C3 cold EPUB / page turn / exit | Verified guest workflow | Verified guest workflow |
| Historical #2332 ditherer output, cleanup and fragmented-heap tradeoff | Verified component A/B | Verified component A/B |
| Full CrossPoint 6,001-entry XTCH page turn / exit | Verified; shared-payload table fixture | Verified; shared-payload table fixture |
| Stock Auto Flip page advancement | Verified; clock substituted | Not validated |
| Physical display/power/timing accuracy | Not validated | Not validated |

Both engines produced byte-identical panel buffers for navigation and Settings. See the [experiment report](REPORT.md), [recorded evidence](evidence/2026-10-04), and [executed EPUB comparison](docs/EPUB_COMPARISON.md).

![Stock Settings screen](evidence/2026-10-04/qemu-x4-settings/screen.png)

## Quick start

Requirements: Docker, Python3.12+, and Linux x86_64 containers. Intel macOS was tested. ARM hosts may require Docker's x86_64 emulation; that host configuration has not been validated here.

```sh
git clone https://github.com/lpla/esp32-ereader-lab.git
cd esp32-ereader-lab
python3 scripts/download.py
python3 scripts/prepare.py
docker build -t crosspoint-esp-emulation-lab:2026-10-04 .
python3 scripts/run_lab.py --engine qemu --scenario settings --prefix first-settings
```

For the SD-backed book probe, rebuild the container after updating the repository, then:

```sh
python3 scripts/create_card.py
python3 scripts/run_lab.py --engine qemu --scenario book --card cards/base.img --prefix first-book
```

The source card is copied per run. Firmware cache/bookmark writes go to `results/<run>/card.img`; inspect it using `mtools`, with the FAT partition offset `@@1048576`. Original EPUB/TXT fixtures are generated from source; `create_card.py --fixture beta --name beta` adds the CSS/image probe and `--fixture gamma --name gamma` adds the 120-chapter probe. No privileged mount or physical SD card is needed. See [SD adapter details](docs/SD_ADAPTER.md).

Other scenarios include `baseline`, `right`, `language`, `folder`, `book-page`, `book-controls`, `book-chapters`, `book-chapter-two`, `book-bookmark`, `book-reopen`, and `book-stride-cycle`. See the runner help for diagnostic probes. SD scenarios require `--card`; `book-page` uses the side Down button. Engines: `qemu`, `esp-emu`, `both`. Each prefix must be new so prior evidence is preserved. Reader menu/held-input scenarios use a documented Arduino-millis offset; they are unsuitable for timing or performance measurements.

The runner emits JSON with status and artifact paths. Screens are saved as `results/<run>/screen.png`; individual display writes, logs, commands and hashes accompany them. A successful process/GDB exit alone does not mean a feature passed: inspect the screen and the scenario's actual behavior.

Downloads are pinned and checked against SHA256 hashes. No emulator executables, ROMs, stock firmware, personal flash backups or SD contents are bundled in Git. `download.py` fetches the documented public sources; their licenses/provenance remain separate from this harness. An Internet connection is needed to download/build; guest test containers run with networking disabled.

## How it works

- `scripts/probe.py` controls bounded emulator/GDB sessions in Docker.
- `scripts/x4-*.gdb` supply GPIO/ADC responses and button schedules for the pinned application.
- `scripts/x4-display-capture.gdb` reads display-driver calls without changing their instructions.
- `scripts/render_display.py` retains panel RAM and composes full/partial writes into PNGs using the Python standard library.
- `scripts/wasm_probe.mjs` exercises the published WASM JavaScript API with instruction/time limits (Node18+).

The screenshots represent firmware requests to the display driver. They do not model e-paper waveforms, ghosting, BUSY timing or optical output. Raw framebuffer RAM is reused for partial windows, so repeatedly dumping the same buffer is insufficient.

## Current priority

Use **QEMU** for practical SD/EPUB regressions and **esp-emulator 0.48.0** for
embedded Wi-Fi/AP workflows. Keep CrossPoint's allocator, filesystem, parser,
rendering and activity code executing; label the board transport supplied by the
adapter. The [current report](docs/REGRESSION_RUNNERS.md) records exact source
pins, completed and incomplete runs, and older issue/PR feedback decisions.

Exact candidate comparisons remain necessary before commenting on a PR. The
existing [hardware PR results](docs/HARDWARE_PR_TESTING.md) and
[historical tests](docs/HISTORICAL_TESTS.md) distinguish component probes from
full firmware integration. Controls do not establish that an unexecuted
candidate passed. Physical timing, RF, reset/RTC retention and complete board
emulation remain separate validation work.

The earlier stock/CrossPoint feature catalogue and comparison are archived in
[SOURCE_FEATURES.md](docs/SOURCE_FEATURES.md) and
[EPUB_COMPARISON.md](docs/EPUB_COMPARISON.md). CrossInk comparison is outside the
current scope.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). Include the image hash, hook ABI evidence, commands, logs, input sequence and screenshots with new support. Distinguish an original flash image from a constructed fixture, and substituted hardware behavior from feature behavior. Keep timeouts and failed probes visible.

Harness source and documentation are MIT licensed. See [NOTICE.md](NOTICE.md) for third-party firmware, tools and UI evidence.
