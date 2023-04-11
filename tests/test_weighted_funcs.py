"""
Module for testing the weighted_funcs module
"""
from copy import deepcopy
import pytest
import pandas as pd
import geopandas as gpd
from caf.space import weighted_funcs, zone_correspondence


@pytest.fixture(name="zones", scope="session")
def fixture_zones(weighted_config):
    zones = zone_correspondence.read_zone_shapefiles(
        weighted_config.zone_1, weighted_config.zone_2
    )
    return zones


@pytest.fixture(name="weighted", scope="class")
def fixture_weighted(weighted_config):
    """
    Fixture returning a lower zone system with a weighting vector attached to
    it.
    """
    weighted = weighted_funcs._weighted_lower(weighted_config.lower_zoning)
    return weighted


@pytest.fixture(name="tiles", scope="class")
def fixture_tiles(weighted_config, zones):
    """
    Fixture returning tiles from the _create_tiles function
    """
    tiles = weighted_funcs._create_tiles(
        zones,
        weighted_config.zone_1,
        weighted_config.zone_2,
        weighted_config.lower_zoning,
        point_handling=False,
        point_tolerance=1,
    )
    return tiles


@pytest.fixture(name="overlaps", scope="class")
def fixture_overlaps(weighted_config, zones):
    """
    Fixture returning overlaps ond totals.
    """
    overlaps = weighted_funcs.get_weighted_translation(
        zones,
        weighted_config.zone_1,
        weighted_config.zone_2,
        weighted_config.lower_zoning,
        False,
        1,
    )
    return overlaps


@pytest.fixture(name="point_handling_no_points", scope="class")
def fixture_no_points(weighted_config):
    zone = gpd.read_file(weighted_config.zone_2.shapefile)
    lower = gpd.read_file(weighted_config.lower_zoning.shapefile)
    adjusted = weighted_funcs._point_handling(
        zone=zone,
        zone_id=weighted_config.zone_2.id_col,
        lower=lower,
        lower_id=weighted_config.lower_zoning.id_col,
        tolerance=weighted_config.point_tolerance,
    )

    return adjusted, zone


@pytest.fixture(name="points_handled", scope="class")
def fixture_points(point_zones, point_shapefile_2, weighted_config):
    polygons = gpd.read_file(point_zones)
    points = gpd.read_file(point_shapefile_2)
    zone = pd.concat([polygons, points])
    lower = gpd.read_file(weighted_config.lower_zoning.shapefile)
    adjusted = weighted_funcs._point_handling(
        zone=zone,
        zone_id=weighted_config.zone_2.id_col,
        lower=lower,
        lower_id=weighted_config.lower_zoning.id_col,
        tolerance=2,
    )
    return adjusted


class TestWeightedLower:
    """
    Class for testing the _weighted_lower function in weighted_funcs
    """

    def test_join(self, weighted):
        """
        Check that weighting is correct after join in the _weighted_lower
        """
        summed = weighted.weight.sum()
        assert summed == 310

    def test_area(self, weighted):
        """
        Check area is correct in weighted lower
        """
        assert (weighted.area == 4).all()

    def test_warning(self, weighted_config, main_dir):
        """
        Check the correct warning is raised from _weighted_lower
        """
        weighting = pd.read_csv(weighted_config.lower_zoning.weight_data)
        weighting.lower_id = range(16)
        weighting_path = main_dir / "mismatched_weighting.csv"
        weighting.to_csv(weighting_path)
        mismatched_config = deepcopy(weighted_config)
        mismatched_config.lower_zoning.weight_data = weighting_path
        with pytest.warns(
            UserWarning,
            match="1 zones do not match up between the lower zoning and weighting data.",
        ):
            weighted_funcs._weighted_lower(mismatched_config.lower_zoning)


class TestCreateTiles:
    """
    Class for testing the _create_tiles function in weighted_funcs
    """

    def test_weight(self, tiles):
        """
        Test the weight of generated tiles.
        """
        summed = tiles.weight.sum()
        assert summed == 310


class TestOverlapsTotals:
    """
    Class for testing the overlaps_and_totals function in weighted_funcs
    """

    def test_sums(self, overlaps):
        """
        Test the weight of overlaps output
        """
        overlap_sum = overlaps.weight_overlap.sum()
        assert overlap_sum == 310


class TestPointHandling:
    """
    Class for testing _point_handling
    """

    def test_no_points(self, point_handling_no_points):
        handled, zone = point_handling_no_points
        pd.testing.assert_frame_equal(handled, zone)

    @pytest.mark.parametrize("column", ["true_point_2", "pseudo_point"])
    def test_point(self, points_handled, column):
        handled = points_handled
        assert (handled.loc[handled["zone_2_id"] == column, "geometry"].area == 4).all()

    @pytest.mark.parametrize("column, area", [("Y", 8), ("X", 16)])
    def test_cutout(self, points_handled, column, area):
        handled = points_handled
        assert (handled.loc[handled["zone_2_id"] == column, "geometry"].area == area).all()
