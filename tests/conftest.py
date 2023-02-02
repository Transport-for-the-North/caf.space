# -*- coding: utf-8 -*-
"""
Created on: 27/01/2023
Updated on:

Original author: Isaac Scott
Last update made by:
Other updates made by:

File purpose:

"""
# Built-Ins
from pathlib import Path

# Third Party
import pytest

# pylint: disable=import-error
from shapely.geometry import Polygon
import geopandas as gpd

# pylint: enable=import-error
import pandas as pd

# Local Imports
# pylint: disable=import-error,wrong-import-position
# Local imports here
from caf.space import inputs, zone_translation

# pylint: enable=import-error,wrong-import-position

# # # CONSTANTS # # #


@pytest.fixture(name="main_dir", scope="session")
def fixture_main_dir(tmp_path_factory) -> Path:
    """
    Parameters
    ----------
    tmp_path_factory

    Returns
    -------
    Path: file path used for all saving and loading of files within the tests
    """
    path = tmp_path_factory.mktemp("main")
    return path


@pytest.fixture(name="lower_zone", scope="session")
def fixture_lower_zone(main_dir) -> Path:
    """
    lower zone system for testing
    Returns:
        Path: Temp path to gdf, 16 attributes, 1-17, ID_COL = lower_id
    """
    lower_df = pd.DataFrame(data=range(1, 17), columns=["lower_id"])
    lower = gpd.GeoDataFrame(
        data=lower_df,
        geometry=[
            Polygon([(0, 0), (0, 2), (2, 2), (2, 0)]),
            Polygon([(0, 2), (0, 4), (2, 4), (2, 2)]),
            Polygon([(0, 4), (0, 6), (2, 6), (2, 4)]),
            Polygon([(0, 6), (0, 8), (2, 8), (2, 6)]),
            Polygon([(2, 0), (2, 2), (4, 2), (4, 0)]),
            Polygon([(2, 2), (2, 4), (4, 4), (4, 2)]),
            Polygon([(2, 4), (2, 6), (4, 6), (4, 4)]),
            Polygon([(2, 6), (2, 8), (4, 8), (4, 6)]),
            Polygon([(4, 0), (4, 2), (6, 2), (6, 0)]),
            Polygon([(4, 2), (4, 4), (6, 4), (6, 2)]),
            Polygon([(4, 4), (4, 6), (6, 6), (6, 4)]),
            Polygon([(4, 6), (4, 8), (6, 8), (6, 6)]),
            Polygon([(6, 0), (6, 2), (8, 2), (8, 0)]),
            Polygon([(6, 2), (6, 4), (8, 4), (8, 2)]),
            Polygon([(6, 4), (6, 6), (8, 6), (8, 4)]),
            Polygon([(6, 6), (6, 8), (8, 8), (8, 6)]),
        ],
        crs="EPSG:27700",
    )
    lower.geometry = lower.geometry.rotate(270, origin=[4, 4])
    file = main_dir / "lower_zone.shp"
    lower.to_file(file)
    return file


@pytest.fixture(name="zone_1_shape", scope="session")
def fixture_zone_1_shape(main_dir) -> Path:
    """
    zone system 1 for testing. Can be manipulated for different permutations
    Returns:
        Path: Temp path to gdf,  3 attributes, A, B and C. ID_COL = zone_1_id
    """
    zone_1_df = pd.DataFrame(data=["A", "B", "C"], columns=["zone_1_id"])
    zone_1 = gpd.GeoDataFrame(
        data=zone_1_df,
        geometry=[
            Polygon([(0, 3), (4, 3), (4, 8), (0, 8)]),
            Polygon([(4, 3), (4, 8), (8, 8), (8, 3)]),
            Polygon([(0, 0), (0, 3), (8, 3), (8, 0)]),
        ],
        crs="EPSG:27700",
    )
    file = main_dir / "zone_1_zone.shp"
    zone_1.to_file(file)
    return file


@pytest.fixture(name="zone_2_shape", scope="session")
def fixture_zone_2_shape(main_dir) -> Path:
    """
    Zone system 2 for testing, can me manipulated for different permutations.
    Returns:
        Path: Temp path to gdf, 4 Attributes, W, X, Y, Z. ID_COL = zone_2_id
    """
    zone_2_df = pd.DataFrame(data=["W", "X", "Y", "Z"], columns=["zone_2_id"])
    zone_2 = gpd.GeoDataFrame(
        data=zone_2_df,
        geometry=[
            Polygon([(0, 8), (0, 4), (3, 4), (3, 8)]),
            Polygon([(3, 4), (3, 8), (8, 8), (8, 4)]),
            Polygon([(0, 0), (0, 4), (3, 4), (3, 0)]),
            Polygon([(3, 0), (3, 4), (8, 4), (8, 0)]),
        ],
        crs="EPSG:27700",
    )
    file = main_dir / "zone_2.shp"
    zone_2.to_file(main_dir / "zone_2.shp")
    return file


@pytest.fixture(name="lower_weighting", scope="session")
def fixture_lower_weighting(main_dir) -> Path:
    """
    Weighting data to be joined to lower zoning system for testing
    Returns:
        Path: Temp path to weighting data in a column called 'weight', with
        an index called 'lower_id', matching lower_id in lower shape.
    """
    weighting = pd.DataFrame(
        data=[
            10,
            20,
            20,
            30,
            20,
            10,
            10,
            10,
            30,
            20,
            20,
            30,
            30,
            30,
            10,
            10,
        ],
        index=range(1, 17),
        columns=["weight"],
    )
    weighting.index.name = "lower_id"
    file = main_dir / "weighting.csv"
    weighting.to_csv(main_dir / "weighting.csv")
    return file


@pytest.fixture(name="paths", scope="session")
def fixture_paths(main_dir) -> dict[str, Path]:
    """
    fixture storing paths for configs
    Parameters
    ----------
    main_dir

    Returns
    -------

    """
    output_path = main_dir / "output"
    cache_path = main_dir / "cache"
    paths = {"output": output_path, "cache": cache_path}
    return paths


@pytest.fixture(name="spatial_config", scope="class")
def fixture_spatial_config(
    zone_1_shape: Path, zone_2_shape: Path, paths: dict
) -> inputs.ZoningTranslationInputs:
    """
    Config for a test case spatial translation.This config can be altered
    for other test cases.
    Parameters
    ----------
    All params are inherited from fixtures
    zone_1_shape
    zone_2_shape
    paths
    Returns
    -------
    A spatial translation config.
    """
    zone_1 = inputs.ZoneSystemInfo(name="zone_1", shapefile=zone_1_shape, id_col="zone_1_id")
    zone_2 = inputs.ZoneSystemInfo(name="zone_2", shapefile=zone_2_shape, id_col="zone_2_id")
    params = inputs.ZoningTranslationInputs(
        zone_1=zone_1,
        zone_2=zone_2,
        output_path=paths["output"],
        cache_path=paths["cache"],
        tolerance=0.99,
        rounding=True,
    )
    return params


@pytest.fixture(name="spatial_trans", scope="class")
def fixture_spatial_trans(spatial_config) -> pd.DataFrame:
    """
    Creates a spatial zone translation to be used in tests.
    Parameters
    ----------
    spatial_config: inherited from fixture

    Returns
    -------
    A complete spatial zone translation stored in a dataframe

    """
    trans = zone_translation.ZoneTranslation(spatial_config).spatial_translation()
    return trans


@pytest.fixture(name="weighted_config", scope="session")
def fixture_weighted_config(
    zone_1_shape: Path,
    zone_2_shape: Path,
    lower_zone: Path,
    lower_weighting: Path,
    paths: dict,
) -> inputs.ZoningTranslationInputs:
    """
    The config for a test weighted translation. This config is used as
    a base for other weighted test cases.
    Parameters
    ----------
    Params are all inherited from fixtures.
    zone_1_shape
    zone_2_shape
    lower_zone
    lower_weighting
    paths

    Returns
    -------
    An input config for running a basic weighted zone translation.
    """
    zone_1 = inputs.ZoneSystemInfo(name="zone_1", shapefile=zone_1_shape, id_col="zone_1_id")
    zone_2 = inputs.ZoneSystemInfo(name="zone_2", shapefile=zone_2_shape, id_col="zone_2_id")
    lower = inputs.LowerZoneSystemInfo(
        name="lower_zone",
        shapefile=lower_zone,
        id_col="lower_id",
        weight_data=lower_weighting,
        data_col="weight",
        weight_id_col="lower_id",
    )
    params = inputs.ZoningTranslationInputs(
        zone_1=zone_1,
        zone_2=zone_2,
        lower_zoning=lower,
        output_path=paths["output"],
        cache_path=paths["cache"],
        method="test",
        tolerance=0.99,
        rounding=True,
    )
    return params


@pytest.fixture(name="weighted_trans", scope="session")
def fixture_weighted_trans(weighted_config) -> pd.DataFrame:
    """
    Creates a weighted zone translation to be used in tests.
    Parameters
    ----------
    weighted_config: inherited from fixture

    Returns
    -------
    A complete weighted zone translation stored in a dataframe
    """
    trans = zone_translation.ZoneTranslation(weighted_config).weighted_translation()
    return trans


# # # CLASSES # # #

# # # FUNCTIONS # # #
