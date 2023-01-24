##### IMPORTS #####
import logging
import pandas as pd
import warnings
import geopandas as gpd
from functools import reduce

from caf.space import inputs as si

##### CONSTANTS #####
logging.captureWarnings(True)
LOG = logging.getLogger(__name__)


##### FUNCTIONS #####
def _weighted_lower(
    params: si.ZoningTranslationInputs,
) -> gpd.GeoDataFrame:
    """
    Joins weighting data to lower zoning shapefile ready to apply.
    Args:
        params (si.ZoningTranslationInputs): see ZoningTranslationInputs
    Returns:
        gdf: A lower zoning system with weighting joined to it.
    """
    lower_zoning = gpd.read_file(params.lower_zoning.shapefile)
    lower_zoning.set_index(params.lower_zoning.id_col, inplace=True)
    weighting = pd.read_csv(
        params.lower_zoning.weight_data,
        index_col=params.lower_zoning.weight_id_col,
    )
    weighted = lower_zoning.join(weighting)
    missing = weighted[params.lower_zoning.data_col].isna().sum()
    warnings.warn(f"{missing} zones do not match up between the lower zoning and weighting data.")
    weighted["lower_area"] = weighted.area
    return weighted


def _create_tiles(params: si.ZoningTranslationInputs) -> pd.DataFrame:
    """
    Creates a spanning set of tiles for the weighted translation
    Args:
        params (si.ZoningTranslationInputs): see ZoningTranslationInputs

    Returns:
        pd.DataFrame: A set of weighted tiles used for weighted translation.
    """
    zone_1 = gpd.read_file(params.zone_1.shapefile)
    zone_2 = gpd.read_file(params.zone_2.shapefile)
    weighting = _weighted_lower(params)
    tiles = reduce(
        lambda x, y: gpd.overlay(x, y, keep_geom_type=True),
        [zone_1, zone_2, weighting],
    )
    tiles.overlay_area = tiles.area
    tiles.prop = tiles.overlay_area / tiles.lower_area
    tiles[params.lower_zoning.data_col] *= tiles.prop
    return tiles[
        [
            params.zone_1.id_col,
            params.zone_2.id_col,
            params.lower_zoning.data_col,
        ]
    ]


def return_totals(
    df: pd.DataFrame, id_col: str, data_col: str
) -> pd.DataFrame:
    """
    Groups df by dataframe and sums, keeping data_col
    Args:
        df (pd.DataFrame): dataframe
        id_col (str): Column to group by
        data_col (str): Column to keep of grouped df

    Returns:
        pd.DataFrame: Grouped and summed df
    """
    totals = df.groupby(id_col).sum().loc[:, data_col]
    return totals


def overlaps_and_totals(
    params: si.ZoningTranslationInputs,
) -> pd.DataFrame:
    """
    Creates overlap totals for each zone system, as well as totals for each zone on its own, then joins them all together.
    Args:
        params (si.ZoningTranslationInputs): see ZoneingTranslationInputs
    Returns:
        pd.DataFrame: Dataframe with columns for overlap total, zone 1 total, zone 2 total weights.
    """
    tiles = _create_tiles(params)
    totals_1 = return_totals(
        tiles, params.zone_1.id_col, params.lower_zoning.data_col
    ).to_frame()
    totals_2 = return_totals(
        tiles, params.zone_2.id_col, params.lower_zoning.data_col
    ).to_frame()
    overlap = (
        tiles.groupby([params.zone_1.id_col, params.zone_2.id_col])
        .sum()
        .loc[:, params.lower_zoning.data_col]
        .to_frame()
    )
    return overlap.join(totals_1, rsuffix="_1").join(
        totals_2, lsuffix="_overlap", rsuffix="_2"
    )


def final_weighted(params: si.ZoningTranslationInputs) -> pd.DataFrame:
    """
    Runs the above functions to produce a weighted translation using parameters provided.
    Args:
        params (si.ZoningTranslationInputs): _description_

    Returns:
        pd.DataFrame: _description_
    """
    full_df = overlaps_and_totals(params)
    full_df[f"{params.zone_1.name}_to_{params.zone_2.name}"] = (
        full_df[f"{params.lower_zoning.data_col}_overlap"]
        / full_df[f"{params.lower_zoning.data_col}_1"]
    )
    full_df[f"{params.zone_2.name}_to_{params.zone_1.name}"] = (
        full_df[f"{params.lower_zoning.data_col}_overlap"]
        / full_df[f"{params.lower_zoning.data_col}_2"]
    )
    return full_df
