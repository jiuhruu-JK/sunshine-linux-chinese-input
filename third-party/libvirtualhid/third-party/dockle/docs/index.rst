Dockle
======

Dockle builds documentation with multiple frameworks and gives the generated sites one coherent visual language.
Projects configure Dockle rather than maintaining configuration for every underlying generator.

Compare every adapter
---------------------

Each example presents the same authoring components and a native API reference. That makes framework differences easy
to spot without unrelated content getting in the way.

.. raw:: html

   <div data-dockle-target-cards></div>

Quick start
-----------

Install Dockle with the adapters your project uses, describe each documentation target in ``dockle.toml``, then let
Dockle generate and invoke the native configuration:

.. code-block:: shell

   python -m pip install "lizardbyte-dockle[all]"
   dockle check
   dockle build

The output is one publishable site. Dockle owns the common navigation, search, typography, color scheme, components,
and project identity while each upstream framework continues to parse its own source language.

.. toctree::
   :maxdepth: 2

   distribution
   architecture
   configuration
   theme-preview
