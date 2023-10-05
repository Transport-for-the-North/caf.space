# -*- coding: utf-8 -*-
"""
Inputs module.

Module containing functionality for storing input parameters and reading config
file. Classes in this module inherit from the BaseConfig class, and are
ultimately used as input parameters for the ZoneTranslation class.
"""

##### IMPORTS #####
from __future__ import annotations

# Standard imports
# pylint: disable=import-error
import logging
import datetime
import dataclasses
import fiona
import os
from pathlib import Path
import pandas as pd
from typing import Optional
from pydantic import validator
from enum import Enum

# Third party imports
from caf.toolkit import BaseConfig
import argparse

# pylint: enable=import-error
# Local imports

##### CONSTANTS #####
LOG = logging.getLogger(__name__)
CACHE_PATH = "I:/Data/Zone Translations/cache"
MODES = ("spatial", "weighted", "GUI")


class ZoneSystemInfo(BaseConfig):
    """Base class for storing information about a shapefile input.

    Parameters
    ----------
    name : str
        The name of the zone system you are providing. This should
        be as simple as possible, so for and MSOA shapefile, name should
        simply be 'msoa'.
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
    def _path_exists(cls, v):
        """
        Validate a path exists.

        Raises
        ------
        ValueError: Informs user the path given is incorrect.

        Returns
        -------
        Unchanged path if no error is raised.
        """
        if os.path.isfile(v) is False:
            raise ValueError(
                f"The path provided for {v} does not exist."
                "If this path is on a network drive make sure you are connected"
            )
        return v

    @validator("id_col")
    def _id_col_in_file(cls, v, values):
        with fiona.collection(values["shapefile"]) as source:
            schema = source.schema
            if v not in schema["properties"].keys():
                raise ValueError(
                    f"The id_col provided, {v}, does not appear"
                    f" in the given shapefile. Please choose from:"
                    f"{schema['properties'].keys()}."
                )
        return v


class TransZoneSystemInfo(ZoneSystemInfo):
    """
    Input data for primary zone systems in translation.

    Inherits from ZoneSystemInfo.

    Parameters
    ----------
    point_shapefile: Optional[Path]
        A shapefile of point zones to be joined to the main shapefile. This
        shapefile must contain the same id_col as the main shapefile as the two
        will be concatenated on this column. If this is provided set 'point_handling'
        to True in the main config class or it will be effectively ignored.
    """

    point_shapefile: Optional[Path]


class LowerZoneSystemInfo(ZoneSystemInfo):
    """
    Lower level zone system input data for `ZoneTranslationInputs`.

    Inherits from ZoneSystemInfo.

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
    weight_data_year: int
        The year the weighting data comes from. This is used for writing files
        to the cache and is important for logging. If you don't know this you
        should consider whether your weighting data is appropriate.
    """

    weight_data: Path
    data_col: str
    weight_id_col: str
    weight_data_year: int

    def _lower_to_higher(self) -> TransZoneSystemInfo:
        return TransZoneSystemInfo(
            name=self.name,
            shapefile=self.shapefile,
            id_col=self.id_col,
            point_shapefile=None,
        )

    @validator("weight_data")
    def _weight_data_exists(cls, v):
        if os.path.isfile(v) is False:
            raise FileNotFoundError(f"The weight data path provided for {v} does not exist.")
        return v

    @validator("data_col", "weight_id_col")
    def _valid_data_col(cls, v, values):
        cols = pd.read_csv(values["weight_data"], nrows=1).columns
        if v not in cols:
            raise ValueError(f"The given col, {v}, does not appear in the weight data.")
        return v


@dataclasses.dataclass
class SpaceArguments:
    """Command Line arguments for running space."""

    config_path: Path
    mode: str
    out_path: Path

    @classmethod
    def parse(cls) -> SpaceArguments:
        """Parse command line argument."""
        parser = argparse.ArgumentParser(
            description=__doc__, formatter_class=argparse.ArgumentDefaultsHelpFormatter
        )
        parser.add_argument(
            "--mode",
            type=str,
            help="Mode to run translation in; spatial, weighted or GUI.",
            default="GUI",
            required=False,
        )
        parser.add_argument(
            "--config",
            type=Path,
            help="path to config file containing parameters",
            default=None,
            required=False,
        )
        parser.add_argument(
            "--out_path",
            type=Path,
            help="Path the translation will be saved in.",
            default=None,
            required=False,
        )

        parsed_args = parser.parse_args()
        return SpaceArguments(parsed_args.config, parsed_args.mode, parsed_args.out_path)

    def validate(self):
        """Raise error for invalid input."""
        if self.config_path:
            if not self.config_path.is_file():
                raise FileNotFoundError(f"config file doesn't exist: {self.config_path}")

        if self.out_path:
            if not self.out_path.is_dir():
                raise FileNotFoundError(f"{self.out_path} does not exist.")

        if self.mode not in MODES:
            raise ValueError(f"{self.mode} is not a valid mode for caf.space to run in.")


class ZoningTranslationInputs(BaseConfig):
    """
    Class for storing and reading input parameters for `ZoneTranslation`.

    Parameters
    ----------
    zone_1: TransZoneSystemInfo
        Zone system 1 information
    zone_2: TransZoneSystemInfo
        Zone system 2 information
    lower_zoning: LowerZoneSystemInfo
        Information about the lower zone system, used for performing
        weighted translations. This should be as small a zone system as
        possible relative to zone_1 and zone_2. For spatially weighted
        translations this isn't needed
    cache_path: Path
        File path to a cache of existing translations. This defaults to
        a location on a network drive, and it is best to keep it there,
        but it's more important for weighted translations.
    method: str, optional
        The name of the method used for weighting (e.g. pop or emp).
        This can be anything, but must be included as the tool checks if
        this parameter exists to decide whether to perform a spatial or
        weighted translation.
    sliver_tolerance: float, default 0.98
        This is a float less than 1, and defaults to 0.98. If
        filter_slivers (explained below) is chosen, tolerance controls
        how big or small the slithers need to be to be rounded away. For
        most users this can be kept as is.
    rounding: bool, default True
        Select whether or not zone totals will be rounded to 1 after the
        translation is performed. Recommended to keep as True.
    filter_slivers: bool, True
        Select whether very small overlaps between zones will be
        filtered out. This accounts for zone boundaries not aligning
        perfectly when they should between shapefiles, and the tolerance
        for this is controlled by the tolerance parameter. With this
        parameter set to false translations can be a bit messy.
    point_handling: bool, False
        Select whether point zones should be handled specially. If this is set
        to True a 'point_tolerance' parameter must also be provided. By default,
        this is set to 1 which would only class true points as point zones.
        This also only works for weighted translations.
    point_tolerance: Optional[float]
        The area of zone below which zones will be treated as point zones. Point
        zones have their geometry adjusted to the lower zone they sit within.
    run_date: str, datetime.datetime.now().strftime("%d_%m_%y")
        When the tool is being run. This is always generated
        automatically and shouldn't be included in the config yaml file.
    """

    zone_1: TransZoneSystemInfo
    zone_2: TransZoneSystemInfo
    lower_zoning: Optional[LowerZoneSystemInfo] = None
    cache_path: Path = Path(CACHE_PATH)
    method: Optional[str] = None
    sliver_tolerance: float = 0.98
    rounding: bool = True
    filter_slivers: bool = True
    point_handling: bool = False
    point_tolerance: float = 1
    run_date: str = datetime.datetime.now().strftime("%d_%m_%y")

    def __post_init__(self) -> None:
        """Make directories if they don't exist."""
        self.cache_path.mkdir(exist_ok=True, parents=True)

    @classmethod
    def write_example_space(cls, out_path: Path):
        """
        Write out an example config file.

        When creating a real config, any optional parameters not set should be
        removed entirely, and not just left blank to the right of the colon.

        Parameters
        ----------
        out_path: Path
            The folder the example will be saved in. The file will be
            called 'example.yml'.
        """
        zones = {}
        for i in range(1, 3):
            zones[i] = TransZoneSystemInfo.construct(
                name=f"zone_{i}_name",
                shapefile=Path(f"path/to/shapefile_{i}"),
                id_col=f"id_col_for_zone_{i}",
                point_shapefile=Path(f"path/to/point/shapefile"),
            )
        lower = LowerZoneSystemInfo.construct(
            name="lower_zone_name",
            shapefile=Path("path/to/lower/shapefile"),
            id_col="id_col_for_lower_zone",
            weight_data=Path("path/to/lower/weight/data"),
            data_col="data_col_name",
            weight_id_col="id_col_in_weighting_data",
            weight_data_year=2018,
        )
        ex = ZoningTranslationInputs.construct(
            zone_1=zones[1],
            zone_2=zones[2],
            lower_zoning=lower,
            cache_path=Path(r"path\to\cache\folder\defaults\to\ydrive"),
            method="OPTIONAL name of method",
        )
        if not isinstance(out_path, Path):
            out_path = Path(out_path)
        ex.save_yaml(out_path / "example.yml")
