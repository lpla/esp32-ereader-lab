# Pinned X4 SD adapter

The GPIO/ADC adapter and SdFat sector adapter execute the stock filesystem and EPUB parser. They substitute hardware responses through GDB; they do not emulate SPI protocol or timing. Firmware application bytes are unchanged. See the image provenance in [REPORT](../REPORT.md).

## ABI evidence

The X4 OTA hash is guarded by `run_lab.py` before installing version-specific hooks. The downloaded IROM segment starts at 0x42000020. GNU RISC-V objdump identifies these routines by their SD commands, buffer lengths, control flow and argument movement:

| Address | Identified boundary | Evidence in instructions |
|---|---|---|
| 0x42061662 | SdSpiCard initialization | Initializes bytes12..18, issues CMD0/8/55/41/58, stores SDHC type3 at byte18 |
| 0x4206197e | sectorCount | CMD9 CSD read and C_SIZE decoding |
| 0x42061b04 | single-sector read | CMD17, destination A2, read512 bytes |
| 0x42061de6 | dedicated single-sector read | A3=1 then tail-call0x42061d70 |
| 0x42061d70 / 0x42061bd2 | multi-sector read | Start sector A1, buffer A2, count A3, increments destination by512 |
| 0x42061c28 | single-sector write | CMD24, source A2, data token0xfe |
| 0x42061e80 | dedicated single-sector write | Selects dedicated path or tail-calls0x42061c28 |
| 0x42061e0a / 0x42061ce4 | multi-sector write | CMD25 path, source increments by512 |
| 0x420614a4 | syncDevice | Dispatches pending read/write stop by state byte16 |

These are binary-derived identifications, not recovered vendor symbols. The register contracts agree with SdFat's public sector APIs. After initialization the adapter sets beginCalled, chip select, no error, idle transfer state and SDHC type, and disables dedicated SPI. The filesystem above these boundaries continues to execute.

Generate a disassembly inside the container for independent inspection:

```sh
docker run --rm -v "$PWD:/work" crosspoint-esp-emulation-lab:2026-10-04   riscv64-linux-gnu-objdump -D -b binary -m riscv:rv32 --adjust-vma=0x42000020   firmware/x4_en_v5.1.6_ota-segments/42000020.bin > results/x4-irom-disassembly.txt
```

## Display coverage

The initial capture hook at0x42066340 writes both controller banks (commands0x26 and0x24 through0x42066190). Reader page turns use0x4206631a, which calls the same internal routine with command0x24. Both wrappers have the same buffer/rectangle register ABI and are captured now. The old-bank wrapper0x420663b4 is excluded because updating comparison RAM is not a new visible image. These addresses were identified from command constants and argument moves in the disassembly.

The earlier `book-next`/`book-menu` probes therefore had incomplete display coverage. Their unchanged composed screens did not establish ignored buttons. Raw guest framebuffer diagnostics exposed changed text; subsequent driver-call capture validates the page turn without relying on a raw framebuffer snapshot.

## Card and evidence

`create_card.py` creates a65MiB card: MBR, a64MiB FAT32 partition at sector2048, and known EPUB/TXT fixtures. This matches the stock partition-first mount path. The earlier superfloppy probes did not mount successfully in the exercised path; no general filesystem limitation is inferred.

The [book-open evidence](../evidence/2026-10-04/sd-book/screen.png) displays “ALPHA EPUB BASELINE” from the synthetic EPUB. The [sector trace](../evidence/2026-10-04/sd-book/sd-events.json) records650 operations including cache/bookmark writes. GDB completed, and the flash hash remained unchanged.

Card reads are copied to the guest's requested RAM buffer and read back for equality. Requests beyond the image or above128 sectors fail. Writes modify only the disposable per-run card. There is no erase, card register, power-loss, concurrency, SPI CRC or performance fidelity claim. Additional firmware routines may require additional hooks; a failed adapter path must not be reported as missing firmware functionality.

Only generated fixtures are suitable for publishing full storage traces. Personal books or SD images can expose filenames and content; keep their run artifacts local.

## Reader input clock

Front ADC polling in the reader advances roughly one virtual millisecond per sample in the traced path. A20-sample pulse is too short for several reader menu actions. `x4-longpress-clock.gdb` intercepts the verified Arduino-millis boundary at `0x42095246`, immediately after `esp_timer_get_time` returns its64-bit microseconds in A0/A1 and before conversion to milliseconds. It adds `max(0, front_reads-250) * 20000` microseconds; the underlying ESP timer remains unmodified. `x4-time-trace.gdb` records the original boundary for inspection.

Menu/chapter/bookmark/reopen/stride scenarios explicitly install this diagnostic offset and write `clock-substitution.json`. This permits deterministic software input-state testing, but invalidates timing/performance comparisons and can cause repeated held-page movement. It does not validate watchdog, button debounce, auto-flip speed or physical input timing. The basic book/page probes do not use this substitution.

`create_card.py --fixture beta --name beta` creates the CSS/image card; `--fixture gamma --name gamma` creates a120-chapter book. A new output name is required; existing cards/results are preserved. Source card bytes are copied per run, and the runner records source/result hashes in `input.json`.
