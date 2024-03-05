# -*- coding: utf-8 -*-

# Built-Ins

# Third Party
import geopandas as gpd
import pandas as pd
# Local Imports
# pylint: disable=import-error,wrong-import-position
# Local imports here
from caf.space.inputs import ZoneSystemInfo
# pylint: enable=import-error,wrong-import-position

# # # CONSTANTS # # #

# # # CLASSES # # #

# # # FUNCTIONS # # #
def produce_zoning(ext_zones: ZoneSystemInfo,
                   int_zones: ZoneSystemInfo,
                   int_bound: ZoneSystemInfo):
    """
    Produce a composite zone system from two zone systems, where one zone system
    is used for zones within a boundary, and the other without.

    This process is written with msoa and lsoa in mind, and as such it is assumed the
    two zone systems nest within each other. The zones should also nest within
    the boundary, but failing that, the centroids of each zone system decides
    whether they are within or without the boundary.

    Parameters
    ----------
    ext_zones: ZoneSystemInfo
        The zone system to use outside the boundary. Generally this would be
        the more aggregate zone system. e.g. msoa.
    int_zones: ZoneSystemInfo
        The zone system to use inside the boundary. Generally this would be the
        less aggregate zone system, e.g. lsoa.
    int_bound: ZoneSystemInfo
        The boundary defining where to use each zone system. This should be a
        polygon layer, ideally a single polygon feature, but it can be many.
        Internal is the extent of this layer, and external is outside this layer.

    Returns
    -------
    gpd.GeoDataFrame: A geodataframe of the combined zone system. This will
        contain two columns, an id (named based on the names of the two zone
        systems), and geometry. The ID column is generated using IDs from the
        two constituent zone systems.
    """
    ext_gdf = gpd.read_file(ext_zones.shapefile)[ext_zones.id_col, 'geometry']
    int_gdf = gpd.read_file(int_zones.shapefile)[int_zones.id_col, 'geometry']
    bound = gpd.read_file(int_bound.shapefile)[int_bound.id_col, 'geometry']
    int_cent = int_gdf.copy()
    int_cent.geometry = int_cent.centroid
    ext_cent = ext_gdf.copy()
    ext_cent.geometry = ext_cent.centroid
    ext_cent = ext_cent.sjoin(bound, how='left', predicate='within')
    ext_gdf = ext_gdf[ext_cent[int_bound.id_col].isna()]
    int_cent = int_cent.sjoin(bound, how='inner', predicate='within')
    int_gdf = int_gdf.loc[int_cent.index]
    int_gdf.rename(columns={int_zones.id_col: f"{int_zones.name}_{ext_zones.name}_id"}, inplace=True)
    ext_gdf.rename(columns={ext_zones.id_col: f"{int_zones.name}_{ext_zones.name}_id"}, inplace=True)
    return gpd.GeoDataFrame(pd.concat([int_gdf, ext_gdf]), geometry='geometry')