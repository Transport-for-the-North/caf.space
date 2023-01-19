import geopandas as gpd
import pandas as pd
from shapely.geometry import Polygon

lower_df = pd.DataFrame(data=range(1,17),columns=['lower_id'])

zone_1_df = pd.DataFrame(data=['A','B','C'],columns = ['zone_1_id'])

zone_2_df = pd.DataFrame(data=['W','X','Y','Z'],columns = ['zone_2_id'])

lower = gpd.GeoDataFrame(data=lower_df, geometry = [Polygon([(0,0),(0,2),(2,2),(2,0)]),
Polygon([(0,2),(0,4),(2,4),(2,2)]),
Polygon([(0,4),(0,6),(2,6),(2,4)]),
Polygon([(0,6),(0,8),(2,8),(2,6)]),
Polygon([(2,0),(2,2),(4,2),(4,0)]),
Polygon([(2,2),(2,4),(4,4),(4,2)]),
Polygon([(2,4),(2,6),(4,6),(4,4)]),
Polygon([(2,6),(2,8),(4,8),(4,6)]),
Polygon([(4,0),(4,2),(6,2),(6,0)]),
Polygon([(4,2),(4,4),(6,4),(6,2)]),
Polygon([(4,4),(4,6),(6,6),(6,4)]),
Polygon([(4,6),(4,8),(6,8),(6,6)]),
Polygon([(6,0),(6,2),(8,2),(8,0)]),
Polygon([(6,2),(6,4),(8,4),(8,2)]),
Polygon([(6,4),(6,6),(8,6),(8,4)]),
Polygon([(6,6),(6,8),(8,8),(8,6)])], crs = "EPSG:27700")

zone_1 = gpd.GeoDataFrame(data=zone_1_df, geometry = [Polygon([(0,3),(4,3),(4,8),(0,8)]),
Polygon([(4,3),(4,8),(8,8),(8,3)]),
Polygon([(0,0),(0,3),(8,3),(8,0)])], crs = "EPSG:27700")

zone_2 = gpd.GeoDataFrame(data=zone_2_df, geometry = [Polygon([(0,8),(0,4),(3,4),(3,8)]),
Polygon([(3,4),(3,8),(8,8),(8,4)]),
Polygon([(0,0),(0,4),(3,4),(3,0)]),
Polygon([(3,0),(3,4),(8,4),(8,0)])], crs = "EPSG:27700")

zone_1.to_file(r"C:\Users\IsaacScott\Projects\zone_1\zone_1.shp")
zone_2.to_file(r"C:\Users\IsaacScott\Projects\zone_2\zone_2.shp")
lower.to_file(r"C:\Users\IsaacScott\Projects\lower\lower.shp")
