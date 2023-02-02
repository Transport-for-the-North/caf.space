"""
Module for testing the weighted_funcs module
"""
from copy import deepcopy
import pytest
import pandas as pd
from caf.space import weighted_funcs


@pytest.fixture(name="weighted", scope="class")
def fixture_weighted(weighted_config):
    """
    Fixture returning a lower zone system with a weighting vector attached to
    it.
    """
    weighted = weighted_funcs._weighted_lower(weighted_config)
    return weighted


@pytest.fixture(name="tiles", scope="class")
def fixture_tiles(weighted_config):
    """
    Fixture returning tiles from the _create_tiles function
    """
    tiles = weighted_funcs._create_tiles(weighted_config)
    return tiles


@pytest.fixture(name="overlaps", scope="class")
def fixture_overlaps(weighted_config):
    """
    Fixture returning overlaps ond totals.
    """
    overlaps = weighted_funcs.overlaps_and_totals(weighted_config.zone_1, weighted_config.zone_2, weighted_config.lower_zoning)
    return overlaps


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
            weighted_funcs._weighted_lower(mismatched_config)


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


# class Test_Cols_In_Both:
#     def __init__(self, right_in: pd.DataFrame, left_in: pd.DataFrame,
#     cols: list, lower_cols_left: list, lower_cols_right: list):
#         self.left_in = left_in
#         self.right_in = right_in
#         self.cols = cols
#         self.lower_cols_left = lower_cols_left
#         self.lower_cols_right = lower_cols_right
#         self.lis, self.left, self.right,  = weighted_funcs._cols_in_both(left_in, right_in)
#
#     def test_returns_lower(self):
#         assert self.left.columns, self.right.columns == self.lower_cols_left, self.lower_cols_right
#
#     def test_returns_matching(self):
#         assert self.list == self.cols
#
# class Test_Var_Appy:
#     def __init__(self, corr_path: str, weight_path: str, area_corr: pd.DataFrame,
#     missing_zones: int):
#         self.corr_path = corr_path
#         self.weight_path = weight_path
#         self.area_corr = area_corr
#         self.output_corr = weighted_funcs._var_apply(corr_path, weight_path,
#         'var','zone_id','lower_name')
#
#     def test_join(self):
#         assert self.output_corr == self.area_corr
#
#     def test_logging(self):
#         with pytest.warns(UserWarning, match="3 zones are not intersected by target zones"):
#             weighted_funcs._var_apply(self.corr_path, self.weight_path_missing, 'var','zone_id','lower_name'
#             )
#
# class Test_Zone_Split:
#     def __init__(self):
#
