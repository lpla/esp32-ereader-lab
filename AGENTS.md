# Working in this lab

- Read `docs/SOURCE_FEATURES.md`, `cases/catalog.json` and the relevant engine
  report before choosing a test. This project compares specific claims and user
  priorities; an arbitrary sequence of button presses is not a feature test.
- Keep firmware, emulator packages, generated EPUBs, SD images and guest RAM out
  of Git. Downloads must have public provenance and verified SHA256. Do not reuse
  X4 GDB addresses on other firmware/chips without verifying the live ABI.
- Preserve completed runs using new names. Record inputs, commands, hashes,
  substitutions and semantic verdicts. A timeout or clean process exit alone
  never establishes a feature pass. Keep incomplete/blocked results visible.
- QEMU is the validated X4 SD/EPUB path. esp-emulator v0.45.0 is the validated
  isolated C3 heap/network path. Full CrossPoint C3 machine/SD reading, page turn and exit now run in both
  engines; see docs/MACHINE_IMPROVEMENTS.md. Exact SD-font PR A/B and X4 Pro
  reading remain unvalidated. Guest-resident stock inputs work only in QEMU.
- The native CrossPoint simulator uses host memory/timing. To test embedded
  allocator/network behavior, execute guest code and preserve the component
  under test. Cite exact PR head/base and distinguish module tests from full
  firmware integration. Firmware changes belong in the separate CrossPoint repo.
- Run `python3 -m compileall -q scripts`,
  `python3 -m unittest discover -s tests -v` and `git diff --check` after relevant
  edits. Guest probe changes also require the appropriate PlatformIO build and
  bounded emulator scenario. Document physical-hardware limits without treating
  them as a reason to skip useful emulator tests.
- Read CrossPoint SCOPE.md and ROADMAP.md before recommending firmware features.
  Separate core candidates from deliberately excluded or fork-deferred features.
  PR drafts must introduce the emulators briefly and report executed results;
  keep test plans for unexecuted candidates private.
- Publication is controlled by the user's authorization. Do not send PR comments
  or messages merely because a referenced PR is being investigated.
