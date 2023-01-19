import pytest
import pandas as pd
import geopandas as gpd
from shapely.geometry import Polygon
from caf.space import zone_translation
from caf.space import inputs

cols = ["zone_1_to_zone_2", "zone_2_to_zone_1"]


@pytest.fixture()
def lower_zone() -> gpd.GeoDataFrame:
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
    lower.geometry = lower.geometry.rotate(270,origin=[4,4])
    return lower


@pytest.fixture()
def zone_1_shape() -> gpd.GeoDataFrame:
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
    return zone_1

@pytest.fixture()
def zone_2_shape() -> gpd.GeoDataFrame:
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
    return zone_2


@pytest.fixture()
def lower_weighting() -> pd.DataFrame:
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
    return weighting

@pytest.fixture()
def expected_output() -> pd.DataFrame:
    """
    The expected output from a weighted translation using vanila inputs.
    Compare to output from weighted translation in testing
    Returns:
        pd.DataFrame: 4 columns of zone_1, zone_2, zone_1_to_zone_2,
        zone_2_to_zone_1
    """
    output = pd.DataFrame({'zone_1':['A','A','A','A','B','B','C','C'],
    'zone_2':['Z','X','Y','W','Z','X','Z','Y'],
    'zone_1_to_zone_2':[0.014,0.187,0.214,0.585,0.383,0.617,0.506,0.494],
    'zone_2_to_zone_1':[0.020,0.303,0.361,1.000,0.401,0.697,0.579,0.639]})
    return output

# @pytest.fixture()
# def weighted_trans():
#     config = inputs.ZoningTranslationInputs.load_yaml("weighted.yml")
#     weighted_trans = zone_translation.ZoneTranslation(config)
#     return weighted_trans


# @pytest.fixture()
# def spatial_trans():
#     config = inputs.ZoningTranslationInputs.load_yaml("spatial.yml")
#     spatial_trans = zone_translation.ZoneTranslation(config)
#     return spatial_trans


class TestZoneTranslation:
    """
    Class containing tests for the ZoneTranslation class
    """

    def test_sum_to_1(self, spatial_trans, weighted_trans):
        """
        Test that totals sum to one.
        Args:
            spatial_trans (_type_): _description_
            weighted_trans (_type_): _description_
        """
        spatial_1 = spatial_trans.groupby("zone_1").sum()
        spatial_2 = spatial_trans.groupby("zone_2").sum()
        weighted_1 = weighted_trans.groupby("zone_1").sum()
        weighted_2 = weighted_trans.groupby("zone_2").sum()
        assert (
            round(spatial_1["zone_1_to_zone_2"], 5).astype("int") == 1
        ).all()
        assert (
            round(spatial_2["zone_2_to_zone_1"], 5).astype("int") == 1
        ).all()
        assert (
            round(weighted_1["zone_1_to_zone_2"], 5).astype("int") == 1
        ).all()
        assert (
            round(weighted_2["zone_2_to_zone_1"], 5).astype("int") == 1
        ).all()

    def test_positive(self, spatial_trans, weighted_trans):
        """
        Test that all translation values are positive.
        Args:
            spatial_trans (_type_): _description_
            weighted_trans (_type_): _description_
        """
        for col in cols:
            assert (spatial_trans[col] > 0).all()
            assert (weighted_trans[col] > 0).all()

    def test_same_zones(self, spatial_trans, weighted_trans):
        """
        Test that the two id columns are identical in weighted and
        spatial translations.
        Args:
            spatial_trans (_type_): _description_
            weighted_trans (_type_): _description_
        """
        assert (spatial_trans.zone_1 == weighted_trans.zone_1).all()
        assert (spatial_trans.zone_2 == weighted_trans.zone_2).all()

    def test_lower_find(self, spatial_trans):
        """
        Test that the _find_lower method works where it should.
        Args:
            spatial_trans (_type_): _description_
        """
        assert (
            spatial_trans.params.zone_1.lower_translation
            == "insert value"
        )

    def test_lower_date(self):
        """
        Test that the find lower method will reject an existing translation
        created before either shapefile involved was last edited.
        """
        with pytest.warns(
            UserWarning,
            match="Shapefile(s) modified since last translation",
        ):
            zone_translation.ZoneTranslation(
                inputs.load_yaml("date_test.yml")
            )

    def test_lower_meta(self):
        """
        Tests that missing or incorrect metadata attached to an existing
        translation returns the correct warning.
        """
        with pytest.warns(
            UserWarning,
            match="The lower translations folder in this cache has no "
            "metadata, or it is names incorrectly. The metadata "
            "should be called 'metadata.yml'.",
        ):
            zone_translation.ZoneTranslation(
                inputs.load_yaml("meta_test.yml")
            )
