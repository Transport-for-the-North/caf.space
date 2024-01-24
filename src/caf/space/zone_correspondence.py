"""
Contains functionality for creating spatial zone translation.

Also checks on various things for translations (rounding, slithers).
"""
import logging
from typing import Tuple, Union
import warnings
from dataclasses import dataclass

import geopandas as gpd
import pandas as pd
from caf.space import inputs

##### CONSTANTS #####
LOG = logging.getLogger("SPACE")
logging.captureWarnings(True)


##### FUNCTIONS #####
@dataclass
class ReadOutput:
    feature: gpd.GeoDataFrame
    geo_type: str


def read_zone_shapefiles(
    zone_1: Union[inputs.TransZoneSystemInfo, inputs.LineInfo],
    zone_2: inputs.TransZoneSystemInfo,
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
    out = {}
    for feature in [zone_1, zone_2]:
        zone = gpd.read_file(feature.shapefile)
        if zone.crs is None:
            warnings.warn(f"Zone {feature.name} has no CRS, setting crs to EPSG:27700.")
            zone.set_crs = "EPSG:27700"
        elif zone.crs != "EPSG:27700":
            warnings.warn(f"Zone {feature.name} has CRS {zone.crs}. Setting to EPSG:27700.")
            zone.geometry.to_crs("EPSG:27700", inplace=True)
        zone = zone.dropna(axis=1, how="all")
        LOG.info(
            "Count of %s features: %s",
            feature.name,
            zone.iloc[:, 0].count(),
        )
        # drop any features with invalid geometries
        zone["geo_check"] = zone.area
        zone = zone.dropna(subset=["geo_check"]).drop("geo_check", axis=1)
        if isinstance(feature, inputs.LineInfo):
            zone.rename(
                columns={feature.id_cols[0]: "A", feature.id_cols[1]: "B"}, inplace=True
            )
            zone[f"{feature.name}_length"] = zone.length
            out[feature.name] = ReadOutput(feature=zone, geo_type="line")
        else:
            zone.rename(columns={feature.id_col: f"{feature.name}_id"}, inplace=True)
            zone[f"{feature.name}_area"] = zone.area
            out[feature.name] = ReadOutput(feature=zone, geo_type="zone")
    return out


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
        zones[zone_1.name].feature,
        zones[zone_2.name].feature,
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
    # Works for line to zone too
    if "factor" in spatial_correspondence.columns:
        slither_filter = spatial_correspondence["factor"] < (1 - tolerance)
    else:
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
        totals = frame[factor_filter].groupby(from_col).sum()
        diffs = (1 - totals).rename(columns={factor_col: "diff"})
        # Convert totals to a Series
        totals = totals.squeeze()
        return totals, diffs

    to_col = f"{to_zone_name}_id"
    if "factor" in zone_corr.columns:
        zone_corr.reset_index(inplace=True)
        from_col = ["A", "B"]
        factor_col = "factor"
    else:
        from_col = f"{from_zone_name}_id"
        factor_col = f"{from_zone_name}_to_{to_zone_name}"
    if isinstance(from_col, list):
        filter = from_col + [to_zone_name]
        factor_filter = from_col + [factor_col]
    else:
        filter = [from_col, to_col]
        factor_filter = [from_col, factor_col]
    counts = zone_corr.groupby(from_col).size()
    zone_corr.set_index(from_col, inplace=True)
    # Set factor to 1 for one to one lookups
    zone_corr.loc[counts[counts == 1].index, factor_col] = 1

    # calculate missing adjustments for those that don't have a one to one mapping
    rest_to_round = zone_corr.loc[counts[counts > 1].index]
    factor_totals, differences = calculate_differences(zone_corr.reset_index())

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
    differences["correction"] = 1 + (differences["diff"] / factor_totals)

    # Multiply zone corresondence by the correction factor
    rest_to_round = rest_to_round.join(differences["correction"])

    rest_to_round[factor_col] = rest_to_round[factor_col] * rest_to_round["correction"]

    rest_to_round = rest_to_round.drop("correction", axis=1)
    rest_to_round.set_index(to_col, append=True, inplace=True)
    zone_corr.set_index(to_col, append=True, inplace=True)
    zone_corr.loc[rest_to_round.index] = rest_to_round

    # Recalculate differences after adjustment
    factor_totals, differences = calculate_differences(zone_corr.reset_index())

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
    if "factor" in zone_corr_no_slithers.columns:
        zone = [i for i in zone_names if "net" not in i][0]
        zone_corr_rounded = rounding_correction(
            zone_corr_no_slithers.copy(), from_zone_name="line", to_zone_name=zone
        )
    else:
        # create rounded zone correspondence
        zone_corr_rounded = rounding_correction(
            zone_corr_no_slithers[
                [
                    f"{zone_names[0]}_id",
                    f"{zone_names[1]}_id",
                    f"{zone_names[0]}_to_{zone_names[1]}",
                ]
            ].copy(),
            *zone_names
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
            zone_names[0]
        )

        zone_corr_rounded = zone_corr_rounded_both_ways.join(
            zone_corr_rounded
        )

    return zone_corr_rounded


def missing_links_check(links: pd.DataFrame, corr: pd.DataFrame, zone_id: str):
    checker = links.set_index(["A", "B"])
    missing = checker.index.difference(
        checker.loc[corr.reset_index(level=zone_id).index].index
    )
    return missing


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

    if zones[zone_1.name].geo_type == "line":
        missing_zone_1 = missing_links_check(
            zones[zone_1.name].feature, zone_correspondence, f"{zone_2.name}_id"
        )
        missing_zone_1_zones = (
            pd.DataFrame(data=0, index=missing_zone_1, columns=["dummy"])
            .reset_index()
            .drop(columns="dummy")
        )
    else:
        missing_zone_1 = zones[zone_1.name].feature.loc[
            ~zones[zone_1.name]
            .feature[f"{zone_1.name}_id"]
            .isin(zone_correspondence.index.get_level_values(f"{zone_1.name}_id")),
            f"{zone_1.name}_id",
        ]
        missing_zone_1_zones = pd.DataFrame(
            data=missing_zone_1,
            columns=[f"{zone_1.name}_id"],
        )
    if zones[zone_2.name].geo_type == "line":
        missing_zone_2 = missing_links_check(
            zones[zone_2.name].feature, zone_correspondence, f"{zone_1.name}_id"
        )
        missing_zone_2_zones = (
            pd.DataFrame(data=0, index=missing_zone_2, columns=["dummy"])
            .reset_index()
            .drop(columns="dummy")
        )
    else:
        missing_zone_2 = zones[zone_2.name].feature.loc[
            ~zones[zone_2.name]
            .feature[f"{zone_2.name}_id"]
            .isin(zone_correspondence.index.get_level_values(f"{zone_2.name}_id")),
            f"{zone_2.name}_id",
        ]
        missing_zone_2_zones = pd.DataFrame(
            data=missing_zone_2,
            columns=[f"{zone_2.name}_id"],
        )

    return missing_zone_1_zones, missing_zone_2_zones


def line_to_zone_trans(
    line: gpd.GeoDataFrame, zone: gpd.GeoDataFrame, line_ids: list[str], zone_id_col: str
):
    """
    Summary
    -------
    Function to translate lines to zones. The function takes a line shapefile
    and a zone shapefile and returns a dataframe with the line ids and the
    zone ids that they fall within.

    Parameters
    ----------
    line: gpd.GeoDataFrame
        Line shapefile
    zone: gpd.GeoDataFrame
        Zone shapefile
    line_ids: list[str]
        List of line ids
    zone_id_col: str
        Name of the zone id column

    Returns
    -------
    pd.DataFrame
        Dataframe with line ids and zone ids
    """
    # Create a geodataframe of the intersection of the line and zone shapefiles
    line_to_zone = line.overlay(zone, how="intersection", keep_geom_type=False)
    index_setter = line_ids + [zone_id_col]
    line_to_zone.set_index(index_setter, inplace=True)
    factors = (line_to_zone.length / line.set_index(line_ids).length).to_frame()
    factors.columns = ["factor"]
    # Create a dataframe with the line ids and the zone ids that they fall within
    return factors
