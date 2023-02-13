"""
Contains functionality for creating weighted translations.

These are called in the 'weighted_trans' method in ZoneTranslation.
"""
##### IMPORTS #####
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
LOG = logging.getLogger(__name__)


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
    lower_zoning = gpd.read_file(lower_zoning.shapefile)
    lower_zoning.set_index(lower_zoning.id_col, inplace=True)
    weighting = pd.read_csv(
        lower_zoning.weight_data,
        index_col=lower_zoning.weight_id_col,
    )
    weighted = lower_zoning.join(weighting)
    missing = weighted[lower_zoning.data_col].isna().sum()
    warnings.warn(
        f"{missing} zones do not match up between the lower zoning and weighting data."
    )
    weighted["lower_area"] = weighted.area
    return weighted


def _create_tiles(
    zone_1: inputs.ZoneSystemInfo,
    zone_2: inputs.ZoneSystemInfo,
    lower_zoning: inputs.LowerZoneSystemInfo,
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
    zone_1 = gpd.read_file(zone_1.shapefile)
    zone_2 = gpd.read_file(zone_2.shapefile)

    LOG.info(
        "Count of %s zone: %s",
        zone_2.name,
        zone_2.iloc[:, 0].count(),
    )
    LOG.info(
        "Count of %s zones: %s",
        zone_1.name,
        zone_1.iloc[:, 0].count(),
    )

    weighting = _weighted_lower(lower_zoning)
    tiles = reduce(
        lambda x, y: gpd.overlay(x, y, keep_geom_type=True),
        [zone_1, zone_2, weighting],
    )
    tiles.overlay_area = tiles.area
    tiles.prop = tiles.overlay_area / tiles.lower_area
    tiles[lower_zoning.data_col] *= tiles.prop
    return tiles[
        [
            zone_1.id_col,
            zone_2.id_col,
            lower_zoning.data_col,
        ]
    ]


def return_totals(
    frame: pd.DataFrame, id_col: str, data_col: str
) -> pd.DataFrame:
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
    zone_1: inputs.ZoneSystemInfo,
    zone_2: inputs.ZoneSystemInfo,
    lower_zoning: inputs.LowerZoneSystemInfo,
) -> pd.DataFrame:
    """
    Create overlap totals for zone systems.

    Creates totals and joins back up.

    Parameters
    ----------
    zone_1: Info on first zone system
    zone_2: Info on second zone system
    lower_zoning: Info on lower zoning and weight data

    Returns
    -------
    Dataframe with columns for overlap total, zone 1 total, zone 2 total
    weights.
    """
    # create a set of spanning weighted, tiles. These tiles will be
    # grouped in different ways to produce the translation.
    tiles = _create_tiles(zone_1, zone_2, lower_zoning)
    # produce total weights by each respective zone system.
    totals_1 = return_totals(
        tiles, zone_1.id_col, lower_zoning.data_col
    ).to_frame()
    totals_2 = return_totals(
        tiles, zone_2.id_col, lower_zoning.data_col
    ).to_frame()
    # get values of overlaps between zone systems by grouping by both
    # zone systems and summing.
    overlap = (
        tiles.groupby([zone_1.id_col, zone_2.id_col])
        .sum()
        .loc[:, lower_zoning.data_col]
        .to_frame()
    )
    return overlap.join(totals_1, rsuffix="_1").join(
        totals_2, lsuffix="_overlap", rsuffix="_2"
    )


def final_weighted(
    zone_1: inputs.ZoneSystemInfo,
    zone_2: inputs.ZoneSystemInfo,
    lower_zoning: inputs.LowerZoneSystemInfo,
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
    full_df = get_weighted_translation(zone_1, zone_2, lower_zoning)
    full_df[f"{zone_1.name}_to_{zone_2.name}"] = (
        full_df[f"{lower_zoning.data_col}_overlap"]
        / full_df[f"{lower_zoning.data_col}_1"]
    )
    full_df[f"{zone_2.name}_to_{zone_1.name}"] = (
        full_df[f"{lower_zoning.data_col}_overlap"]
        / full_df[f"{lower_zoning.data_col}_2"]
    )
    full_df.index.names = [f"{zone_1.name}_id", f"{zone_2.name}_id"]
    return full_df
