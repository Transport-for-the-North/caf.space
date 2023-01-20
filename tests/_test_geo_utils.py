import pytest
from caf.space import geo_utils
import pandas as pd


class Test_Cols_In_Both:
    def __init__(self, right_in: pd.DataFrame, left_in: pd.DataFrame,
    cols: list, lower_cols_left: list, lower_cols_right: list):
        self.left_in = left_in
        self.right_in = right_in
        self.cols = cols
        self.lower_cols_left = lower_cols_left
        self.lower_cols_right = lower_cols_right
        self.lis, self.left, self.right,  = geo_utils._cols_in_both(left_in, right_in)

    def test_returns_lower(self):
        assert self.left.columns, self.right.columns == self.lower_cols_left, self.lower_cols_right

    def test_returns_matching(self):
        assert self.list == self.cols

class Test_Var_Appy:
    def __init__(self, corr_path: str, weight_path: str, area_corr: pd.DataFrame,
    missing_zones: int):
        self.corr_path = corr_path
        self.weight_path = weight_path
        self.area_corr = area_corr
        self.output_corr = geo_utils._var_apply(corr_path, weight_path,
        'var','zone_id','lower_name')
    
    def test_join(self):
        assert self.output_corr == self.area_corr

    def test_logging(self):
        with pytest.warns(UserWarning, match="3 zones are not intersected by target zones"):
            geo_utils._var_apply(self.corr_path, self.weight_path_missing, 'var','zone_id','lower_name'
            )

class Test_Zone_Split:
    def __init__(self):
        