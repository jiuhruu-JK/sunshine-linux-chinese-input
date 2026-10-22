# JSDoc example

This fixture demonstrates the JSDoc adapter with JavaScript API documentation.
Dockle generates `jsdoc.json`, points it at the source and tutorials, and
normalizes the generated HTML with the shared presentation layer.

> [!NOTE]
> This source tree contains no consumer-maintained JSDoc configuration.

## What to compare

| Page | Purpose |
| --- | --- |
| [Component reference](tutorial-component-reference.html) | Authoring syntax beside rendered results |
| [API reference](module-dockle-demo.html) | Framework-native JavaScript API output |

## Use Dockle with JSDoc

Add a JSDoc target to `dockle.toml`. Dockle supplies `jsdoc.json`, discovers
the tutorial directory, and attaches the shared theme:

```toml
[[targets]]
name = "javascript"
framework = "jsdoc"
source = "docs/javascript"
entry = "README.md"
```

Then build just that target:

```shell
python -m dockle check javascript
python -m dockle build javascript
```

Every example uses the same concepts and page structure so visual differences
come from the generator integration rather than unrelated prose.
