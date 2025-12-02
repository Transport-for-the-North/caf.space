import caf.space as cs
from pathlib import Path

lower = cs.LowerZoneSystemInfo(
    name="pop",
    shapefile=Path(r"I:\Airport demand\Alok\shapefiles\pop_weighted.gpkg"),
    id_col="lsoa21cd",
    data_col="pop_weighted",
    weight_data_year=2021,
)

buffer = cs.TransZoneSystemInfo(
    name="buffer",
    shapefile=r"I:\Airport demand\Alok\shapefiles\buffere.gpkg",
    id_col="band_km",
)

gor = cs.TransZoneSystemInfo(
    name="gor", shapefile=r"I:\Airport demand\Alok\shapefiles\zone.gpkg", id_col="OBJECTID"
)

params = cs.ZoningTranslationInputs(
    zone_1=gor,
    zone_2=buffer,
    lower_zoning=lower,
    output_path=r"I:\Airport demand\Alok\shapefiles",
    cache_path=r"I:\Airport demand\Alok\shapefiles",
    method="gaussian_pop",
    tolerance=0.99,
    rounding=True,
)
x = cs.ZoneTranslation(params)
y = x.weighted_translation()
print("debugging")
