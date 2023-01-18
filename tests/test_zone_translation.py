import pytest
import pandas as pd
from caf.space import zone_translation
from caf.space import inputs

cols = ['zone_1_to_zone_2','zone_2_to_zone_1']

@pytest.fixture():
def weighted_trans():
    input = inputs.ZoningTranslationInputs.load_yaml("weighted.yml")
    return zone_translation.ZoneTranslation(input)

@pytest.fixture():
def spatial_trans():
    input = inputs.ZoningTranslationInputs.load_yaml("spatial.yml")
    return zone_translation.ZoneTranslation(input)

def class TestZoneTranslation:
    def test_sum_to_1(self, spatial_trans, weighted_trans):
        spatial_1 = spatial_trans.groupby('zone_1').sum()
        spatial_2 = spatial_trans.groupby('zone_2').sum()
        weighted_1 = weighted_trans.groupby('zone_1').sum()
        weighted_2 = weighted_trans.groupby('zone_2').sum()
        assert (round(spatial_1['zone_1_to_zone_2'],5).astype('int')==1).all()
        assert (round(spatial_2['zone_2_to_zone_1'],5).astype('int')==1).all()
        assert (round(weighted_1['zone_1_to_zone_2'],5).astype('int')==1).all()
        assert (round(weighted_2['zone_2_to_zone_1'],5).astype('int')==1).all()

    def test_positive(self, spatial_trans, weighted_trans):
        for col in cols:
            assert (spatial_trans.col > 0).all()
            assert (weighted_trans.col > 0).all()

    def test_same_zones(self, spatial_trans, weighted_trans):
        assert (spatial_trans.zone_1 == weighted_trans.zone_1).all()
        assert (spatial_trans.zone_2 == weighted_trans.zone_2).all()

    def test_lower_find(self, spatial_trans):
        assert spatial_trans.params.zone_1.lower_translation == "insert value"

    def test_lower_date(self):
        with pytest.warns(UserWarning, match="Shapefile(s) modified since last translation"):
            zone_translation.ZoneTranslation(inputs.load_yaml('date_test.yml'))

    def test_lower_meta(self):
        with pytest.warns(UserWarning, match="The lower translations folder in this cache has no "
                    "metadata, or it is names incorrectly. The metadata "
                    "should be called 'metadata.yml'."):
            zone_translation.ZoneTranslation(inputs.load_yaml('meta_test.yml'))

    