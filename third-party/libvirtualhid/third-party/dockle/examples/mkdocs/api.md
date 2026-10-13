# API reference

MkDocs focuses on prose rather than extracting a language API. This example
uses Dockle's target configuration as its reference surface.

## `targets`

Each `[[targets]]` table selects an upstream generator and source directory.

| Key | Type | Meaning |
| --- | --- | --- |
| `name` | string | Stable target and output name |
| `framework` | string | Generator adapter to invoke |
| `source` | path | Input resolved from `dockle.toml` |
| `entry` | string | Optional framework entry point |
