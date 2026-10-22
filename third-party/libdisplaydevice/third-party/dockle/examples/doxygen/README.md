# Doxygen example

This fixture demonstrates the Doxygen adapter with C++ API documentation.
Dockle generates the complete `Doxyfile`, enables strict warnings, and attaches
the shared presentation layer through supported Doxygen hooks.

> [!NOTE]
> This source tree contains no consumer-maintained Doxygen configuration.

## What to compare

| Page | Purpose |
| --- | --- |
| [Component reference](component-reference.md) | Authoring syntax beside rendered results |
| [API reference](@ref dockle::demo::target) | Framework-native C++ API output |

## Use Dockle with Doxygen

Add a Doxygen target to `dockle.toml`. Dockle supplies the complete `Doxyfile`,
including the tree view, custom admonition aliases, and theme hooks:

```toml
[[targets]]
name = "cpp"
framework = "doxygen"
source = "src"
entry = "README.md"
```

Then build just that target:

```shell
python -m dockle check cpp
python -m dockle build cpp
```

Dockle also supplies `@tab`, `@tabs`, and `@tabs_grouped` authoring aliases.
Named grouped tab sets synchronize matching labels; ordinary tab sets remain
independent.

Every example uses the same concepts and page structure so visual differences
come from the generator integration rather than unrelated prose.
