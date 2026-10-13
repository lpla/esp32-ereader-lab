# Developer guide

Use the native simulator for fast UI checks, QEMU for practical guest SD/EPUB
regressions, and esp-emulator for guest Wi-Fi tests. Start with a known control
before investigating a particular issue or PR.

## Requirements and setup

Install Python 3.12+, Docker with Linux containers, Git, and PlatformIO CLI
(`pio --version`). Initial setup and guest builds need Internet access. Test
containers run with `--network none`; AP forwards are container-local loopback.

```sh
python3 lab.py setup --engine all
python3 lab.py doctor --engine qemu
python3 lab.py doctor --engine esp-emu
python3 lab.py profiles
```

`all` installs only QEMU and the default esp-emulator **0.49.0**. Choose `qemu`
or `esp-emu` to install one. Select an older engine with `--esp-version` on setup,
doctor and run. Existing evidence retains its recorded version.

Archives and executables are SHA256 checked, and extraction uses Python's data
filter. Do not modify a pin to bypass a mismatch. Remove only the corrupt download
and repeat setup. No stock firmware or historical WASM is needed.

The container is built as `linux/amd64`. Intel macOS is exercised here. ARM hosts
may use Docker's x86_64 translation; doctor checks container execution but does
not establish that every guest workflow works there. WSL with Docker integration
is the suggested Windows route, but that host workflow remains unvalidated.

## First test: embedded AP

```sh
python3 lab.py build --profile ap
python3 lab.py doctor --profile ap
python3 lab.py run --profile ap --name first-ap
```

This guest runs the Wi-Fi stack and allocator, performs six checked HTTP uploads
across three AP starts, and records teardown heap-integrity samples. It has no
SD card and does not execute CrossPoint's activity. `result.json` and `uart.log`
are stored in `results/first-ap/`. The guest test has a fixed bounded budget.

## Full CrossPoint: SD reading

The adapter supports the explicit control CrossPoint
`223c20b4864da9e7ee400d8234f7544fbbe54b62`, SDK
`aef1a6c89e36f331b2e1aacbbf7ce0debdeb732a`. It is not current develop. The build
lives in ignored `tools/crosspoint-machine`, separate from your checkout. The
preparation script verifies symbols and object layout before packaging it.

```sh
python3 lab.py build --profile reader
python3 lab.py card --name base
python3 lab.py doctor --profile reader --card cards/base.img
python3 lab.py run --profile reader --name first-reader \
  --card cards/base.img --book /alpha.epub --scenario turn-exit
```

The default engine is QEMU and budget 180 seconds. The runner copies the SD image,
executes the guest filesystem/parser/renderer/allocator, and requires two page
renders plus a paint after entering Home. Inspect `verdict.json`,
`checkpoint.json`, `guest.log`, `sd-events.json` and the PNGs. Check expected page
content as well as workflow completion. This is a board transport adapter;
physical SD and display timing are not exercised.

`lab.py card --fixture beta` creates a media fixture, and `--fixture gamma`
creates a chapter fixture. Pass `/beta.epub` or `/gamma.epub` as `--book`.
Advanced large-TOC and XTCH fixtures are documented in
[the regression report](REGRESSION_RUNNERS.md).

Run the same scenario with `--engine esp-emu --debug-remote` to capture debugger
packets for warning attribution. Its default budget is 300 seconds. QEMU remains
preferred for large EPUBs: the 0.49.0 3,001-spine run did not reach a completed
checkpoint. This is an incomplete result, not a diagnosed firmware failure.

## CrossPoint hotspot transfer

```sh
python3 lab.py doctor --profile file-transfer --card cards/base.img
python3 lab.py run --profile file-transfer --name first-crosspoint-ap \
  --card cards/base.img --debug-remote
```

The default engine is esp-emulator. The test creates a hotspot, uploads ALPHA,
and downloads identical bytes through the actual guest SD filesystem.
`http-result.json` records transfer assertions. Back reaches the silent restart
request; the observer stops before reset. Reboot landing, RTC retention and
post-reboot heap recovery remain untested.

## Custom firmware and comparisons

Follow [testing your code](TESTING_YOUR_CODE.md) for your own PlatformIO project
and merged test image. `lab.py build --project` leaves source selection and SDK
pinning to you; built-in `build --profile reader` always builds the known control.

For two completed reader engine controls using identical firmware and input:

```sh
python3 lab.py check results/qemu-reader results/esp-reader
```

This requires the current activity-paint checkpoint protocol and compares
recorded checkpoints, input, source pins, heap samples and SD counts. It rejects
different firmware or inputs; it is not a candidate-PR comparison. It does not
assert that rendered content is correct or validate an unsupported ABI. Inspect
screens and candidate-specific assertions separately.

## Troubleshooting and automation

- `doctor --json` exits 0 only when every selected check passes. It checks
  Docker/image execution, executable hashes and guest package hashes. It neither
  installs dependencies nor starts a guest workflow.
- Missing `pio`: install PlatformIO CLI before building. Existing packaged
  guests can run without PlatformIO.
- Stale guest package: rebuild with `lab.py build --profile …`. Advanced users
  can run `scripts/prepare_machine.py --package` on an already-built clean control.
- Existing result/card name: choose a new name. Each run modifies its own SD copy.
- Incomplete checkpoint: inspect guest logs, debugger status and process result.
  A timeout, disconnect or normal exit alone does not establish a pass.
- A GDB startup read at `0x3ffffffc` can produce an esp-emulator bus warning.
  `--debug-remote` records attribution; the warning remains visible. This is not
  proof of physical memory safety.

`python3 lab.py test` runs host regressions. Host CI does not execute all guests;
the optional AP guest workflow must be explicitly dispatched. Every guest
assertion needs its recorded scope: component, full firmware or physical device.
