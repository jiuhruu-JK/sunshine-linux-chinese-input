# Sphinx example

This fixture demonstrates the Sphinx adapter with Python API documentation.
Dockle generates `conf.py`, enables MyST Markdown and autodoc, and selects its
first-party Sphinx theme.

> [!NOTE]
> This source tree contains no consumer-maintained Sphinx configuration.

## What to compare

| Page | Purpose |
| --- | --- |
| [Markdown component reference](component-reference.md) | MyST Markdown syntax beside rendered results |
| [reStructuredText component reference](component-reference-rst.rst) | Native RST syntax beside rendered results |
| [API reference](api.md) | Framework-native Python API output |

## Use Dockle with Sphinx

Add a Sphinx target to `dockle.toml`. Dockle supplies `conf.py`, the MyST
extensions, and the theme:

```toml
[[targets]]
name = "python"
framework = "sphinx"
source = "docs/python"
entry = "index"
```

Then build just that target:

```shell
python -m dockle check python
python -m dockle build python
```

Every example uses the same concepts and page structure so visual differences
come from the generator integration rather than unrelated prose.

```{toctree}
:maxdepth: 2
:hidden:

component-reference
component-reference-rst
api
```
