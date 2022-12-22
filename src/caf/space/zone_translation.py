import os
import datetime
import logging
import csv
import sys
import pandas as pd

from space import geo_utils as nf, zone_correspondence as zc, inputs as si

##### CONSTANTS #####
LOG = logging.getLogger(__name__)

##### CLASSES #####
class ZoneTranslation:
    def __init__(
        self,
        params: si.ZoningTranslationInputs
    ):
        self.params = params
        if params.method is None:
            if params.existing_translation is not None:
                self.zone_translation = pd.read_csv(params.existing_translation)
            else:
                self.zone_translation, final_zone_corr_path = zc.main_zone_correspondence(
                    self.params
                )
        else:
            if params.zone_1.lower_translation is None:
                try:
                    self.zone_1.lower_translation = self.find_lower_translation(
                    )
                except Exception:
                    LOG.info(
                        "Running Zone to lower zoning correspondence for zones 1"
                    )
                    self.zone_1_lower_trans = self.run_spatial_translation(
                        params.zone_1_name
                    )
            if params.zone_2.lower_translation is None:
                try:
                    self.zone_2_lower_trans = self.find_lower_translation(
                    )
                except Exception:
                    LOG.info(
                        "Running Zone to lower zoning correspondence for zones 2"
                    )
                    self.zone_2_lower_trans = self.run_spatial_translation(
                        params.zone_2_name
                    )
            self.zone_translation = self.weighted_translation(datetime.datetime.now, write=False)
            
                
            
            
    def run_spatial_translation(self, zone_to_translate_from):
        """Runs a spatial correspondence between specified zones and a lower zoning system.
        Parameters
        ----------
        zone_to_translate : str
            Path to zone system shapefile
        Returns
        -------
        pd.DataFrame
        Contains correspondence values between zone and LSOA zone.
        Columns are zone_id, lsoa code, zone to lsoa match value,
        lsoa to zone match value.
        """
        if zone_to_translate_from == self.zone_1.name:
            trans_shape = self.zone_1.shapefile
            trans_name = self.zone_1.name
            trans_id_col = self.zone_1.id_col
        elif zone_to_translate_from == self.zone_2.name:
            trans_shape = self.zone_2.shapefile
            trans_name = self.zone_2.name
            trans_id_col = self.zone_2.id_col

        lower_translation, lower_path = zc.main_zone_correspondence(
            zone_1_path=trans_shape,
            zone_2_path=self.lower_zoning.shapefile,
            zone_1_name=trans_name,
            zone_2_name=self.lower_zoning.name,
            zone_1_id_col=trans_id_col,
            zone_2_id_col=self.lower_zoning.id_col,
            tolerance=self.tolerance,
            out_path=self.output_path,
            point_handling=self.point_handling,
            point_tolerance=self.point_tolerance,
            point_zones_path=self.point_zones_path,
            lower_shapefile_path=self.lower_zoning.shapefile,
            lower_weight_data_path=self.lower_zoning.weight_data,
            rounding=self.rounding,
            filter_slithers=self.filter_slithers,
        )

        return lower_translation, lower_path

    def find_lower_translation(self):
        """
        =================================
        This function needs to be rewritten once the metadata and file structures are decided
        =================================
        """

    def weighted_translation(self, start_time, write=True):
        """
        Runs a weighted translation using the zone 1 to lower correspondence
        csv file and the zone 2 to lower correspondence csv file. The type of
        variable to weight the translation by, such as population or 
        employment, is chosen by the method variable. 
        
         Parameters
         ----------
         method: str
             Weighting method choice, for reporting only
         start_time : datetime
             Start time and date of script run
         write : bool
             Indicates if weighted translation should be exported to csv
         Returns
         -------
         weighted_translation: pd.DataFrame
             Weighted Translation between Zone 1 and Zone 2
         """
        LOG.info("Starting weighted translation")
        # Init
        zone_name1 = self.zone_1_name.lower()
        zone_name2 = self.zone_2_name.lower()

        weighted_translation = nf.zone_split(
            area_correspondence_path1=self.zone_1_lower_trans,
            area_correspondence_path2=self.zone_2_lower_trans,
            weighting_data=self.lower_weight_data_path,
            weighting_zone_col=self.lower_zoning_weight_id_col,
            weighting_var_col=self.lower_zoning_data_col,
            zone_1_name=self.zone_1.name,
            zone_2_name=self.zone_2.name,
            lower_zone_name = self.lower_zoning.name
        )
        # TODO check code from here to bottom when the tool is functional. I think it works but
        # not sure what it does and it should definitely be refactored
        column_list = list(weighted_translation.columns)

        summary_table_1 = weighted_translation.groupby(column_list[0])[
            column_list[2]
        ].sum()
        summary_table_2 = weighted_translation.groupby(column_list[1])[
            column_list[3]
        ].sum()

        under_1_zones_1 = summary_table_1[summary_table_1 < 0.999999]
        under_1_zones_2 = summary_table_2[summary_table_2 < 0.999999]

        if len(pd.unique(weighted_translation[column_list[0]])) == sum(summary_table_1):
            LOG.info("Split factors add up to 1 for %s", column_list[0])
        else:
            LOG.warning(
                "Split factors DO NOT add up to 1 for %s. CHECK TRANSLATION IS ACCURATE\n%s",
                column_list[0],
                under_1_zones_1,
            )

        if len(pd.unique(weighted_translation[column_list[1]])) == sum(summary_table_2):
            LOG.info("Split factors add up to 1 for %s", column_list[1])
        else:
            LOG.warning(
                "Split factors DO NOT add up to 1 for %s. CHECK TRANSLATION IS ACCURATE\n%s",
                column_list[1],
                under_1_zones_2,
            )

        if write:
            f_name = "%s_%s_%s_weight.csv" % (zone_name1, zone_name2, self.method)
            out_path = os.path.join(self.out_path, f_name)
            weighted_translation.to_csv(out_path, index=False)

            LOG.info("Copy of translation written to: %s", out_path)

        run_time = datetime.datetime.now() - start_time
        LOG.info("Script Completed in : %s", run_time)

        log_data = {
            "Run Time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "Zone 1 name": self.zone_1_name,
            "Zone 2 name": self.zone_2_name,
            "Zone 1 shapefile": self.zone_1_path,
            "Zone 2 Shapefile": self.zone_2_path,
            "Output directory": out_path,
            "Tolerance": self.tolerance,
            "Point handling": self.point_handling,
            "Point list": self.point_zones_path,
            "Point tolerance": self.point_tolerance,
            "Lower weight data": self.lower_weight_data_path,
            "Lower shapefile path": self.lower_shapefile_path,
            "Rounding": self.rounding,
            "filter_slithers": self.filter_slithers,
            "type": "weighted_translation",
            "method": self.method,
            "run_time": run_time,
        }

        # Update master log spreadsheet with run parameter
        # convert dict values to list

        list_of_elem = list(log_data.values())
        try:
            with open(
                os.path.join(self.out_path, "master_zone_translation_log.csv"),
                "a+",
                newline="",
            ) as write_obj:
                # Create a writer object from csv module
                csv_writer = csv.writer(write_obj)
                # Add contents of list as last row in the csv file
                csv_writer.writerow(list_of_elem)
        except Exception:
            LOG.error("Failed to add to Master Log:", exc_info=True)

        return weighted_translation