# Working in this lab

- Start with `README.md`, `docs/DEVELOPER_GUIDE.md`, and
  `docs/TESTING_YOUR_CODE.md`. Use `lab.py` as the public entry point. Machine-
  readable `profiles --json` and `doctor --json` support agent workflows.
- Current work is reusable CrossPoint emulator regression infrastructure.
  Closed-stock feature comparison is stopped; preserve old evidence without
  expanding it. Consult CrossPoint SCOPE.md and ROADMAP.md before recommending
  firmware features.
- esp-emulator defaults to SHA256-pinned 0.49.0; older controls require explicit
  `--esp-version`. QEMU is preferred for large guest SD/EPUB workloads, and
  esp-emulator for guest Wi-Fi. Check exact inputs rather than inferring support
  from an engine version. Firmware/SDK/ABI pins remain explicit.
- Generic `lab.py firmware` runs a merged component-test image with a serial
  assertion, not a full-reader adapter. Do not reuse X4 GDB addresses on another
  build/chip. The full reader currently accepts one verified control; latest
  develop and other devices require their own verified ABI/adapters.
- Keep firmware, emulator packages, generated EPUBs, SD images and guest RAM out
  of Git. Downloads need public provenance and verified SHA256. Preserve runs
  with new names; record commands, hashes, substitutions and semantic verdicts.
  A timeout or clean process exit alone never establishes a pass.
- Run `python3 -m compileall -q scripts lab.py`, `python3 lab.py test` and
  `git diff --check` after relevant edits. Guest-source changes need their build
  and bounded scenario. Runner changes need representative guest execution.
  The main agent owns verification; reviewers inspect code and recorded results
  without writing files, building, testing or publishing.
- Full-reader verdicts require checkpoint protocol 2: the target activity must
  paint after entering. Distinguish debugger-generated warnings from guest
  faults with captured packets. Preserve warnings and incomplete experiments;
  attribution is not physical memory-safety proof.
- Cite exact base/head for PR comparisons. Keep allocator/network components
  executing in the guest. Distinguish component tests, full firmware integration
  and physical validation; neither engine proves device speed, RF, e-paper,
  SD timing or reset/RTC retention. Useful reproduction is a prerequisite for
  upstream feedback; keep unexecuted plans private.
- Creating/amending local commits requires explicit human approval. Push only
  on an explicit push instruction. Never open/close PRs or write PR descriptions;
  give concise factual notes and checks. Public comments/messages require
  explicit authorization. The human owns architecture and maintenance decisions.
