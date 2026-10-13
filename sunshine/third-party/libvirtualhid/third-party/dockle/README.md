<div align="center">
  <img
    src="/branding/dockle-logo.svg"
    alt="Dockle logo"
    width="192"
  />
  <h1 align="center">Dockle</h1>
  <h4 align="center">Build documentation with multiple frameworks and one consistent theme.</h4>
</div>

<div align="center">
  <a href="https://github.com/LizardByte/dockle"><img src="https://img.shields.io/github/stars/lizardbyte/dockle.svg?logo=github&style=for-the-badge" alt="GitHub stars"></a>
  <a href="https://codecov.io/gh/LizardByte/dockle"><img src="https://img.shields.io/endpoint.svg?url=https%3A%2F%2Fapp.lizardbyte.dev%2Fdashboard%2Fshields%2Fcodecov%2Fdockle.json&style=for-the-badge&logo=codecov" alt="Codecov"></a>
  <a href="https://sonarcloud.io/project/overview?id=LizardByte_dockle"><img src="https://img.shields.io/sonar/quality_gate/LizardByte_dockle?server=https%3A%2F%2Fsonarcloud.io&style=for-the-badge&logo=sonarqubecloud&label=sonarcloud" alt="SonarCloud"></a>
</div>

Dockle is a configuration and presentation layer for documentation generators. A project describes itself once in
`dockle.toml`; Dockle translates that model into temporary Sphinx, Doxygen, MkDocs, JSDoc, or rustdoc configuration,
runs the underlying tool, and applies its own shared, Furo-inspired visual layer to the generated HTML. A full build
publishes a configured home target directly, adding a landing page only when a project needs one.

Any framework can own the root, with cards to other published targets injected
when needed. Project assets and metadata are configured once and then applied
to every generated documentation set. Redirect-only compatibility aliases under
the home target's name preserve existing target-prefixed deep links without
restoring a separate landing page.

The Sphinx integration is a first-party `dockle` theme. Furo is a design reference, not a runtime dependency or base
theme.

## Why Dockle?

- Keep framework-specific configuration out of consumer repositories.
- Build one or several documentation targets from one command.
- Give prose and API references the same colors, typography, spacing, code blocks, tables, and responsive behavior.
- Keep the generators replaceable: Dockle orchestrates them rather than attempting to parse every source format itself.

## Quick start

Dockle requires Python 3.11 or newer. Install the adapters needed by the project:

```shell
python -m pip install "lizardbyte-dockle[sphinx,mkdocs]"
```

The PyPI distribution uses the organization-qualified name `lizardbyte-dockle`; the project, Python package, and
command remain `dockle`. Doxygen, JSDoc, and the Rust toolchain remain native tool dependencies. Their executable paths
can be overridden in `dockle.toml` when they are not available on `PATH`.

JavaScript-only projects can use the native Dockle JSDoc template without Python, Doxygen, or Graphviz:

```shell
npm install --save-dev @lizardbyte/dockle
npx dockle-jsdoc src --destination docs
```

That npm package includes JSDoc and the first-party template. The Python package uses the same template when JSDoc is
one target in a larger multi-framework site.

Create a single configuration file:

```toml
[project]
name = "Example"
version = "1.0.0"
description = "Example project documentation"
repository = "https://github.com/example/example"
logo = "branding/logo.png"

[theme]
primary = "#2962ff"
content = "#2e3440"
light_background = "#ffffff"
dark_background = "#131416"

[build]
output = "_site"
work = ".dockle"
strict = true

[[targets]]
name = "docs"
title = "Project documentation"
framework = "sphinx"
source = "docs"
home = true

[[targets]]
name = "cpp-api"
framework = "doxygen"
source = "."

[targets.doxygen]
inputs = ["README.md", "docs", "src"]
main_page = "README.md"
predefined = ["EXAMPLE_PUBLIC_API=1"]

[[targets]]
name = "rust-api"
framework = "rustdoc"
source = "."

[[targets]]
name = "web-api"
framework = "jsdoc"
source = "src"

[targets.jsdoc]
readme = "README.md"
```

Then inspect or run the build:

```shell
dockle build --dry-run
dockle check
dockle build
dockle build manual cpp-api
```

The configuration path can be changed with `dockle --config path/to/dockle.toml build`. A complete build cleans the
whole output tree so removed targets cannot leave stale pages behind; a named-target build only replaces that target.
Strict mode is opt-in for consumers; set `strict = true` when warnings should fail the build. Doxygen's individual
documentation warning switches remain enabled by default. A Sphinx target can set `extra_config` to a Python fragment
that Dockle executes after its generated `conf.py`, and a Doxygen target can set `generate_xml = true` and
`publish = false` when an extension such as Breathe needs XML without a separate public API site. On Read the Docs,
Dockle derives the displayed version from `READTHEDOCS_VERSION` and preserves the configured width of all-zero versions
for numeric pull-request builds.

## Review all five adapters

This repository is also an executable comparison suite. Every adapter has an
overview, component reference, GitHub-style alerts, code, tables, and an API or
reference page. Each language fixture differs only where the underlying
generator requires it:

```shell
python -m pip install -e ".[all]"
npm ci --ignore-scripts
npm run build
dockle check
dockle build
```

Doxygen and Cargo must be installed separately. The JSDoc adapter finds a project-local executable in
`node_modules/.bin`, so a global Node.js package is not required. Open `_site/index.html` to move between the generated
Sphinx, Doxygen, MkDocs, JSDoc, and rustdoc sites.

The language gallery uses upstream fixtures from the pinned `third-party/highlight.js` submodule. `npm run build`
initializes it automatically; keep its release tag aligned with the `@highlightjs/cdn-assets` dependency.

## Read the Docs

The root `.readthedocs.yaml` delegates to `readthedocs_build.sh` because Dockle, rather than Read the Docs, owns generator
selection. Consumers call the same script from a `third-party/dockle` checkout. A fully pinned conda environment supplies
Doxygen, Graphviz, and Python while Read the Docs supplies Node.js and Rust. For Doxygen targets, the script creates
Dockle's shared environment and binds its virtual environment to that Conda interpreter so the pinned generators are
used. Other projects use the Read the Docs Python environment. The script installs the hosted prerequisites, builds the
portal, and copies it to `$READTHEDOCS_OUTPUT/html/`. Optional project hooks named `readthedocs_pre_build.sh` and
`readthedocs_post_build.sh` run immediately before and after Dockle. Consumers can declare Python documentation
dependencies in a `docs` dependency group, a `docs` optional extra, or both in their root `pyproject.toml` and commit
`uv.lock`. The shared script installs the selected documentation dependencies and the project's runtime dependencies
needed by autodoc into Dockle's build environment. It excludes the consumer's Dockle package requirement so the checked
out Dockle remains installed. A legacy `docs/requirements.txt` remains supported when neither a `docs` group nor extra is
declared.

No Sphinx or MkDocs configuration is duplicated for the hosting service. Once this repository is imported into Read
the Docs, each branch and pull request build will exercise the root Sphinx documentation and all five adapters used
locally.

## Distribution

The Python package is the canonical multi-framework orchestrator. PyPI provides the normal install path, while
standalone per-platform executables make that command available to C++, JavaScript, and Rust projects without requiring
a managed Python environment. The `@lizardbyte/dockle` npm package is intentionally narrower: it provides JSDoc, the
native Dockle JSDoc template, and the `dockle-jsdoc` command without installing Python or unrelated documentation
toolchains. A crates.io package still only makes sense if it provides comparable installation value or a real Rust API
rather than a second implementation.

For CMake projects, [`cmake/Dockle.cmake`](cmake/Dockle.cmake) already exposes `dockle_add_docs()`. It finds an installed
or standalone Dockle command and falls back to `Python3 -m dockle`.

## Adapter status

| Framework | Configuration generated by Dockle | Shared theme path | Initial adapter |
| --- | --- | --- | --- |
| Sphinx | `conf.py` | Dockle's packaged Sphinx theme | Implemented |
| Doxygen | `Doxyfile` | `HTML_EXTRA_STYLESHEET` | Implemented |
| MkDocs | `mkdocs.yml` | Dockle's packaged MkDocs theme | Implemented |
| JSDoc | `jsdoc.json` | Dockle's packaged native JSDoc template | Implemented |
| rustdoc | Cargo command and environment | Generated HTML normalization | Implemented |

Every adapter now receives Dockle's generated client-side search index and the
same search interface, including result ranking and empty/error behavior. The
color-scheme control sits beside search and uses a state-aware Lucide icon.
Sphinx, MkDocs, and JSDoc use first-party templates. Doxygen and rustdoc keep
their semantic output while Dockle normalizes their structure and visual
primitives. Doxygen additionally receives a persistent tree, an automatically
completed page outline, and generated previous/next navigation.

Authored code blocks are re-highlighted with Dockle's pinned Highlight.js
runtime after each framework renders them, so native Pygments, Prettify,
Doxygen, and rustdoc token markup cannot produce different results. Dockle
normalizes common language aliases before highlighting; use `shell` for
commands and scripts, and reserve `console` for transcripts that include a
prompt or command output. Line-numbered native source listings retain their
generator-provided navigation.

Markdown GitHub alerts are enabled through MyST for Sphinx, a
Dockle Markdown extension for MkDocs and the root portal, Doxygen's native
parser, and a shared post-render enhancement for JSDoc and rustdoc. Dockle
extends the same syntax with attention, danger, error, hint, see-also, and todo
alerts. Its generated Doxyfile also supplies matching Doxygen aliases for
admonition types that Doxygen does not provide itself. Portable tab sets use
semantic `details` markup and are upgraded by Dockle's self-contained client
script with keyboard navigation. An optional `data-dockle-tab-group` name links
matching selections across tab sets and pages. Doxygen receives equivalent
`@tab`, `@tabs`, and `@tabs_grouped` aliases without depending on
`doxygen-awesome-css` or `doxyconfig`.

## Development

The centralized common-lint workflow handles repository linting on pull
requests. Install the locked Python dependencies and run the test suite:

```shell
uv sync --locked --all-extras
$env:PYTHONPATH = "src"  # PowerShell
python -m unittest discover -s tests -v
python -m compileall -q src tests
```

The root documentation is built from [docs/index.rst](docs/index.rst) with the
same first-party Sphinx theme used by the example. The Sphinx fixture includes
both MyST Markdown and reStructuredText component references.
