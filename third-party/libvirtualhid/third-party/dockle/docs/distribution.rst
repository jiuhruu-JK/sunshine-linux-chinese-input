Installation and distribution
=============================

Dockle has one shared presentation layer with two supported entry points. The ``lizardbyte-dockle`` Python
distribution installs the multi-framework ``dockle`` orchestrator, while ``@lizardbyte/dockle`` packages the same
first-party JSDoc template with a JavaScript-only ``dockle-jsdoc`` command. The npm entry point is intentionally
narrower; it does not reimplement the multi-framework configuration or adapters in JavaScript.

Python projects
---------------

PyPI will be the canonical package channel. After the first release, install the core command or select the
Python-backed adapters that the project needs:

.. code-block:: shell

   python -m pip install lizardbyte-dockle
   python -m pip install "lizardbyte-dockle[sphinx]"
   python -m pip install "lizardbyte-dockle[mkdocs]"
   python -m pip install "lizardbyte-dockle[all]"

``pipx install "lizardbyte-dockle[all]"`` is a good fit for developers who want a globally available command in an
isolated environment. Doxygen, Node.js/JSDoc, Cargo, and Graphviz remain native tool dependencies when their adapters
are used.

Tested compatibility
--------------------

The release workflows and hosted dogfood build exercise the following compatibility baseline. Python dependencies are
resolved by ``uv.lock``; native tools are pinned in the Read the Docs environment or selected by the hosted runner.

================  =======================  ================================================
Component         Tested versions          Compatibility promise
================  =======================  ================================================
Python            3.11 and 3.14            Supported range starts at Python 3.11.
Sphinx            9.0.4 and 9.1.0          ``sphinx>=8.1``; both locked Python resolutions.
MyST Parser       5.1.0                    Markdown support for Sphinx.
MkDocs            1.6.1                    ``mkdocs>=1.6``.
Doxygen           1.18.0                   Pinned hosted end-to-end build.
Graphviz          14.1.2                   Pinned with Doxygen for graph generation.
JSDoc             4.0.5                    Pinned npm fixture and hosted build.
Node.js           22 and 24                Read the Docs runtime and npm package CI.
Rust and rustdoc  1.91                     Read the Docs rustdoc runtime.
================  =======================  ================================================

Newer native generator versions are expected to work but are not part of the initial compatibility promise until the
dogfood build and visual fixtures exercise them.

Standalone executables
----------------------

Release artifacts package the same Python command as a standalone executable for Windows, Linux, and macOS on Intel
and ARM64. These binaries make Dockle usable from C++, JavaScript, and Rust repositories without asking contributors
to manage a Python environment. Sphinx, MyST, MkDocs, and Markdown are bundled because they run in Python. Doxygen,
Graphviz, Node.js/JSDoc, and Cargo/rustdoc remain external native toolchains.

Native JSDoc package
--------------------

JavaScript projects that only need JSDoc can install ``@lizardbyte/dockle``. It contains JSDoc, Dockle's native JSDoc
template, and a small ``dockle-jsdoc`` command; it does not install Python, Doxygen, Graphviz, Sphinx, MkDocs, or Rust:

.. code-block:: shell

   npm install --save-dev @lizardbyte/dockle
   npx dockle-jsdoc src --destination docs

The package reads the consumer's name, version, and repository from ``package.json``. A normal JSDoc configuration can
provide additional source and template options, and ``dockle-jsdoc --configure jsdoc.json`` applies the Dockle template
unless another template was explicitly selected. The multi-framework Python adapter emits the same native template
configuration from ``dockle.toml``.

The standalone template accepts the equivalent ``extraStylesheets`` and
``extraJavascript`` arrays under ``templates.dockle``. Each entry can be a
project file or an absolute HTTP(S) URL; local assets are copied into the
generated site:

.. code-block:: json

   {
     "templates": {
       "dockle": {
         "extraStylesheets": ["docs/project.css", "https://cdn.example.com/widget.css"],
         "extraJavascript": ["docs/project.js", "https://cdn.example.com/widget.js"]
       }
     }
   }

A crates.io package is less useful: Cargo expects source that it can compile, while Dockle has no Rust API. Cargo users
can consume the standalone release asset directly; a crate should wait for a Rust-native API or a supported
``cargo-binstall`` contract.

CMake projects
--------------

CMake integration locates the installed or standalone ``dockle`` command and exposes a documentation target. It does
not make Dockle itself a CMake project. ``dockle cmake-dir`` prints the module directory from any Python installation;
add that directory to ``CMAKE_MODULE_PATH`` and use:

.. code-block:: cmake

   include(Dockle)
   dockle_add_docs(docs CONFIG "${PROJECT_SOURCE_DIR}/dockle.toml")

Add ``ALL`` to include documentation in the default build, or ``TARGETS cpp-api`` to build only named Dockle targets.
Set ``DOCKLE_EXECUTABLE`` when a project keeps a standalone binary in a tools directory. Otherwise the module finds the
``dockle`` command and falls back to ``Python3 -m dockle``.

Release requirements
--------------------

The CI workflow obtains its build version from LizardByte's ``release_setup`` action, updates the Python project
metadata only inside the runner, builds the Python source archive, wheel, npm package, and six native executables, and
smoke-tests every installation path. A selected ``master`` build creates a draft prerelease containing the Python
distributions and native executables. Changing that release to a stable release triggers the registry workflows. PyPI
uses OpenID Connect trusted publishing, while npmjs and GitHub Packages use the organization-standard npm release
workflow. Pull requests, ordinary pushes, drafts, and prereleases never publish registry packages. GitHub provides
artifact digests in its API and user interface.

The PyPI trusted publisher targets the ``lizardbyte-dockle`` project from the ``LizardByte/dockle`` repository,
``ci-release.yml`` workflow, and ``pypi`` environment.

npm trusted publishing can only be configured after ``@lizardbyte/dockle`` exists in the registry. If npm does not
allow the release workflow to create the package, bootstrap that package once under the LizardByte scope, then bind its
trusted publisher to ``_update-npm.yml`` and the ``npmjs`` environment. Subsequent publication remains release-driven;
the repository's ``npm-pkg`` label keeps the centrally managed workflow in sync with the organization template.
