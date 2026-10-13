# rustdoc example

This fixture demonstrates the rustdoc adapter with Rust API documentation.
Dockle runs Cargo with an isolated target directory and normalizes the generated
HTML with the shared presentation layer.

> [!NOTE]
> This source tree contains no consumer-maintained rustdoc configuration.

## What to compare

| Page | Purpose |
| --- | --- |
| [Component reference](component_reference/index.html) | Authoring syntax beside rendered results |
| [API reference](struct.DocumentationTarget.html) | Framework-native Rust API output |

## Use Dockle with rustdoc

Add a rustdoc target to `dockle.toml`. Dockle invokes Cargo with an isolated
target directory and attaches the shared theme:

```toml
[[targets]]
name = "rust"
framework = "rustdoc"
source = "rust-crate"
```

Then build just that target:

```shell
python -m dockle check rust
python -m dockle build rust
```

Every example uses the same concepts and page structure so visual differences
come from the generator integration rather than unrelated prose.
