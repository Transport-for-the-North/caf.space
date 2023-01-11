import os
import datetime
import logging
import pandas as pd
from pathlib import Path

from caf.space import (
    geo_utils as nf,
    zone_correspondence as zc,
    inputs as si,
    metadata as me,
)

##### CONSTANTS #####
LOG = logging.getLogger(__name__)

##### CLASSES #####
class ZoneTranslation:
    def __init__(self, params: si.ZoningTranslationInputs):
        """
        This is the main class for the caf.space tool. Running it with an
        instance of inputs.ZoningTranslationInputs will return a zone
        translation dataframe.

        Parameters
        ----------
        params (si.ZoningTranslationInputs): Params should usually be
        read in from a yml file using the load_yaml method of the
        ZoningTranslationInputs class. Refer to this class for info on
        parameters.
        """
        self.params = params
        if self.params.method is None:
            self.zone_translation = zc.main_zone_correspondence(
                self.params
            )
        else:
            if params.zone_1.lower_translation is None:
                LOG.info(
                    "Searching for lower translation for "
                    f"{self.params.zone_1.name}."
                )
                lower = self._find_lower_translation(params.zone_1.name)
                if lower is None:
                    self.params.zone_1.lower_translation = (
                        self._save_lower(self.params.zone_1.name)
                    )
                    LOG.info(
                        "Lower translation created and saved to cache."
                    )
                else:
                    self.params.zone_1.lower_translation = lower
            if params.zone_2.lower_translation is None:
                LOG.info(
                    "Searching for lower translation for "
                    f"{self.params.zone_2.name}."
                )
                lower = self._find_lower_translation(params.zone_2.name)
                if lower is None:
                    self.params.zone_2.lower_translation = (
                        self._save_lower(self.params.zone_2.name)
                    )
                    LOG.info(
                        "Lower translation created and saved to cache."
                    )
                else:
                    self.params.zone_2.lower_translation = lower
            self.zone_translation = self._weighted_translation(
            )

    def run_spatial_translation(self, zone_to_translate_from):
        """Runs a spatial correspondence between specified zones and a
        lower zoning system, specified by the given params.
        Parameters
        ----------
        zone_to_translate : str
            Path to zone system shapefile
        Returns
        ----------
        pd.DataFrame
        Contains correspondence values between zone and lower zone.
        Columns are zone_id, lower zone code, zone to lower match value,
        lower to zone match value.
        """
        inner_params = self.params.copy()
        inner_params.zone_2 = (
            self.params.lower_zoning._lower_to_higher()
        )
        inner_params.lower_zoning = None
        if zone_to_translate_from == self.params.zone_2.name:
            inner_params.zone_1 = self.params.zone_2

        lower_translation = zc.main_zone_correspondence(inner_params)

        return lower_translation

    def _find_lower_translation(self, zone: str) -> Path:
        """
        Function to search the cache path for existing lower
        translations.
        Parameters:
            - zone (str): Name of the zone. This must always be
            identical to the corresponding zone name within the config.
        Returns:
            lower (Path): If an appropriate existing lower translation
            exists, this will return a path to it. If not returns None.
        """
        if zone == self.params.zone_1.name:
            zone = self.params.zone_1
        elif zone == self.params.zone_2.name:
            zone = self.params.zone_2
        else:
            NameError(
                "The zone name selected isn't part of this translation."
            )
        lower_path = (
            self.params.cache_path
            / f"{zone.name}_{self.params.lower_zoning.name}"
        )
        lower = None
        if os.path.isdir(lower_path):
            meta_path = lower_path / "metadata.yml"
            if os.path.isfile(meta_path):
                meta = me.LowerMetadata.load_yaml(
                    lower_path / "metadata.yml"
                ).translations
                for trans in meta:
                    if (
                        trans.zone_shapefile == zone.shapefile
                        and trans.lower_shapefile
                        == self.params.lower_zoning.shapefile
                    ):
                        mod_date = max(
                            os.path.getmtime(zone.shapefile),
                            os.path.getmtime(
                                self.params.lower_zoning.shapefile
                            ),
                        )
                        if (
                            datetime.datetime.timestamp(trans.date)
                            > mod_date
                        ):
                            lower = (
                                lower_path
                                / f'{trans.date.strftime("%d_%m_%y")}.csv'
                            )
                            LOG.info(
                                f"Appropriate translation found at {lower}."
                            )
                        else:
                            LOG.error(
                                "Shapefile(s) modified since last translation"
                            )
                    else:
                        continue
            else:
                LOG.error(
                    "The lower translations folder in this cache has no "
                    "metadata, or it is names incorrectly. The metadata "
                    "should be called 'metadata.yml'."
                )
            if lower is None:
                LOG.error(
                    f"No appropriate translation exists for {zone.name} "
                    f"to {self.params.lower_zoning.name}, running "
                    "spatial correspondence."
                )
        return lower

    def _weighted_translation(self):
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

        weighted_translation = nf.zone_split(
            self.params
        )

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

    def _save_lower(self, zone_name: str):
        """
        Basically a wrapper for run_spatial_translation, which saves the
         translation created along with associated metadata, and returns
         a path to it.

        Args:
            zone_name (str): name of the zone to create a lower
            translation from
        Returns:
            lower_translation: A path to the lower translation created
            and saved here.
        """
        lower = self.run_spatial_translation(zone_name)
        if zone_name == self.params.zone_1.name:
            zone = self.params.zone_1
        else:
            zone = self.params.zone_2
        zone_path = (
            self.params.cache_path
            / f"{zone_name}_{self.params.lower_zoning.name}"
        )
        zone_path.mkdir(exist_ok=True, parents=True)
        zone.lower_translation = (
            zone_path
            / f'{datetime.datetime.now().strftime("%d_%m_%y")}.csv'
        )
        lower.to_csv(zone.lower_translation)
        lower_log = me.SpatialTransLog(
            zone_shapefile=zone.shapefile,
            lower_shapefile=self.params.lower_zoning.shapefile,
            date=datetime.datetime.now(),
        )
        meta_path = zone_path / "metadata.yml"
        if os.path.isdir(meta_path):
            meta = me.LowerMetadata.load_yaml(
                zone_path / "metadata.yml"
            )
            meta.translations.append(lower_log)
        else:
            meta = me.LowerMetadata(translations=[lower_log])
        meta.save_yaml(zone_path / "metadata.yml")
        return zone.lower_translation
