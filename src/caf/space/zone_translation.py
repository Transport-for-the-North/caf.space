# -*- coding: utf-8 -*-
"""
Module containing ZoneTranslation class.

Class for producing zone translations from a set of inputs, provided by the
ZoneTranslationInputs class in 'inputs'.
"""
import logging
import warnings
from pathlib import Path
import pandas as pd
import geopandas as gpd

from caf.space import weighted_funcs, zone_correspondence, inputs, utils

##### CONSTANTS #####
LOG = logging.getLogger("SPACE")
# logging.basicConfig(format="%(asctime)s [%(name)-20.20s] [%(levelname)-8.8s]  %(message)s")
logging.captureWarnings(True)


##### CLASSES #####
class ZoneTranslation:
    """
    Store paramaters and create zone translations.

    This is the main class for the caf.space tool. Running it with an
    instance of 'inputs.ZoningTranslationInputs' will return a zone
    translation dataframe.

    Parameters
    ----------
    params: ZoningTranslationInputs
        Params should usually be read in from a yml file using the
        load_yaml method of the ZoningTranslationInputs class. Refer to
        this class for info on parameters.

    Returns
    -------
    Instance of self
        Instance of ZoneTranslation, where a spatial or weighted
        zone translation, dependent on inputs, is stored as
        self.zone_translation
    """

    def __init__(self, params: inputs.ZoningTranslationInputs):
        self.params = params
        self.zone_1 = params.zone_1
        self.zone_2 = params.zone_2

        self.cache_path = params.cache_path
        if params.lower_zoning:
            self.lower_zoning = params.lower_zoning
        if params.method:
            self.method = params.method
        self.slither_tolerance = params.sliver_tolerance
        self.rounding = params.rounding
        self.filter_slithers = params.filter_slivers
        self.point_handling = params.point_handling
        self.point_tolerance = params.point_tolerance
        self.run_date = params.run_date
        sorted_names = sorted([params.zone_1.name, params.zone_2.name])
        self.names = (sorted_names[0], sorted_names[1])
        self.logger = logging.getLogger("SPACE")
        self.handler = logging.FileHandler(
            self.cache_path / f"{self.names[0]}_{self.names[1]}.log", mode="w"
        )
        self.handler.setFormatter(
            logging.Formatter("%(asctime)s [%(name)-20.20s] [%(levelname)-8.8s]  %(message)s")
        )
        self.logger.addHandler(self.handler)
        self.logger.setLevel(logging.INFO)

    def spatial_translation(self) -> pd.DataFrame:
        """
        Create spatial zone translation.

        Performs zone correspondence between two zoning systems, zone 1 and
        zone 2. Default correspondence is spatial (by zone area), but includes
        options for handling point zones with different data (for example LSOA
        employment data). Also includes option to check adjustment factors from
        zone 1 to zone 2 add to 1. Any options for this are set in the config
        file/class or the UI, depending on how you run the tool.

        Returns
        -------
        spatial_translation: pd.DataFrame
            Dataframe containing spatial zone translation between zone 1 and zone 2.
        """
        zones = zone_correspondence.read_zone_shapefiles(self.zone_1, self.zone_2)
        spatial_correspondence = zone_correspondence.spatial_zone_correspondence(
            zones, self.zone_1, self.zone_2
        )
        final_zone_corr = self._slithers_and_rounding(spatial_correspondence)
        # Save correspondence output
        out_path = self.cache_path / f"{self.names[0]}_{self.names[1]}"
        out_path.mkdir(exist_ok=True, parents=False)
        self._post_processing(zones, final_zone_corr, out_path)
        out_name = f"{self.names[0]}_to_{self.names[1]}_spatial"
        final_zone_corr.to_csv(out_path / f"{out_name}.csv", index=False)
        self.params.save_yaml(out_path / f"{out_name}.yml")
        return final_zone_corr

    def weighted_translation(self) -> pd.DataFrame:
        """
        Create a weighted zone translation.

        Runs a weighted translation using the zone 1 to lower correspondence
        csv file and the zone 2 to lower correspondence csv file. The type of
        variable to weight the translation by, such as population or
        employment, is chosen by the method variable.

        Parameters
        ----------
        self: for this to run self.params must contain lower zoning and a method.

        Returns
        -------
        weighted_translation: pd.DataFrame
            Dataframe containing weighted zone translation between zone 1 and zone 2.
        """
        self.logger.info("Starting weighted translation")
        # Init
        if self.params.method is False:
            raise ValueError("A method must be provided to perform a weighted translation.")
        if self.params.lower_zoning is False:
            raise ValueError("Lower zoning data is required for a weighted translations.")
        zones = zone_correspondence.read_zone_shapefiles(self.zone_1, self.zone_2)
        points_1 = None
        points_2 = None
        if self.zone_1.point_shapefile:
            if self.zone_2.point_shapefile:
                points_1 = gpd.read_file(self.zone_1.point_shapefile)
                points_2 = gpd.read_file(self.zone_2.point_shapefile)
                if len(points_1) > len(points_2):
                    matches = utils.find_point_matches(
                        points_1,
                        points_2,
                        1000,
                        self.zone_1.id_col,
                        self.zone_2.id_col,
                        self.zone_1.name,
                        self.zone_2.name,
                    )
                else:
                    matches = utils.find_point_matches(
                        points_2,
                        points_1,
                        1000,
                        self.zone_2.id_col,
                        self.zone_1.id_col,
                        self.zone_2.name,
                        self.zone_1.name,
                    )
                points_1 = utils.points_update(
                    points_1, matches, self.zone_1.id_col, f"{self.zone_1.name}_id"
                )
                points_2 = utils.points_update(
                    points_2, matches, self.zone_2.id_col, f"{self.zone_2.name}_id"
                )
            else:
                points_1 = gpd.read_file(self.zone_1.point_shapefile)
        elif self.zone_2.point_shapefile:
            points_2 = gpd.read_file(self.zone_2.point_shapefile)
        weighted_translation = weighted_funcs.final_weighted(
            zones,
            self.zone_1,
            self.zone_2,
            self.lower_zoning,
            self.point_handling,
            self.point_tolerance,
            points_1,
            points_2,
        )
        weighted_translation = weighted_translation[
            [
                f"{self.names[0]}_to_{self.names[1]}",
                f"{self.names[1]}_to_{self.names[0]}",
            ]
        ]
        fill_columns = list(weighted_translation.columns)
        weighted_translation.reset_index(inplace=True)

        weighted_translation = self._slithers_and_rounding(weighted_translation)
        out_path = self.cache_path / f"{self.names[0]}_{self.names[1]}"
        out_path.mkdir(exist_ok=True, parents=False)
        if "matches" in locals():
            matches[fill_columns] = 1
            weighted_translation = pd.concat([weighted_translation, matches])
        self._post_processing(zones, weighted_translation, out_path)
        out_name = f"{self.names[0]}_to_{self.names[1]}_{self.method}_{self.lower_zoning.weight_data_year}"
        weighted_translation.to_csv(out_path / f"{out_name}.csv", index=False)
        self.params.save_yaml(out_path / f"{out_name}.yml")
        return weighted_translation

    def _slithers_and_rounding(self, translation: pd.DataFrame) -> pd.DataFrame:
        """
        Process slithers and rounding parameters.

        Reads params and filters slithers and rounds outputs if those
        parameters are selected.

        Parameters
        ----------
        translation: The zone translation dataframe for the method to be run on.

        Returns
        -------
        The input dataframe with slithers removed and/or values rounded
        according to input params.
        """
        if self.params.filter_slivers:
            self.logger.info("Filtering out small overlaps.")
            (
                _,
                spatial_correspondence_no_slithers,
            ) = zone_correspondence.find_slithers(
                translation, self.names, self.params.sliver_tolerance
            )

            if self.params.rounding:
                self.logger.info("Checking all adjustment factors add to 1")
                final_zone_corr = zone_correspondence.round_zone_correspondence(
                    spatial_correspondence_no_slithers, self.names
                )
            else:
                final_zone_corr = spatial_correspondence_no_slithers
        else:
            if self.params.rounding:
                self.logger.info("Checking all adjustment factors add to 1")
                final_zone_corr = zone_correspondence.round_zone_correspondence(
                    translation, self.names
                )
            else:
                final_zone_corr = translation

        return final_zone_corr

    def _post_processing(
        self, zones: dict, zone_translation: gpd.GeoDataFrame, out_path: Path
    ):
        """
        Log info after producing a zone translation.

        Parameters
        ----------
        zones: dict produced by zone_correspondence.read_zone_shapefile
        zone_translation: A dataframe containing a weighted or spatial translation.
        out_path: Path logging files will be written to.

        Returns
        -------
        Nothing.
        """
        (
            missing_zones_1,
            missing_zones_2,
        ) = zone_correspondence.missing_zones_check(
            zones, zone_translation, self.zone_1, self.zone_2
        )
        if len(missing_zones_1) > 0:
            warnings.warn(f"Missing Zones from 1 : {len(missing_zones_1)}", stacklevel=2)
        if len(missing_zones_2) > 0:
            warnings.warn(f"Missing Zones from 2 : {len(missing_zones_2)}", stacklevel=2)
        log_file = out_path / "missing_zones_log.xlsx"
        with pd.ExcelWriter(
            log_file, engine="openpyxl"
        ) as writer:  # pylint: disable=abstract-class-instantiated
            missing_zones_1.to_excel(
                writer,
                sheet_name=f"{self.names[0]}_missing",
                index=False,
            )
            missing_zones_2.to_excel(
                writer,
                sheet_name=f"{self.names[1]}_missing",
                index=False,
            )
        self.logger.info(
            "List of missing zones can be found in log file found here: %s",
            log_file,
        )
        column_list = list(zone_translation.columns)

        summary_table_1 = zone_translation.groupby(column_list[0])[column_list[2]].sum()
        summary_table_2 = zone_translation.groupby(column_list[1])[column_list[3]].sum()

        under_1_zones_1 = summary_table_1[summary_table_1 < 0.999999]
        under_1_zones_2 = summary_table_2[summary_table_2 < 0.999999]

        if len(pd.unique(zone_translation[column_list[0]])) == sum(summary_table_1):
            self.logger.info("Split factors add up to 1 for %s", column_list[0])
        else:
            self.logger.warning(
                "Split factors DO NOT add up to 1 for %s. CHECK "
                "TRANSLATION IS ACCURATE\n%s",
                column_list[0],
                under_1_zones_1,
            )

        if len(pd.unique(zone_translation[column_list[1]])) == sum(summary_table_2):
            self.logger.info("Split factors add up to 1 for %s", column_list[1])
        else:
            self.logger.warning(
                "Split factors DO NOT add up to 1 for %s. CHECK "
                "TRANSLATION IS ACCURATE\n%s",
                column_list[1],
                under_1_zones_2,
            )
