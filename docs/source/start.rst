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

`Pipx <https://pipx.pypa.io/stable/>`__ is the recommended way to use caf.space as a utility.
It handles installing the tool in its own container, and makes it easy to access from a terminal.

First install pipx into your default Python environment using pip or conda, see
`Pipx's installation instructions <https://pipx.pypa.io/stable/installation/>`__ for more details.

Once pipx is installed and setup caf.space can be installed using ``pipx install caf.space``,
this should make it available in command-line anywhere using ``caf.space ...``.


Usage
-----

Using caf.space as a command-line tool can be done in one of two ways:

- Called directly (if installed using pipx) ``caf.space ...``
- Ran as a Python module ``python -m caf.space ...``

The graphical user interface (GUI) can be accessed by calling caf.space (as above)
without any arguments i.e. ``caf.space``.

More details can be found in :ref:`tool usage`.

Python
^^^^^^

When using caf.space functionality within Python the recommended alias is `cs`:

.. code:: python

    import caf.space as cs

The :ref:`user guide` contains :ref:`tutorials` and :ref:`code examples`, which
explain available functionality. For a detailed look at the
package API see :ref:`API Reference`.
