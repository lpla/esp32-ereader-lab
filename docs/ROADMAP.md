# Emulation roadmap

Priorities below follow the lab's current gaps, not general emulator feature
lists. The goal is useful, reproducible evidence for CrossPoint changes before
hardware testing. An item is complete when its assertions execute and recorded
negative cases fail as expected.

## 1. Run actual candidate full-reader builds

The full-reader path currently accepts one older control, while custom images
support serial component tests. Add explicit project/environment/ELF/image
inputs for full-reader runs, derive addresses and object members from that ELF,
and validate the selected FreeInk board contract. Keep a manifest per build;
reject missing symbols, mismatched images and incompatible layouts.

Use a separate checkout for each base/head. Preserve the requested SDK revision
and record local overrides rather than silently changing them. A matched
candidate workflow must accept different firmware hashes while requiring shared
fixtures and test assertions; the current `check` command only compares identical
firmware engine controls.

Completion: latest develop and an exact PR base/head both read the same EPUB,
turn pages, paint Home, preserve expected content and record guest heap/SD
observations. A deliberately mismatched ELF or unsupported profile is rejected.

## 2. Diagnose the large EPUB and reduce debugger overhead

The esp-emulator 0.49.0 3,001-spine test ended with `Remote connection closed`
without a completed reader checkpoint. Do not classify this as OOM or a guest
hang without evidence. QEMU remains the practical control.

Record execution progress, emulator/GDB lifetimes, guest heap phases and time
spent servicing SD/log/display hooks. Minimize a failing case and separate a
host budget or adapter bottleneck from an emulator or firmware defect. Use
upstream tracing where it works without altering the code under test.

If the boundary adapter dominates, reduce unnecessary GDB transactions or move
SD/device transport into an emulator peripheral model. A faster workaround must
still execute the guest filesystem/parser/allocator; host parsing is not a
replacement for this test.

Completion: the large control reaches indexing, expected content, page turn and
Home within a documented budget, or a minimal reproducible defect is isolated
with logs sufficient for the correct upstream owner.

## 3. Execute reset and validate persistence

The AP test stops at CrossPoint's restart request. Extend it to execute reset,
observe a second boot and validate landing state, SD progress/cache, and NVS.
Test RTC retention separately for each reset type; flash persistence does not
prove RTC retention. Operate only on disposable copies.

esp-emulator exposes `--control-tcp` reset operations and `--save-state`; these
are existing upstream mechanisms to evaluate, not proof that CrossPoint's
software-reset/RTC paths already work. Verify firmware-triggered reset as well
as host-triggered reset.

Completion: an asserted boot counter/reset reason, expected persisted state and
post-boot reader paint are observed. A lost/corrupt state case is detected.

## 4. Test the complete network and heap lifecycle

Go beyond hotspot upload/download: station association, disconnect/reconnect,
DHCP/DNS, HTTP/TLS and representative CrossPoint clients. Use deterministic local
services in an isolated test network, with controlled delays, dropped connections,
bad responses and truncated payloads; avoid depending on public services.

Measure guest free/minimum heap, largest block and integrity before networking,
after traffic, after teardown, and after reopening/turning an EPUB. Repeated
cycles should expose leaks, fragmentation and allocation-failure behavior. Keep
the guest network stack and allocator executing. A success verdict needs both
content/protocol assertions and meaningful cleanup/reader checkpoints.

Completion: a repeatable base/head regression with a useful failure-injection
case, plus recorded post-network reader allocations. RF, interference and
carrier behavior remain hardware checks.

## 5. Add verified board/device models

Start with the C3 X3/X4 profile differences, then S3/X4 Pro. Derive panel sizes,
input wiring, flash and PSRAM from the actual selected SDK profile. Test the
configured memory capacity, allocation capabilities and relevant core behavior;
selecting `--chip esp32s3` alone does not establish a supported e-reader.

Prefer native SPI SD, GPIO/ADC/input and panel-controller models where feasible.
Boundary adapters remain useful for parser/UI regressions, but cannot expose
driver initialization, DMA, bus arbitration or peripheral timing defects they
bypass. Upstream CPU/peripheral defects belong in the emulator projects; board
composition, workloads and assertions belong in this lab.

Completion: each advertised board has a boot/read/turn/exit test, asserted panel
dimensions/input, verified memory configuration and explicit substitutions.

## 6. Improve regression automation and reporting

Expand guest CI from the standalone AP smoke to reader and candidate workflows.
Pin the container/dependency inputs, cache builds, preserve complete failures and
publish machine-readable assertions. Validate ARM/WSL workflows separately.

Expose ELF-backed task/PC tracing and stack/heap diagnostics, then automate
content checks against generated EPUB markers and expected screens. Guest
instruction/task observations can support relative software comparisons;
emulator wall time cannot establish physical device speed or battery use.

Completion: a fresh runner can reproduce the supported scenarios, report exact
base/head inputs and failing assertions, and retain useful artifacts without
binaries, private data or raw RAM.

## Limits that still require hardware

Functional peripheral models can reduce many gaps. Physical e-paper waveforms,
ghosting, RF behavior, electrical SD failures, power consumption and precise
device timing still require a hardware reference. Emulator-vs-hardware traces can
calibrate selected behavior, but do not establish general silicon equivalence.

Keep the native simulator for fast UI iteration, QEMU for the established large
SD/EPUB path, and esp-emulator as the main networking/S3 improvement target.
Avoid maintaining two implementations of every new capability unless a second
engine supplies a useful independent control.

Sources: [executed lab results](DEVELOPER_WORKFLOWS_2026-10-13.md),
[esp-emulator reset, persistence, tracing and PSRAM contracts](https://github.com/espressif/esp-emulator/blob/v0.49.0/README.md),
and [Espressif QEMU supported-peripheral guidance](https://docs.espressif.com/projects/esp-idf/en/stable/esp32c3/api-guides/tools/qemu.html).
