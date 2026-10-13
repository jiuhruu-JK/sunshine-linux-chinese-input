Theme preview
=============

This page is a visual fixture for Dockle's first-party Sphinx theme. It deliberately combines the content patterns
that documentation sites use most often so regressions are easy to spot in a hosted preview.

Admonitions
-----------

.. note::

   Dockle generates ``conf.py`` and selects its own Sphinx theme. A consuming project only maintains
   ``dockle.toml`` and its documentation sources.

.. warning::

   The adapters intentionally fail the build on warnings when strict mode is enabled.

Code and API shapes
-------------------

Configuration stays framework-neutral:

.. code-block:: toml

   [project]
   name = "Example"

   [[targets]]
   name = "guide"
   framework = "sphinx"
   source = "docs"

.. py:function:: build(targets, *, strict=True)

   Build each selected documentation target and publish a common landing page.

   :param targets: Ordered target names from ``dockle.toml``.
   :param bool strict: Treat native generator warnings as errors.
   :returns: A result for every completed target.

Tables and lists
----------------

================  ================================  =====================
Framework         Dockle-owned configuration        Styling integration
================  ================================  =====================
Sphinx            ``conf.py``                       Native Dockle theme
Doxygen           ``Doxyfile``                      Extra stylesheet
MkDocs            ``mkdocs.yml``                    Native Dockle theme
JSDoc             ``jsdoc.json``                    Native Dockle template
rustdoc            Cargo command and environment    HTML normalization
================  ================================  =====================

The design aims for three qualities:

#. readable content at comfortable line lengths;
#. quiet navigation with a clear current-page state; and
#. matching typography, color, code, and spacing across generators.

Definition list
---------------

Adapter
   Translates Dockle configuration into a native generator invocation.

Compatibility theme
   Applies common design tokens to HTML that is still structurally owned by the upstream generator.

   Nested content remains clear at smaller screen sizes.
