import pytest
from caf.space import zone_correspondence, inputs
import pandas as pd

class Test_Read_Zone_Shapefiles:
    def __init__(self, crs_params:inputs.ZoningTranslationInputs):
        self.crs_params = crs_params

    def test_crs_warn(self):
        with pytest.warns(UserWarning, match = "Zone LSOA has no CRS, setting crs to EPSG:27700.")
            zone_correspondence._read_zone_shapefiles(self.crs_params)

    def test_crs_change(self):
        zones = zone_correspondence._read_zone_shapefiles(self.crs_params)
        assert zones['Major']['Zone'].crs is not None
        assert zones['Minor']['Zone'].crs is not None
    
class Test_Spatial_Zone_Correspondence:
    def __init__(self, test_zones, spatial_corr):
        self.test_zones = test_zones
        self.spatial_corr = spatial_corr
    
    def _test_format(self):
        corr = zone_correspondence._spatial_zone_correspondence(self.test_zones)
        pd.testing.assert_frame_equal(corr, self.spatial_corr)
    
class Test_Find_Slithers:
    def __init__(self, spatial_corr, zone_names)
    



    