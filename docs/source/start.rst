Quick Start
===========

CAF space is provided as a Python package and a command-line utility with a GUI.
The command-line utility aims to make some of the commonly used functionality 
available without needing to use Python code, see :ref:`usage` for details.

CAF space can be installed from pip, conda-forge or pipx
(when using as a command-line utility).

Pip
---
Installing through pip is easy and can be done in one command:
``pip install caf.space``

conda-forge
-----------
Installing through conda-forge is easy and can be done in one command:
``conda install caf.space -c conda-forge``

Pipx
----

.. todo::
    Does CAF space support being installed with
    `Pipx <https://pipx.pypa.io/stable/>`__?


Usage
-----

The tool has two main options for running a translation, either a purely spatial translation
(where overlapping zones are split by area), or a weighted translation where overlapping
zones are split by some other type of weighting data like population or employment data.

More details can be found in :ref:`tool usage`.

Python
^^^^^^

.. todo::
    Does CAF space have a suggested alias?

When using CAF space functionality within Python:

.. code:: python

    import caf.space

The :ref:`user guide` contains :ref:`tutorials` and :ref:`code examples`, which
explain available functionality. For a detailed look at the
package API see :ref:`API Reference`.
