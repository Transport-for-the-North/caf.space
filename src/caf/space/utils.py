# -*- coding: utf-8 -*-
"""

"""
# Built-Ins
from pathlib import Path
# Third Party
import pandas as pd
import geopandas as gpd
# Local Imports
# pylint: disable=import-error,wrong-import-position
# Local imports here
# pylint: enable=import-error,wrong-import-position

# # # CONSTANTS # # #

# # # CLASSES # # #

# # # FUNCTIONS # # #
def generate_points(point_folder: Path, points_name: str, zones_path: Path, join_col: str):
    points = pd.read_csv(point_folder / points_name)
    main_zones = gpd.read_file(zones_path)
    point_polys = main_zones.merge(points, on=join_col, how="right")
    out_zones = pd.concat([main_zones, point_polys]).drop_duplicates(keep=False)
    point_polys.geometry = point_polys.centroid
    point_polys.to_file(point_folder / "point_zones.shp")
    out_zones.to_file(point_folder / "zones_no_points.shp")
