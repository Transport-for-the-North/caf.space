# -*- coding: utf-8 -*-
"""Module for some miscellaneous functions used elsewhere."""
# Built-Ins
from pathlib import Path

# Third Party
import pandas as pd
import geopandas as gpd
import numpy as np
from scipy.spatial import cKDTree

# Local Imports
# pylint: disable=import-error,wrong-import-position
# Local imports here
# pylint: enable=import-error,wrong-import-position

# # # CONSTANTS # # #

# # # CLASSES # # #


# # # FUNCTIONS # # #
def generate_points(point_folder: Path, points_name: str, zones_path: Path, join_col: str):
    """
    Generate a point shapefile from a polygon shapefile and list of point IDs.

    Reads in a polygon shapefile and a list of IDs from a csv. Removes all polygons
    with IDs matching the list, converts those features to points (centroids of
    the polygons), then fills in the spaces in the polygon gdf. Saves a point
    shapefile and a polygon shapefile with point features removes and filled in.

    Parameters
    ----------
    point_folder: Folder containing points csv
    points_name: Name of points file
    zones_path: Path to zones shapefile
    join_col: The name of the ID column in the csv and the shapefile.

    Returns
    -------
    Returns nothing, saves shapefiles to point_folder
    """
    points = pd.read_csv(point_folder / points_name)
    main_zones = gpd.read_file(zones_path)
    point_polys = main_zones.merge(points, on=join_col, how="right")
    for i in point_polys.index:
        update = main_zones.loc[
            point_polys.loc[i, "geometry"].buffer(1).overlaps(main_zones.geometry), join_col
        ].to_list()
        main_zones.loc[
            main_zones[join_col] == point_polys.loc[i, join_col], join_col
        ] = update[0]
    dissolved = main_zones.dissolve(by=join_col)
    point_polys.geometry = point_polys.centroid
    point_polys.to_file(point_folder / "point_zones.shp")
    dissolved.to_file(point_folder / "zones_no_points.shp")


def find_point_matches(
    gda: gpd.GeoDataFrame,
    gdb: gpd.GeoDataFrame,
    max_dist: int,
    id_col_1: str,
    id_col_2: str,
    name_1: str,
    name_2: str,
):
    """
    Find corresponding point features between two geodataframe.

    Finds the nearest point feature from gdA to each feature in gdB, then
    filters for distance < max_dist.

    Parameters
    ----------
    gda: Point geodataframe
    gdb: Point geodataframe
    max_dist: The max distance two points can be considered as matching, in metres.
    id_col_1: id_col pf gda
    id_col_2: id_col of gdb
    name_1: name of gda
    name_2: name of gdb
    Returns
    -------
    gdB with a column for corresponding points in gdA, and the distance between them.
    """
    gda = gda.rename(columns={id_col_1: f"{name_1}_id"})
    gdb = gdb.rename(columns={id_col_2: f"{name_2}_id"})
    aarray = np.array(list(gda.geometry.apply(lambda x: (x.x, x.y))))
    barray = np.array(list(gdb.geometry.apply(lambda x: (x.x, x.y))))
    btree = cKDTree(barray)
    dist, idx = btree.query(aarray, k=1)
    gdb_nearest = gdb.iloc[idx].drop(columns="geometry").reset_index(drop=True)
    gdf = pd.concat(
        [gda.reset_index(drop=True), gdb_nearest, pd.Series(dist, name="dist")], axis=1
    )
    return gdf.loc[gdf["dist"] < max_dist, [f"{name_1}_id", f"{name_2}_id", "dist"]]


def points_update(
    points: gpd.GeoDataFrame, matches: pd.DataFrame, id_col: str, matches_id: str
):
    """
    Remove matching points from point shapefile.

    Reads in a master points shapefile, and a matching points shapefile and removes
    features from the master file which appear in the matching one.

    Parameters
    ----------
    points: master shapefile
    matches: matches shapefile
    id_col: ID column of master points
    matches_id: id column od matching points

    Returns
    -------
    master gdf with matching points removed.
    """
    points.set_index(id_col, inplace=True)
    points.drop(list(matches[matches_id]), axis=0, inplace=True)
    return points.reset_index()
