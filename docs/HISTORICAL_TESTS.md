# Older CrossPoint problems now worth testing

Espressif QEMU and esp-emulator run ESP32 machine code, FreeRTOS and the embedded
allocator. The desktop CrossPoint simulator runs native code with host libraries
and a simulated heap. It remains useful for UI/parser tests; these machines add
the C3 allocator, 32-bit ABI and, in esp-emulator, Wi-Fi/lwIP execution.

This is not a claim that every problem below was impossible to investigate in
the simulator. Logical rendering errors often are. The added coverage is the
actual embedded resource/failure path. SD sectors, buttons and display transport
are supplied by lab adapters; optical output, RF and real SD latency remain
outside these tests.

## Executed historical PR: #2332 image allocations

[PR #2332](https://github.com/crosspoint-reader/crosspoint-reader/pull/2332)
was opened in June. We compiled its original and revised ditherer classes
unchanged into separate C3 probes. Their exact URLs and hashes are in
[source-manifest.json](../probes/image-heap/source-manifest.json):
base `3e60e13025e2b5715352386dc49d687d8849b4e5`,
head `fa1c69adb68a7032e67d170d1249bc0bfd114bbc`.

The concrete mechanism is in the head's
[BitmapHelpers.h:39–49](https://github.com/crosspoint-reader/crosspoint-reader/blob/fa1c69adb68a7032e67d170d1249bc0bfd114bbc/lib/GfxRenderer/BitmapHelpers.h#L39-L49):
three same-lifetime Atkinson error rows become one allocation. Requested pixel
storage is unchanged. Fewer allocations can reduce churn and allocator overhead,
but require a larger contiguous block. This test isolates the ditherers; it does
not execute all PNG/BMP/XTC call sites. The external tone adjustment is identity.
The probe uses Arduino 3.3.11 / IDF 5.5.5; it does not reproduce the historical
release's complete framework configuration or application heap layout.

For each class, the guest processes an 800×32 deterministic gradient, rotates and
resets the rows, destroys the object and samples the heap. Then it deliberately
fills the real heap with 2 KiB blocks and frees alternate blocks. Static pointer
metadata avoids unrelated allocations; heap pressure is deliberately dynamic
because it is the subject of the test.

| Ditherer | Normal pixel hash, both builds | Original retained bytes | Revised retained bytes | Original / revised allocation with 4,084-byte largest block |
|---|---:|---:|---:|---|
| Atkinson 1 bit | 1183029984 | 5,004 | 4,868 | succeeds / fails cleanly |
| Atkinson 2 bit | 3451566204 | 5,004 | 4,868 | succeeds / fails cleanly |
| Floyd–Steinberg | 4222431649 | 3,336 | 3,332 | succeeds / succeeds |

The pressure heap has 154,460 bytes free. An Atkinson combined allocation needs
4,824 payload bytes; each separate row needs 1,608. The observed normal retained
difference includes this allocator's block overhead/rounding. It is not a
universal saving, a timing gain, or proof of fewer fragments in a book workload.

Both engines reproduce every result. Each ditherer's allocations are released,
heap integrity remains valid, and free/largest return to their baseline after
pressure is removed. A deliberately oversized nothrow allocation primes the
runtime failure path before that baseline: the first failure retains 420 bytes
in both builds. Unprimed runs are retained locally; that one-time effect must not
be called a ditherer leak. Its internal runtime allocation site was not traced.

This is a real tradeoff to retain as regression coverage. It does not justify
reverting the merged PR without measuring affected image workloads. The lab has
not reproduced an ordinary book failure from it.

[QEMU comparison](../evidence/2026-10-04/history-image-qemu-comparison.json),
[esp-emulator comparison](../evidence/2026-10-04/history-image-esp-comparison.json)
and the four `history-image-final-*` directories retain guest records.

```sh
python3 scripts/prepare_history.py
pio run -d probes/image-heap
python3 scripts/prepare_history.py --images
python3 scripts/run_image_heap.py --engine esp-emu --label base --name original
python3 scripts/run_image_heap.py --engine esp-emu --label head --name revised
python3 scripts/check_image_heap.py results/original results/revised
# Repeat with --engine qemu and new names for the independent engine control.
```

## Executed large XTC/XTCH control

The runner now recognizes XtcReader completion and accepts XTC/XTCH resume paths.
The guest still allocates the actual 48/96 KB page buffers and executes the
parser, HAL, filesystem, grayscale cleanup and progress writes.
The source justification is
[XtcReaderActivity.cpp:144–173](https://github.com/crosspoint-reader/crosspoint-reader/blob/223c20b4864da9e7ee400d8234f7544fbbe54b62/src/activities/reader/XtcReaderActivity.cpp#L144-L173)
and the SD-backed page table in
[XtcParser.cpp:192–230](https://github.com/crosspoint-reader/crosspoint-reader/blob/223c20b4864da9e7ee400d8234f7544fbbe54b62/lib/Xtc/Xtc/XtcParser.cpp#L192-L230).

The deterministic fixture contains 6,001 valid index entries and two distinct
shared page payloads. It tests a large table without distributing a huge book.
It does **not** test 6,001 unique payloads, SD throughput or the original reporter's
file. Both 1-bit and 2-bit first pages render on clean guest heaps. With the
two-payload XTCH fixture, both engines render pages 1 and 2, then return Home.

The matched turn/exit runs each read 500 sectors and write 81. Both report
largest block 114,676 and minimum free 45,536 bytes at the final checkpoint.
Final free heap differs by 64 bytes: QEMU 143,936, esp-emulator 144,000. We retain
that difference instead of asserting equal heap snapshots. Its cause is not
established; it supplies no candidate memory-saving claim.

The esp-emulator XTCH logs also contain repeated unmapped byte-read warnings
at address zero (3,267 in the first-page run, 7,131 in the turn/exit run).
Their origin is unresolved. The first-page run panics **after** the debugger
disconnects and removes the board adapters; the completed turn/exit run has no
guest panic. Logs include this post-detach interval because the shared probe
resumes briefly before terminating. These checkpoints establish workflow
completion, **not a clean invalid-access or long-run memory-safety verdict**.
The isolated ditherer runs have no bus warnings or guest panics.
[Warning summary](../evidence/2026-10-04/model-warning-summary.json) retains the
counts; do not hide them or attribute them to a CrossPoint bug without a PC trace.

These are current-reader controls, not an A/B of #815, #2287 or #2361 and not a
sleep/wake reproduction of #814. The original large-page problem in #1422 is not
declared fixed. Real sleep/reset/RTC handling and controlled reader heap pressure
are still required for those verdicts.

```sh
python3 scripts/create_xtc_fixture.py
# Copy the generated table6001.xtc/xtch to a disposable card with mcopy,
# using the @@1048576 partition offset as in docs/SD_ADAPTER.md.
python3 scripts/run_machine.py --engine qemu --name large-table \
  --card cards/xtc-table6001-two.img --book /table6001.xtch --scenario turn-exit --seconds 90
```

## Earlier backlog, beyond the recent font PRs

The [retrieved inventory](../evidence/2026-10-04/historical-inventory.json) includes
issue text, dates and current PR heads/bases. Historical descriptions identify
tests; they are not treated as facts about current develop.

| Older work | Useful machine test | Status and boundary |
|---|---|---|
| [#36](https://github.com/crosspoint-reader/crosspoint-reader/pull/36), split 48 KB secondary display buffer | Heap holes between 8 and 48 KB; verify cleanup and identical pixels | Candidate not run; physical grayscale/ghosting still needs a panel |
| [#457](https://github.com/crosspoint-reader/crosspoint-reader/pull/457), 2,000+ chapter EPUB OOM | Large spine/TOC, real 32-bit container sizes, parse/exit allocation failures | Candidate not run; GAMMA120 is insufficient evidence for 2,000+ entries |
| [#610](https://github.com/crosspoint-reader/crosspoint-reader/pull/610), cyclic XTC metadata | Many page/chapter records and repeated batch boundaries | New 6,001-entry control works; chapter metadata and historical candidate untested |
| [#814](https://github.com/crosspoint-reader/crosspoint-reader/issues/814) / [#815](https://github.com/crosspoint-reader/crosspoint-reader/pull/815), post-boot 96 KB allocation | Real allocation after sleep/wake, repeated turns and exit | Clean-boot controls pass; RTC wake and exact historical fix untested |
| [#1151](https://github.com/crosspoint-reader/crosspoint-reader/pull/1151), German hyphenation plus KOSync OOM | Actual Wi-Fi teardown followed by inflate; heap and render-task stack watermarks | High-value next integration case; generic Wi-Fi cycles do not validate it |
| [#1459](https://github.com/crosspoint-reader/crosspoint-reader/pull/1459), HTTP buffer and AP connection limits | Sustained guest HTTP uploads with reader resources resident | Not run; station traffic cannot validate the AP limit or RF stability |
| [#1908](https://github.com/crosspoint-reader/crosspoint-reader/pull/1908), reboot after Wi-Fi exit | Compare contiguous heap before/after teardown and reboot; preserve RTC route | Existing C3 probe shows teardown effects, not this reboot flow |
| [#2018](https://github.com/crosspoint-reader/crosspoint-reader/issues/2018) / [#2074](https://github.com/crosspoint-reader/crosspoint-reader/pull/2074), OTA memory floor | Local TLS/redirect server, actual HTTP client buffers, failure before download, progress callback count | Not run; preserve OTA/TLS code and X3 memory configuration before drawing conclusions |
| [#1422](https://github.com/crosspoint-reader/crosspoint-reader/issues/1422), [#2287](https://github.com/crosspoint-reader/crosspoint-reader/pull/2287), [#2361](https://github.com/crosspoint-reader/crosspoint-reader/pull/2361), XTC streaming | Compare full-page and streaming rendering under identical fragmented heaps | New full-reader control is usable; candidates still untested |

The next tests should integrate #1151/#1908 lifecycle behavior and the XTC
streaming candidates rather than treating generic allocator probes as PR passes.
QEMU can cover reader/allocator work. Use esp-emulator for the actual station
stack; substituting OpenETH would change the networking component under test.
