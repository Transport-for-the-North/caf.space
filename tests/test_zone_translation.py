"""
    Module for testing the zone_translation module
"""
from math import sqrt
from pathlib import Path
import pytest
import pandas as pd
import geopandas as gpd
from copy import deepcopy

# pylint: disable=import-error, wrong-import-position
from caf.space import zone_translation
from caf.space import inputs


# pylint: enable=import-error,wrong-import-position


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
    file = main_dir / "zone_2_altered.shp"
    gdf.to_file(file)
    return file


@pytest.fixture(name="dupe_shapes_config", scope="class")
def fixture_dupe_shapes_config(
    weighted_config: inputs.ZoningTranslationInputs,
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
    config = deepcopy(weighted_config)
    config.zone_2.shapefile = weighted_config.lower_zoning.shapefile
    config.zone_2.id_col = weighted_config.lower_zoning.id_col
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


@pytest.fixture(name="expected_points", scope="class")
def fixture_expected_points() -> pd.DataFrame:
    # fmt: off
    output = pd.DataFrame(
        {
            "zone_1_id": ["A", "A", "A", "A", "B", "B", "B", "C", "C", "C"],
            "zone_2_id": ["W", "X", "Y", "Z", "X", "Z", "true_point_2", "Y", "Z", "pseudo_point"],
            "zone_1_to_zone_2": [
                0.529, 0.176, 0.235, 0.059, 0.526, 0.263, 0.211, 0.269, 0.5, 0.231
            ],
            "zone_2_to_zone_1": [
                1, 0.231, 0.364, 0.053, 0.769, 0.263, 1, 0.636, 0.684, 1
            ],
        }
    )
    # fmt: on
    return output


@pytest.fixture(name="expected_point_to_point", scope="class")
def fixture_expetced_point_to_point(expected_weighted) -> pd.DataFrame:
    df = deepcopy(expected_weighted)
    df["dist"] = 0
    df.loc[8] = ["true_point_1", "true_point_2", 1, 1, round(sqrt(2), 3)]
    df.set_index(["zone_1_id", "zone_2_id"], inplace=True)

    return df


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
    trans = zone_translation.ZoneTranslation(dupe_shapes_config).weighted_translation()
    return trans


class TestZoneTranslation:
    """
    Class containing tests for the ZoneTranslation class
    """

    @pytest.mark.parametrize(
        "translation_str",
        [
            "spatial_trans",
            "weighted_trans",
            "dupe_trans",
            "point_trans",
            "point_to_point_trans",
        ],
    )
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
        rounded = round(summed[f"zone_{origin_zone}_to_zone_{dic[origin_zone]}"], 5).astype(
            "int"
        )
        assert (rounded == 1).all()

    @pytest.mark.parametrize(
        "translation_str",
        [
            "spatial_trans",
            "weighted_trans",
            "dupe_trans",
            "point_trans",
            "point_to_point_trans",
        ],
    )
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
        assert sorted(spatial_trans[f"zone_{number}_id"]) == sorted(
            weighted_trans[f"zone_{number}_id"]
        )

    @pytest.mark.parametrize(
        "expected_str,trans_str",
        [
            ("expected_spatial", "spatial_trans"),
            ("expected_weighted", "weighted_trans"),
            ("expected_points", "point_trans"),
            ("expected_point_to_point", "point_to_point_trans"),
        ],
    )
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
        df_1 = trans.groupby(["zone_1_id", "zone_2_id"]).sum().round(3)
        df_1.sort_index(inplace=True)
        df_2 = expected.groupby(["zone_1_id", "zone_2_id"]).sum()
        df_2.sort_index(inplace=True)
        pd.testing.assert_frame_equal(df_1, df_2)
