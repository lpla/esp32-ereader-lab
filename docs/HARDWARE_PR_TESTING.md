# Guest heap and networking PR experiments — 2026-10-04

**esp-emulator v0.45.0 is useful for controlled guest allocator and network-stack
tests. An actual CrossPoint networking PR module passed a baseline/candidate
experiment. Full CrossPoint SD-font workloads, physical radio behavior and
device performance remain unvalidated.**

Keep QEMU for the already-working stock X4 SD/EPUB comparison. Use esp-emulator
for these network experiments: [Espressif's QEMU support table](https://github.com/espressif/esp-toolchain-docs/blob/main/qemu/README.md)
marks Wi-Fi unsupported. QEMU's OpenETH network adapter exercises a different
interface and cannot validate station-driver reconnect behavior. This division
avoids bringing up a second network path just to repeat weaker tests.

## What executes, and what is modeled?

The independent [C3 probe](../probes/esp32c3/src/main.cpp) runs compiled
Arduino-ESP32 3.3.11 / ESP-IDF v5.5.5 firmware, including the guest heap allocator,
Wi-Fi station API and lwIP stack. These versions match the pinned PlatformIO
platform used by the current CrossPoint checkout. It is a devkit-targeted lab
application with 4 MiB flash, not the full Xteink/CrossPoint board application.
The baseline starts with 263,448 free internal/8-bit-capable heap bytes.

The emulator executes the ROM/bootloader/application path, while intercepting
selected ROM functions, including Wi-Fi TX. Its [documentation](https://github.com/espressif/esp-emulator/blob/8b20ca7c40b8a3d3b2d865984cbc5ed1ddd780b0/README.md)
describes a built-in access point and user-mode NAT. Thus “no substituted Wi-Fi
driver” in the guest record means no lab/GDB replacement of guest Wi-Fi APIs;
it does **not** mean RF hardware or every ROM operation is simulated faithfully.
Raw model internals are not distributed in that repository.

Each run uses a Docker container with `--network none`. The emulator's gateway
`192.168.4.1` maps to loopback **inside that container**. An HTTP server bound to
`127.0.0.1:8088` serves only this experiment. No physical adapter, Internet
endpoint or mobile hotspot is involved. No GPIO, ADC, SD or clock GDB hooks are
used in these C3 probes.

## Executed PR #3612: TCP Don't Fragment

[PR #3612](https://github.com/crosspoint-reader/crosspoint-reader/pull/3612)
changes station IPv4 output to set DF on whole TCP packets and repair the IP
checksum. Exact code from head
`85ff81e8aab78533476f4db57986f71f18ee231a` was fetched, SHA-checked and compiled
unchanged. The [source manifest](../probes/esp32c3/pr-manifest.json) pins
`src/network/TcpDontFragment.cpp` and `.h`. A logging-only adapter supplies the
project macros; no packet behavior is reimplemented by the lab.

Both builds share the same probe. The baseline excludes the PR translation
unit; the candidate compiles it and calls `applyTcpDontFragment()` twice after
each of three station connections. An observer sits **after the PR wrapper and
before the original IPv4 output callback**. It reads actual guest headers,
checks their one's-complement checksum and delegates without modifying them.
The observer is installed through the lwIP task, and counters are atomic.

Each cycle sends a UDP datagram and completes an HTTP GET, disconnects and
destroys the station interface, then the next cycle reconnects. The candidate
therefore exercises both repeated installation and installation on a new netif.
The wrapper's production call site in `WifiSelectionActivity` is not executed
by this isolated harness; full-application integration remains a separate test.

| Recorded result across three cycles | Baseline | Candidate |
|---|---:|---:|
| DHCP / station connection | 3/3 | 3/3 |
| HTTP 200 / local server requests | 3/3 | 3/3 |
| Observed TCP packets | 17 | 18 |
| TCP packets with DF | 0 | 18 |
| Observed UDP packets / UDP with DF | 3 / 0 | 3 / 0 |
| Invalid IPv4 checksums | 0 | 0 |
| Guest heap integrity checks | All pass | All pass |

Packet totals are snapshots of this workload, not an entire-link PCAP or a
requirement that both runs emit equal ACK counts. Every cycle independently
checks TCP DF, UDP preservation and checksum validity. The [baseline](../evidence/2026-10-04/tcp-df-base),
[candidate](../evidence/2026-10-04/tcp-df-patched) and
[machine-checked comparison](../evidence/2026-10-04/tcp-df-comparison.json)
retain commands, image hashes and UART records.

**Validated:** this module changes the observed whole-TCP headers correctly,
leaves the tested station UDP headers unchanged, and remains operational after
the tested repeated installations/reconnects.

**Not validated:** carrier 464XLAT/hotspot compatibility, fragmented IPv4 input,
oversized TCP payloads, AP-mode output, IPv6, TLS, full CrossPoint file transfer,
or all possible netif teardown races. The tiny local HTTP workload is sufficient
for the stated header contract; it is not proof of the original carrier fix.

## Executed allocator fragmentation control

The same probe uses a fixed static table of 128 pointers and deliberately
allocates fallible 2 KiB blocks until no more fit (118 blocks in these runs).
It frees alternating entries, requests a block 1 KiB larger than the largest
free block, then frees all surviving allocations. Deliberate dynamic allocation
is the subject of this test; a stack buffer would not exercise heap contiguity.
The bounded static pointer table avoids repeated metadata allocation.

| Internal/8-bit heap phase | Free bytes | Largest block |
|---|---:|---:|
| Baseline | 263,448 | 122,868 |
| After allocating blocks | 5,312 | 1,268 |
| Alternate blocks freed | 134,316 | 2,292 |
| All blocks freed | 263,448 | 122,868 |

A 3,316-byte request failed despite 134,316 bytes total free. The allocator
recovered exactly to the original free/largest values; integrity stayed valid.
This is a useful positive control: the guest test distinguishes free capacity
from contiguous capacity, unlike the native simulator's synthetic host heap.
It is **not** an SD-font fragmentation reproduction or evidence that a font PR
improves the reader.

Wi-Fi initialization/deinitialization also changes the measured heap. After the
three cycles, baseline free heap is 242,528 bytes and candidate 242,784, both
with largest block 114,676. Those small between-run differences do not establish
a leak or memory improvement. Deferred cleanup, driver state and TCP pools need
isolated controls. The since-boot minimum is dominated by the earlier deliberate
allocation exhaustion and cannot measure Wi-Fi's minimum. Use a separate
Wi-Fi-only workload before analyzing that watermark.

A prior simpler heap/Wi-Fi run also completed three HTTP requests
([evidence](../evidence/2026-10-04/soc-c3-esp)). QEMU's bounded run of that same
guest produced no diagnostic records before termination
([failure retained](../evidence/2026-10-04/soc-c3-qemu)); its boot/UART behavior
was not diagnosed, so that run supplies no executed allocator verdict.

## Current PR suitability

Heads were checked live on 2026-10-04. Claims in their descriptions are authors'
reported measurements, not measurements reproduced by this lab.

| PR / issue | Pinned head | Emulator assessment and actual status |
|---|---|---|
| [#3612 TCP DF](https://github.com/crosspoint-reader/crosspoint-reader/pull/3612) | `85ff81e8aab78533476f4db57986f71f18ee231a` | **Executed isolated module pass**, limits above |
| [#3831 SD-font fragmentation](https://github.com/crosspoint-reader/crosspoint-reader/pull/3831) | `f2d55c34787c808ea6c5494e858da90b0981494e` | Guest allocator is suitable in principle; exact base `f1d0af1afdcec5118f829bae11c310cec81b1ec4` and candidate need real CP font/layout allocations plus SD workload. **Not executed** |
| [#3705 advance-cache memory](https://github.com/crosspoint-reader/crosspoint-reader/pull/3705), draft | `bd4117603579d4a6ebd4b116e4dfd54b5a40e47c` | Same prerequisite, with both uniform and varying-width fonts. Its description explicitly distinguishes retained memory from fragmentation and reports a varying-width regression. **Not executed** |
| [#3702 heap tracing](https://github.com/crosspoint-reader/crosspoint-reader/pull/3702) | `695d71298cbfb418f88a9dff1f7a6da22ad9e800` | C3 tracing is promising, but its static ring changes the memory budget. First establish non-tracing A/B, then use tracing diagnostically. Unwinder, hooks and USB capture need validation. **Not executed** |
| [#2127 web-server restart after reconnect](https://github.com/crosspoint-reader/crosspoint-reader/pull/2127) | `606a0c871740f8049d3ee2757218b0b6d6ca03ce` | Guest reconnects are demonstrated, but the actual CrossPoint web-server lifecycle is absent from the probe. Require requests before/after reconnect and repeated cycles. **Not executed** |
| [#3564 Wi-Fi fragmentation on touch devices](https://github.com/crosspoint-reader/crosspoint-reader/issues/3564) | Issue, not a tested PR | C3 probe cannot establish S3/touch-board reproduction. Need matching chip/PSRAM, firmware and interaction workload; no diagnosis claimed |

For font PRs, preserve exact parent/candidate source, SDK, compile flags,
allocator configuration, font bytes and EPUB bytes. A development branch with
unrelated memory changes is not the baseline. Capture cold open, font preparation,
first layout, foreground page turns, background layout, cache eviction and reader
exit. At matched checkpoints collect free heap, largest block, low-water mark,
failed allocation size and integrity. Compare rendered text/landings too; memory
savings with incorrect metrics are not a pass. Uniform and varying-width fonts
are both necessary, especially for #3705.

An SD sector adapter can preserve the filesystem/parser allocation workload but
removes SPI/DMA/SD timing and associated lower-driver allocations. It cannot
validate `storageMutex` races or driver-level memory behavior. The existing X4
adapter has closed-firmware addresses and is not an adapter for CrossPoint.
Therefore a whole-CrossPoint machine runner remains the blocking prerequisite
for those reading PRs. Host-only stubs would invalidate the reason to use a
machine emulator.

## Reproduce the executed C3 A/B

Requirements: the prepared emulator/container, PlatformIO and the pinned platform
download. The build log, source hashes and image provenance are archived under
`evidence/2026-10-04/soc-*`. Build timestamps can change binary hashes on rebuild;
the archived hashes identify the executed images, not a promised reproducible ELF.

```sh
python3 scripts/prepare_soc.py
pio run -d probes/esp32c3 -e c3 -e c3_df
python3 scripts/prepare_soc.py --images
docker run --rm --network none --cpus 2 --memory 1g -v "$PWD:/work" \
  crosspoint-esp-emulation-lab:2026-10-04 python3 scripts/probe_soc.py \
  --engine esp-emu --image /work/firmware/soc-c3-df-base.bin --name df-baseline
docker run --rm --network none --cpus 2 --memory 1g -v "$PWD:/work" \
  crosspoint-esp-emulation-lab:2026-10-04 python3 scripts/probe_soc.py \
  --engine esp-emu --image /work/firmware/soc-c3-df-patched.bin --name df-candidate
python3 scripts/check_soc.py results/df-baseline/status.json results/df-candidate/status.json
```

All run names must be new to preserve earlier evidence. Check the JSON verdict,
not just the emulator exit code. Host tests reject missing cycles, wrong TCP DF,
changed UDP DF, bad checksums and heap corruption using the archived guest records.
CI verifies the harness/evidence contracts; it does not rerun the guest firmware.

## Boundary of confidence

Suitable now: guest allocation order/capacity/contiguity, controlled OOM and
recovery, selected IPv4/lwIP behavior, local station reconnects and isolated
modules using the tested APIs.

Needs more work: actual CrossPoint display/input/SD bring-up, full reader/font
workloads, S3-specific failures, deterministic checkpoint instrumentation and
repeatable workload scheduling. Avoid replacing allocators or network APIs when
testing those components.

Needs physical-device corroboration: RF quality, carrier routing, power/deep
sleep, optical e-paper behavior, SD electrical/DMA timing, flash-cache suspension
windows, contention/interruption timing and battery-dependent failures. Emulator
wall-clock speed is not reader performance, and a modeled timer alone does not
establish realistic task scheduling.
