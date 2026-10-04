# Source-driven feature comparison — 2026-10-04

Follow-up: [broader feature comparison and current CrossPoint scope](FEATURE_SCOPE.md),
including existing in-book search work, executed Auto Flip and Pro RTC diagnosis.

Tests now start with a claim, an applicable firmware/model, a fixture and an
observable result. The machine-readable [catalogue](../cases/catalog.json)
contains 20 features and 20 sources. It distinguishes manufacturer documentation,
project documentation/source, community announcements, user impressions and user
requests. CrossInk remains excluded.

The sources were retrieved on 2026-10-04. A recent manual is not proof that an
older binary implements every described feature. Reddit impressions motivate
tests; they do not establish speed, correctness or the current support list.
Requests for dictionaries or hyphenation are recorded as requests.

## Sources and applicable versions

- [X4 manufacturer manual](https://cdn.shopify.com/s/files/1/0759/9344/8689/files/X4_User_Guide.pdf?v=1783668551),
  reading controls on PDF pages 7–8 and EPUB image caveat on page 9. The tested
  application is the byte-pinned v5.1.6 fixture, not an unspecified latest build.
- [X4 Pro manufacturer guide](https://cdn.shopify.com/s/files/1/0759/9344/8689/files/X4_Pro_User_Guide_0818.pdf?v=1787034606),
  English page 4 describes app transfers, progress synchronization and reports;
  page 6 covers Wi-Fi. Its claims concern the stock ecosystem, not automatically
  Licorice. Page 4 was visually inspected after extracting the large multilingual PDF.
- CrossPoint's [reader guide](https://github.com/crosspoint-reader/crosspoint-reader/blob/223c20b4864da9e7ee400d8234f7544fbbe54b62/USER_GUIDE.md#L652-L698),
  [font documentation](https://github.com/crosspoint-reader/crosspoint-reader/blob/223c20b4864da9e7ee400d8234f7544fbbe54b62/docs/sd-card-fonts.md#L3-L8),
  [dictionary guide](https://github.com/crosspoint-reader/crosspoint-reader/blob/223c20b4864da9e7ee400d8234f7544fbbe54b62/docs/dictionary.md),
  and [session-event contract](https://github.com/crosspoint-reader/crosspoint-reader/blob/223c20b4864da9e7ee400d8234f7544fbbe54b62/docs/plugin-events.md#L60-L90)
  are pinned to the source used in the native comparison.
- [Licorice launch discussion](https://www.reddit.com/r/xteinkereader/comments/1wo86sh/xt_licorice_is_now_rolling_out_to_x4_pro/),
  [reader impressions](https://www.reddit.com/r/XTEINK/comments/1wjpri2/tried_licorice_firmware_for_x4_pro/),
  and [early typography discussion](https://www.reddit.com/r/XTEINK/comments/1wa1mu9/licorice_is_coming_to_the_x4pro/)
  identify direct fonts, styling, font adjustment and bookshelf workflows worth
  comparing. Early unsupported-feature statements are not carried forward as
  limitations of the downloaded 260923 build. The launch account's affiliation
  was not independently authenticated.
- [Dictionary workflow discussion](https://www.reddit.com/r/XTEINK/comments/1vjlspr/how_to_use_dictionaries_on_the_xteink_x4_pro/)
  and [Licorice feedback](https://www.reddit.com/r/XTEINK/comments/1wsuhjf/really_enjoying_the_new_xt_licorice_firmware_on/)
  provide user priorities, including dictionary workflow and typography requests.

The historical `docs/comparison.md` in CrossPoint explicitly compares versions
0.5.1 and 3.1.1. It is useful background, not current feature evidence.

## Executed and pending cases

| Semantic check | Stock X4 v5.1.6 | CrossPoint pinned native source | Evidence / limitation |
|---|---|---|---|
| Known EPUB text, page turn, select Chapter Two | Pass | Pass | [Earlier executable comparison](EPUB_COMPARISON.md) |
| Bookmark and same-process resume | Pass | Pass | Same report; reboot persistence is a separate test |
| Light text on dark reading background | Pass | Pass | [Stock](../evidence/2026-10-04/manual-stock-dark/screen.png), [CrossPoint](../evidence/2026-10-04/manual-crosspoint-dark-reading/dark.png) |
| Landscape reflow | Partial: direction selector and cache-rebuild messages reached | Pass | [Stock partial result](../evidence/2026-10-04/manual-stock-landscape/screen.png), [CrossPoint reading result](../evidence/2026-10-04/manual-crosspoint-orientation-reading/orientation.png) |
| Built-in/external font selector | Selector observed; no external font installed | Documented, not executed here | [Stock](../evidence/2026-10-04/manual-stock-fonts/screen.png); loading/metrics remain a separate case |
| CSS, italic/underline and PNG | Partial styles; checker PNG absent in this fixture | Styles and actual PNG rendered | [BETA comparison](EPUB_COMPARISON.md); X4 manual also cautions about images |
| Internal-link target and Back | Unverified | Pass | ALPHA unique target/return, earlier comparison |
| Large-TOC target jump | ×1/×10/×100 controls observed; target not established | Held list navigation observed | GAMMA; controls alone do not prove a 100-chapter jump |
| Auto-turn / Go to position | Auto-turn advances without page input; Go to position pending | Already documented; machine cases pending | [Executed Auto Flip](FEATURE_SCOPE.md); clock-substituted, no interval claim |
| X4 Pro stock / Licorice reading features | Blocked before usable reader | Pro source support is documented; this native comparison uses X4 | Boot evidence below is not a feature comparison |

The stock orientation case intentionally retains its incomplete result. Choosing
an orientation produced “Clear Cache”, “Success” and “Ready to Rebuild Index”,
but the final capture still shows the dialog. No landscape reading pass is
claimed. The preceding canceled-dialog probe is archived too.

Every executable case in `cases/` includes its source ID, expectation and exact
button schedule. `run_feature.py` rejects missing source references and schedules
with overlapping input. It saves the case alongside logs and screenshots. The
input schedule is navigation to a specific assertion, not a behavioral oracle:
screen inspection is still required. The clock and SD substitutions are retained
and labelled; interval timing cannot be validated with those cases.

```sh
python3 scripts/run_feature.py cases/dark.json --card cards/base.img --prefix claim-dark
python3 scripts/run_feature.py cases/fonts.json --card cards/base.img --prefix claim-fonts
python3 scripts/run_feature.py cases/orientation.json --card cards/base.img --prefix claim-orientation
```

The native runner now also has `dark` and `orientation` scenarios; see
[native build instructions](../compat/README.md). Both use ALPHA on a fresh SD
directory. Native host memory and timing remain outside embedded validation.

## Wider closed-firmware coverage: X4 Pro

The manufacturer's public [XTCloud flashing UI](https://xtcloud.xteink.cc/app)
exposes an unauthenticated [full-package API](https://api-prod.xteink.cc/api/v2/public/firmware/full-packages/latest?model_code=ESP32S3_X4_TL&lang=en).
The public model list also distinguishes X3, X4, X4 Classic and X4 Pro. This audit
added Pro rather than requiring a device recording or account.

| Downloaded full image | Bytes | Locally computed SHA256 |
|---|---:|---|
| Stock v7.4.4 | 16,662,528 | `f583b8c635111c99054fe12467ee89bad1aef7fd3f74ce2f8c2748199120539a` |
| XT Licorice 260923 | 3,970,704 | `17d81c50c95ecb39da46679d22db1a96ed9a782bf7bcecc1e6d2f2da02d5f34f` |

URLs, source API and hashes are in the [download manifest](../downloads/manifest.json)
and [public provenance](../evidence/2026-10-04/x4pro-public-provenance.json).
The API did not provide a publisher checksum: these hashes pin the retrieved
bytes, not a manufacturer signature. A separate stock V7.6.8 OTA was discovered
through CrossPoint's stock-download API, but was not executed. Full-package and
OTA version labels differ and must not be conflated.

`prepare.py` verifies the downloads and only appends FF bytes to reach 16 MiB.
Every original byte is preserved. Bootloader and applications were not patched.
Both have chip ID 9 (S3), app slots at `0x10000` and `0x7f0000`, each `0x7e0000`
bytes. The [SDK board document](https://github.com/Free-Ink/freeink-sdk/blob/aef1a6c89e36f331b2e1aacbbf7ce0debdeb732a/docs/xteink-x4pro-support.md#L1-L17)
specifies 8 MiB PSRAM; the probe explicitly selects that model. The SDK's linked
Licorice-analysis document was absent in this checkout and was not treated as a
read source.

| esp-emulator v0.45.0, 20-second host budget | Observation | Reading verdict |
|---|---|---|
| Stock v7.4.4 | ROM/bootloader, 8 MiB PSRAM discovery; last progress is multicore app startup; budget expires | Blocked |
| Licorice 260923 | Application executes, then repeated CPU0 interrupt-watchdog panics (10 in recorded run) | Blocked |

See [stock log/status](../evidence/2026-10-04/x4pro-stock-recorded) and
[Licorice log/status](../evidence/2026-10-04/x4pro-licorice-recorded).
The failing peripheral/root cause has not been established. No claim is made
that these symptoms occur on real readers. QEMU's existing X4 SD adapter and
hard-coded C3 addresses are not reused on S3.

```sh
docker run --rm --network none --cpus 2 --memory 1g -v "$PWD:/work" \
  crosspoint-esp-emulation-lab:2026-10-04 python3 scripts/probe_s3.py \
  --image /work/firmware/x4pro-licorice-padded.bin --name pro-licorice
```

Continue reading tests with the working X4/QEMU path. Pro bring-up is a clearly
bounded prerequisite for Pro comparison, not a reason to invent passing results
or postpone all usable feature work.

## What merits a CrossPoint change?

Several praised features already exist, but the comparison is incomplete.
[FEATURE_SCOPE.md](FEATURE_SCOPE.md) now tracks a concrete in-book search candidate
and separates interesting features from changes admissible in core CrossPoint.
The items below are investigation status, not an exhaustive absence claim.

1. **Precise large-TOC navigation** is the strongest small-device candidate from
   the executable stock UI. First establish an exact GAMMA target, then compare
   against CrossPoint's existing held scrolling. Its
   [chapter activity, lines 55–71](https://github.com/crosspoint-reader/crosspoint-reader/blob/223c20b4864da9e7ee400d8234f7544fbbe54b62/src/activities/reader/EpubReaderChapterSelectionActivity.cpp#L55-L71)
   reads a bounded window; [header lines 13–25](https://github.com/crosspoint-reader/crosspoint-reader/blob/223c20b4864da9e7ee400d8234f7544fbbe54b62/src/activities/reader/EpubReaderChapterSelectionActivity.h#L13-L25)
   keeps 24 rows. Any jump control should preserve this SD-backed window rather
   than materializing a whole TOC. A numeric target can use fixed scalar state;
   no new TOC-sized allocation is warranted.
2. **Font adjustment and richer bookshelf/history workflows** have user interest,
   but their specific advantage over current CrossPoint needs a working Pro
   comparison. CrossPoint already has a bounded recent-books store
   ([RecentBooksStore.h:8–30](https://github.com/crosspoint-reader/crosspoint-reader/blob/223c20b4864da9e7ee400d8234f7544fbbe54b62/src/RecentBooksStore.h#L8-L30)).
   Preference for a screenshot is insufficient evidence of missing behavior.
3. **Reading reports** are explicitly deferred to forks by current SCOPE.md.
   For an external/plugin comparison, start with existing `reader.session`
   events and KOSync. CrossPoint already counts eligible forward-page dwell time
   ([ReaderSession.cpp:16–36](https://github.com/crosspoint-reader/crosspoint-reader/blob/223c20b4864da9e7ee400d8234f7544fbbe54b62/src/activities/reader/ReaderSession.cpp#L16-L36))
   and documents deferred delivery. A fork or external report, if wanted, needs an
   explicit retention limit and throttled SD writes, not an unbounded session list.
4. **Direct TTF on C3** is not a safe parity shortcut. CrossPoint already supports
   direct TTF/OTF/TTC when external RAM is enabled; every supported device can use
   converted `.cpfont`. The C3 has no PSRAM. A port requires measured parser,
   rasterizer and cache peaks within its real RAM budget; disabling the gate does
   not establish feasibility.
5. **Dictionary fallback** is a user-requested workflow, not a confirmed closed
   feature to port. CrossPoint's existing StarDict hit/miss/synonym behavior should
   be tested first. Hyphenation is also already implemented; reported demand calls
   for a language fixture, not duplicate implementation.

Touch/frontlight behavior and claimed fast wake/UI need physical or accurately
modeled hardware. They cannot be inferred from framebuffer captures, and hardware
capabilities absent from C3 readers cannot be added by firmware alone.

The next independent workstream is [guest heap/network PR validation](HARDWARE_PR_TESTING.md).
