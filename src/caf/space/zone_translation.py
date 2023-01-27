# -*- coding: utf-8 -*-
"""
    Module containing ZoneTranslation class for producing a zone
    translation from a set of inputs, provided by the
    ZoneTranslationInputs class in 'inputs'.
"""
import logging
import warnings
import pandas as pd
from caf.space import geo_utils as nf, zone_correspondence as zc, inputs as si

##### CONSTANTS #####
LOG = logging.getLogger(__name__)
logging.captureWarnings(True)


##### CLASSES #####
class ZoneTranslation:
    """
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

    def __init__(self, params: si.ZoningTranslationInputs):
        self.params = params
        self.names = sorted([params.zone_1.name, params.zone_2.name])
        cacher = self.params.cache_path / f"{self.names[0]}_{self.names[1]}"
        cacher.mkdir(exist_ok=True, parents=True)
        if self.params.method is None:
            self.zone_translation = self.main_zone_correspondence()

            self.zone_translation.to_csv(
                cacher / f"{self.params.run_date}.csv")
            self.params.save_yaml(cacher / f"{self.params.run_date}.yml")
        else:
            cacher = cacher / self.params.method
            cacher.mkdir(exist_ok=True, parents=True)
            self.zone_translation = self.weighted_translation()
            self.zone_translation.to_csv(
                cacher / f"{self.params.run_date}.csv", index=False)
            self.params.save_yaml(cacher / f"{self.params.run_date}.yml")

    def main_zone_correspondence(self):
        """Performs zone correspondence between two zoning systems, zone 1 and
        zone 2. Default correspondence is spatial (by zone area), but includes
        options for handling point zones with different data (for example LSOA
        employment data). Also includes option to check adjustment factors from
        zone 1 to zone 2 add to 1.
        """
        # read in zone shapefiles
        zones = zc.read_zone_shapefiles(self.params)
        # produce spatial zone correspondence
        spatial_correspondence = zc.spatial_zone_correspondence(zones)
        # Determine if slither filtering and rounding required.
        zone_names = [zones["Major"]["Name"], zones["Minor"]["Name"]]
        if self.params.filter_slithers:
            LOG.info("Filtering out small overlaps.")
            (_, spatial_correspondence_no_slithers,) = zc.find_slithers(
                spatial_correspondence, zone_names, self.params.tolerance
            )

            if self.params.rounding:
                LOG.info("Checking all adjustment factors add to 1")
                final_zone_corr = zc.round_zone_correspondence(
                    spatial_correspondence_no_slithers, zone_names
                )
            else:
                final_zone_corr = spatial_correspondence_no_slithers
        else:
            if self.params.rounding:
                LOG.info("Checking all adjustment factors add to 1")
                final_zone_corr = zc.round_zone_correspondence(
                    spatial_correspondence, zone_names
                )
            else:
                final_zone_corr = spatial_correspondence
        # Save correspondence output
        final_zone_corr_path = (
                self.params.output_path
                / f"{zone_names[0]}_to_{zone_names[1]}_correspondence.csv"
        )
        missing_zones_1, missing_zones_2 = zc.missing_zones_check(
            zones, final_zone_corr
        )

        warnings.warn(f"Missing Zones from 1 : {len(missing_zones_1)}")
        warnings.warn(f"Missing Zones from 2 : {len(missing_zones_2)}")
        log_path = self.params.cache_path / f"{zone_names[0]}_{zone_names[1]}"
        log_path.mkdir(exist_ok=True, parents=True)
        log_file = (log_path /
                    "missing_zones_log.xlsx")
        with pd.ExcelWriter(log_file, engine="openpyxl") as writer: # pylint: disable=abstract-class-instantiated
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

    def weighted_translation(self):
        """
        Runs a weighted translation using the zone 1 to lower
        correspondence csv file and the zone 2 to lower correspondence
        csv file. The type of variable to weight the translation by,
        such as population or employment, is chosen by the method
        variable.

         Parameters
         ----------
         Returns
         -------
         weighted_translation: pd.DataFrame
             Weighted Translation between Zone 1 and Zone 2
        """
        LOG.info("Starting weighted translation")
        # Init

        weighted_translation = nf.final_weighted(
            self.params
        )
        weighted_translation = weighted_translation[
            [f"{self.params.zone_1.name}_to_{self.params.zone_2.name}",
             f"{self.params.zone_2.name}_to_{self.params.zone_1.name}"]]
        weighted_translation.reset_index(inplace=True)

        column_list = list(weighted_translation.columns)

        summary_table_1 = weighted_translation.groupby(column_list[0])[
            column_list[2]
        ].sum()
        summary_table_2 = weighted_translation.groupby(column_list[1])[
            column_list[3]
        ].sum()

        under_1_zones_1 = summary_table_1[summary_table_1 < 0.999999]
        under_1_zones_2 = summary_table_2[summary_table_2 < 0.999999]

        if len(pd.unique(weighted_translation[column_list[0]])) == sum(
                summary_table_1
        ):
            LOG.info("Split factors add up to 1 for %s", column_list[0])
        else:
            LOG.warning(
                "Split factors DO NOT add up to 1 for %s. CHECK "
                "TRANSLATION IS ACCURATE\n%s",
                column_list[0],
                under_1_zones_1,
            )

        if len(pd.unique(weighted_translation[column_list[1]])) == sum(
                summary_table_2
        ):
            LOG.info("Split factors add up to 1 for %s", column_list[1])
        else:
            LOG.warning(
                "Split factors DO NOT add up to 1 for %s. CHECK "
                "TRANSLATION IS ACCURATE\n%s",
                column_list[1],
                under_1_zones_2,
            )

        return weighted_translation
