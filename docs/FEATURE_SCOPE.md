# Useful closed-firmware features and CrossPoint's scope

There is no evidence for an exhaustive claim that closed firmware has nothing
interesting left to offer. The executed X4 sample is one pinned version; Pro
reading remains blocked. Documentation, requests and working prototypes expose
further candidates. Lack of emulator coverage must never become a feature-absence
claim.

This follow-up reads **SCOPE.md, ROADMAP.md, the PR template, USER_GUIDE.md,
font/dictionary docs and the SD-plugin/session contract**. Scope docs and reader
source were refreshed at official develop
`50823ffa125b437b4c9fe5882f326458780198da` on 2026-10-04.
The executed CrossPoint machine remains `223c20b`; its results are not relabelled
as latest-develop results. These snapshots diverge; the compare API lists changes
in platform configuration, ActivityManager, keyboard and themes. The reader menu
and scope conclusions were checked directly at the newer official head.
[Source URLs/hashes](../evidence/2026-10-04/current-scope-sources.json) are retained.

## Scope changes what we recommend, not what exists

[SCOPE.md:15–17](https://github.com/crosspoint-reader/crosspoint-reader/blob/50823ffa125b437b4c9fe5882f326458780198da/SCOPE.md#L15-L17)
explicitly defers non-core features already handled well by popular forks, using
statistics as the example. Lines 30–35 freeze new themes and external network
connectors while welcoming fixes to existing OPDS support. Lines 56–59 exclude
interactive apps, authoring tools/typed notes, active RSS/news/browser features
and PDF rendering. The
[roadmap:23–24](https://github.com/crosspoint-reader/crosspoint-reader/blob/50823ffa125b437b4c9fe5882f326458780198da/ROADMAP.md#L23-L24)
says Phase 0 is closed: old-roadmap provenance does not exempt a new proposal.

The SD-plugin and server route matters: roadmap lines 66–69 describe integrations
without new compiled-in connectors. Existing session events can feed external
reports. That does not mean CrossPoint already has a local statistics screen or
that every cloud integration is admissible as a new core feature.

| Candidate from closed firmware | CrossPoint comparison | Recommendation |
|---|---|---|
| In-book phrase search and jump to an occurrence | Kobo documents keyword search. PocketBook Mini's manual describes button-driven entry and moving between hits. Current official reader menu has no in-book search; library search is a different function. Issue #1984 requests this and PR #3441 implements a streaming search. | Worth testing the existing PR. Core reading interaction, with bounded memory and cancellation; do not open a duplicate. |
| Local reading reports/statistics | X4 Pro manual describes reports in its app ecosystem. Kobo documents reading stats. CrossPoint's ReaderSession/session events are useful building blocks, not a demonstrated equivalent local dashboard. | Keep in the comparison; defer the core dashboard to forks per SCOPE.md. Existing server/plugin approaches can be evaluated separately. |
| Highlighted passages / typed notes | Kobo documents both. Several CrossPoint clipping PRs are open (#1742, #3589 and others). | Distinguish simple clipping from authoring. Typed notes are explicitly excluded; clipping needs maintainer agreement, not automatic acceptance because another device has it. |
| Precise large-TOC navigation | X4 shows multipliers, but the exact 100-chapter activation contract is unresolved. CrossPoint has held scrolling, a bounded SD-backed TOC and chapter scrubbing in its toolbar. | Compare a precise target against both current navigation paths before calling this missing or implementing a numeric jump. |
| Font weight/size changes and bookshelf workflows | Licorice discussions praise these. CrossPoint already has text settings, recent books, indexed title/author views and custom fonts; direct fonts are enabled on external-RAM boards. | Compare the specific operation and anchoring behavior after Pro bring-up, not screenshots alone. No blanket C3 font-port rejection, but measure parser/rasterizer/cache peaks. |
| PDF, RSS, typed notebooks and new cloud clients | Available in some richer stock ecosystems; not implied to exist in X4 stock. | Excluded or frozen in CrossPoint. Their existence does not justify a core PR. |

Primary references:
[Kobo reading menu](https://help.kobo.com/hc/en-us/articles/360020494854-About-the-Kobo-eReader-Reading-Menu),
[Kobo highlights/notes](https://help.kobo.com/hc/en-us/articles/360017481334-Highlight-text-on-your-Kobo-eReader),
[PocketBook Mini manual](https://download.pocketbook-int.com/515/ug/ww/User_Guide_PocketBook_515_ww%28EN%29.pdf)
(printed pages 17 and 40–43), and the X4 Pro manual in [SOURCE_FEATURES.md](SOURCE_FEATURES.md).
The PocketBook manual is historical: it supplies a concrete button workflow,
not a claim about every current model. Its Linux/256 MB hardware is not an ESP32
emulation target. Neither lab engine runs Kobo or PocketBook firmware; those rows
are documentation comparisons, not machine test passes.

## Search is the strongest newly tracked core candidate

[Issue #1984](https://github.com/crosspoint-reader/crosspoint-reader/issues/1984)
gives a concrete use: find the same passage when switching between book formats.
[PR #3441](https://github.com/crosspoint-reader/crosspoint-reader/pull/3441),
head `5aacbbdcef5e0f10b82c05b725567004a09c066a`, claims a 2 KB streaming buffer,
bounded/paginated results and offset-based navigation. Those are author claims,
not independent measurements from this lab. Its machine integration is pending.

Useful acceptance cases are repeated phrases, text split by XHTML tags or an
inflate boundary, escaped entities, Unicode case handling, exact second-hit
navigation, cancellation and repeated open/search/exit. The simulator can check
many text semantics; the machines add allocation peaks, largest block, 32-bit
offset handling and cleanup with real reader resources present. No book-sized
search index or unbounded result list should be justified by desktop success.

## New executed stock case

X4 v5.1.6 Auto Flip opens its numeric interval editor and, once confirmed,
advances ALPHA from Paragraph 01 to Paragraphs 05–06 with no page-button input.
[Final screen and semantic record](../evidence/2026-10-04/stock-auto-advance-long)
and [source-backed schedule](../cases/auto-advance.json) are published.
The first short run did not wait long enough; a Back press exits the reader after
confirmation, so the completed schedule omits it. The stock function is verified;
the injected Arduino reader clock prevents an interval/performance claim.
CrossPoint already documents auto-turn, so this is coverage rather than a feature
proposal. Its exact automatic-turn machine case remains separate.

## Pro bring-up: more precise blocker, still no reading verdict

`diagnose_s3.py` now makes a bounded, byte-pinned debug connection to Licorice.
At PC `0x4037d1c0`, instruction bytes `92 2a 00` load RTC raw interrupt status
from `0x60008044`; the following two-bit test loops until sleep wake/reject is
reported. Observed status is zero. This is a sleep/wake wait, not evidence of
missing EPUB features or a watchdog fault on real devices.

An optional experiment advances PC once past this polling block. The subsequent
watchdog moves to `0x403768c4`, an explicit infinite jump after the sleep call.
Simply returning from the wait is therefore insufficient; a proper reset/wake
model or a verified boot-input contract is required. We keep this failure instead
of patching application control flow until a screenshot appears.

The S3 remote stub also advertises an RV32 target XML while returning a different
register layout. The tool verifies the actual PC prefix and instruction before
the diagnostic PC write; it does not decode Xtensa register windows using RV32
names. No on-disk firmware bytes change. This is reproducible debugger/board-layer
progress, not working Pro support. The emulator core source is unavailable in the
public distribution, so a core sleep/register fix cannot be contributed here yet.

```sh
docker run --rm --network none --cpus 2 --memory 1g -v "$PWD:/work" \
  crosspoint-esp-emulation-lab:2026-10-04 python3 scripts/diagnose_s3.py --name pro-rtc
# Optional diagnostic only: append --wake-experiment, using a new name.
```

See [observation](../evidence/2026-10-04/pro-rtc-observe) and
[failed wake experiment](../evidence/2026-10-04/pro-rtc-wake).
The next Pro step is to establish its startup input/wake contract and SDMMC
boundary on this exact binary. C3 input addresses and SdSpiCard layout cannot be
reused for Pro's different chip and SDMMC transport.
