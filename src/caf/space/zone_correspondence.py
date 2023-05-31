"""
Contains functionality for creating spatial zone translation.

Also checks on various things for translations (rounding, slithers).
"""
import logging
from typing import Tuple
import warnings

import geopandas as gpd
import pandas as pd
from caf.space import inputs

##### CONSTANTS #####
LOG = logging.getLogger("SPACE")
logging.captureWarnings(True)

##### FUNCTIONS #####


def read_zone_shapefiles(
    zone_1: inputs.TransZoneSystemInfo, zone_2: inputs.TransZoneSystemInfo
) -> dict:
    """
    Read in zone system shapefiles.

    Reads in shapefiles and sets zone id and area column names, as well as
    matching to same crs. If the provided shapefiles don't contain CRS
    information then they're assumed to be "EPSG:27700".

    Parameters
    ----------
    zone_1: inputs.TransZoneSystemInfo
        Info on first zone system
    zone_2: inputs.TransZoneSystemInfo
        Info on second zone system

    Returns
    -------
    zones(dict): A nested dictionary containing zones
    for translation. zone_1.name and zone_1.name contain 'Zone'
    (GeoDataFrame) and 'ID_col'(str)
    """
    # create geodataframes from zone shapefiles
    z_1 = gpd.read_file(zone_1.shapefile)
    z_2 = gpd.read_file(zone_2.shapefile)

    z_1 = z_1.dropna(axis=1, how="all")
    z_2 = z_2.dropna(axis=1, how="all")

    LOG.info(
        "Count of %s zones: %s",
        zone_2.name,
        z_2.iloc[:, 0].count(),
    )
    LOG.info(
        "Count of %s zones: %s",
        zone_1.name,
        z_1.iloc[:, 0].count(),
    )

    z_1["area"] = z_1.area
    z_1 = z_1.dropna(subset=["area"])
    z_2["area"] = z_2.area
    z_2 = z_2.dropna(subset=["area"])

    zones = {
        zone_1.name: {
            "Zone": z_1.drop("area", axis=1),
            "ID_col": zone_1.id_col,
        },
        zone_2.name: {
            "Zone": z_2.drop("area", axis=1),
            "ID_col": zone_2.id_col,
        },
    }

    for name, zone in zones.items():
        zone["Zone"].rename(
            columns={zone["ID_col"]: f"{name}_id"},
            inplace=True,
        )
        zone["Zone"][f"{name}_area"] = zone["Zone"].area

        if not zone["Zone"].crs:
            warnings.warn(f"Zone {name} has no CRS, setting crs to EPSG:27700.")
            zone["Zone"].set_crs = "EPSG:27700"
        else:
            zone["Zone"].to_crs("EPSG:27700")

    return zones


def spatial_zone_correspondence(
    zones: dict,
    zone_1: inputs.TransZoneSystemInfo,
    zone_2: inputs.TransZoneSystemInfo,
):
    """
    Find the spatial zone correspondence.

    Finds zone correspondence through calculating adjustment factors with areas
    only.

    Parameters
    ----------
    zones: Return value from 'read_zone_shapefiles'.
    zone_1: inputs.TransZoneSystemInfo
        Info on first zone system
    zone_2: inputs.TransZoneSystemInfo
        Info on second zone system

    Returns
    -------
    GeoDataFrame
    GeoDataFrame with 4 columns: zone 1 IDs, zone 2 IDs, zone 1 to zone
    2 adjustment factor and zone 2 to zone 1 adjustment factor.
    """
    # create geodataframe for intersection of zones
    zone_overlay = gpd.overlay(
        zones[zone_1.name]["Zone"],
        zones[zone_2.name]["Zone"],
        how="intersection",
        keep_geom_type=False,
    ).reset_index()
    zone_overlay.loc[:, "intersection_area"] = zone_overlay.area

    # columns to include in spatial correspondence
    column_list = [
        f"{zone_1.name}_id",
        f"{zone_2.name}_id",
    ]

    # create geodataframe with spatial adjusted factors
    spatial_correspondence = zone_overlay.loc[:, column_list]

    # create geodataframe with spatial adjusted factors
    spatial_correspondence.loc[:, f"{zone_1.name}_to_{zone_2.name}"] = (
        zone_overlay.loc[:, "intersection_area"] / zone_overlay.loc[:, f"{zone_1.name}_area"]
    )
    spatial_correspondence.loc[:, f"{zone_2.name}_to_{zone_1.name}"] = (
        zone_overlay.loc[:, "intersection_area"] / zone_overlay.loc[:, f"{zone_2.name}_area"]
    )

    LOG.info("Unfiltered Spatial Correspondence completed")

    return spatial_correspondence


def find_slithers(
    spatial_correspondence: gpd.GeoDataFrame,
    zone_names: tuple[str, str],
    tolerance: float,
):
    """
    Find overlap areas between zones which are very small slithers.

    Finds slithers and filters them out of the spatial zone correspondence
    GeoDataFrame, and returns the filtered zone correspondence as well as the
    GeoDataFrame wit only the slithers.

    Parameters
    ----------
    spatial_correspondence : GeoDataFrame
        Spatial zone correspondence between zone 1 and zone 2 produced with
        spatial_zone_correspondence
    zone_names: List[str, str]
        List of the zone names that the spatial correspondence was performed
        between
    tolerance : float
        User-defined tolerance for filtering out slithers, must be a float
        between 0 and 1, recommended value is 0.98

    Returns
    -------
    GeoDataFrame, GeoDataFrame
        slithers, GeoDataFrame with all the small zone overlaps, and
        no_slithers, the zone correspondence GeoDataFrame with these zones
        filtered out. slithers isn't usually required but is returned for
        testing.
    """
    LOG.info("Finding Slithers")

    slither_filter = (
        spatial_correspondence[f"{zone_names[0]}_to_{zone_names[1]}"] < (1 - tolerance)
    ) & (spatial_correspondence[f"{zone_names[1]}_to_{zone_names[0]}"] < (1 - tolerance))
    slithers = spatial_correspondence.loc[slither_filter]
    no_slithers = spatial_correspondence.loc[~slither_filter]

    return slithers, no_slithers


def rounding_correction(
    zone_corr: pd.DataFrame, from_zone_name: str, to_zone_name: str
) -> pd.DataFrame:
    """
    Fix error causing negative factors.

    For most translations this function will do almost nothing, but is run
    anyway.

    Parameters
    ----------
    zone_corr (pd.DataFrame): Zone translation dataframe.
    from_zone_name (str): Name of zone_1.
    to_zone_name (str): Name of zone_2.

    Returns
    -------
    pd.DataFrame: The input zone_corr dataframe adjusted to remove errors.
    """

    def calculate_differences(
        frame: pd.DataFrame,
    ) -> Tuple[pd.Series, pd.DataFrame]:
        totals = frame[[from_col, factor_col]].groupby(from_col).sum()
        diffs = (1 - totals).rename(columns={factor_col: "diff"})
        # Convert totals to a Series
        totals = totals.iloc[:, 0]
        return totals, diffs

    from_col = f"{from_zone_name}_id"
    factor_col = f"{from_zone_name}_to_{to_zone_name}"

    counts = zone_corr.groupby(from_col).size()

    # Set factor to 1 for one to one lookups
    zone_corr.loc[zone_corr[from_col].isin(counts[counts == 1].index), factor_col] = 1.0

    # calculate missing adjustments for those that don't have a one to one mapping
    rest_to_round = zone_corr.loc[zone_corr[from_col].isin(counts[counts > 1].index)]
    factor_totals, differences = calculate_differences(zone_corr)

    LOG.info(
        "Adjusting %s correspondence factors for %s which don't sum to exactly 1\n"
        "Difference statistics: max: %.3g, min: %.3g, mean: %.3g, median: %.3g",
        (factor_totals != 1).sum(),
        factor_col,
        differences["diff"].max(),
        differences["diff"].min(),
        differences["diff"].mean(),
        differences["diff"].median(),
    )

    # Calculate factor to adjust the zone correspondence by
    differences.loc[:, "correction"] = 1 + (differences["diff"] / factor_totals)

    # Multiply zone corresondence by the correction factor
    rest_to_round = rest_to_round.merge(
        differences["correction"],
        how="left",
        left_on=from_col,
        right_on=differences.index,
    ).set_index(rest_to_round.index)

    rest_to_round.loc[:, factor_col] = (
        rest_to_round.loc[:, factor_col] * rest_to_round.loc[:, "correction"]
    )

    rest_to_round = rest_to_round.drop(labels="correction", axis=1)

    zone_corr.loc[zone_corr[from_col].isin(rest_to_round[from_col]), :] = rest_to_round

    # Recalculate differences after adjustment
    factor_totals, differences = calculate_differences(zone_corr)

    LOG.info(
        "After adjustment of %s, %s correspondence factors don't sum to exactly 1\n"
        "Difference statistics: max: %.3g, min: %.3g, mean: %.3g, median: %.3g",
        (factor_totals != 1).sum(),
        factor_col,
        differences["diff"].max(),
        differences["diff"].min(),
        differences["diff"].mean(),
        differences["diff"].median(),
    )

    # Check for negative zone correspondences
    negatives = (zone_corr[factor_col] < 0).sum()
    if negatives > 0:
        raise ValueError(f"{negatives} negative correspondence factors for {factor_col}")
    too_big = (zone_corr[factor_col].round(3) > 1).sum()
    if too_big > 0:
        warnings.warn(
            f"{too_big} correspondence factors > 1 for {factor_col}. "
            f"The translation will complete but check the output."
        )

    return zone_corr


def round_zone_correspondence(
    zone_corr_no_slithers: pd.DataFrame, zone_names: Tuple[str, str]
):
    """
    Round translation factors.

    Changes zone_1_to_zone_2 adjustment factors such that they sum to 1 for
    every zone in zone 1.

    Parameters
    ----------
    zone_corr_no_slithers : pd.DataFrame
        3 column (zone 1 id, zone 2 id, zone 1 to zone 2) zone correspondence
        DataFrame, with slithers filtered out
    zone_names : List[str, str]
        List of zone 1 and zone 2 names

    Returns
    -------
    pd.DataFrame
        3 column zone correspondence DataFrame with zone_1_to_zone_2 values
        which sum to 1 for each zone 1 id.
    """
    LOG.info(
        "Rounding Zone Correspondences, spatial gaps in the overlap of zone "
        "2 onto zone 1 will be equally distributed between each of zone 2 zones"
    )

    # create rounded zone correspondence
    zone_corr_rounded = rounding_correction(
        zone_corr_no_slithers[
            [
                f"{zone_names[0]}_id",
                f"{zone_names[1]}_id",
                f"{zone_names[0]}_to_{zone_names[1]}",
            ]
        ].copy(),
        *zone_names,
    )

    # Save rounding to final variable to turn to csv
    zone_corr_rounded_both_ways = zone_corr_rounded

    # create rounded zone correspondence for the other direction
    zone_corr_rounded = rounding_correction(
        zone_corr_no_slithers[
            [
                f"{zone_names[0]}_id",
                f"{zone_names[1]}_id",
                f"{zone_names[1]}_to_{zone_names[0]}",
            ]
        ].copy(),
        zone_names[1],
        zone_names[0],
    )

    zone_corr_rounded_both_ways = zone_corr_rounded_both_ways.merge(
        zone_corr_rounded[f"{zone_names[1]}_to_{zone_names[0]}"],
        how="left",
        left_on=zone_corr_rounded_both_ways.index,
        right_on=zone_corr_rounded.index,
    )

    zone_corr_rounded_both_ways = zone_corr_rounded_both_ways.drop(labels="key_0", axis=1)

    return zone_corr_rounded_both_ways


def missing_zones_check(
    zones: dict,
    zone_correspondence: pd.DataFrame,
    zone_1: inputs.TransZoneSystemInfo,
    zone_2: inputs.TransZoneSystemInfo,
):
    """
    Find missing zones.

    Checks for zone 1 and zone 2 zones missing from zone correspondence.

    Parameters
    ----------
    zones : List[gpd.GeoDataFrame, gpd.GeoDataFrame]
        Zone 1 and zone 2 GeoDataFrames.
    zone_correspondence : pd.DataFrame
        Zone correspondence between zone systems 1 and 2.
    zone_1: inputs.TransZoneSystemInfo
        Info on first zone system
    zone_2: inputs.TransZoneSystemInfo
        Info on second zone system
    Returns
    -------
    pd.DataFrame
        Zone 1 missing zones.
    pd.DataFrame
        Zone 2 missing zones.
    """
    LOG.info("Checking for missing zones")

    missing_zone_1 = zones[zone_1.name]["Zone"].loc[
        ~zones[zone_1.name]["Zone"][f"{zone_1.name}_id"].isin(
            zone_correspondence[f"{zone_1.name}_id"]
        ),
        f"{zone_1.name}_id",
    ]
    missing_zone_2 = zones[zone_2.name]["Zone"].loc[
        ~zones[zone_2.name]["Zone"][f"{zone_2.name}_id"].isin(
            zone_correspondence[f"{zone_2.name}_id"]
        ),
        f"{zone_2.name}_id",
    ]
    missing_zone_1_zones = pd.DataFrame(
        data=missing_zone_1,
        columns=[f"{zone_1.name}_id"],
    )
    missing_zone_2_zones = pd.DataFrame(
        data=missing_zone_2,
        columns=[f"{zone_2.name}_id"],
    )

    return missing_zone_1_zones, missing_zone_2_zones
