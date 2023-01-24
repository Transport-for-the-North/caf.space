import pytest
import pandas as pd
import geopandas as gpd
from shapely.geometry import Polygon
from caf.space import zone_translation
from caf.space import inputs

cols = ["zone_1_to_zone_2", "zone_2_to_zone_1"]

@pytest.fixture(scope="class")
def main_dir(tmp_path_factory):
    """
    Create temporary directory for files to be written to and from
    Args:
        tmp_path_fatory (_type_): _description_

    Returns:
        _type_: _description_
    """
    path = tmp_path_factory.mktemp("main")
    return path


@pytest.fixture(scope="class")
def lower_zone(main_dir) -> gpd.GeoDataFrame:
    """
    lower zone system for testing
    Returns:
        gpd.GeoDataFrame: 16 attributes, 1-17, ID_COL = lower_id
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


@pytest.fixture(scope="class")
def zone_1_shape(main_dir) -> gpd.GeoDataFrame:
    """
    zone system 1 for testing. Can be manipulated for different permutations
    Returns:
        gpd.GeoDataFrame: 3 attributes, A, B and C. ID_COL = zone_1_id
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


@pytest.fixture(scope="class")
def zone_2_shape(main_dir) -> gpd.GeoDataFrame:
    """
    Zone system 2 for testing, can me manipulated for different permutations.
    Returns:
        gpd.GeoDataFrame: 4 Attributes, W, X, Y, Z. ID_COL = zone_2_id
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


@pytest.fixture(scope="class")
def lower_weighting(main_dir) -> pd.DataFrame:
    """
    Weighting data to be joined to lower zoning system for testing
    Returns:
        pd.DataFrame: Weighting data in a column called 'weight', with
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


@pytest.fixture(scope="class")
def cache_path(main_dir):
    path = main_dir / "cache"
    return path


@pytest.fixture(scope="class")
def out_path(main_dir):
    path = main_dir / "output"
    return path


@pytest.fixture(scope="class")
def weighted_config(zone_1_shape, zone_2_shape, lower_zone, lower_weighting, out_path, cache_path):
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
        output_path=out_path,
        cache_path=cache_path,
        method="test",
        tolerance=0.99,
        rounding = True
    )
    return params

@pytest.fixture(scope="class")
def spatial_config(zone_1_shape, zone_2_shape, lower_zone, lower_weighting, out_path, cache_path):
    zone_1 = inputs.ZoneSystemInfo(
        name="zone_1", shapefile=zone_1_shape, id_col="zone_1_id"
    )
    zone_2 = inputs.ZoneSystemInfo(
        name="zone_2", shapefile=zone_2_shape, id_col="zone_2_id"
    )
    params = inputs.ZoningTranslationInputs(
        zone_1=zone_1,
        zone_2=zone_2,
        output_path=out_path,
        cache_path=cache_path,
        tolerance=0.99,
        rounding = True
    )
    return params

@pytest.fixture(scope="class")
def expected_output() -> pd.DataFrame:
    """
    The expected output from a weighted translation using vanila inputs.
    Compare to output from weighted translation in testing
    Returns:
        pd.DataFrame: 4 columns of zone_1, zone_2, zone_1_to_zone_2,
        zone_2_to_zone_1
    """
    output = pd.DataFrame(
        {
            "zone_1_id": ["A", "A", "A", "A", "B", "B", "C", "C"],
            "zone_2_id": ["Z", "X", "Y", "W", "Z", "X", "Z", "Y"],
            "zone_1_to_zone_2": [
                0.059,
                0.176,
                0.235,
                0.529,
                0.263,
                0.737,
                0.500,
                0.500,
            ],
            "zone_2_to_zone_1": [
                0.053,
                0.176,
                0.235,
                1.000,
                0.263,
                0.824,
                0.684,
                0.765,
            ],
        }
    )
    return output


@pytest.fixture(scope="class")
def weighted_trans(weighted_config):
    trans = zone_translation.ZoneTranslation(weighted_config).zone_translation
    return trans


@pytest.fixture(scope="class")
def spatial_trans(spatial_config):
    trans = zone_translation.ZoneTranslation(spatial_config).zone_translation
    return trans


class TestZoneTranslation:
    """
    Class containing tests for the ZoneTranslation class
    """

    @pytest.mark.parametrize("translation_str", ["spatial_trans", "weighted_trans"])
    @pytest.mark.parametrize("origin_zone", [1, 2])
    def test_sum_to_1(self, translation_str: str, origin_zone: int, request):
        """
        Test that totals sum to one.
        Args:
        """
        dic = {1: 2, 2: 1}
        trans = request.getfixturevalue(translation_str)
        summed = trans.groupby(f"zone_{origin_zone}_id").sum()
        assert (
            round(summed[f"zone_{origin_zone}_to_zone_{dic[origin_zone]}"], 5).astype("int") == 1
        ).all()

    @pytest.mark.parametrize("translation_str", ["spatial_trans", "weighted_trans"])
    @pytest.mark.parametrize("col", ["zone_1_to_zone_2", "zone_2_to_zone_1"])
    def test_positive(self, translation_str: str, col: str, request):
        """
        Test that all translation values are positive.
        Args:
        """
        trans = request.getfixturevalue(translation_str)
        assert (trans[col] > 0).all()

    @pytest.mark.parametrize("number", [1, 2])
    def test_same_zones(self, spatial_trans, weighted_trans, number: int):
        """
        Test that the two id columns are identical in weighted and
        spatial translations.
        Args:
            spatial_trans (_type_): _description_
            weighted_trans (_type_): _description_
        """
        assert (sorted(spatial_trans[f"zone_{number}_id"]) == sorted(weighted_trans[f"zone_{number}_id"]))
    
    def test_output(self, weighted_trans, expected_output):
        df_1 = weighted_trans.groupby(['zone_1_id', 'zone_2_id']).sum().round(3)
        df_1.sort_index(inplace=True)
        df_2 = expected_output.groupby(['zone_1_id', 'zone_2_id']).sum()
        df_2.sort_index(inplace=True)
        pd.testing.assert_frame_equal(df_1, df_2)

    # def test_lower_find(self):
    #     """
    #     Test that the _find_lower method works where it should.
    #     Args:
    #         spatial_trans (_type_): _description_
    #     """
    #     assert (
    #         spatial_trans.params.zone_1.lower_translation
    #         == "insert value"
    #     )

    # def test_lower_date(self):
    #     """
    #     Test that the find lower method will reject an existing translation
    #     created before either shapefile involved was last edited.
    #     """
    #     with pytest.warns(
    #         UserWarning,
    #         match="Shapefile(s) modified since last translation",
    #     ):
    #         zone_translation.ZoneTranslation(
    #             inputs.load_yaml("date_test.yml")
    #         )

    # def test_lower_meta(self):
    #     """
    #     Tests that missing or incorrect metadata attached to an existing
    #     translation returns the correct warning.
    #     """
    #     with pytest.warns(
    #         UserWarning,
    #         match="The lower translations folder in this cache has no "
    #         "metadata, or it is names incorrectly. The metadata "
    #         "should be called 'metadata.yml'.",
    #     ):
    #         zone_translation.ZoneTranslation(
    #             inputs.load_yaml("meta_test.yml")
    #         )
