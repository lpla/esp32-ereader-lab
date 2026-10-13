# Documentation

## Current developer guidance

- [Developer guide](DEVELOPER_GUIDE.md): setup and supported workflows.
- [Testing your code](TESTING_YOUR_CODE.md): custom projects, serial assertions,
  base/candidate comparisons and agent usage.
- [Architecture](ARCHITECTURE.md): structure, contracts and extension points.
- [Roadmap](ROADMAP.md): prioritized gaps, implementation direction and completion
  criteria for better emulation.
- [Public CLI validation](DEVELOPER_WORKFLOWS_2026-10-13.md): executed developer
  commands, guest results, preserved evidence and remaining coverage.
- [October 13 readiness audit](DEVELOPER_READINESS_2026-10-13.md): device coverage
  and executed 0.49.0 upgrade results. Its initial default-retention decision was
  superseded by the public CLI's 0.49.0 default; measurements retain their pins.
- [Regression runners](REGRESSION_RUNNERS.md): established full-reader/AP
  protocols, exact controls and older issue/PR evidence. Version statements
  there describe the recorded 0.48.0-era runs.

## Historical reports

These retain the inputs and limits of earlier experiments; they are not the
current onboarding path. Closed-stock feature research is stopped.

- [Initial lab report](../REPORT.md)
- [Source feature catalogue](SOURCE_FEATURES.md)
- [Feature scope](FEATURE_SCOPE.md)
- [EPUB comparison](EPUB_COMPARISON.md)
- [SD adapter experiments](SD_ADAPTER.md)
- [Machine improvements](MACHINE_IMPROVEMENTS.md)
- [Hardware PR testing](HARDWARE_PR_TESTING.md)
- [Historical tests](HISTORICAL_TESTS.md)

Use each report's source hashes, firmware revisions and engine versions when
reproducing it. Do not silently apply historical GDB addresses to a new binary.
