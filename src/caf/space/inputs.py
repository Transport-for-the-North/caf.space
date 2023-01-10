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
import dataclasses
import os
from pathlib import Path
from typing import Any, Dict, Union
from caf.space import config_base
from pydantic import validator

# Third party imports

# Local imports

##### CONSTANTS #####
LOG = logging.getLogger(__name__)


class ShapefileInfo(config_base.BaseConfig):
    """Base class for storing information about a shapefile input."""

    name: str
    shapefile: Path
    id_col: str

    @validator('shapefile')
    def path_exists(cls, v):
        if os.path.isfile(v) == False:
            raise ValueError(f'The path provided for {v} does not exist.')
        return v


class ZoneSystemInfo(ShapefileInfo):
    """Zone system input data for `ZoneTranslationInputs`.

    Parameters
    ----------
    name : str
        Name of the zone system.
    shapefile : Path
        Path to the shapefile.
    id_col : str
        The name of the column in the shapefile you want to use as ID
    lower_translation : Path, optional
        Path to a lower level translation.
    """

    lower_translation: Path = None

    @validator('lower_translation')
    def lower_exists(cls, v):
        if v:
            if os.pathing.isfile(v) == False:
                raise ValueError(f'The lower translation path provided for {cls.name} does not exist.')
        return v


class LowerZoneSystemInfo(ShapefileInfo):
    """Lower level zone system input data for `ZoneTranslationInputs`.

    Parameters
    ----------
    name : str
        Name of the zone system.
    shapefile : Path
        Path to the shapefile.
    id_col : str
        The name of the column in the shapefile you want to use as ID
    weight_data : Path
        Path to weighting data.
    data_col: str
        Name of the column containing weighting data.
    weight_id_col: str
        The name of the column in the weighting data you want to use as ID
    """

    weight_data: Path
    data_col: str
    weight_id_col: str

    def __post_init__(self) -> None:
        super().__post_init__()
        self.weight_data = self.weight_data
    
    def _lower_to_higher(self) -> ZoneSystemInfo:
        return ZoneSystemInfo(name = self.name,
        shapefile = self.shapefile,
        id_col = self.id_col)
    
    @validator('weight_data')
    def weight_data_exists(cls, v):
        if os.path.isfile(v) == False:
            raise FileNotFoundError(f'The weight data path provided for {v} does not exist.')
        return v


class ZoningTranslationInputs(config_base.BaseConfig):
    """Class for storing and reading input parameters for `ZoneTranslation`.

    Attributes
    ----------
    zone_1 : ZoneSystemInfo
        Zone system 1 information
    zone_2 : ZoneSystemInfo
        Zone system 2 information
    output_path : Path
        Folder to save outputs to.
    method : str, optional
        Method for zone correpondence calculation.
    tolerance : float, default 0.98
        Tolerance for rounding and filtering.
    point_handling : bool, default True
        Should point handling be ran.
    point_tolerance : float, default 0.95
        Tolerance for determining point zones.
    point_zones_path : Path, optional
        Path to list of point zones.
    rounding : bool, default True
        Should rounding be done on outputs.
    filter_slithers : bool, True
        Should slithers be filtered out.
    lower_zoning : LowerZoneSystemInfo, optional
        Information about the lower zone system.
    run_date : str
        When the tool is being run
    """

    run_date: str = datetime.datetime.now().strftime("%d_%m_%y")
    zone_1: ZoneSystemInfo
    zone_2: ZoneSystemInfo
    lower_zoning: LowerZoneSystemInfo
    output_path: Path
    cache_path: Path
    method: str = None
    tolerance: float = 0.98
    point_handling: bool = True
    point_tolerance: float = 0.95
    point_zones_path: Path = None
    rounding: bool = True
    filter_slithers: bool = True

    def __post_init__(self) -> None:
        self.output_path.mkdir(exist_ok=True, parents=True)

    @staticmethod
    def _path_none(value: str) -> Union[Path, None]:
        """Convert string to Path, or None if empty."""
        if value is None or value.strip() == "":
            return None
        return Path(value)

def write_example(out_path: Path):
    zones = {}
    for i in range(1,3):
        zones[i] = ZoneSystemInfo(name = f"zone_{i}_name", shapefile = Path(f"path/to/shapefile_{i}"), id_col = f"id_col_for_zone_{i}", lower_translation= Path(f"path/to/lower_trans_{i}"))
    lower = LowerZoneSystemInfo(name = "lower_zone_name", shapefile = Path("path/to/lower/shapefile"), id_col = "id_col_for_lower_zone", weight_data=Path("path/to/lower/weight/data"), data_col="data_col_name", weight_id_col = "id_col_in_weighting_data")
    ex = ZoningTranslationInputs(zone_1=zones[1],
    zone_2 = zones[2],
    lower_zoning = lower,
    output_path = r"path\to\output\folder",
    cache_path= r"path\to\cache\folder\defaults\to\ydrive",
    method = "OPTIONAL name of method",
    point_zones_path = r"OPTIONAL\path\to\list\of\point\zones"
    )
    ex.save_yaml(out_path)