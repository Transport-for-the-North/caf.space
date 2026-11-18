"""
Reverse Lines
=============

Create a copy of lines data with duplicate lines in the opposite direction.
"""

# %%
# Imports

# Third Party
import geopandas as gpd
import numpy as np
import pandas as pd
from shapely import geometry

# Local Imports
import caf.space as cspace

# %%
# Define data file to load, using :class:`GeoDataFile` to provide optional
# layer and columns to read.

input_file = cspace.GeoDataFile(
    path="lines.shp",
    columns=["id"],
    index_cols="id",
)

lines = input_file.read()
print(f"Loaded {len(lines):,} features from {input_file.path.name}")
lines

# %%
# Check the geometry data contains only :class:`LineString`` and :class:`MultiLineString`
# geometries.

geom_types: dict[str, int] = dict(zip(*np.unique_counts(lines.geom_type)))

print(
    *[f"{i:<15.15} : {j:,} ({j / len(lines):.1%})" for i, j in geom_types.items()],
    sep="\n",
)

if any(not i.endswith("LineString") for i in geom_types):
    raise TypeError(f"found not linestring geometries: {geom_types}")


# %%
# Define a function for reversing :class:`LineString`` and :class:`MultiLineString`
# geometries.


def line_reverse(
    geom: geometry.LineString | geometry.MultiLineString,
) -> geometry.MultiLineString | geometry.LineString:
    """Reverse direction of a LineString or MultiLineString.

    Works differently to :meth:`MultiLineString.reverse()` because it
    reverses the list of geometries in addition to reversing the coorinates
    in the individual lines.
    """
    if isinstance(geom, geometry.MultiLineString):
        return geometry.MultiLineString([i.reverse() for i in reversed(geom.geoms)])
    return geom.reverse()


# %%
# Copy the lines dataset and reverse linestrings.

reversed_lines = lines.copy()
reversed_lines.geometry = reversed_lines.geometry.apply(line_reverse)
reversed_lines

# %%
# Create new index column to keep track of reversed vs original and combine datasets.

lines = lines.set_index(pd.Index([False] * len(lines), name="reversed"), append=True)
reversed_lines = reversed_lines.set_index(
    pd.Index([True] * len(reversed_lines), name="reversed"), append=True
)
lines = gpd.GeoDataFrame(
    pd.concat([lines, reversed_lines], axis=0, verify_integrity=True), crs=lines.crs
)
lines

# %%
# Output combined dataset to new GeoSpatial file in the same location as the original.

out_path = input_file.path.with_name(
    input_file.path.stem + f"-reversed{input_file.path.suffix}"
)
lines.to_file(out_path, layer=input_file.layer)
print(f"Written: {out_path}")
