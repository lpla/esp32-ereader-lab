# Architecture and extension points

This repository supplies test infrastructure around the released emulator cores.
It does not contain a QEMU or esp-emulator fork. Use upstream projects for CPU or
peripheral-model fixes; keep board transport and test orchestration here.

| Path | Responsibility |
|---|---|
| `lab.py` | Public CLI: setup, doctor, profiles, build, card, run, firmware, check, test |
| `config/profiles.json` | Supported workflow names, preferred engines and honest scope |
| `downloads/manifest.json` | Public package URLs, byte counts and archive hashes |
| `adapters/engines.json` | Extracted executable paths, versions and hashes |
| `adapters/` | Verified firmware symbol/ABI and board-adapter contracts |
| `probes/` | Buildable guest component tests |
| `fixtures/`, `cases/` | Deterministic test sources and existing case catalogue |
| `scripts/` | Container/host orchestration, GDB hooks, capture and assertions |
| `tests/` | Host regression tests, including negative verdict cases |
| `evidence/` | Selected small, reviewable logs, JSON and screenshots |
| `docs/` | Current guides plus indexed historical reports |

`tools/`, `firmware/`, `cards/`, `fixtures/generated/` and `results/` are ignored
outputs. Generated images and raw guest RAM must not enter Git. Existing dated
evidence is immutable provenance; changing the default engine does not relabel it.

## Execution contracts

Setup verifies only the selected engine archives, extracts with the data filter,
and builds a Linux/amd64 container. Doctor is read-only. Runs verify executable
hashes again. The two emulators share reader assertions through the machine
adapter; the generic serial runner uses no firmware addresses.

The full-reader adapter supplies SD sector transport, input and display capture
at verified firmware boundaries. The actual guest filesystem, parser, rendering,
activity code and allocator execute. These substitutions are recorded and do
not validate physical peripherals. The reader completion protocol requires a
paint from the target activity, including Home after exit.

The AP probe executes the guest Wi-Fi/WebServer implementation and validates
host payloads, guest upload records, repeated AP starts and teardown integrity.
The generic firmware runner ends at an explicit serial marker and rejects known
fault reports. Neither substitutes a host allocator for the guest allocator.

## Add support without hiding uncertainty

Add an engine release to both package and executable manifests, verify each
hash, and run representative guest workloads before changing the default.
Keep older engine versions selectable for comparisons.

A profile entry describes a workflow; it does not install a new board adapter.
Adding a workflow also requires CLI routing, a bounded runner, semantic
assertions, negative host tests and documented results. Avoid generic configuration
for unverified hook addresses. For a new firmware ABI or device, derive contracts
from its source/ELF and selected SDK profile, then prove the control with observed
screens, input and SD behavior. Reset, RTC, power, RF and optical display behavior
need their own validation.

## Historical compatibility

Existing low-level `scripts/` commands remain available for recorded experiments.
The download/preparation defaults now select the two current engines only.
Archived stock setup requires explicit `--legacy-fixtures` on both
`scripts/download.py` and `scripts/prepare.py`. `--emulators-only` selects all
historical engine packages. Historical reports may show the older defaults;
follow the current developer guide for new work.
