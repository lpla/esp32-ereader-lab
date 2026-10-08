# CrossPoint regression runners — 2026-10-08

Closed-stock feature investigation has stopped. The current work is making
embedded CrossPoint tests reliable and useful for developers. QEMU and
esp-emulator run target machine code, FreeRTOS and the embedded allocator; the
native simulator remains the faster choice for UI tests. Board adapters supply
SD sectors, ADC/GPIO and display transport without replacing the allocator,
filesystem, parser or application lifecycle.

These changes are in the lab harness, not emulator-core forks. The newer engine
defaults to **esp-emulator 0.48.0**, whose release adds host reachability for
firmware-created APs. QEMU remains `esp-develop-9.2.2-20260417`.
[Espressif release notes](https://github.com/espressif/esp-emulator/releases/tag/v0.48.0)
describe that new model support; the executed tests below establish this lab's
coverage. Both engine executables are hash-pinned in
[engines.json](../adapters/engines.json); 0.45.0 remains selectable as a control.

## Reader and debugger fixes

- The runner terminates the emulator at the stopped checkpoint, before GDB
  disconnects. It no longer deliberately resumes the guest for half a second
  after removing its board-transport adapters. That interval manufactured a
  previous post-detach SPI panic.
- RV32 register reads/writes use checked remote packets. After writes, the
  adapter flushes GDB's register/frame cache. Omitting that flush caused an
  unsuccessful prototype to restart unexpectedly; it is not accepted evidence.
- The old expression-based register setter triggered speculative GDB reads at
  address zero. A captured control has **1,235 `m0,2` requests and 1,235 matching
  unmapped-read warnings**. The accepted full XTCH runs have **zero** such
  requests or warnings. One startup `m3ffffffc,4` query still produces a matching
  warning in esp-emulator. We retain it and its attribution; it is not a guest
  null-pointer finding or physical memory-safety proof.
- Checkpoint protocol 2 resets the paint flag on activity entry and records the
  activity for each display submission. Home completion now requires a Home
  paint after entering, preventing an earlier reader paint from satisfying exit.
  Legacy logs remain readable, but `--require-activity-paint` rejects their
  weaker checkpoint contract.
- Diagnostic reports retain bus warnings, guest panics and lockup messages
  separately from workflow completion. Timeouts are never successes.

The firmware is still the explicit control
`223c20b4864da9e7ee400d8234f7544fbbe54b62`, SDK
`aef1a6c89e36f331b2e1aacbbf7ce0debdeb732a`, Arduino 3.3.11 / IDF 5.5.5.
It is **not relabeled as current develop**. The current device audit uses develop
`43694c9018d26446ab30cce2fa65ee608355ae50` and SDK `425d200a...`.

The corrected 6,001-entry XTCH workflow completes two page renders and a Home
paint in QEMU and esp-emulator 0.48.0. Both read 500 sectors and write 81;
largest block is 114,676 bytes and minimum free is 45,536. Final free differs by
64 bytes (QEMU 143,936; newer engine 144,000), so heap equality is not asserted.
QEMU reports no bus warning or panic. esp-emulator reports only the attributed
startup debugger query and no guest panic. The older 0.45.0 register-transport
control also completes; its protocol-1 checkpoint is retained separately.

[Protocol-2 comparison](../evidence/2026-10-08/checkpoint2-comparison.json),
[QEMU run](../evidence/2026-10-08/checkpoint2-qemu-xtch),
[newer-engine run](../evidence/2026-10-08/checkpoint2-esp48-xtch),
[debugger attribution](../evidence/2026-10-08/legacy-remote-summary.json).

```sh
python3 scripts/run_machine.py --engine qemu --name my-qemu-xtch \
  --card cards/xtc-table6001-two.img --book /table6001.xtch \
  --scenario turn-exit --seconds 180
python3 scripts/run_machine.py --engine esp-emu --debug-remote --name my-esp-xtch \
  --card cards/xtc-table6001-two.img --book /table6001.xtch \
  --scenario turn-exit --seconds 300
python3 scripts/check_machine.py results/my-qemu-xtch results/my-esp-xtch \
  --require-activity-paint
```

`--debug-remote` records packet traces for attribution. `summarize_remote.py`
keeps hashes, counts and excerpts; publication can omit the multi-megabyte
packet log. Symbol-only ELF and a custom-unwinder experiment were bounded and
unsuccessful here; they are not the chosen reader path. Modeled timers and host
run duration are not physical performance measurements.

## Firmware-created AP coverage

The new standalone C3 probe starts a real guest `WiFi.softAP`, serves HTTP with
Arduino WebServer, and takes heap/integrity samples. An isolated container
forwards only its loopback port; no external network or physical device is used.

Three AP starts, two teardown/restart cycles and final teardown complete. Each
cycle uploads **4,097 and 262,177 bytes**. All six host responses and guest
completed-upload records match the payload length and FNV-32 checksum. Heap
integrity is valid at every sample; there are no bus warnings or guest panics.
The server does not retain whole upload bodies in the probe. This is transport
coverage, not the CrossPoint web activity, SD writes, AP station-limit enforcement
or a verdict on #1459/#2127. Retained network/framework state is recorded rather
than presented as a leak diagnosis.

The next integration run also executes **CrossPoint's own web activity**:
automated ADC button inputs navigate Home → File Transfer → Create Hotspot,
the host reads `/api/status` reporting AP mode, uploads the original 2,074-byte
ALPHA EPUB through `/upload`, and retrieves identical bytes through `/download`.
The guest performs real HAL/FAT writes to its disposable SD image. No network
or HTTP activity code is replaced. The run records 20 read / 21 write sectors.
The logged server diagnostic has free 79,020, minimum 74,400 and largest 73,716
bytes; upload-start free is 70,196. These samples are stages, not a peak-allocation
trace or a post-reboot heap comparison.

Back exits the actual web activity and reaches `esp_restart` through the
existing `silentRestart(target=home)` path. The observer stops **before** reset:
RTC retention, boot landing and fragmentation recovery after reboot are not
validated. The full run has no guest panic, and only the attributed startup GDB
warning. [Application run](../evidence/2026-10-08/crosspoint-ap-upload) and
[checked result](../evidence/2026-10-08/crosspoint-ap-check.json).

```sh
python3 scripts/run_machine.py --engine esp-emu --debug-remote \
  --name my-crosspoint-ap --card cards/base.img --scenario web-ap --seconds 300
```

Use a clean Home card with no recent books or additional Home menu entries;
the input schedule follows this pinned build's default button mapping. Input
levels are the SDK's documented X4 ladder values, not logical-button bypasses.
The same clock runs the actual Wi-Fi stack, FreeRTOS and application. Reported
guest upload rates are modeled timing and must not be quoted as device speed.

[AP build](../evidence/2026-10-08/wifi-ap-build.log) and
[executed payload/restart evidence](../evidence/2026-10-08/ap48-restart).
Build/reproduce commands are in the README. `probe_ap.validate` rejects missing
cycles, mismatched bytes/checksums, missing teardown samples and heap corruption.

## Older work and feedback

| Work | Executed result | Feedback decision |
|---|---|---|
| [#134](https://github.com/crosspoint-reader/crosspoint-reader/issues/134) / closed unmerged [#457](https://github.com/crosspoint-reader/crosspoint-reader/pull/457), OOM indexing 2,000+ chapters | A deterministic EPUB with **3,001 distinct XHTML files, spine entries and TOC entries** indexes, renders chapters 1 and 2, and paints Home in QEMU. The strict checkpoint has final free 143,392 B, minimum 68,696 B, largest 114,676 B; no modeled fault/panic. | Useful regression control. It is not the reporter's book or an A/B of #457, and is not evidence that every current book is fixed. No upstream comment from this alone. |
| [#2332](https://github.com/crosspoint-reader/crosspoint-reader/pull/2332), image allocation consolidation | Exact historical source A/B reproduces the same matching pixels, cleanup and contiguous-allocation tradeoff in 0.48.0 as in the earlier engines. | Existing short local draft has a concrete component result. Do not claim a normal-book regression or a universal speedup. |
| [#1422](https://github.com/crosspoint-reader/crosspoint-reader/issues/1422), large XTC/XTH failure | The corrected 6,001-entry shared-payload XTCH control completes in both engines. | This tests table size, not 6,001 distinct pages, reporter-file content, sleep/wake or fragmented-reader pressure. No issue-closing claim. |
| Open [#2361](https://github.com/crosspoint-reader/crosspoint-reader/pull/2361), 12 KiB streaming / recovery | Current head refreshed to `ad1d1c6d...`; its candidate has not run. | No review or comment based on the full-page control. Preserve exact base/head, streaming pixel parity and failure/recovery as the needed test. |
| Older #1151/#1908, Wi-Fi teardown → reader allocation / restart | Standalone AP teardown is automatic, and full CrossPoint AP exit reaches its real silent-restart request. The candidate source, RTC reset/resume and post-Wi-Fi reader allocation are unvalidated. | No generic “Wi-Fi works” comment or heap-defrag claim. |
| #1459/#2127, HTTP/AP buffer and reconnect behavior | Real guest AP HTTP is available; exact historical candidates and STA reconnect activity are not tested. | Hold feedback until a direct candidate reproduction exists. |

The 3,001-entry newer-emulator run writes all 3,001 spine/TOC records but expires
its 300-second debugger budget before completing the reader checkpoint. Keep
[that incomplete result](../evidence/2026-10-08/history3001-esp48-budget) visible.
It is not an OOM or crash reproduction. Use QEMU for this reader/SD regression
today and esp-emulator for Wi-Fi; do not keep repeating the unchanged timeout.

[Large-EPUB manifest](../evidence/2026-10-08/omega-manifest.json),
[strict QEMU reader run](../evidence/2026-10-08/checkpoint2-qemu-3001),
[new historical ditherer comparison](../evidence/2026-10-08/history2332-48-comparison.json)
and [TCP DF/edge comparison on 0.48.0](../evidence/2026-10-08/tcp-edge48-comparison.json).
The latter retains the existing isolated #3612 module test; it is not a full
application or carrier-network verdict.

## Simulator device audit

Metalio support is already merged as simulator PR #43. EEGO A4 support already
has open PR #44. The current firmware SDK corrected
[EEGO `hasHomeKey` to true](https://github.com/Free-Ink/freeink-sdk/blob/425d200a8ea447326b4b9696e4e47dc84ad9d7f6/libs/hardware/BoardConfig/include/BoardConfig.h#L1427).
The existing simulator branch has been brought into line: capability true,
normal Home-key gating, updated source pin/docs and expectations.

Eight profile contracts, 17 invalid selections, both EEGO light variants and
the Metalio input tests pass. These cover native SDL input, geometry and
orientation behavior. The earlier full-application build blockers documented
in PR #44 remain outside this small capability correction; no new end-to-end
application or physical EEGO validation is claimed.
