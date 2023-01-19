import logging
from typing import Tuple

import geopandas as gpd
import pandas as pd
import sys
import warnings

sys.path.append('..')

from caf.space import inputs as si

##### CONSTANTS #####
LOG = logging.getLogger(__name__)
logging.captureWarnings(True)

##### FUNCTIONS #####
def _read_zone_shapefiles(params: si.ZoningTranslationInputs) -> dict:
    """Reads in zone system shapefiles, sets zone id and area column
    names, sets to same crs.

    If the provided shapefiles don't contain CRS information then
    they're assumed to be "EPSG:27700".
    Parameters
    ----------
    params (csi.ZoningTranslationInputs): Instance of
    ZoningTranslationInputs, see class for info.
    Returns
    ----------
    zones(dict): A nested dictionary containing major and minor zones
    for translation. 'Major' and 'Minor' contain 'Name'(str), 'Zone'
    (GeoDataFrame) and 'ID_col'(str)
    """

    # create geodataframes from zone shapefiles
    zone_1 = gpd.read_file(params.zone_1.shapefile)
    zone_2 = gpd.read_file(params.zone_2.shapefile)

    zone_1 = zone_1.dropna(axis=1, how="all")
    zone_2 = zone_2.dropna(axis=1, how="all")

    LOG.info(
        "Count of %s zones: %s",
        params.zone_2.name,
        zone_2.iloc[:, 0].count(),
    )
    LOG.info(
        "Count of %s zones: %s",
        params.zone_1.name,
        zone_1.iloc[:, 0].count(),
    )

    zone_1["area"] = zone_1.area
    zone_1 = zone_1.dropna(subset=["area"])
    zone_2["area"] = zone_2.area
    zone_2 = zone_2.dropna(subset=["area"])


    major_zone = zone_1.copy()
    major_zone_name = params.zone_1.name
    minor_zone = zone_2.copy()
    minor_zone_name = params.zone_2.name
    zones = {
        "Major": {
            "Name": major_zone_name,
            "Zone": major_zone.drop("area", axis=1),
            "ID_col": params.zone_1.id_col,
        },
        "Minor": {
            "Name": minor_zone_name,
            "Zone": minor_zone.drop("area", axis=1),
            "ID_col": params.zone_2.id_col,
        },
    }

    del zone_1, zone_2

    for zone in zones.values():
        zone["Zone"].rename(
            columns={zone["ID_col"]: f"{zone['Name']}_zone_id"},
            inplace=True,
        )
        zone["Zone"][f"{zone['Name']}_area"] = zone["Zone"].area

        if not zone["Zone"].crs:
            warnings.warn(f"Zone {zone['Name']} has no CRS, setting crs to EPSG:27700.")
            zone["Zone"].crs = "EPSG:27700"

    return zones


def _spatial_zone_correspondence(zones: dict):
    """Finds the spatial zone corrrespondence through calculating
    adjustment factors with areas only.
    Parameters
    ----------
    zones: Return value from 'read_zone_shapefiles'.
    Returns
    -------
    GeoDataFrame
    GeoDataFrame with 4 columns: zone 1 IDs, zone 2 IDs, zone 1 to zone
    2 adjustment factor and zone 2 to zone 1 adjustment factor.
    """

    # create geodataframe for intersection of zones
    zone_overlay = gpd.overlay(
        zones["Major"]["Zone"],
        zones["Minor"]["Zone"],
        how="intersection",
        keep_geom_type=False,
    ).reset_index()
    zone_overlay.loc[:, "intersection_area"] = zone_overlay.area

    # columns to include in spatial correspondence
    column_list = [
        f"{zones['Major']['Name']}_zone_id",
        f"{zones['Minor']['Name']}_zone_id",
    ]

    # create geodataframe with spatial adjusted factors
    spatial_correspondence = zone_overlay.loc[:, column_list]

    # create geodataframe with spatial adjusted factors
    spatial_correspondence.loc[
        :, f"{zones['Major']['Name']}_to_{zones['Minor']['Name']}"
    ] = (
        zone_overlay.loc[:, "intersection_area"]
        / zone_overlay.loc[:, f"{zones['Major']['Name']}_area"]
    )
    spatial_correspondence.loc[
        :, f"{zones['Minor']['Name']}_to_{zones['Major']['Name']}"
    ] = (
        zone_overlay.loc[:, "intersection_area"]
        / zone_overlay.loc[:, f"{zones['Minor']['Name']}_area"]
    )

    LOG.info("Unfiltered Spatial Correspondence completed")

    return spatial_correspondence


def _find_slithers(
    spatial_correspondence: gpd.GeoDataFrame,
    zone_names: list[str],
    tolerance: float,
):
    """Finds overlap areas between zones which are very small slithers,
    filters them out of the spatial zone correspondence GeoDataFrame, and
    returns the filtered zone correspondence as well as the GeoDataFrame with
    only the slithers.

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
        slithers GeoDataFrame with all the small zone overlaps, and
        no_slithers the zone correspondence GeoDataFrame with these zones
        filtered out
    """
    LOG.info("Finding Slithers")

    slither_filter = (
        spatial_correspondence[f"{zone_names[0]}_to_{zone_names[1]}"]
        < (1 - tolerance)
    ) & (
        spatial_correspondence[f"{zone_names[1]}_to_{zone_names[0]}"]
        < (1 - tolerance)
    )
    slithers = spatial_correspondence.loc[slither_filter]
    no_slithers = spatial_correspondence.loc[~slither_filter]

    return slithers, no_slithers


def _rounding_correction(
    zone_corr: pd.DataFrame, from_zone_name: str, to_zone_name: str
) -> pd.DataFrame:
    """
    Fixes error causing negative factors. For most translations this
    function will do almost nothing, but is run anyway.
    Parameters
    ----------
    zone_corr (pd.DataFrame): Zone translation dataframe.
    from_zone_name (str): Name of zone_1.
    to_zone_name (str): Name of zone_2.
    Returns
    ----------
    pd.DataFrame: The input zone_corr dataframe adjusted to remove errors.
    """

    def calculate_differences(
        df: pd.DataFrame,
    ) -> Tuple[pd.Series, pd.DataFrame]:
        factor_totals = (
            df[[from_col, factor_col]].groupby(from_col).sum()
        )
        differences = (1 - factor_totals).rename(
            columns={factor_col: "diff"}
        )
        # Convert totals to a Series
        factor_totals = factor_totals.iloc[:, 0]
        return factor_totals, differences

    from_col = f"{from_zone_name}_zone_id"
    factor_col = f"{from_zone_name}_to_{to_zone_name}"

    counts = zone_corr.groupby(from_col).size()

    # Set factor to 1 for one to one lookups
    zone_corr.loc[
        zone_corr[from_col].isin(counts[counts == 1].index), factor_col
    ] = 1.0

    # calculate missing adjustments for those that don't have a one to one mapping
    rest_to_round = zone_corr.loc[
        zone_corr[from_col].isin(counts[counts > 1].index)
    ]
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
    differences.loc[:, "correction"] = 1 + (
        differences["diff"] / factor_totals
    )

    # Multiply zone corresondence by the correction factor
    rest_to_round = rest_to_round.merge(
        differences["correction"],
        how="left",
        left_on=from_col,
        right_on=differences.index,
    ).set_index(rest_to_round.index)

    rest_to_round.loc[:, factor_col] = (
        rest_to_round.loc[:, factor_col]
        * rest_to_round.loc[:, "correction"]
    )

    rest_to_round = rest_to_round.drop(labels="correction", axis=1)

    zone_corr.loc[
        zone_corr[from_col].isin(rest_to_round[from_col]), :
    ] = rest_to_round

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
        raise ValueError(
            f"{negatives} negative correspondence factors for {factor_col}"
        )
    too_big = (zone_corr[factor_col] > 1).sum()
    if too_big > 0:
        raise ValueError(
            f"{too_big} correspondence factors > 1 for {factor_col}"
        )

    return zone_corr


def _round_zone_correspondence(
    zone_corr_no_slithers: pd.DataFrame, zone_names: Tuple[str, str]
):
    """Changes zone_1_to_zone_2 adjustment factors such that they sum to 1 for
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
    zone_corr_rounded = _rounding_correction(
        zone_corr_no_slithers[
            [
                f"{zone_names[0]}_zone_id",
                f"{zone_names[1]}_zone_id",
                f"{zone_names[0]}_to_{zone_names[1]}",
            ]
        ].copy(),
        *zone_names,
    )

    # Save rounding to final variable to turn to csv
    zone_corr_rounded_both_ways = zone_corr_rounded

    # create rounded zone correspondence for the other direction
    zone_corr_rounded = _rounding_correction(
        zone_corr_no_slithers[
            [
                f"{zone_names[0]}_zone_id",
                f"{zone_names[1]}_zone_id",
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

    zone_corr_rounded_both_ways = zone_corr_rounded_both_ways.drop(
        labels="key_0", axis=1
    )

    return zone_corr_rounded_both_ways


def _missing_zones_check(zones: dict, zone_correspondence: pd.DataFrame):
    """Checks for zone 1 and zone 2 zones missing from zone correspondence.

    Parameters
    ----------
    zone_list : List[gpd.GeoDataFrame, gpd.GeoDataFrame]
        Zone 1 and zone 2 GeoDataFrames.
    zone_names : List[str, str]
        Zone 1 and zone 2 names.
    zone_correspondence : pd.DataFrame
        Zone correspondence between zone systems 1 and 2.

    Returns
    -------
    pd.DataFrame
        Zone 1 missing zones.
    pd.DataFrame
        Zone 2 missing zones.
    """
    LOG.info("Checking for missing zones")

    missing_zone_1 = zones["Major"]["Zone"].loc[
        ~zones["Major"]["Zone"][
            f"{zones['Major']['Name']}_zone_id"
        ].isin(
            zone_correspondence[f"{zones['Major']['Name']}_zone_id"]
        ),
        f"{zones['Major']['Name']}_zone_id",
    ]
    missing_zone_2 = zones["Minor"]["Zone"].loc[
        ~zones["Minor"]["Zone"][
            f"{zones['Minor']['Name']}_zone_id"
        ].isin(
            zone_correspondence[f"{zones['Minor']['Name']}_zone_id"]
        ),
        f"{zones['Minor']['Name']}_zone_id",
    ]
    missing_zone_1_zones = pd.DataFrame(
        data=missing_zone_1,
        columns=[f"{zones['Major']['Name']}_zone_id"],
    )
    missing_zone_2_zones = pd.DataFrame(
        data=missing_zone_2,
        columns=[f"{zones['Minor']['Name']}_zone_id"],
    )

    return missing_zone_1_zones, missing_zone_2_zones


def _main_zone_correspondence(params: si.ZoningTranslationInputs):
    """Performs zone correspondence between two zoning systems, zone 1 and
    zone 2. Default correspondence is spatial (by zone area), but includes
    options for handling point zones with different data (for example LSOA
    employment data). Also includes option to check adjustment factors from
    zone 1 to zone 2 add to 1.
    Args:
        params (csi.ZoningTranslationInputs): Instance of zone paramaters.
    """
    # read in zone shapefiles
    zones = _read_zone_shapefiles(params)
    # produce spatial zone correspondence
    spatial_correspondence = _spatial_zone_correspondence(zones)
    # Determine if slither filtering and rounding required.
    zone_names = [zones["Major"]["Name"], zones["Minor"]["Name"]]
    if params.filter_slithers:
        LOG.info("Filtering out small overlaps.")
        (_, spatial_correspondence_no_slithers,) = _find_slithers(
            spatial_correspondence, zone_names, params.tolerance
        )

        if params.rounding:
            LOG.info("Checking all adjustment factors add to 1")
            final_zone_corr = _round_zone_correspondence(
                spatial_correspondence_no_slithers, zone_names
            )
        else:
            final_zone_corr = spatial_correspondence_no_slithers
    else:
        if params.rounding:
            LOG.info("Checking all adjustment factors add to 1")
            final_zone_corr = _round_zone_correspondence(
                spatial_correspondence, zone_names
            )
        else:
            final_zone_corr = spatial_correspondence
    # Save correspondence output
    final_zone_corr_path = (
        params.output_path
        / f"{zone_names[0]}_to_{zone_names[1]}_correspondence.csv"
    )
    missing_zones_1, missing_zones_2 = _missing_zones_check(
        zones, final_zone_corr
    )

    warnings.warn("Missing Zones from 1 : %s", len(missing_zones_1))
    warnings.warn("Missing Zones from 2 : %s", len(missing_zones_2))

    log_file = (params.cache_path / f"{zone_names[0]}_{zone_names[1]}" /
    "missing_zones_log.xlsx")
    with pd.ExcelWriter(log_file, engine="openpyxl") as writer:
        missing_zones_1.to_excel(
            writer, sheet_name=f"{zone_names[0]}_missing", index=False
        )
        missing_zones_2.to_excel(
            writer, sheet_name=f"{zone_names[1]}_missing", index=False
        )
    LOG.info(
        "List of missing zones can be found in log file found here: %s",
        log_file,
    )
    LOG.info(
        "Zone correspondence finished, file saved here: %s",
        final_zone_corr_path,
    )

    return final_zone_corr
