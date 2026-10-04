# Contributing

The near-term goal is automated reading-feature comparison. Prefer small transport/input/capture adapters that let existing firmware logic execute. Broad SoC/peripheral fidelity and performance benchmarking are later work.

For new firmware support, provide:

1. Public provenance or instructions for supplying a user's own firmware, with SHA256 and image layout.
2. The exact supported chip, firmware revision and hook addresses. Verify the live code/ABI rather than assuming nearby versions match.
3. Which hardware responses are substituted and which firmware behavior actually executed.
4. A bounded reproducible scenario with input events, logs and correctly composed screens.
5. Tests for the relevant host-side adapter and honest failure/timeout status.

Do not commit firmware, emulator executables, ROMs, private SD images, credentials or generated guest RAM dumps. Screenshots and narrowly selected logs are useful evidence; disclose their provenance. Avoid performance claims from hardware-substituted UI experiments.

The firmware checkout is separate from this repository. CrossPoint changes should be based on observed behavior and tested there, without copying proprietary implementations.

For a feature comparison, start with `cases/catalog.json`: identify the source,
firmware/model applicability, user value and observable assertion. Distinguish
implemented claims from user requests and subjective praise. Add a deterministic
fixture/semantic case, retain partial or blocked outcomes, and require an actual
target/result rather than menu presence before marking a feature as passed.

For hardware PR experiments, keep exact base/head commits and shared build inputs.
Do not replace the allocator, driver or protocol component being tested. State
whether the full application or an isolated module executed. An emulator pass
does not establish physical RF, timing, optical-display or carrier behavior.
