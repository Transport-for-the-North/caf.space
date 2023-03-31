# -*- coding: utf-8 -*-
"""

"""
# Built-Ins
from pathlib import Path

# Third Party
import pandas as pd
import geopandas as gpd
import numpy as np
from scipy.spatial import cKDTree
from shapely import Polygon, MultiPolygon
from shapely.geometry import Point

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
    gdA: gpd.GeoDataFrame,
    gdB: gpd.GeoDataFrame,
    max_dist: int,
    id_col_1,
    id_col_2,
    name_1,
    name_2,
):
    """
    Find corresponding point features between two geodataframe.

    Finds the nearest point feature from gdA to each feature in gdB, then
    filters for distance < max_dist.
    Parameters
    ----------
    gdA: Point geodataframe
    gdB: Point geodataframe
    max_dist: The max distance two points can be considered as matching, in metres.

    Returns
    -------
    gdB with a column for corresponding points in gdA, and the distance between them.
    """
    gdA = gdA.rename(columns={id_col_1: f"{name_1}_id"})
    gdB = gdB.rename(columns={id_col_2: f"{name_2}_id"})
    nA = np.array(list(gdA.geometry.apply(lambda x: (x.x, x.y))))
    nB = np.array(list(gdB.geometry.apply(lambda x: (x.x, x.y))))
    btree = cKDTree(nB)
    dist, idx = btree.query(nA, k=1)
    gdB_nearest = gdB.iloc[idx].drop(columns="geometry").reset_index(drop=True)
    gdf = pd.concat(
        [gdA.reset_index(drop=True), gdB_nearest, pd.Series(dist, name="dist")], axis=1
    )
    return gdf.loc[gdf["dist"] < max_dist, [f"{name_1}_id", f"{name_2}_id", "dist"]]


def points_update(
    points: gpd.GeoDataFrame, matches: pd.DataFrame, id_col: str, matches_id: str
):
    """
    Removes matching points from point shapefile.

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
    points.drop([i for i in matches[matches_id]], axis=0, inplace=True)
    return points.reset_index()


if __name__ == "__main__":
    points_1 = gpd.read_file(
        r"Y:\Freight\1.Local_Freight_Tool\Version2_WSP\zone_correspondence\1.GBFM_to_NoHAM\Inputs\point_zones.shp"
    )
    points_2 = gpd.read_file(
        r"Y:\Freight\1.Local_Freight_Tool\Version2_WSP\Zoning\GBFM_Zones_Combined_2021\GBFM_points.shp"
    )
    gdf = find_point_matches(points_1, points_2, 1000, "UniqueID", "UniqueID", "noham", "gbfm")
    print("debugging")
