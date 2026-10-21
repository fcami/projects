<!-- SPDX-FileCopyrightText: 2026 François Cami <contribs@fcami.net> -->
<!-- SPDX-License-Identifier: MIT -->
# Projects

A single repository hosting multiple independent open-source projects.

Each subproject lives in `projects/` with its own license, language,
and build system. A uniform `Makefile` contract (`build`, `test`,
`lint`, `fmt-check`, `fmt`, `clean`, `release`) provides the interface
between subprojects and CI. CI detects which subprojects changed and
runs their targets in parallel.

## Subprojects

Each subproject is licensed independently. See `projects/*/LICENSE`.

| Project | Language | License | Description |
|---|---|---|---|
| [gdkm](projects/gdkm/) | Python | MIT | Move GitHub deploy keys between repositories with one command |

## Quick Start

```bash
# Create a new subproject
./new-project.py my-tool --language rust --license MIT

# Work on it
cd projects/my-tool
# ... edit Makefile, write code ...
make lint build test

# Commit and push — CI handles the rest
```

## Documentation

- [User Guide](infrastructure/docs/user-guide.md) — how to create, build, and manage subprojects
- [Design Document](infrastructure/docs/design.md) — architecture and principles behind this monorepo
- [LLM Prompts](infrastructure/docs/llm-prompts.md) — ready-to-use prompts for LLM-assisted development

## The Uniform Contract

Every subproject implements these targets via `Makefile`:

| Target | Purpose |
|---|---|
| `make build` | Compile / prepare |
| `make test` | Run all tests |
| `make lint` | Static analysis |
| `make fmt-check` | Verify formatting |
| `make fmt` | Apply formatting |
| `make clean` | Remove artifacts |
| `make release` | Release artifact (optional) |

## Adding a New Subproject

```bash
./new-project.py PROJECT_NAME --language LANGUAGE --license LICENSE
```

See the [User Guide](infrastructure/docs/user-guide.md) for details.

## CI

The CI pipeline (GitHub Actions and Azure Pipelines) automatically:

1. Detects which subprojects changed
2. Sets up the appropriate toolchain per subproject
3. Runs `lint`, `build`, `test` in parallel per subproject
4. Runs ALL subprojects weekly to catch dependency rot

## Licensing

This repo is [REUSE-compliant](https://reuse.software/). Every file has
explicit copyright and license information via SPDX headers or
`REUSE.toml`. Run `reuse lint` to verify.

**Infrastructure** (infrastructure/, new-project.py, this README)
is licensed under [MIT](LICENSE).

**Subprojects** are licensed independently — each has its own `LICENSE`
file under `projects/<name>/LICENSE`. Co-habitation in this repo does not
create license interactions between independent subprojects. A GPL or
LGPL subproject remains solely under its own license. See
[infrastructure/docs/design.md](infrastructure/docs/design.md#licensing) for details.

## Design Principles

This monorepo is designed following principles from:
Booch, Gamma, Lakos, Beck, Fowler, Martin, Humble+Farley, and
Winters+Manshreck+Wright. See the [Design Document](infrastructure/docs/design.md)
for the full treatment.
