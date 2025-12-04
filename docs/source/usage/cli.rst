Command-Line Interface
======================

CAF.space provides a command-line interface (CLI) for the zone correspondence functionality.
The below details the basic usage and arguments for running from the command line.

.. seealso::
    :ref:`graphical user interface` for information on parameters.

.. argparse::
    :module: caf.space.inputs
    :func: _create_parser
    :prog: caf.space

Config
------

CAF.space uses a configuration file in YAML format to provide all the parameters
for running zone correspondence with CLI. An example of the config file is given
below and details of the parameters are given in :ref:`parameters`.

.. code:: yaml

  zone_1:
    name: zone_1
    shapefile: examples/zone_1/zone_1.shp
    id_col: zone_1_id
  zone_2:
    name: zone_2
    shapefile: examples/zone_2/zone_2.shp
    id_col: zone_2_id
  cache_path: examples\test_cache
  method: test
  tolerance: 0.98
  rounding: True
  filter_slithers: True
  lower_zoning:
    name: lower
    shapefile: examples/lower_zone/lower_zone.shp
    id_col: lower_id
    weight_data: examples/lower_zone/weight.csv
    data_col: weight
    weight_id_col: lower_id
    weight_data_year: 100

