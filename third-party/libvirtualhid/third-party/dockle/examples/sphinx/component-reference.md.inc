## Sphinx-specific components

### Native admonition

MyST directives remain available when a custom title is useful.

#### Source

````markdown
```{admonition} Adapter detail
:class: important
Dockle generates `conf.py`; the consumer does not maintain it.
```
````

#### Result

```{admonition} Adapter detail
:class: important
Dockle generates `conf.py`; the consumer does not maintain it.
```
