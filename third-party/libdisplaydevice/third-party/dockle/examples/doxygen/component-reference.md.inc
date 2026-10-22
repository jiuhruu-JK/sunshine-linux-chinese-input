## Doxygen-specific components

### Authoring aliases

Dockle generates aliases for admonitions Doxygen does not provide. Consumers
can use them in Markdown pages and API comments without maintaining a shared
`Doxyfile`.

#### Source

```text
@admonition{Custom title |:| A neutral custom admonition.}
@attention{Something requires immediate consideration.}
@caution{An action may have harmful consequences.}
@danger{A condition is likely to cause serious failure.}
@error{A failure state must be corrected.}
@hint{A small clue helps the reader make progress.}
@important{The reader must understand this before continuing.}
@note{Useful supplemental context.}
@seealso{A closely related page or API.}
@tip{A practical suggestion.}
@todo{Work remains to be completed.}
@warning{A condition may cause an unexpected result.}
```

#### Result

@admonition{Custom title |:| A neutral custom admonition.}

@attention{Something requires immediate consideration.}

@caution{An action may have harmful consequences.}

@danger{A condition is likely to cause serious failure.}

@error{A failure state must be corrected.}

@hint{A small clue helps the reader make progress.}

@important{The reader must understand this before continuing.}

@note{Useful supplemental context.}

@seealso{A closely related page or API.}

@tip{A practical suggestion.}

@todo{Work remains to be completed.}

@warning{A condition may cause an unexpected result.}

### Tab aliases

Dockle also generates `@tab`, `@tabs`, and `@tabs_grouped` aliases. The
grouped form takes a stable group name before the `|:|` separator; tab sets
with the same name keep their selected labels synchronized. Use `@tabs` when
the selection should remain independent.

#### Source

```text
@tabs_grouped{workflow|:|
@tab{Configure|:|Dockle writes the Doxyfile.}
@tab{Build|:|Doxygen builds the HTML site.}
}

@tabs_grouped{workflow|:|
@tab{Configure|:|Review the generated configuration.}
@tab{Build|:|Review the generated pages.}
}
```

#### Result

@tabs_grouped{workflow|:|
@tab{Configure|:|Dockle writes the Doxyfile.}
@tab{Build|:|Doxygen builds the HTML site.}
}

@tabs_grouped{workflow|:|
@tab{Configure|:|Review the generated configuration.}
@tab{Build|:|Review the generated pages.}
}
