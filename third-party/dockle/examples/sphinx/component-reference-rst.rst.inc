reStructuredText component reference
====================================

This page mirrors the Markdown component reference with native Sphinx syntax. Each section shows the source first and
then the rendered result.

Admonitions
-----------

Source
~~~~~~

.. code-block:: rst

   .. note::

      Useful context that supplements the surrounding content.

   .. tip::

      A practical suggestion that can improve the result.

   .. important::

      Information the reader must understand before continuing.

   .. warning::

      A condition that may cause an unexpected result.

   .. caution::

      An action that may have harmful consequences.

   .. danger::

      A condition likely to cause serious failure.

   .. error::

      A failure state must be corrected.

   .. hint::

      A small clue helps the reader make progress.

   .. seealso::

      The Markdown component reference contains the same examples.

   .. admonition:: Custom title

      A neutral custom admonition.

Result
~~~~~~

.. note::

   Useful context that supplements the surrounding content.

.. tip::

   A practical suggestion that can improve the result.

.. important::

   Information the reader must understand before continuing.

.. warning::

   A condition that may cause an unexpected result.

.. caution::

   An action may have harmful consequences.

.. danger::

   A condition is likely to cause serious failure.

.. error::

   A failure state must be corrected.

.. hint::

   A small clue helps the reader make progress.

.. seealso::

   The Markdown component reference contains the same examples.

.. admonition:: Custom title

   A neutral custom admonition.

Code blocks
-----------

Source
~~~~~~

.. code-block:: rst

   .. code-block:: python

      targets = ["sphinx", "doxygen", "mkdocs", "jsdoc", "rustdoc"]
      enabled = [target for target in targets if target != "disabled"]

Result
~~~~~~

.. code-block:: python

   targets = ["sphinx", "doxygen", "mkdocs", "jsdoc", "rustdoc"]
   enabled = [target for target in targets if target != "disabled"]

Tables
------

Source
~~~~~~

.. code-block:: rst

   ==========  =====================
   Framework   Native configuration
   ==========  =====================
   Sphinx      ``conf.py``
   Doxygen     ``Doxyfile``
   MkDocs      ``mkdocs.yml``
   ==========  =====================

Result
~~~~~~

==========  =====================
Framework   Native configuration
==========  =====================
Sphinx      ``conf.py``
Doxygen     ``Doxyfile``
MkDocs      ``mkdocs.yml``
==========  =====================

Disclosure tabs
---------------

Portable tab sets use semantic ``details`` elements so their content remains useful without JavaScript. Dockle upgrades
them into the same keyboard-accessible presentation used by the Markdown examples. Sets with the same optional
``data-dockle-tab-group`` name keep their selections linked.

Source
~~~~~~

.. code-block:: html

   <div class="dockle-tabs" data-dockle-tab-group="installer">
     <details open><summary>Python</summary><p>Install from PyPI.</p></details>
     <details><summary>Node.js</summary><p>Use the npm launcher.</p></details>
   </div>
   <div class="dockle-tabs" data-dockle-tab-group="installer">
     <details open><summary>Python</summary><p>Run Dockle from the Python environment.</p></details>
     <details><summary>Node.js</summary><p>Run the Dockle JSDoc launcher.</p></details>
   </div>

Result
~~~~~~

.. raw:: html

   <div class="dockle-tabs" data-dockle-tab-group="installer">
     <details open><summary>Python</summary><p>Install from PyPI.</p></details>
     <details><summary>Node.js</summary><p>Use the npm launcher.</p></details>
   </div>
   <div class="dockle-tabs" data-dockle-tab-group="installer">
     <details open><summary>Python</summary><p>Run Dockle from the Python environment.</p></details>
     <details><summary>Node.js</summary><p>Run the Dockle JSDoc launcher.</p></details>
   </div>
