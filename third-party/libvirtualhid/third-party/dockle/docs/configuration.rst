Configuration reference
=======================

Dockle reads one TOML file, ``dockle.toml``, from the current directory by default. Use
``dockle --config path/to/dockle.toml`` to select another file. Relative paths are resolved from the directory that
contains the selected configuration file.

Complete example
----------------

.. code-block:: toml

   [project]
   name = "Example"
   version = "1.2.0"
   description = "Example project documentation"
   repository = "https://github.com/example/example"
   author = "Example maintainers"
   copyright = "2026, Example maintainers"
   logo = "branding/logo.png"
   favicon = "branding/favicon.svg"

   [theme]
   primary = "#2962ff"
   content = "#2e3440"
   light_background = "#ffffff"
   dark_background = "#131416"

   [build]
   output = "_site"
   work = ".dockle"
   strict = true
   clean = true

   [tools]
   doxygen = "/opt/doxygen/bin/doxygen"

   [[targets]]
   name = "docs"
   title = "Project documentation"
   framework = "sphinx"
   source = "docs"
   home = true

   [[targets]]
   name = "api"
   title = "API reference"
   description = "Public headers and authored guides."
   framework = "doxygen"
   source = "."

   [targets.doxygen]
   inputs = ["README.md", "docs", "include"]
   excludes = ["docs/private"]
   exclude_patterns = ["*/generated/*"]
   image_paths = ["docs/images"]
   include_paths = ["include"]
   predefined = ["EXAMPLE_PUBLIC_API=1"]
   extra_stylesheets = ["docs/project.css"]
   extra_javascript = ["docs/project.js", "https://cdn.example.com/widget.js"]
   extra_files = ["docs/project-icon.svg"]
   aliases = ['example_link{1}=<a href="\\1">Example</a>']
   main_page = "README.md"
   dot_graph_max_nodes = 75
   warn_if_undocumented = true
   warn_no_paramdoc = true

Project metadata
----------------

``project.name`` is required. The optional ``version``, ``description``, ``repository``, ``author``, and ``copyright``
values are translated into native metadata where a generator supports them. Every generated documentation backend
automatically exposes a repository button when ``repository`` is set, with GitHub and GitLab icons plus a generic Git
fallback for other services. The optional ``logo`` and ``favicon`` may name files within the project or HTTP(S) URLs.
Dockle copies local assets into every generated backend and uses remote assets directly. On Read the Docs,
``READTHEDOCS_VERSION`` overrides ``version``. A
numeric pull-request version replaces the final component of an all-zero configured version (for example, ``0.0.0``
becomes ``0.0.908``), preserving each project's version width.

Theme tokens
------------

All theme settings are optional. ``primary``, ``content``, ``light_background``, and ``dark_background`` accept CSS
color values. ``font`` and ``code_font`` accept CSS font-family stacks. Unsafe delimiters are rejected because these
values are written into a generated stylesheet.

Build behavior
--------------

``build.output``
   Root of the publishable site. Defaults to ``_site``.

``build.work``
   Disposable native configurations and intermediate files. Defaults to ``.dockle``.

``build.strict``
   Enables warning-as-error behavior in each adapter. Defaults to ``false``.

``build.clean``
   Replaces generated output instead of merging into it. A full build owns and cleans the whole output tree; a build
   naming one or more targets only cleans those target directories. Defaults to ``true``.

Both output paths must stay within the project and must not contain one another.

Targets
-------

At least one ``[[targets]]`` table is required. ``name``, ``framework``, and ``source`` are required. Names use
lowercase letters, numbers, hyphens, and underscores and become output directory names by default. ``title`` and
``description`` label the target on a generated multi-target portal. ``output`` can select another directory below
``build.output``. Set ``publish = false`` when an adapter must generate non-HTML artifacts for another target without
appearing in the published site.

One published target of any framework may set ``home = true``. Dockle publishes that target at ``build.output``. When
other published targets exist, Dockle injects comparison cards after its first heading; control their exact location
with ``<div data-dockle-target-cards></div>`` in a raw HTML block. A home target cannot set ``output``; all other
targets remain in their own directories below it. Redirect-only compatibility pages are generated beneath
``build.output/<home target name>`` so target-prefixed deep links remain valid without adding a separate entry page.

The supported framework names and ``entry`` behavior are:

==========  =======================  =============================================================
Framework   Native requirement       ``entry``
==========  =======================  =============================================================
Sphinx      Python ``sphinx``         Root document without its extension; defaults to ``index``.
Doxygen     ``doxygen`` executable    Existing Markdown main page; otherwise normal Doxygen behavior.
MkDocs      Python ``mkdocs``         Reserved; MkDocs discovers ``index.md`` normally.
JSDoc       ``jsdoc`` executable      Existing README or Markdown landing page.
rustdoc     Cargo and Rust            Reserved; ``source`` names a crate directory or ``Cargo.toml``.
==========  =======================  =============================================================

Each non-home output directory must be unique and must remain below ``build.output``. Entry paths cannot be absolute
or escape the source directory.

Doxygen target settings
-----------------------

Dockle always generates the Doxyfile. A Doxygen target can add a typed
``[targets.doxygen]`` table for project-specific behavior without introducing
a second native configuration file:

``inputs``
   Source files and directories. Defaults to the target ``source``.

``excludes`` and ``exclude_patterns``
   Paths and glob patterns omitted from Doxygen's recursive input scan.

``image_paths`` and ``include_paths``
   Additional image lookup and source include directories.

``predefined``
   Project-specific preprocessor definitions. Dockle defines only ``DOXYGEN``
   by default; platform and feature macros belong here because they change
   which project declarations are visible.

``extra_stylesheets`` and ``extra_javascript``
   Project files or absolute HTTP(S) URLs injected into every generated page
   in configuration order. Dockle copies local assets to the target output.

``extra_files``
   Other project files copied through Doxygen's supported HTML hook.

``aliases``
   Complete project-specific Doxygen alias definitions. Dockle adds these after
   its shared alert, tab, color, example, and expander aliases.

``main_page``
   Markdown main page anywhere inside the project. When omitted, Dockle uses
   ``source / entry`` if that file exists.

``dot_graph_max_nodes``
   Graph node limit from 0 through 10000. Defaults to ``50``.

``optimize_output_java`` and ``separate_member_pages``
   Native presentation switches used by projects such as C# API references.

``warn_if_undoc_enum_val``, ``warn_if_undocumented``, and ``warn_no_paramdoc``
   Strict documentation checks. All three default to ``true``.

JSDoc target settings
---------------------

Use ``[targets.jsdoc]`` when the API source and authored landing page live in
different parts of the repository:

``inputs``
   JavaScript source files and directories. Defaults to the target ``source``.

``readme``
   Authored JSDoc landing page anywhere inside the project.

``include_pattern`` and ``exclude_pattern``
   Regular expressions applied by JSDoc while discovering source files. The
   include pattern defaults to JavaScript and JSX variants.

``extra_files``
   Project files copied to the JSDoc output root.

``extra_stylesheets`` and ``extra_javascript``
   Project files or absolute HTTP(S) URLs injected into every generated page
   in configuration order. Dockle copies local assets to the target output.

MkDocs target settings
----------------------

Use ``[targets.mkdocs]`` to attach project assets through MkDocs' supported
configuration hooks:

``extra_stylesheets`` and ``extra_javascript``
   Local paths relative to the documentation source, or absolute web URLs.
   Dockle's theme assets remain in place.

Sphinx target settings
----------------------

Use ``[targets.sphinx]`` for authored assets that the generated ``conf.py``
must expose:

``exclude_patterns``
   Source patterns Sphinx should omit.

``static_paths``
   Static asset directories inside the project.

``extra_stylesheets`` and ``extra_javascript``
   Asset names from the configured static directories, or absolute web URLs.
   Dockle's theme assets remain in place.

``source_edit_link``
   URL template for the page's pencil button. Dockle replaces ``{filename}``
   with the current Sphinx source filename.

rustdoc target settings
-----------------------

Use ``[targets.rustdoc]`` to attach supporting assets:

``extra_stylesheets`` and ``extra_javascript``
   Project files or absolute HTTP(S) URLs injected into every generated page
   in configuration order. Dockle copies local assets to the target output.

``extra_files``
   Project files copied beside every generated rustdoc HTML page. Cargo runs
   from the manifest directory so its local ``.cargo/config.toml`` and HTML
   hook paths are honored.

Tool resolution
---------------

Dockle normally finds native executables on ``PATH``. Python console scripts are also resolved beside the running
Python interpreter, and Node.js tools are resolved from ``node_modules/.bin`` in the project. A ``[tools]`` entry can
override any adapter with a command name or a path relative to ``dockle.toml``:

.. code-block:: toml

   [tools]
   sphinx = ".venv/bin/sphinx-build"
   doxygen = "vendor/doxygen/bin/doxygen"
   mkdocs = ".venv/bin/mkdocs"
   jsdoc = "node_modules/.bin/jsdoc"
   rustdoc = "cargo"

Generated native files
----------------------

Dockle writes generated native configuration under ``build.work/<target>/`` and replaces it on every build. These
files are deliberately not a public configuration surface and should not be edited or committed. Use
``dockle build --dry-run`` to inspect commands without generating files, and ``dockle check`` to validate sources and
tool availability before building.
