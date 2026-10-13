# Testing your own code

The public CLI supports your own PlatformIO builds and serial component tests.
Full CrossPoint SD/display/input workflows currently require the pinned X4/C3
adapter. New firmware revisions and other boards need a verified adapter before
those workflows can provide trustworthy results.

## Build your project

```sh
python3 lab.py build --project /absolute/path/to/project --environment your-test-env
```

The project must contain `platformio.ini`, and the environment is mandatory.
The lab invokes the installed `pio`, preserves its exit status and writes the
complete build output under `results/build-logs/`. It does not check out a revision,
edit your source, substitute a SDK, or repackage the pinned reader control as
if it were your candidate. PlatformIO may download dependencies and write its
normal build outputs inside the supplied project.

## Prepare a component test

Build an ESP32-C3 test that exercises the actual module under investigation.
Keep its allocator/network implementation in the guest. Emit a unique serial
marker such as `HEAP_CASE_PASS` only after every assertion passes. For heap
work, record free heap, minimum heap, largest allocatable block and allocator
integrity at meaningful phases. A total free-heap number alone does not measure
fragmentation. Avoid using desktop time as a physical performance measurement.

Supply a **merged flash binary at offset zero** containing the bootloader,
partition table at `0x8000`, and application at its declared offset. An OTA file
or bare `.pio/build/<environment>/firmware.bin` is insufficient. Some projects,
including the pinned CrossPoint build, generate `firmware.factory.bin`; otherwise
use the project's documented esptool merge procedure and exact flash offsets.
The runner checks header chip IDs and required layout entries; it is not a
replacement for esptool's complete image validation.

```sh
python3 lab.py firmware --image /path/to/merged-flash.bin \
  --source /path/to/project --chip esp32c3 --name heap-base \
  --expect HEAP_CASE_PASS --seconds 60
```

The result lives in `results/heap-base/`:

- `input.json`: original image hash/layout, runner source hashes, test scope, engine selection and
  optional source Git head, tracked diff hash, status and submodule revisions.
  Untracked file contents are not hashed; the executed binary hash is recorded.
- `command.json` and `uart.log`: exact invocation and guest output.
- `result.json`: marker observation, exit status, fault diagnostics, engine hash,
  and pass/fail. The test stops when the marker is observed. Later behavior is
  outside that assertion.
- `source-check.json`: whether the original image remained unchanged.

The emulator works on `flash.bin`, a private copy in that result directory.
Guest flash writes execute in the emulator, but this runner does not request
`--save-state`: persisted NVS/flash across runs is not asserted. The final copy's
file hash is recorded. Tests use an
isolated container and no board-address hooks. There is no SD, e-paper, button or
AP host-forwarding adapter in this generic path. A full CrossPoint image can
therefore stall on hardware initialization; use a focused test or implement and
verify the missing adapter. `--chip esp32s3` checks S3 image IDs, but an S3 run
has not been validated in this lab. It does not establish X4 Pro support.

A missing marker, abnormal exit, host deadline, reported panic, assertion/abort
or unexplained bus fault fails. A marker printed before an assertion would be a
bad guest test; the runner cannot infer what your test intended to prove.

## Compare a base and candidate

Build the exact base and candidate using the same environment, SDK, fixture and
test source. Use separate run names and retain both input hashes. Confirm the
control passes, the candidate-specific assertion was reached, and the expected
output differs where the change requires it. Record substitutions explicitly.
Do not attach a component result to a claim about a full unexecuted PR.

For a full reader candidate, first derive its symbols and verify the live object
layouts and hook contracts in `scripts/prepare_machine.py` and
`scripts/crosspoint-board.gdb`. Do not disable the control revision checks or
reuse addresses from another binary. Current build/run support deliberately
rejects such a mismatch. A maintainable candidate adapter is still needed for
arbitrary latest-develop full-reader tests.

## Agents and CI

Use `lab.py profiles --json` to choose a supported scope and `doctor --json` for
prerequisites. Run an explicit assertion with a new result name and bounded
budget. Preserve incomplete results; do not convert a clean exit to a feature
pass. Never send an upstream review merely because a control test completed.

The host suite runs on pushes and pull requests. The manual **AP guest smoke**
workflow builds the standalone probe and exercises the default pinned engine.
It uploads logs and JSON, without binaries or SD images. Check the
[Actions runs](https://github.com/lpla/esp32-ereader-lab/actions) for execution
status; a workflow definition is not executed CI evidence.
