"""Module for metadata. None of this is currently used but hasn't been deleted."""
from __future__ import annotations
import datetime
from pathlib import Path


# Third party imports
# pylint: disable=no-name-in-module
from caf.toolkit import BaseConfig

# pylint: enable=no-name-in-module


class WeightMetadata(BaseConfig):
    """
    Class for storing metadata about weighting date.

    This is not currently used but could be part of a GUI.
    """

    data_col: str
    id_col: str
    year: int
    type: str


class ShapefileMetadata(BaseConfig):
    """
    Store shapefile metadata.

    Class for creating, storing and loading metadata relating to shapefiles
    used for translations. This is not currently used but could be part of a
    GUI.
    """

    name: str
    path: Path
    id_col: str
    weighting_data: WeightMetadata | None = None


class SpatialTransLog(BaseConfig):
    """
    Output log of a spatial translation.

    Mainly used for the lower translations used in weighted translations.

    Parameters
    ----------
    zone_shapefile: Path to the primary zone shapefile used in the
    translation this metadata corresponds to.
    lower_shapefile: Path to the lower shapefile used in the translation
    this metadata corresponds to.
    date: The date this translation took place.
    """

    zone_shapefile: Path
    lower_shapefile: Path
    date: datetime.datetime


class LowerMetadata(BaseConfig):
    """
    Store metadata for all translations between two zones.

    Every time a translation is run between two zones info about that
    translation should be added to an instance of this class saved as
    'metadata.yml'.

    Parameters
    ----------
    translations: A list of SpatialTransLog classes for all translations
    for a given pair of zone systems.
    """

    translations: list[SpatialTransLog]
