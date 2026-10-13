import pandas as pd
import geopandas as gpd

import caf.toolkit as ctk
from caf.space import zone_correspondence
from caf.space.inputs import (
    ZoneSystemInfo,
    TransZoneSystemInfo,
    LowerZoneSystemInfo,
    ZoningTranslationInputs,
)
from caf.space import ZoneTranslation

import localisation

# lsoa_shapefile =r"D:\normits\data\input\zoning\gb_lsoa2021ew_dz2011sg_area_types.shp"
oa_pop_shapefile = r"D:\normits\data\input\gb_oa2021ew_oa2011sg_pop=emp_scot.shp"
target_shapefile = r"D:\normits\data\zones\cumbria_localisation_zones\zoning_cumbria_local_OA.shp"

# lsoa_zs = ZoneSystemInfo(
#                 name="lsoa_2021",
#                 shapefile=lsoa_shapefile,
#                 id_col="lsoa21cd",
#             )

target_zs = ZoneSystemInfo(
    name = "cumbria_local",
    shapefile = target_shapefile,
    id_col = "zone_id"
)
data = target_zs.model_dump()
trans_target_zs = TransZoneSystemInfo(**data)

oa_pop = LowerZoneSystemInfo(
  name = "oa_pop",
  shapefile = oa_pop_shapefile,
  id_col = "OA21CD",
  weight_data = r"D:\normits\data\input\gb_oa2021ew_oa2011sg_pop=emp_scot.csv",
  data_col = "Pop",
  weight_id_col = "OA21CD",
  weight_data_year = "2021"
)

config = ZoningTranslationInputs(
    zone_1=trans_target_zs,
    lower_zoning=oa_pop,
    method="pop",
)
centroids = ZoneTranslation(config).weighted_centroids()
centroids.to_csv(r"D:\normits\data\zones\centroids\pop_weighted\cumbria_local_pop_weighted_centroids_v2.csv")
centroids_gdf = gpd.GeoDataFrame(
    centroids.reset_index(),
    geometry=gpd.points_from_xy(centroids["x"], centroids["y"]),
    crs="EPSG:27700",
)

# These centroids are weighted for OA population but for internal area that means they haven't been weighted because it's at the same level (OA)
# Insert the internal area from OA weighted centroids
oa_pop_centroids = gpd.read_file(r"D:\normits\localisation\create_costs\input\Output_Areas_(December_2021)_EW_Population_Weighted_Centroids_(V4)_\Output_Areas_(December_2021)_EW_Population_Weighted_Centroids_(V4)_.shp")
cumbria = gpd.read_file(target_shapefile)
cumbria_internal_ids = cumbria[cumbria["zone_syste"] == "OA"]  # 1744
oa_pop_centroids_cumbria = oa_pop_centroids.merge(
    cumbria_internal_ids.drop(columns="geometry"),
    left_on="OA21CD",
    right_on="zone_name",
    how="inner"
)
oa_pop_centroids_cumbria = oa_pop_centroids_cumbria[["zone_id", "geometry"]].set_index("zone_id")

centroids_gdf = centroids_gdf[["cumbria_lo", "geometry"]].set_index("cumbria_lo")
centroids_gdf.update(oa_pop_centroids_cumbria)
centroids_gdf.reset_index().to_file(r"D:\normits\data\zones\centroids\pop_weighted\cumbria_local_pop_weighted_centroids_v2.shp")
