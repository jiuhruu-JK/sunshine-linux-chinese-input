# MkDocs example

This fixture demonstrates the MkDocs adapter with Markdown configuration
documentation. Dockle generates `mkdocs.yml`, enables common Markdown
extensions, and selects its first-party MkDocs theme.

> [!NOTE]
> This source tree contains no consumer-maintained MkDocs configuration.

## What to compare

| Page | Purpose |
| --- | --- |
| [Component reference](component-reference.md) | Authoring syntax beside rendered results |
| [API reference](api.md) | A configuration-oriented reference page |

## Use Dockle with MkDocs

Add a MkDocs target to `dockle.toml`. Dockle supplies `mkdocs.yml`, the
Markdown extensions, and the theme:

```toml
[[targets]]
name = "guide"
framework = "mkdocs"
source = "docs"
```

Then build just that target:

```shell
python -m dockle check guide
python -m dockle build guide
```

Every example uses the same concepts and page structure so visual differences
come from the generator integration rather than unrelated prose.
