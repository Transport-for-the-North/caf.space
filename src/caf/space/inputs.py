# -*- coding: utf-8 -*-
"""
    Module containing functionality for storing
    input parameters and reading config file.
"""

##### IMPORTS #####
from __future__ import annotations

# Standard imports
import logging
import datetime
import os
from pathlib import Path
from typing import Union
from pydantic import validator

# Third party imports
from caf.space import config_base
# Local imports

##### CONSTANTS #####
LOG = logging.getLogger(__name__)


class ShapefileInfo(config_base.BaseConfig):
    """Base class for storing information about a shapefile input.

    Parameters
    ----------
    name : str
        The name of the zone system you are providing. This should
        be as simple as possible, so for and MSOA shapefile, name should
        simply be.
    shapefile : Path
        Path to the shapefile.
    id_col : str
        The name of the unique ID column in your chosen shapefile. This
        can be any column as long as it is unique for each zone in the
        shapefile.
    """
    name: str
    shapefile: Path
    id_col: str
    
    @validator("shapefile")
    def path_exists(cls, v):
        """
        Validator to make sure the shapefile path exists
        Raises:
            ValueError: Informs user the path given is incorrect.

        Returns:
            Unchanged path if no error is raised.
        """
        if os.path.isfile(v) is False:
            raise ValueError(f"The path provided for {v} does not exist."
            "If this path is on a network drive make sure you are connected")
        return v


class ZoneSystemInfo(ShapefileInfo):
    """Zone system input data for `ZoneTranslationInputs`.
    Inherits from ShapefileInfo.

    Parameters
    ----------
    lower_translation : Path, optional
        This is an optional parameter providing a path to an existing
        translation between the respective zone and the lower zone.
        Almost the entire run time of the tool is creating these lower
        translations so it is worth providing this if you have it.
        Alternatively if this translation has previusly been created and
        saved in the cache, the tool should find it and use it.
    """

    lower_translation: Path = None

    @validator("lower_translation")
    def lower_exists(cls, v):
        """
        Validator to make sure the shapefile path exists
        Raises:
            ValueError: Informs user the path given is incorrect.

        Returns:
            Unchanged path if no error is raised.
        """
        if v:
            if os.path.isfile(v) is False:
                raise ValueError(
                    f"The lower translation path provided for {self.name} does not exist."
                )
        return v


class LowerZoneSystemInfo(ShapefileInfo):
    """Lower level zone system input data for `ZoneTranslationInputs`.
    Inherits from ShapefileInfo.

    Parameters
    ----------
    weight_data: Path
        File path to the weighting data for the lower zone system. This
        should be saved as a csv, and only needs two columns (an ID
        column and a column of weighting data)
    data_col: str
        The name of the column in the weighting data csv containing the
        weight data.
    weight_id_col: str
        The name of the columns in the weighting data containing the
        zone ids. This will be used to join the weighting data to the
        lower zoning, so the IDs must match, but the names of the ID
        columns may be different.
    """

    weight_data: Path
    data_col: str
    weight_id_col: str

    def _lower_to_higher(self) -> ZoneSystemInfo:
        return ZoneSystemInfo(
            name=self.name, shapefile=self.shapefile, id_col=self.id_col
        )

    @validator("weight_data")
    def weight_data_exists(cls, v):
        if os.path.isfile(v) is False:
            raise FileNotFoundError(
                f"The weight data path provided for {v} does not exist."
            )
        return v


class ZoningTranslationInputs(config_base.BaseConfig):
    """Class for storing and reading input parameters for
    `ZoneTranslation`.

    Parameters
    ----------
    zone_1: ZoneSystemInfo
        Zone system 1 information
    zone_2: ZoneSystemInfo
        Zone system 2 information
    lower_zoning: LowerZoneSystemInfo
        Information about the lower zone system, used for performing
        weighted translations. This should be as small a zone system as
        possible relative to zone_1 and zone_2. For spatially weighted
        translations this isn't needed.
    output_path: Path
        File path to where you want your translation saved. If the path
        provided doesn't exist it will be created, but it's best to
        check first to avoid surprises.
    cache_path: Path
        File path to a cache of existing translations. This defaults to
        a location on a network drive, and it is best to keep it there,
        but it's more important for weighted translations.
    method: str, optional
        The name of the method used for weighting (e.g. pop or emp).
        This can be anything, but must be included as the tool checks if
        this parameter exists to decide whether to perform a spatial or
        weighted translation.
    tolerance: float, default 0.98
        This is a float less than 1, and defaults to 0.98. If
        filter_slivers (explained below) is chosen, tolerance controls
        how big or small the slithers need to be to be rounded away. For
        most users this can be kept as is.
    rounding: bool, default True
        Select whether or not zone totals will be rounded to 1 after the
        translation is performed. Recommended to keep as True.
    filter_slithers: bool, True
        Select whether very small overlaps between zones will be
        filtered out. This accounts for zone boundaries not aligning
        perfectly when they should between shapefiles, and the tolerance
        for this is controlled by the tolerance parameter. With this
        parameter set to false translations can be a bit messy.
    run_date: str, datetime.datetime.now().strftime("%d_%m_%y")
        When the tool is being run. This is always generated
        automatically and shouldn't be included in the config yaml file.
    """

    #TODO choose and set default path for cache path
    zone_1: ZoneSystemInfo
    zone_2: ZoneSystemInfo
    lower_zoning: LowerZoneSystemInfo
    output_path: Path
    cache_path: Path
    method: str = None
    tolerance: float = 0.98
    rounding: bool = True
    filter_slithers: bool = True
    run_date: str = datetime.datetime.now().strftime("%d_%m_%y")

    def __post_init__(self) -> None:
        self.output_path.mkdir(exist_ok=True, parents=True)
        self.cache_path.mkdir(exist_ok=True, parents=True)

    @staticmethod
    def _path_none(value: str) -> Union[Path, None]:
        """Convert string to Path, or None if empty."""
        if value is None or value.strip() == "":
            return None
        return Path(value)


    def write_example(self, out_path: Path):
        """
        Method to write out an example config file. When creating a real
        config, any optional parameters not set should be removed
        entirely, and not just left blank to the right of the colon.

        Parameters
        ----------
        out_path: Path
            The folder the example will be saved in. The file will be
            called 'example.yml'.
        """
        zones = {}
        for i in range(1, 3):
            zones[i] = ZoneSystemInfo(
                name=f"zone_{i}_name",
                shapefile=Path(f"path/to/shapefile_{i}"),
                id_col=f"id_col_for_zone_{i}",
                lower_translation=Path(f"path/to/lower_trans_{i}"),
            )
        lower = LowerZoneSystemInfo(
            name="lower_zone_name",
            shapefile=Path("path/to/lower/shapefile"),
            id_col="id_col_for_lower_zone",
            weight_data=Path("path/to/lower/weight/data"),
            data_col="data_col_name",
            weight_id_col="id_col_in_weighting_data",
        )
        ex = ZoningTranslationInputs(
            zone_1=zones[1],
            zone_2=zones[2],
            lower_zoning=lower,
            output_path=r"path\to\output\folder",
            cache_path=r"path\to\cache\folder\defaults\to\ydrive",
            method="OPTIONAL name of method"
        )
        ex.save_yaml(out_path / "example.yml")
