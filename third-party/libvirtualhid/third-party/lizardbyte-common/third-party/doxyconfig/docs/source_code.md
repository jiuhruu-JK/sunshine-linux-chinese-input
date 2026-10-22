# Source Code

Code should be documented using Doxygen syntax.

## Guidelines

### Doxygen Comments

* Use Doxygen comments to document all files, functions, classes, and variables.
* [Inline documenation block](#inline-documentation-blocks) should use the following format:

  @verbatim
///< A brief description of the member.
@endverbatim

* Multi-line comments, such as for a [documentation block](#documentation-blocks), should use the following format:

  @verbatim
/**
 * @brief A brief description of the member.
 * More detailed description of the member.
 */
@endverbatim

### Documentation Blocks

Documentation blocks should be placed above the declaration of the function, class, or variable. Below is an example
of a documentation block for the main function.

@verbatim
/**
 * @brief Main application entry point.
 * @param argc The number of arguments.
 * @param argv The arguments.
 * @return The exit code.
 * @examples
 * main(1, const char* args[] = {"hello", "markdown", nullptr});
 * @examples_end
 */
int main(int argc, char *argv[]);
@endverbatim

@note The \@examples and \@examples_end tags are not standard Doxygen tags. They are custom aliases
we have specified to simplify documenting examples. Do not confuse this with the standard \@example tag.

In some cases, it could be valuable to have slightly different documentation for the definitions, especially when
the definition may change depending on the platform or other factors. In such cases, you should put the documentation
that is common in the declaration and the definition-specific documentation in the definition. Below is an example of
how to document the declaration and definition of a function.

@verbatim
// myFile.h
/**
 * @brief A brief description of the function.
 * @param arg1 Describe the first argument.
 * @param arg2 Describe the second argument.
 * @return Describe the result.
 */
int myFunction(int arg1, int arg2);

// myFile.cpp
/**
 * This describes anything which is specific to the implementation of the function.
 */
int myFunction(int arg1, int arg2)
{
    // Implementation
}
@endverbatim

### File Documentation

The file documentation block must be placed at the top of the file. If it is not present, Doxygen will ignore the file.
Understandably, it is difficult to make a creative description for every file, although it is still required.
Below is an example of a file documentation block.

@verbatim
/**
 * @file src/main.cpp
 * @brief Main application entry point.
 */
@endverbatim

### Inline Documentation Blocks

Inline comments can be used to describe enum values, variables, and other code constructs.
To document the members of a file, struct, union, class, or enum, it is sometimes desired to place the documentation
block after the member instead of before. For this purpose you have to put an additional `<` marker in the comment
block. Below is an example of an inline comment for an enum value.

@verbatim
enum class MyEnum
{
   FIRST_VALUE,  ///< A brief description of the FIRST_VALUE
   SECOND_VALUE  ///< A brief description of the SECOND_VALUE
};
@endverbatim

### Admonitions

#### Standard Admonitions

<table class="doxtable code-result-table">
<tr>
<th>Code</th>
<th>Result</th>
</tr>
<tr>
<td>
@verbatim
@attention Attention needed.
@endverbatim
</td>
<td>
@attention Attention needed.
</td>
</tr>
<tr>
<td>
@verbatim
@important An important message.
@endverbatim
</td>
<td>
@important An important message.
</td>
</tr>
<tr>
<td>
@verbatim
@note A note.
@endverbatim
</td>
<td>
@note A note.
</td>
</tr>
<tr>
<td>
@verbatim
@pre A precondition.
@endverbatim
</td>
<td>
@pre A precondition.
</td>
</tr>
<tr>
<td>
@verbatim
@remark Some remarks.
@endverbatim
</td>
<td>
@remark Some remarks.
</td>
</tr>
<tr>
<td>
@verbatim
@warning A warning.
@endverbatim
</td>
<td>
@warning A warning.
</td>
</tr>
</table>

#### GitHub Flavored Markdown Admonitions

<table class="doxtable code-result-table">
<tr>
<th>Code</th>
<th>Result</th>
</tr>
<tr>
<td>
@verbatim
> [!CAUTION]
> This is a caution.
@endverbatim
</td>
<td>

> [!CAUTION]
> This is a caution.

</td>
</tr>
<tr>
<td>
@verbatim
> [!IMPORTANT]
> This is important.
@endverbatim
</td>
<td>

> [!IMPORTANT]
> This is important.

</td>
</tr>
<tr>
<td>
@verbatim
> [!NOTE]
> This is a note.
@endverbatim
</td>
<td>

> [!NOTE]
> This is a note.

</td>
</tr>
<tr>
<td>
@verbatim
> [!TIP]
> This is a tip.
@endverbatim
</td>
<td>

> [!TIP]
> This is a tip.

</td>
</tr>
<tr>
<td>
@verbatim
> [!WARNING]
> This is a warning.
@endverbatim
</td>
<td>

> [!WARNING]
> This is a warning.

</td>
</tr>
</table>

### Custom Aliases

We have defined some custom aliases to simplify documenting examples.

* \@examples - Start of an example block. This will format the following text as `cpp`.
* \@examples_end - End of an example block.

#### Lucide Icons

Use `\@lucide_icon{icon name}` to insert a Lucide icon.

<table class="doxtable code-result-table">
<tr>
<th>Code</th>
<th>Result</th>
</tr>
<tr>
<td>
@verbatim
@lucide_icon{check}
@endverbatim
</td>
<td>
@lucide_icon{check}
</td>
</tr>
</table>

#### Admonitions

<table class="doxtable code-result-table">
<tr>
<th>Code</th>
<th>Result</th>
</tr>
<tr>
<td>
@verbatim
@admonition{Custom Title | Content}
@endverbatim
</td>
<td>
@admonition{The one with the custom titles | It’s got a certain charm to it.}
</td>
</tr>
<tr>
<td>
@verbatim
@attention{Content}
@endverbatim
</td>
<td>
@attention{The sun causes global warming.}
</td>
</tr>
<tr>
<td>
@verbatim
@caution{Content}
@endverbatim
</td>
<td>
@caution{Cliff ahead: Don’t drive off it.}
</td>
</tr>
<tr>
<td>
@verbatim
@danger{Content}
@endverbatim
</td>
<td>
@danger{Mad scientist at work!}
</td>
</tr>
<tr>
<td>
@verbatim
@error{Content}
@endverbatim
</td>
<td>
@error{Does not compute.}
</td>
</tr>
<tr>
<td>
@verbatim
@hint{Content}
@endverbatim
</td>
<td>
@hint{Insulators insulate, until they are subject to ______ voltage.}
</td>
</tr>
<tr>
<td>
@verbatim
@important{Content}
@endverbatim
</td>
<td>
@important{Tech is not neutral, nor is it apolitical.}
</td>
</tr>
<tr>
<td>
@verbatim
@note{Content}
@endverbatim
</td>
<td>
@note{This is a note.}
</td>
</tr>
<tr>
<td>
@verbatim
@seealso{Content}
@endverbatim
</td>
<td>
@seealso{Other relevant information.}
</td>
</tr>
<tr>
<td>
@verbatim
@tip{Content}
@endverbatim
</td>
<td>
@tip{25% if the service is good.}
</td>
</tr>
<tr>
<td>
@verbatim
@todo{Content}
@endverbatim
</td>
<td>
@todo{Fix this.}
</td>
</tr>
<tr>
<td>
@verbatim
@warning{Content}
@endverbatim
</td>
<td>
@warning{Reader discretion is strongly advised.}
</td>
</tr>
</table>

#### Markers

<table class="doxtable code-result-table">
<tr>
<th>Code</th>
<th>Result</th>
</tr>
<tr>
<td>
@verbatim
@red{Content}
@endverbatim
</td>
<td>
@red{This is red.}
</td>
</tr>
<tr>
<td>
@verbatim
@blue{Content}
@endverbatim
</td>
<td>
@blue{This is blue.}
</td>
</tr>
<tr>
<td>
@verbatim
@green{Content}
@endverbatim
</td>
<td>
@green{This is green.}
</td>
</tr>
<tr>
<td>
@verbatim
@yellow{Content}
@endverbatim
</td>
<td>
@yellow{This is yellow.}
</td>
</tr>
</table>

#### Expander

<table class="doxtable code-result-table">
<tr>
<th>Code</th>
<th>Result</th>
</tr>
<tr>
<td>
@verbatim
@expander{Expander Title | Expander Content}
@endverbatim
</td>
<td>
@expander{Expander Title | Expander Content}
</td>
</tr>
</table>

#### Tabs

Use `\@tab_with_pipe` when the tab content contains a pipe (`|`). Its arguments use `|:|` as the separator.

<table class="doxtable code-result-table">
<tr>
<th>Code</th>
<th>Result</th>
</tr>
<tr>
<td>
@verbatim
@tabs{
  @tab{ Tab 1 Title | Tab 1 Content }
  @tab_with_pipe{ Pipeline |:| `printf 'Hello\n' | grep Hello` }
}
@endverbatim
</td>
<td>
@tabs{
  @tab{ Tab 1 Title | Tab 1 Content }
  @tab_with_pipe{ Pipeline |:| `printf 'Hello\n' | grep Hello` }
}
</td>
</tr>
</table>

<details style="display: none;">
  <summary></summary>
  [TOC]
</details>
