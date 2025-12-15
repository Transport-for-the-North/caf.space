"""
Merge MultiLineStrings
======================

Example of using GeoPandas to merge :class:`MultiLineString` together into single
:class:`LineString` and then split any remaining :class:`MultiLineString` into
separate features.
"""

# %%
# Imports

import caf.toolkit as ctk
import geopandas as gpd
import numpy as np

import caf.space as cspace

# %%
# Load path to Shapefile from config.


class Config(ctk.BaseConfig):
    multilines_file: cspace.GeoDataFile
    output_file: cspace.GeoDataFile


config = Config.load_yaml("merge_multilines.yml")
print(config.to_yaml())


# %%
# Read Geospatial data

multilines = config.multilines_file.read()
multilines.head()

# %%
# Count geometry types


def print_types(data: gpd.GeoDataFrame) -> None:
    for value, count in zip(*np.unique(data.geom_type, return_counts=True)):
        print(f"{value} : {count}")


print_types(multilines)

# %%
# Merge lines using :func:`gpd.GeoSeries.line_merge` with `directed=True`

multilines.geometry = multilines.line_merge(directed=True)
print_types(multilines)

# %%
# Split any remaining :class:`MultiLineString` into separate features
# and define a new ID column to keep track.

lines = multilines.explode(index_parts=True)
print_types(lines)
lines

# %%
# Combine index into single ID column for use in :mod:`caf.space.line_to_line`

lines["ID"] = (
    lines.index.get_level_values(0) + "_" + lines.index.get_level_values(1).astype(str)
)
lines = lines.reset_index(0).set_index("ID", verify_integrity=True)
lines

# %%
# Convert to British National Grid CRS

lines = lines.to_crs(epsg=27700)

# %%
# Save lines to output file

lines.reset_index().to_file(config.output_file.path, layer=config.output_file.layer)
print(f"Written: {config.output_file.path}")
