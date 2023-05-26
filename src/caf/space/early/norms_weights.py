import pandas as pd
import geopandas as gpd
from shapely import Point
from typing import Union


def convert(weight: pd.DataFrame, lookup: pd.DataFrame):
    """
    Convert a weighting vector from one zone system to another.

    Currently hard coded as lsoa to norms, but can be made more flexible if
    needed.
    Args:
        weight (_type_): _description_
        lookup (_type_): _description_

    Returns:
        _type_: _description_
    """
    joined = weight.merge(lookup, how="right", on="lsoa_zone_id")
    joined["new_weight"] = joined["var"] * joined["lsoa_to_norms2018"]
    grouped = joined.groupby("norms2018_zone_id").sum()["new_weight"]
    return grouped


def weighted_centroid(
    lsoa_coords: pd.DataFrame, lsoa_weights: pd.DataFrame, lookup: pd.DataFrame, coord: str
):
    """
    Takes in a dataframe containing lsoa coords (x or y), weights for lsoa zones,
    a lookup of lsoa to norms, and the name of the coord ('x' or 'y'). This
    function could easily be made more flexible to work with any lower/upper zone
    systems.

    Parameters
    ----------
        lsoa_coords (pd.DataFrame): Dataframe of coordinates of lsoa centroids. Index should be zone code.
        lsoa_weights (pd.DataFrame): LSOA weight data. Index should be zone code.
        lookup (pd.DataFrame): A zone translation lookup, produced by caf.space or of the same format.
        coord (str): The coord in this run (usually 'x' or 'y', but must correspond to a column of lsoa_coords.)

    Returns
    -------
        pd.DataFrame:
    """
    joined = lookup.join(lsoa_weights, how="left").join(lsoa_coords, how="left")
    joined["weight"] = joined["var"] * joined["lsoa_to_norms2018"]
    joined["coord_weight"] = joined[coord] * joined["weight"]
    grouped = joined.groupby("norms2018_zone_id").sum()[["weight", "coord_weight"]]
    grouped[coord] = grouped["coord_weight"] / grouped["weight"]
    return grouped


def centroid_shapefile(
    centroids: Union[pd.DataFrame, gpd.GeoDataFrame],
    weight: pd.DataFrame,
    lookup: pd.DataFrame,
    crs: str,
):
    """
    Read in a centroids file, weight data and a lookup between zone systems and
    return a geodataframe of weighted centroids in a new zone system
    Args:
        centroids (Union): Can be a geodataframe(either polygon or point), or dataframe. A dataframe must contain
        'x' and 'y' coord columns, and in all cases the index must be lower zone id
        weight (pd.DataFrame): Weight data for the lower zone system the centroids or proviided for.
        lookup (pd.DataFrame): A lookup produced by caf.space or same format.
        crs (str): The CRS you want the centroids output with.

    Returns:
        gpd.GeoDataFrame: A centroid geodataframe.
    """
    if isinstance(centroids, gpd.GeoDataFrame):
        if (centroids.geom_type != Point).all():
            x = pd.DataFrame(centroids.centroid.x, columns=["x"])
            y = pd.DataFrame(centroids.centroid.y, columns=["y"])
    else:
        x = pd.DataFrame(centroids.x, columns=["x"])
        y = pd.DataFrame(centroids.y, columns=["y"])
    weighted_x = weighted_centroid(x, weight, lookup, "x")
    weighted_y = weighted_centroid(y, weight, lookup, "y")
    centroids = pd.concat([weighted_x, weighted_y], axis=1)[["x", "y"]]
    centroids["geometry"] = centroids.apply(lambda row: Point(row["x"], row["y"]), axis=1)
    gdf = gpd.GeoDataFrame(centroids, geometry="geometry", crs=crs)
    return gdf


# if __name__ == "__main__":
# emp_weight = pd.read_csv(r"I:\Data\Zone Translations\weighting vectors\lsoa_emp_2018_weighting.csv", index_col=0)
# pop_weight = pd.read_csv(r"I:\Data\Zone Translations\weighting vectors\lsoa_pop_2018_weighting.csv", index_col=0)
# lookup = pd.read_csv(r"I:\Data\Zone Translations\norms2018_to_lsoa_correspondence.csv", index_col=1)
# lsoa_shape = gpd.read_file(r"Y:\Data Strategy\GIS Shapefiles\UK LSOA and Data Zone Clipped 2011\uk_ew_lsoa_s_dz.shp")
# lsoa_shape.set_index('lsoa11cd', inplace=True)
# emp_cent_x = pd.DataFrame(data=lsoa_shape.centroid.x, columns=['x'])
# emp_cent_y = pd.DataFrame(data=lsoa_shape.centroid.y, columns=['y'])
# pop_centroids = pd.read_csv(r"C:\Users\Predator\Downloads\LSOA_Dec_2011_PWC_in_England_and_Wales_2022_1923591000694358693.csv", index_col=1)
# pop_cent_x = pop_centroids['x']
# pop_cent_y = pop_centroids['y']
# norm_emp_x = weighted_centroid(emp_cent_x, emp_weight, lookup, 'x')
# norm_emp_y = weighted_centroid(emp_cent_y, emp_weight, lookup, 'y')
# norm_pop_x = weighted_centroid(pop_cent_x, pop_weight, lookup, 'x')
# norm_pop_y = weighted_centroid(pop_cent_y, pop_weight, lookup, 'y')
# norms_emp_centroids = pd.concat([norm_emp_x, norm_emp_y], axis=1)[['x','y']]
# norms_pop_centroids = pd.concat([norm_pop_x, norm_pop_y], axis=1)[['x','y']]
# norms_emp_centroids['geometry'] = norms_emp_centroids.apply(lambda row: Point(row['x'], row['y']), axis=1)
# gdf_emp = gpd.GeoDataFrame(norms_emp_centroids, geometry='geometry', crs=lsoa_shape.crs)
# norms_pop_centroids['geometry'] = norms_pop_centroids.apply(lambda row: Point(row['x'], row['y']), axis=1)
# gdf = gpd.GeoDataFrame(norms_pop_centroids, geometry='geometry', crs=lsoa_shape.crs)
# print('debugging')
