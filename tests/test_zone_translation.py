"""
    Module for testing the zone_translation module
"""
from pathlib import Path
import pytest
import pandas as pd
import geopandas as gpd
from shapely.geometry import Polygon
# pylint: disable=import-error, wrong-import-position
from caf.space import zone_translation
from caf.space import inputs


# pylint: enable=import-error,wrong-import-position

@pytest.fixture(name="main_dir", scope="class")
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


@pytest.fixture(name="lower_zone", scope="class")
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


@pytest.fixture(name="zone_1_shape", scope="class")
def fixture_zone_1_shape(main_dir) -> Path:
    """
    zone system 1 for testing. Can be manipulated for different permutations
    Returns:
        Path: Temp path to gdf,  3 attributes, A, B and C. ID_COL = zone_1_id
    """
    zone_1_df = pd.DataFrame(
        data=["A", "B", "C"], columns=["zone_1_id"]
    )
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


@pytest.fixture(name="zone_2_shape", scope="class")
def fixture_zone_2_shape(main_dir) -> Path:
    """
    Zone system 2 for testing, can me manipulated for different permutations.
    Returns:
        Path: Temp path to gdf, 4 Attributes, W, X, Y, Z. ID_COL = zone_2_id
    """
    zone_2_df = pd.DataFrame(
        data=["W", "X", "Y", "Z"], columns=["zone_2_id"]
    )
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


@pytest.fixture(name="zone_2_moved", scope="class")
def fixture_zone_2_moved(zone_2_shape, main_dir) -> Path:
    """
    TODO add in testing for this fixture
    Parameters
    ----------
    zone_2_shape
    main_dir

    Returns
    -------

    """
    gdf = gpd.read_file(zone_2_shape)
    gdf.affine_transform(1, 0, 0, 1, 4, 4)
    file = main_dir / 'zone_2_altered.shp'
    gdf.to_file(file)
    return file


@pytest.fixture(name="lower_weighting", scope="class")
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

@pytest.fixture(name="paths", scope="class")
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

@pytest.fixture(name="weighted_config", scope="class")
def fixture_weighted_config(zone_1_shape: Path, zone_2_shape: Path, lower_zone: Path,
                            lower_weighting: Path, paths: dict
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
    zone_1 = inputs.ZoneSystemInfo(
        name="zone_1", shapefile=zone_1_shape, id_col="zone_1_id"
    )
    zone_2 = inputs.ZoneSystemInfo(
        name="zone_2", shapefile=zone_2_shape, id_col="zone_2_id"
    )
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
        output_path=paths['output'],
        cache_path=paths['cache'],
        method="test",
        tolerance=0.99,
        rounding=True
    )
    return params


@pytest.fixture(name="spatial_config", scope="class")
def fixture_spatial_config(zone_1_shape: Path, zone_2_shape: Path, paths: dict
                           ) -> inputs.ZoningTranslationInputs:
    """
    Config for a test case spatial translation.This config can be altered
    for other test cases.
    Parameters
    ----------
    All params are inherited from fixtures
    zone_1_shape
    zone_2_shape
    Returns
    -------
    A spatial translation config.
    """
    zone_1 = inputs.ZoneSystemInfo(
        name="zone_1", shapefile=zone_1_shape, id_col="zone_1_id"
    )
    zone_2 = inputs.ZoneSystemInfo(
        name="zone_2", shapefile=zone_2_shape, id_col="zone_2_id"
    )
    params = inputs.ZoningTranslationInputs(
        zone_1=zone_1,
        zone_2=zone_2,
        output_path=paths['output'],
        cache_path=paths['cache'],
        tolerance=0.99,
        rounding=True
    )
    return params


@pytest.fixture(name="dupe_shapes_config", scope="class")
def fixture_dupe_shapes_config(weighted_config: inputs.ZoningTranslationInputs
                               ) -> inputs.ZoningTranslationInputs:
    """
    A config file for testing translations with one zone the same as
    lower zoning.
    Parameters
    ----------
    weighted_config:
        weighted config to modify and use for a new translation.
    Returns
    -------
        A new config with lower zoning and zone 2 the same.
    """
    config = weighted_config.copy()
    config.zone_2 = weighted_config.lower_zoning
    config.zone_2.name = weighted_config.zone_2.name
    config.lower_zoning.name = weighted_config.zone_2.name
    return config


@pytest.fixture(name="expected_weighted", scope="class")
def fixture_expected_weighted() -> pd.DataFrame:
    """
    The expected output from a weighted translation using vanila inputs.
    Compare to output from weighted translation in testing
    Returns:
        pd.DataFrame: 4 columns of zone_1, zone_2, zone_1_to_zone_2,
        zone_2_to_zone_1
    """
    # fmt: off
    output = pd.DataFrame(
        {
            "zone_1_id": ["A", "A", "A", "A", "B", "B", "C", "C"],
            "zone_2_id": ["Z", "X", "Y", "W", "Z", "X", "Z", "Y"],
            "zone_1_to_zone_2": [
                0.059, 0.176, 0.235, 0.529, 0.263, 0.737, 0.500, 0.500,
            ],
            "zone_2_to_zone_1": [
                0.053, 0.176, 0.235, 1.000, 0.263, 0.824, 0.684, 0.765,
            ],
        }
    )
    # fmt: on
    return output


@pytest.fixture(name="expected_spatial", scope="class")
def fixture_expected_spatial() -> pd.DataFrame:
    """
    The expected output from a weighted translation using vanila inputs.
    Compare to output from weighted translation in testing
    Returns:
        pd.DataFrame: 4 columns of zone_1, zone_2, zone_1_to_zone_2,
        zone_2_to_zone_1
    """
    # fmt: off
    output = pd.DataFrame(
        {
            "zone_1_id": ["A", "A", "A", "A", "B", "B", "C", "C"],
            "zone_2_id": ["Z", "X", "Y", "W", "Z", "X", "Z", "Y"],
            "zone_1_to_zone_2": [
                0.05, 0.2, 0.15, 0.6, 0.2, 0.8, 0.625, 0.375,
            ],
            "zone_2_to_zone_1": [
                0.05, 0.2, 0.25, 1.000, 0.2, 0.8, 0.75, 0.75,
            ],
        }
    )
    # fmt: on
    return output


@pytest.fixture(name="weighted_trans", scope="class")
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
    trans = zone_translation.ZoneTranslation(weighted_config).zone_translation
    return trans


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
    trans = zone_translation.ZoneTranslation(spatial_config).zone_translation
    return trans


@pytest.fixture(name="dupe_trans", scope="class")
def fixture_dupe_trans(dupe_shapes_config):
    """
    A weighted zone translation with zone_2 and lower_zone the same.
    Parameters
    ----------
    dupe_shapes_config: see fixture
    Returns
    -------

    """
    trans = zone_translation.ZoneTranslation(
        dupe_shapes_config).zone_translation
    return trans


class TestZoneTranslation:
    """
    Class containing tests for the ZoneTranslation class
    """

    @pytest.mark.parametrize("translation_str",
                             ["spatial_trans", "weighted_trans", "dupe_trans"])
    @pytest.mark.parametrize("origin_zone", [1, 2])
    def test_sum_to_1(self, translation_str: str, origin_zone: int, request):
        """
        Test that translation totals from each zone sum to 1.
        Parameters
        ----------
        translation_str: Used to parametrize and test the different translations
        origin_zone: 1 or 2 for each test zone system/
        request: pytest inbuilt for parametrizing with fixtures

        Returns
        -------

        """
        dic = {1: 2, 2: 1}
        trans = request.getfixturevalue(translation_str)
        summed = trans.groupby(f"zone_{origin_zone}_id").sum()
        rounded = round(summed[f"zone_{origin_zone}_to_zone_{dic[origin_zone]}"], 5).astype("int")
        assert (rounded == 1).all()

    @pytest.mark.parametrize("translation_str",
                             ["spatial_trans", "weighted_trans", "dupe_trans"])
    @pytest.mark.parametrize("col", ["zone_1_to_zone_2", "zone_2_to_zone_1"])
    def test_positive(self, translation_str: str, col: str, request):
        """
        Tests that all translation values are positive
        Parameters
        ----------
        translation_str
        col: column being checked for positives
        request

        Returns
        -------

        """
        trans = request.getfixturevalue(translation_str)
        assert (trans[col] > 0).all()

    @pytest.mark.parametrize("number", [1, 2])
    def test_same_zones(self, spatial_trans, weighted_trans, number: int):
        """
        Test that the two id columns are identical in weighted and
        spatial translations.
        Args:
            spatial_trans (_type_): The spatial translation being checked
            weighted_trans (_type_): Weighted translation being checked
        """
        assert (sorted(spatial_trans[f"zone_{number}_id"]) == sorted(
            weighted_trans[f"zone_{number}_id"]))

    @pytest.mark.parametrize("expected_str,trans_str",
                             [("expected_spatial", "spatial_trans"),
                              ("expected_weighted", "weighted_trans")])
    def test_output(self, trans_str: str, expected_str: str, request):
        """
        Test to see if generated test case zone translations match expected values calculated
        independently.
        Parameters
        ----------
        All provided to request to be read from fixtures.
        trans_str
        expected_str
        request

        Returns
        -------

        """
        trans = request.getfixturevalue(trans_str)
        expected = request.getfixturevalue(expected_str)
        df_1 = trans.groupby(['zone_1_id', 'zone_2_id']).sum().round(3)
        df_1.sort_index(inplace=True)
        df_2 = expected.groupby(['zone_1_id', 'zone_2_id']).sum()
        df_2.sort_index(inplace=True)
        pd.testing.assert_frame_equal(df_1, df_2)
