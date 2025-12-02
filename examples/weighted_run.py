"""
Example of weighted translation run
===================================
"""

import caf.space as cs
from pathlib import Path

lower = cs.LowerZoneSystemInfo(
    name="pop",
    shapefile=Path("dir/pop_weighted.gpkg"),
    id_col="lsoa21cd",
    data_col="pop_weighted",
    weight_data_year=2021,
)

zone_1 = cs.TransZoneSystemInfo(
    name="zone_1",
    shapefile=r"dir/zone_1.gpkg",
    id_col="id",
)

zone_2 = cs.TransZoneSystemInfo(
    name="zone_2",
    shapefile=r"dir/zone_2.gpkg",
    id_col="id",
)

params = cs.ZoningTranslationInputs(
    zone_1=zone_1,
    zone_2=zone_2,
    lower_zoning=lower,
    method="pop",
    rounding=True,
)
trans_class = cs.ZoneTranslation(params)
trans_df = trans.weighted_translation()
