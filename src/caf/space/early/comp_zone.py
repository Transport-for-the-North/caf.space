# -*- coding: utf-8 -*-

# Built-Ins

# Third Party
import geopandas as gpd
import pandas as pd
import warnings
from functools import reduce
# Local Imports
# pylint: disable=import-error,wrong-import-position
# Local imports here
from caf.space.inputs import ZoneSystemInfo, TransZoneSystemInfo
from caf.space import ZoneTranslation, ZoningTranslationInputs
# pylint: enable=import-error,wrong-import-position

# # # CONSTANTS # # #

# # # CLASSES # # #

# # # FUNCTIONS # # #
def check_nesting(target_zoning: TransZoneSystemInfo, ref_zoning: list[TransZoneSystemInfo]):
    out = {}
    for zones in ref_zoning:
        config = ZoningTranslationInputs(zone_1=target_zoning,
                                         zone_2=zones)
        trans = ZoneTranslation(config).spatial_translation()
        factor_col = f"{target_zoning.name}_to_{zones.name}"
        non_nested = trans[trans[factor_col] < 1]
        if len(non_nested > 0):
            warnings.warn(f"Non-nested zones between {zones.name} and {target_zoning.name}."
                          f"{non_nested}")
        out[zones.name] = non_nested
    return out
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


def filter_intersecting_features(geodataframes):
    filtered_gdfs = []

    # Iterate over each GeoDataFrame
    for i, gdf in enumerate(geodataframes):
        # Start with the current GeoDataFrame
        filtered_gdf = gdf.copy()

        # Intersect with all other GeoDataFrames
        for j, other_gdf in enumerate(geodataframes):
            if i != j:  # Skip the current GeoDataFrame itself
                # Perform spatial join to retain only features that intersect with other_gdf
                filtered_gdf = gpd.sjoin(filtered_gdf, other_gdf, how="inner", op="intersects")

                # Drop unnecessary columns from the spatial join result to clean up
                filtered_gdf = filtered_gdf.drop(
                    columns=[col for col in filtered_gdf.columns if col.endswith('_right')],
                    errors='ignore')

        # Append the filtered GeoDataFrame to the list
        filtered_gdfs.append(filtered_gdf.drop_duplicates(subset='geometry'))

    return filtered_gdfs

def minimum_common_zoning(zone_systems: list[gpd.GeoDataFrame], size_threshold: int):
    filtered_gdfs = filter_intersecting_features(zone_systems)
    tiles: gpd.GeoDataFrame = reduce(lambda x, y: gpd.overlay(x, y), filtered_gdfs)
    out: gpd.GeoDataFrame = tiles[tiles.area > size_threshold]
    out['geometry'] = out['geometry'].snap(out['geometry'])



if __name__ == "__main__":
    from shapely.geometry import Polygon
    normits = gpd.read_file(r"E:\shapefiles\normits_v1.shp")
    normits = normits[normits.area > 1000]
    cornwall = normits[normits['ZONE NAME'] == 'Cornwall']
    new_corn = cornwall['geometry'].snap(cornwall.unary_union, tolerance=100)
    # Create three polygons with slightly offset vertices
    polygon_1 = Polygon([(0, 0), (2, 0), (2, 2), (0, 2), (0, 0)])  # Square
    polygon_2 = Polygon(
        [(0.1, 0.1), (2.1, 0.1), (2.1, 2.1), (0.1, 2.1), (0.1, 0.1)])  # Slightly offset
    polygon_3 = Polygon(
        [(0.2, 0.2), (2.2, 0.2), (2.2, 2.2), (0.2, 2.2), (0.2, 0.2)])  # Slightly more offset

    # Create three GeoDataFrames
    gdf_1 = gpd.GeoDataFrame({'geometry': [polygon_1]}, crs="EPSG:4326")
    gdf_2 = gpd.GeoDataFrame({'geometry': [polygon_2]}, crs="EPSG:4326")
    gdf_3 = gpd.GeoDataFrame({'geometry': [polygon_3]}, crs="EPSG:4326")

    gdf_1['geometry'] = gdf_1['geometry'].snap(gdf_2['geometry'], tolerance=1)
    print('debugging')
