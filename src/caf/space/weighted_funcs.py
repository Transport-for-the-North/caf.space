"""
Contains functionality for creating weighted translations.

These are called in the 'weighted_trans' method in ZoneTranslation.
"""
##### IMPORTS #####
from typing import Optional
import logging
import warnings
from functools import reduce
import pandas as pd


# pylint: disable=import-error
import geopandas as gpd

# pylint: enable=import-error

from caf.space import inputs

##### CONSTANTS #####
logging.captureWarnings(True)
LOG = logging.getLogger("SPACE")


##### FUNCTIONS #####
def _weighted_lower(
    lower_zoning: inputs.LowerZoneSystemInfo,
) -> gpd.GeoDataFrame:
    """
    Join weighting data to lower zoning shapefile ready to apply.

    Parameters
    ----------
    lower_zoning: Info on lower zoning and weight data

    Returns
    -------
    A lower zoning system with weighting joined to it.
    """
    lower_zone = gpd.read_file(lower_zoning.shapefile)
    lower_zone.set_index(lower_zoning.id_col, inplace=True)
    weighting = pd.read_csv(
        lower_zoning.weight_data,
        index_col=lower_zoning.weight_id_col,
    )
    weighted = lower_zone.join(weighting)
    missing = weighted[lower_zoning.data_col].isna().sum()
    if missing > 0:
        warnings.warn(
            f"{missing} zones do not match up between the lower zoning and weighting data.",
            stacklevel=2,
        )
    weighted["lower_area"] = weighted.area
    return weighted


def _point_handling(
    zone: gpd.GeoDataFrame,
    zone_id: str,
    lower: gpd.GeoDataFrame,
    lower_id: str,
    tolerance: float,
) -> gpd.GeoDataFrame:
    """
    Assign points to zones for weighting.

    Find point zones and assign them to the lower zone they lie within to
    recieve appropriate weighting.

    Parameters
    ----------
    zone: The zone gdf for point zones to be altered within.
    zone_id: The name of the id column in the zone gdf.
    lower: The lower gdf to be used for point zone adjustment.
    lower_id: The name of the id column in the lower gdf.
    tolerance: The area below which zones will be classified as point zones
    and handled accordingly.

    Returns
    -------
    The input zone gdf, but with any point zones replaced with the lower zone
    they lie within spatially. The id of these zones remains identical with only
    the geometry changed. Where there are no zones smaller than threshold the
    function simply returns zone unchanged.
    """
    zone.loc[zone.geometry.geometry.type == "Point", "geometry"] = zone.loc[
        zone.geometry.geometry.type == "Point", "geometry"
    ].buffer(0.1)
    points = zone[zone.area < tolerance]
    points = points.set_crs("EPSG:27700")
    if len(points) > 0:
        lower.reset_index(inplace=True)
        joined = gpd.sjoin(points, lower, how="left", predicate="within")
        new = pd.merge(lower.reset_index(), joined, how="inner", on=lower_id)
        new = gpd.GeoDataFrame(data=new[zone_id], geometry=new["geometry_x"])
        overlay = zone.overlay(new, how="symmetric_difference", keep_geom_type=False)
        overlay.rename(columns={f"{zone_id}_1": zone_id}, inplace=True)
        out = overlay[~overlay[zone_id].isna()]
        zone = pd.concat([out.loc[:, [zone_id, "geometry"]], new])
    return zone


def _create_tiles(
    zones: dict,
    zone_1: inputs.TransZoneSystemInfo,
    zone_2: inputs.TransZoneSystemInfo,
    lower_zoning: inputs.LowerZoneSystemInfo,
    point_handling: bool,
    point_tolerance: float,
    zone_1_points: Optional[gpd.GeoDataFrame] = None,
    zone_2_points: Optional[gpd.GeoDataFrame] = None,
) -> pd.DataFrame:
    """
    Create a spanning set of tiles for the weighted translation.

    Parameters
    ----------
    zone_1: Info on first zone system
    zone_2: Info on second zone system
    lower_zoning: Info on lower zoning and weight data

    Returns
    -------
    A set of weighted tiles used for weighted translation.
    """
    zone_1_gdf = zones[zone_1.name]["Zone"][[f"{zone_1.name}_id", "geometry"]]
    zone_2_gdf = zones[zone_2.name]["Zone"][[f"{zone_2.name}_id", "geometry"]]
    weighting = _weighted_lower(lower_zoning)
    if point_handling:
        if zone_1_points is not None:
            zone_1_points = zone_1_points.loc[:, [zone_1.id_col, "geometry"]]
            zone_1_points.rename(columns={zone_1.id_col: f"{zone_1.name}_id"}, inplace=True)
            zone_1_gdf = pd.concat([zone_1_gdf, zone_1_points])
        zone_1_gdf = _point_handling(
            zone_1_gdf, f"{zone_1.name}_id", weighting, lower_zoning.id_col, point_tolerance
        )
        if zone_2_points is not None:
            zone_2_points = zone_2_points.loc[:, [zone_2.id_col, "geometry"]]
            zone_2_points.rename(columns={zone_2.id_col: f"{zone_2.name}_id"}, inplace=True)
            zone_2_gdf = pd.concat([zone_2_gdf, zone_2_points])
        zone_2_gdf = _point_handling(
            zone_2_gdf, f"{zone_2.name}_id", weighting, lower_zoning.id_col, point_tolerance
        )
    tiles = reduce(
        lambda x, y: gpd.overlay(x, y, keep_geom_type=True),
        [zone_1_gdf, zone_2_gdf, weighting],
    )
    tiles["overlay_area"] = tiles.area
    tiles["prop"] = tiles.overlay_area / tiles.lower_area
    tiles[lower_zoning.data_col] *= tiles.prop
    return tiles[
        [
            f"{zone_1.name}_id",
            f"{zone_2.name}_id",
            lower_zoning.data_col,
        ]
    ]


def return_totals(frame: pd.DataFrame, id_col: str, data_col: str) -> pd.DataFrame:
    """
    Group df by id_col and sums, keeping data_col.

    Parameters
    ----------
    frame: A dataframe.
    id_col: Column to group by.
    data_col: Column to keep

    Returns
    -------
    Grouped and summed df
    """
    totals = frame.groupby(id_col).sum().loc[:, data_col]
    return totals


def get_weighted_translation(
    zones: dict,
    zone_1: inputs.TransZoneSystemInfo,
    zone_2: inputs.TransZoneSystemInfo,
    lower_zoning: inputs.LowerZoneSystemInfo,
    point_handling: bool,
    point_tolerance: float,
    zone_1_points: Optional[gpd.GeoDataFrame] = None,
    zone_2_points: Optional[gpd.GeoDataFrame] = None,
) -> pd.DataFrame:
    """
    Create overlap totals for zone systems.

    Creates totals and joins back up.

    Parameters
    ----------
    zone_1: Info on first zone system
    zone_2: Info on second zone system
    lower_zoning: Info on lower zoning and weight data
    point_handling: Should point handling run.
    point_tolerance: see inputs.

    Returns
    -------
    Dataframe with columns for overlap total, zone 1 total, zone 2 total
    weights.
    """
    # create a set of spanning weighted, tiles. These tiles will be
    # grouped in different ways to produce the translation.
    tiles = _create_tiles(
        zones,
        zone_1,
        zone_2,
        lower_zoning,
        point_handling,
        point_tolerance,
        zone_1_points,
        zone_2_points,
    )
    # produce total weights by each respective zone system.
    totals_1 = return_totals(tiles, f"{zone_1.name}_id", lower_zoning.data_col).to_frame()
    totals_2 = return_totals(tiles, f"{zone_2.name}_id", lower_zoning.data_col).to_frame()
    # get values of overlaps between zone systems by grouping by both
    # zone systems and summing.
    overlap = (
        tiles.groupby([f"{zone_1.name}_id", f"{zone_2.name}_id"])
        .sum()
        .loc[:, lower_zoning.data_col]
        .to_frame()
    )
    return overlap.join(totals_1, rsuffix="_1").join(
        totals_2, lsuffix="_overlap", rsuffix="_2"
    )


def final_weighted(
    zones: dict,
    zone_1: inputs.TransZoneSystemInfo,
    zone_2: inputs.TransZoneSystemInfo,
    lower_zoning: inputs.LowerZoneSystemInfo,
    point_handling: bool,
    point_tolerance: float,
    zone_1_points: Optional[gpd.GeoDataFrame] = None,
    zone_2_points: Optional[gpd.GeoDataFrame] = None,
) -> pd.DataFrame:
    """
    Run functions from module to produce a weighted translation.

    Parameters
    ----------
    zone_1: Info on first zone system
    zone_2: Info on second zone system
    lower_zoning: Info on lower zoning and weight data

    Returns
    -------
    A weighted zone translation DataFrame. This contains more column than the
    final output and will be passed through more checks for slither and
    rounding before being output, according to the input parameters.
    """
    full_df = get_weighted_translation(
        zones,
        zone_1,
        zone_2,
        lower_zoning,
        point_handling,
        point_tolerance,
        zone_1_points,
        zone_2_points,
    )
    full_df[f"{zone_1.name}_to_{zone_2.name}"] = (
        full_df[f"{lower_zoning.data_col}_overlap"] / full_df[f"{lower_zoning.data_col}_1"]
    )
    full_df[f"{zone_2.name}_to_{zone_1.name}"] = (
        full_df[f"{lower_zoning.data_col}_overlap"] / full_df[f"{lower_zoning.data_col}_2"]
    )
    full_df.index.names = [f"{zone_1.name}_id", f"{zone_2.name}_id"]
    return full_df
