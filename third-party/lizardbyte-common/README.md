<div align="center">
  <img
    src="https://raw.githubusercontent.com/LizardByte/.github/refs/heads/master/branding/logos/logo.svg"
    alt="LizardByte icon"
    width="256"
  />
  <h1 align="center">lizardbyte-common</h1>
  <h4 align="center">Common library and helpers for LizardByte projects.</h4>
</div>

<div align="center">
  <a href="https://github.com/LizardByte/lizardbyte-common"><img src="https://img.shields.io/github/stars/lizardbyte/lizardbyte-common.svg?logo=github&style=for-the-badge" alt="GitHub stars"></a>
  <a href="https://github.com/LizardByte/lizardbyte-common/actions/workflows/ci.yml?query=branch%3Amaster"><img src="https://img.shields.io/github/actions/workflow/status/lizardbyte/lizardbyte-common/ci.yml.svg?branch=master&label=CI&logo=github&style=for-the-badge" alt="CI"></a>
  <a href="https://codecov.io/gh/LizardByte/lizardbyte-common"><img src="https://img.shields.io/endpoint.svg?url=https%3A%2F%2Fapp.lizardbyte.dev%2Fdashboard%2Fshields%2Fcodecov%2Flizardbyte-common.json&style=for-the-badge&logo=codecov" alt="Codecov"></a>
  <a href="https://sonarcloud.io/project/overview?id=LizardByte_lizardbyte-common"><img src="https://img.shields.io/sonar/quality_gate/LizardByte_lizardbyte-common.svg?server=https%3A%2F%2Fsonarcloud.io&style=for-the-badge&logo=sonarqubecloud&label=sonarcloud" alt="SonarCloud"></a>
</div>

# Overview

## ℹ️ About

This repository contains shared helper scripts, repository-level tooling, and C++ helpers used across LizardByte
projects.

The current tooling includes Python-managed helpers, reusable GitHub workflows, and a small C++ helper library:

- `scripts/update_clang_format.py` runs `clang-format` across supported source directories.
- `scripts/localize.py` updates gettext and Babel locale files.
- `.github/workflows/localize.yml` runs the locale helper from GitHub Actions and opens localization update pull requests.
- `lizardbyte::common` provides shared C++ helpers, starting with environment variable manipulation.
- `lizardbyte::test_support` provides shared GoogleTest fixtures and test macros for LizardByte C++ projects.

## ⚙️ Python Tooling

Install [uv](https://docs.astral.sh/uv/) and sync the locked tool environment:

```bash
uv sync --locked
```

Run the clang-format helper:

```bash
uv run --locked --only-group c lb-update-clang-format
```

Run gettext extraction:

```bash
uv run --locked --only-group locale lb-localize --extract
```

## 🗜️ C++ Tooling

Initialize submodules before configuring the C++ targets:

```bash
git submodule update --init --recursive
```

Configure, build, and test the C++ helpers with CMake:

```bash
cmake -DBUILD_DOCS=OFF -DBUILD_TESTS=ON -B build -S .
cmake --build build --parallel
ctest --test-dir build --output-on-failure
```

The C++ library exports the `lizardbyte::common` target and public headers under `lizardbyte/common/`.

```cpp
#include <lizardbyte/common/env.h>

std::string value;
if (lizardbyte::common::get_env("MY_ENV", value)) {
  lizardbyte::common::append_env("MY_ENV", "suffix", ";");
}

if (lizardbyte::common::is_github_actions()) {
  // Apply GitHub Actions-specific behavior.
}
```

The optional test support target is available when `BUILD_TESTS=ON` or `LIZARDBYTE_COMMON_BUILD_TEST_SUPPORT=ON`.

```cpp
#include <lizardbyte/common/testing.h>

TEST(MySuite, CapturesOutputUntilFailure) {
  std::cout << "only printed when this test fails";
}
```

Build the Doxygen documentation through the shared doxyconfig submodule:

```bash
cmake -DBUILD_DOCS=ON -DBUILD_TESTS=OFF -B build/docs -S .
cmake --build build/docs --target docs
```

## 📐 Consuming Projects

Projects with a `pyproject.toml` can use this repository as a local path dependency. For a submodule at
`third-party/lizardbyte-common`, add the dependency and source to the consuming project's `pyproject.toml`:

```toml
[project]
dependencies = [
    "lizardbyte-common[c]",
]

[tool.uv.sources]
lizardbyte-common = { path = "third-party/lizardbyte-common" }
```

Then sync and run the installed commands from the consuming project root:

```bash
uv sync --python 3.14
uv run lb-update-clang-format
uv run lb-localize --extract
```

Projects without a `pyproject.toml` can still create a `.venv` in the consuming project root and install
the local checkout into it:

```bash
uv venv --python 3.14
uv pip install --editable "third-party/lizardbyte-common[c]"
```

Then run the commands from the consuming project root:

```bash
lb-update-clang-format
lb-localize --extract
```

CMake projects can consume the C++ helpers from the same submodule:

```cmake
add_subdirectory(third-party/lizardbyte-common)
target_link_libraries(my_target PRIVATE lizardbyte::common)
```

To consume the shared GoogleTest support helpers from a project that already builds tests, link the test binary to
`lizardbyte::test_support`:

```cmake
set(LIZARDBYTE_COMMON_BUILD_TEST_SUPPORT ON)
add_subdirectory(third-party/lizardbyte-common)
target_link_libraries(my_test_binary PRIVATE lizardbyte::test_support)
```

## ♾️ Workflows

Reusable GitHub workflows live under `.github/workflows/`.

- `localize.yml` extracts gettext strings with the shared locale helper and can open a localization update pull request.

```yaml
name: localize
permissions: {}

on:
  push:
    branches:
      - master
    paths:
      - '.github/workflows/localize.yml'
      - 'src/**'
      - 'locale/sunshine.po'
  workflow_dispatch:

jobs:
  localize:
    name: Update Localization
    permissions:
      contents: read
    uses: LizardByte/lizardbyte-common/.github/workflows/localize.yml@master
    secrets:
      GH_TOKEN: ${{ secrets.GH_BOT_TOKEN }}
```

## 🧪 Tests

Run the pytest suite:

```bash
uv run --locked --only-group test-python pytest
```

Run the C++ GoogleTest suite:

```bash
cmake -DBUILD_DOCS=OFF -DBUILD_TESTS=ON -B build -S .
cmake --build build --parallel
ctest --test-dir build --output-on-failure
```

<details style="display: none;">
  <summary></summary>
  [TOC]
</details>
