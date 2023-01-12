##### IMPORTS #####
import logging
import pandas as pd
from caf.space import inputs as si

##### CONSTANTS #####
LOG = logging.getLogger(__name__)


##### FUNCTIONS #####
def var_apply(
    area_correspondence_path: str,
    weighting_data: str,
    weighting_var_col: str,
    zone_name: str,
    lower_name: str,
) -> pd.DataFrame:
    """
    Joins chosen method variable to lower zoning shapefile.

    Parameters
    ----------
    area_correspondence_path : str
        Path to correspondence csv file
    weighting_data : str
        Path to variable csv file
    weighting_var_col: str
        Column name of weighting variable
    zone_name: str
        Name of the primary zone system e.g. 'MSOA'
    lower_name: str
        Name of the lower zone system used e.g. 'LSOA'
    Returns
    -------
    area_correspondence_var: pd.DataFrame
        Zone to lower correspondence code with attached variable values
        scaled  by lower to zone correspondence values.
    """

    # Read in the variables to join to the lsoa to zone translation
    LOG.info("Importing weighting data from: %s", weighting_data)
    zone_variables = pd.read_csv(weighting_data)

    if weighting_var_col is None:
        weighting_var_col = list(zone_variables)[-1]
    zone_variables[weighting_var_col] = zone_variables[
        weighting_var_col
    ].astype(float)

    # Read in the lower to zone correspondences
    area_correspondence = pd.read_csv(
        area_correspondence_path, index_col=False
    )

    # Work out cols in left and right for merge
    merge_cols, area_correspondence, zone_variables = _cols_in_both(
        area_correspondence, zone_variables
    )
    LOG.info("Joining on lower zones id, %s", merge_cols)

    # Merge var zones onto area translation file
    area_correspondence_var = pd.merge(
        area_correspondence, zone_variables, how="outer", on=merge_cols
    )
    # Count lsoas/msoas which have not joined to translation indicating 
    # they do not intersect with lsoa/msoa zones.
    missing_lower = area_correspondence_var[merge_cols].isna().sum()

    LOG.warning(
        "%s zones are not intersected by target zones", missing_lower
    )

    # Multiply var by the minor to major overlap
    area_correspondence_var[
        weighting_var_col
    ] *= area_correspondence_var.loc[:, f"{lower_name}_to_{zone_name}"]

    return area_correspondence_var


def zone_split(
    params: si.ZoningTranslationInputs
) -> pd.DataFrame:
    """Joins chosen method variable to Zone to Lower Weighted
    correspondence table on a standard code using var_apply function
    then calculates weighted translation between Zone 1 and Zone 2.
    Parameters
    ----------
    area_correspondence_path1 : str
         Path to Zone 1 to lower correspondence csv file
    area_correspondence_path2 : str
         Path to Zone 2 to lower correspondence csv file
    weighting_data: pd.DataFrame:
        Data to weight translation by
    weighting_var_col: str
        Name of the variable to weight by

    Returns
     -------
     weighted_translation: pd.DataFrame
         Zone 1 to Zone 2 weighted translation using defined method
    """

    # 2 zone weighted translation
    area_correspondence_path1=params.zone_1.lower_translation,
    area_correspondence_path2=params.zone_2.lower_translation,
    weighting_data=params.lower_zoning.weight_data,
    weighting_zone_col=params.lower_zoning.weight_id_col,
    weighting_var_col=params.lower_zoning.data_col,
    zone_1_name=params.zone_1.name.lower(),
    zone_2_name=params.zone_2.name.lower(),
    lower_zoning_name=params.lower_zoning.name.lower()
    ats = {
        zone_1_name: var_apply(
            area_correspondence_path1,
            weighting_data,
            weighting_var_col,
            zone_1_name,
            lower_zoning_name,
        ),
        zone_2_name: var_apply(
            area_correspondence_path2,
            weighting_data,
            weighting_var_col,
            zone_2_name,
            lower_zoning_name,
        ),
    }

    # Outer Join to keep var zones which do not intersect with any zone
    area_correspondence_var = pd.merge(
        ats[zone_1_name],
        ats[zone_2_name],
        how="outer",
        on=weighting_zone_col,
        suffixes=(zone_1_name, zone_2_name),
    )

    area_correspondence_var[
        weighting_var_col
    ] = area_correspondence_var[
        [
            f"{weighting_var_col}{zone_1_name}",
            f"{weighting_var_col}{zone_2_name}",
        ]
    ].min(
        axis=1
    )
    area_correspondence_var.drop(
        [
            f"{weighting_var_col}{zone_1_name}",
            f"{weighting_var_col}{zone_2_name}",
        ],
        axis=1,
        inplace=True,
    )

    # Loop to get sums from newly adjusted totals
    # the atsum variables stores the var total for each zone area. one 
    # table for zone 1 totals and another for zone 2 totals
    area_correspondence_sums = {}
    for at in ats.keys():
        # pass zone_names here
        zone_col = f"{at.lower()}_zone_id"
        # group by the zone code
        area_correspondence_sum = area_correspondence_var.groupby(
            zone_col
        ).sum()
        del zone_col
        area_correspondence_sums[at] = area_correspondence_sum[
            weighting_var_col
        ]

    # This part here is what determines the "overlap_var" it is a groupby on the zone1 then 2
    var_merge_step = (
        area_correspondence_var.groupby(
            [f"{zone_1_name}_zone_id", f"{zone_2_name}_zone_id"]
        )[weighting_var_col]
        .sum()
        .reset_index()
    )
    var_merge_step = var_merge_step.rename(
        columns={weighting_var_col: "overlap_value"}
    )

    # Merges the individual zone totals onto the zone1 zone 2 overlap var table
    weighted_translation = pd.merge(
        var_merge_step,
        area_correspondence_sums[zone_1_name],
        how="inner",
        on=f"{zone_1_name}_zone_id",
    )
    weighted_translation = pd.merge(
        weighted_translation,
        area_correspondence_sums[zone_2_name],
        how="inner",
        on=f"{zone_2_name}_zone_id",
        suffixes=[f"_{zone_1_name}", f"_{zone_2_name}"],
    )

    # Name split factors
    weighted_translation[f"{zone_1_name}_to_{zone_2_name}"] = (
        weighted_translation["overlap_value"]
        / weighted_translation[f"var_{zone_1_name}"]
    )
    weighted_translation[f"{zone_2_name}_to_{zone_1_name}"] = (
        weighted_translation["overlap_value"]
        / weighted_translation[f"var_{zone_2_name}"]
    )

    LOG.debug("Weighted translation:\n%s", weighted_translation)

    # Drop non essential columns
    # Zone_correspondence should be in configuration: 0 'zone1ID', 1 'zone2ID',
    #  2 'overlap_population', 3 'zone1_population', 4 'zone2_population',
    #  5 'overlap_zone1_factor', 6 'overlap_zone2_factor'
    # All calls to iloc are based on this so if it's not right these won't work
    weighted_translation.drop(
        weighted_translation.columns[[2, 3, 4]], axis=1, inplace=True
    )

    return weighted_translation


def _cols_in_both(left: pd.DataFrame, right: pd.DataFrame):
    """
    Short function to find column names common to two dataframes in order
    to merge them. Also lowers all columns names to lower case to merge
    more flexibly.
    Args:
        left (pd.DataFrame): A dataframe to be merged later
        right (pd.DataFrame): A dataframe to be merged later

    Returns:
        lis: List of common column names
        left: the input dataframe with lower case column names
        right: the input datafarame with lower case column names
    """

    left.columns = [x.lower() for x in left.columns]
    right.columns = [x.lower() for x in right.columns]
    lis = [x for x in list(left) if x in list(right)]
    return lis, left, right
