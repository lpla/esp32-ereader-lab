# Contributing

Build reusable CrossPoint regression workflows that developers can reproduce.
Start with the [developer guide](docs/DEVELOPER_GUIDE.md) and
[architecture](docs/ARCHITECTURE.md). Keep firmware changes in the separate
CrossPoint repository and emulator-core changes in their upstream projects.

## Before changing a runner

Establish the existing behavior and a concrete assertion. Preserve the component
being tested: guest allocator, filesystem, protocol or driver. State whether the
result comes from a component probe, full firmware with board substitutions, or
physical hardware. Controls do not prove unexecuted candidates passed.

For a new adapter or workflow, include exact chip/source/SDK/image/engine inputs,
verified ABI where hooks are used, substituted hardware responses, a bounded
scenario, semantic verdicts and useful logs/screenshots. Preserve failed and
incomplete runs. A timeout or normal process exit is not an assertion.

## Checks

```sh
python3 -m compileall -q scripts lab.py
python3 lab.py test
git diff --check
```

Guest probe changes also require its PlatformIO build and bounded guest scenario.
Runner changes require an appropriate real guest integration run. Host-only
documentation changes use link/command review. The optional manual AP workflow
adds a reproducible guest smoke test; host CI does not execute every workflow.

## Evidence and ownership

Use new run names; keep generated images, packages, binaries, private SD data,
credentials and guest RAM out of Git. Commit only selected small evidence with
provenance. Report exact base/head and shared inputs for a comparison. Avoid
physical speed, RF or optical-display claims from substituted hardware tests.

Agents may implement and verify authorized local tooling changes. The human
owns maintenance and publication: creating or amending commits requires explicit
approval, pushing requires an explicit push instruction, and agents must not
open or close PRs or write PR descriptions. Give concise factual findings and
checks for the human to use. Public comments/messages also require explicit
authorization. Read-only reviewers inspect recorded checks; they do not build,
write files or publish.
