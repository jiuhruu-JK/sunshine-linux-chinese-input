Architecture and roadmap
========================

Goals
-----

Dockle owns the stable, framework-neutral interface for documentation builds. It should:

* describe project metadata, build targets, and visual tokens once;
* generate disposable native configuration rather than modifying consumer files;
* invoke upstream generators normally so their source-language features remain available;
* make generated sites feel like parts of one documentation system; and
* fail clearly when a tool, source path, or configuration value is invalid.

Dockle is not a new documentation parser. Reimplementing Sphinx domains, Doxygen's language model, rustdoc's type
information, or JSDoc's tag processing would discard the strongest part of each tool.

Build pipeline
--------------

::

   dockle.toml
       |
       v
   validated neutral model
       |
       +--> Sphinx adapter  --> generated conf.py
       +--> Doxygen adapter --> generated Doxyfile
       +--> MkDocs adapter  --> generated mkdocs.yml
       +--> JSDoc adapter   --> generated jsdoc.json
       +--> rustdoc adapter --> generated Cargo invocation
       |
       v
   upstream/native themed HTML output
       |
       +--> Sphinx, MkDocs, JSDoc native templates
       +--> Doxygen, rustdoc compatibility enhancement
       |
       v
   publishable target directories
       |
       v
   Sphinx home target, comparison cards, and cross-target links --> one hosted documentation site

Configuration boundary
----------------------

``dockle.toml`` is the public contract. Generated files under ``.dockle/<target>`` are implementation details and are
deleted before each build. The first schema deliberately exposes only concepts shared by the supported frameworks:

* project name, version, description, repository, author, and copyright;
* theme colors and font stacks;
* output/work directories and strict/clean behavior;
* named targets with a title, description, framework, source, output, entry document, and optional Sphinx home role;
* typed, namespaced settings for generator behavior that has no portable equivalent, beginning with Doxygen inputs,
  paths, definitions, assets, warnings, graph limits, and aliases.

Unvalidated framework-specific passthrough dictionaries remain intentionally absent. They make an integration quick to
ship but turn the wrapper into five native configuration files hidden inside TOML. New settings are first evaluated for
a portable meaning; irreducible behavior receives a strict typed table owned and documented by Dockle.

Theme strategy
--------------

Furo is a visual reference only: content-first pages, quiet navigation chrome, readable typography, responsive
behavior, and automatic light/dark palettes. Dockle does not depend on or inherit from Furo. It ships and registers its
own Sphinx theme, inheriting only Sphinx's intentionally minimal ``basic`` template primitives. Doxygen receives
Dockle's generated CSS through its supported extra-stylesheet setting. JSDoc uses a first-party native template that
delegates semantic document rendering to JSDoc's default publisher through its supported layout and static-file hooks.
Rustdoc receives the shared stylesheet after the upstream build.

The compatibility layer normalizes design tokens and common content components. Post-processing marks each page with
its framework, attaches subpath-safe relative assets, adds common search and color-scheme controls, renders Lucide
icons, and links back to the root portal. Sphinx, MkDocs, and JSDoc use maintained native templates. Doxygen keeps its
semantic HTML while Dockle completes missing page outlines and derives previous/next links from Doxygen's generated
navigation tree. Rustdoc receives the same controls through generated-HTML enhancement. Icons come from the pinned
``lucide`` npm package; Dockle packages its official browser runtime so built sites remain self-contained. These
implementations are first-party Dockle code; ``doxygen-awesome-css`` and ``doxyconfig`` are design references, not
dependencies.

Each target publishes a ``dockle-search.html`` results page. The search field offers live suggestions and submits to
that page with a shareable ``?q=`` URL. On Read the Docs, Dockle uses the Addons project and version metadata to query
the hosted search API; elsewhere, and when a hosted index is unavailable, it uses the target's local ``search.json``.

Dockle also packages the complete pinned Highlight.js browser distribution. After a generator renders authored code,
the shared client normalizes its language identifier and replaces native Pygments, Prettify, Doxygen, or rustdoc token
markup with one Highlight.js token stream. This gives every adapter the same lexer behavior and palette without making
the npm-only JSDoc path depend on Python. Line-numbered native source listings are intentionally left intact because
their anchors are part of the generator's navigation. ``shell`` identifies commands or scripts; ``console`` is
reserved for prompted terminal transcripts and output.

Milestones
----------

Milestone 0: executable foundation (implemented)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

* Strict TOML loader with safe, project-relative output paths.
* ``build``, ``build --dry-run``, and ``check`` commands.
* Initial adapters for Sphinx, Doxygen, MkDocs, JSDoc, and rustdoc.
* Generated Furo-inspired CSS with per-project design tokens.
* Framework-free unit tests for configuration, adapters, and HTML normalization.

Milestone 1: theme fidelity (in progress)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

* Representative visual fixtures for every supported generator are implemented and built together.
* The native MkDocs theme now shares Dockle's sidebar/page structure and assets with Sphinx.
* The native JSDoc template replaces post-build HTML rewriting and is consumable independently from npm.
* Keep the documented supported-version matrix current and add visual regression baselines.
* Add accessible color contrast, keyboard navigation, and mobile-layout checks.
* Decide whether rustdoc needs a maintained template or a deliberately narrower compatibility promise.

Milestone 2: multi-target documentation sites (in progress)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

* A root Sphinx target with injected comparison cards and cross-target return links is implemented.
* Theme and portal URLs are relative and safe under hosted, versioned subpaths.
* Build a combined search index without replacing framework-local search prematurely.
* Add ``serve`` with file watching and incremental rebuilds.

Hosted dogfood build
--------------------

The repository's Read the Docs configuration deliberately has no top-level Sphinx or MkDocs selection. A conda
environment provides pinned Doxygen and Graphviz together so strict graph generation cannot depend on the base image.
Custom commands create that environment and run Dockle inside it, then publish ``_site`` as the HTML artifact. This
exercises the public configuration path rather than maintaining a second hosting-only build graph.

Milestone 3: ecosystem and distribution
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

* Define a typed third-party adapter interface.
* Add adapters based on demand, with TypeDoc and Dokka as likely candidates.
* Publish reproducible Python packages, standalone platform executables, and a supported CI action.
* Maintain the native npm/JSDoc and CMake installation paths; publish a crate only when it adds Rust value.
* Add machine-readable schema documentation and configuration migration tooling before stabilizing version 1.

Known risks
-----------

Generated HTML and native template APIs change between upstream releases. Dockle should test explicit compatibility
ranges and prefer stable extension hooks over copied upstream headers. Shared styling also needs semantic fixture pages;
a successful generator exit alone does not prove navigation, search, or responsive layout.
