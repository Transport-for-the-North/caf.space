Welcome to caf.space's documentation!
=====================================

Common Analytical Framework (CAF) Space contain geo-processing functionality useful
for transport planners. Primarily it is a tool for generating standard weighting
translations in `.csv` format describing how to convert between different zoning systems.
The aim is to free tools up from directly having to do their own geo-processing, and    
instead have a single source of truth to get them from!

Tool info
---------
The tool has two main options for running a translation, either a purely spatial translation
(where overlapping zones are split by area), or a weighted translation where overlapping
zones are split by some other type of weighting data like population or employment data. for
most purposes a weighted translation will be more accurate, and it is up to the user to
decide the most appropriate weighting data to use. For both types of translation the tool
runs from a config file (a file called config.yml in the base folder). Parameters for this
config are described below.

Installation
------------
caf.space can be installed from pip with the command:

pip install caf.space

After that the easiest way to use caf.space is to launch the GUI. This can by done by importing caf.space then calling SpaceUI

import caf.space as space

space.SpaceUI()

This will launch the GUI in a new window.

.. toctree::
   :maxdepth: 4
   :caption: Contents:



Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

Contents
--------

.. toctree::

   input
   zonesystem
   zone_trans
   weighted_trans
   op_model