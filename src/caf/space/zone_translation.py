import os
import datetime
import logging
import csv
import sys
import pandas as pd

from caf.space import geo_utils as nf, zone_correspondence as zc, inputs as si, metadata as me

##### CONSTANTS #####
LOG = logging.getLogger(__name__)

##### CLASSES #####
class ZoneTranslation:
    def __init__(
        self,
        params: si.ZoningTranslationInputs
    ):
        self.params = params
        if self.params.method is None:
            if self.params.existing_translation is not None:
                self.zone_translation = pd.read_csv(params.existing_translation)
            else:
                self.zone_translation = zc.main_zone_correspondence(
                    self.params
                )
        else:
            if params.zone_1.lower_translation is None:
                lower = self.find_lower_translation(params.zone_1.name)
                if lower == None:
                    self.params.zone_1.lower_translation = self.save_lower(self.params.zone_1.name)
                else:
                    self.params.zone_1.lower_translation = lower
            if params.zone_2.lower_translation is None:
                lower = self.find_lower_translation(params.zone_1.name)
                if lower == None:
                    self.params.zone_2.lower_translation = self.save_lower(self.params.zone_2.name)
                else:
                    self.params.zone_2.lower_translation = lower
            self.zone_translation = self.weighted_translation(datetime.datetime.now)
            
                
            
            
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
        inner_params = self.params.copy()
        inner_params.zone_2 = self.params.lower_zoning._lower_to_higher()
        inner_params.lower_zoning = None
        if zone_to_translate_from == self.params.zone_2.name:
            inner_params.zone_1 = self.params.zone_2

        lower_translation = zc.main_zone_correspondence(
            inner_params
        )

        return lower_translation

    def find_lower_translation(self, zone: str):
        """
        =================================
        TODO This function needs to be rewritten once the metadata and file structures are decided
        =================================
        """
        if zone == self.params.zone_1.name:
            zone = self.params.zone_1
        elif zone == self.params.zone_2.name:
            zone = self.params.zone_2
        else:
            NameError("The zone name selected isn't part of this translation.")
        lower_path = self.params.cache_path / f"{zone.name}_{self.params.lower_zoning.name}"
        if os.path.isdir(lower_path):
            meta = me.lower_metadata.load_yaml(lower_path / "metadata.yml").translations
            lower = None
            for trans in meta:
                if trans.zone_shapefile == zone.shapefile and trans.lower_shapefile == self.params.lower_zoning.shapefile:
                    mod_date = max(os.path.getmtime(zone.shapefile),os.path.getmtime(self.params.lower_zoning.shapefile))
                    if datetime.datetime.timestamp(meta.date) > mod_date:
                        lower =  lower_path / f'{meta.date.strftime("%d_%m_%y")}.csv'
                    else:
                        LOG.error("Shapefile(s) modified since last translation")
                else:
                    continue
            if lower == None:
                LOG.error(f"No appropriate translation exists for {zone.name} to {self.lower_zoning.name}, running spatial correspondence.")
        return lower

    def weighted_translation(self, start_time):
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
        zone_name1 = self.params.zone_1.name.lower()
        zone_name2 = self.params.zone_2.name.lower()

        weighted_translation = nf.zone_split(
            area_correspondence_path1=self.params.zone_1.lower_translation,
            area_correspondence_path2=self.params.zone_2.lower_translation,
            weighting_data=self.params.lower_zoning.weight_data,
            weighting_zone_col=self.params.lower_zoning.weight_id_col,
            weighting_var_col=self.params.lower_zoning.data_col,
            zone_1_name=self.params.zone_1.name.lower(),
            zone_2_name=self.params.zone_2.name.lower(),
            lower_zoning_name = self.params.lower_zoning.name.lower()
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


        # LOG.info("Copy of translation written to: %s", out_path)

        run_time = datetime.datetime.now() - start_time()
        # LOG.info("Script Completed in : %s", run_time)

        log_data = {
            "Run Time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "Zone 1 name": self.params.zone_1.name,
            "Zone 2 name": self.params.zone_2.name,
            "Zone 1 shapefile": self.params.zone_1.shapefile,
            "Zone 2 Shapefile": self.params.zone_2.shapefile,
            "Output directory": self.params.output_path,
            "Tolerance": self.params.tolerance,
            "Point handling": self.params.point_handling,
            "Point list": self.params.point_zones_path,
            "Point tolerance": self.params.point_tolerance,
            "Lower weight data": self.params.lower_zoning.weight_data,
            "Lower shapefile path": self.params.lower_zoning.shapefile,
            "Rounding": self.params.rounding,
            "filter_slithers": self.params.filter_slithers,
            "type": "weighted_translation",
            "method": self.params.method,
            "run_time": run_time,
        }

        # Update master log spreadsheet with run parameter
        # convert dict values to list

        list_of_elem = list(log_data.values())
        try:
            with open(
                os.path.join(self.params.output_path, "master_zone_translation_log.csv"),
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

    def save_lower(self, zone_name):
        lower = self.run_spatial_translation(
            zone_name
        )
        if zone_name == self.params.zone_1.name:
            zone = self.params.zone_1
        else:
            zone = self.params.zone_2
        zone_path = self.params.cache_path / f"{zone_name}_{self.params.lower_zoning.name}"
        if os.path.isdir(zone_path) == False:
            os.mkdir(zone_path)
        zone.lower_translation = zone_path / f'{datetime.datetime.now().strftime("%d_%m_%y")}.csv'
        lower.to_csv(zone.lower_translation)
        meta = me.lower_metadata.load_yaml(zone_path / "metadata.yml")
        lower_log = me.lower_trans_log(zone.shapefile, self.lower_zoning.shapefile, datetime.datetime.now())
        meta.translations.append(lower_log)
        meta.save_yaml(zone_path / "metadata.yml")
        return zone.lower_translation