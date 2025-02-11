import pandas as pd
import geopandas as gpd
from shapely import Point
from typing import Union
import caf.space as cs


def convert(weight: pd.DataFrame, lookup: pd.DataFrame):
    """"
    Summary
    -------
    Convert a weighting vector from one zone system to another.

    Currently hard coded as lsoa to norms, but can be made more flexible if
    needed.

    Parameters
    ----------

    weight (pd.DataFrame): Weighting vector
    lookup (pd.DataFrame): space generated lookup

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
    Parameters
    ----------

    centroids (Union): Can be a geodataframe(either polygon or point), or dataframe. A dataframe must contain
        'x' and 'y' coord columns, and in all cases the index must be lower zone id.
    weight (pd.DataFrame): Weight data for the lower zone system the centroids or proviided for.
    lookup (pd.DataFrame): A lookup produced by caf.space or same format.
    crs (str): The CRS you want the centroids output with.

    Returns
    -------

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

def oa_centroids(lower_shape: cs.TransZoneSystemInfo, low_to_high_lookup: pd.DataFrame, lower_weight_id: str, lower_weight: pd.DataFrame, upper_id: str):
    """
    Summary
    -------
    Create centroids based on oa weighting data.

    This function isn't that flexible now and assumes a lookup from caf.space among other things.

    Parameters
    ----------

    oa_shape (gpd.GeoDataFrame): An oa geodataframe.
    oa_lsoa_lookup (pd.DataFrame): lookup of oa to lsoa.
    oa_weight (pd.DataFrame): OA weight data

    Returns
    -------

    pd.DataFrame: A dataframe of lsoa centroids, with columns for 'x' and 'y'.
    """
    lower_gdf = gpd.read_file(lower_shape.shapefile)
    join_1 = lower_gdf.merge(low_to_high_lookup, left_on=lower_shape.id_col, right_on=f"{lower_shape.name}_id")
    cent = join_1.merge(lower_weight, left_on=lower_shape.id_col, right_on=lower_weight_id)[['val', upper_id, 'geometry']]
    cent['x_weight'] = cent.centroid.x * cent['val']
    cent['y_weight'] = cent.centroid.y * cent['val']
    grouped = cent.groupby(upper_id)[['val', 'x_weight', 'y_weight']].sum()
    grouped['x'] = grouped['x_weight'] / grouped['val']
    grouped['y'] = grouped['y_weight'] / grouped['val']
    return grouped[['x','y']]

if __name__ == "__main__":
    emp_weight = pd.read_csv(r"I:\Data\Zone Translations\weighting vectors\oa_emp_2021_weighting.csv", index_col=0)
    pop_weight = pd.read_csv(r"I:\Data\Zone Translations\weighting vectors\oa_pop_2021_weighting.csv", index_col=0)
    hh_weight = pd.read_csv(r"I:\Data\Zone Translations\weighting vectors\oa_hh_2021_weighting.csv", index_col=0)
    oa_shape = gpd.read_file(r"Y:\Data Strategy\GIS Shapefiles\Output_Areas\OA_2021\OA_2021_EW_BFC_V8.shp")
    oa_conf = cs.TransZoneSystemInfo(name="oa_21", shapefile=r"Y:\Data Strategy\GIS Shapefiles\Output_Areas\OA_2021\OA_2021_EW_BFC_V8.shp", id_col="OA21CD")
    ##### Above here stays the same #####
    ##### Put confs for zone systems here

    normits_conf = cs.TransZoneSystemInfo(name='normits_v3.3', shapefile=r"Y:\Data Strategy\GIS Shapefiles\NorMITs 2024 zone system\NorMITs zone\v3.3\NorMITs_zoning_v3.3.shp",
                                          id_col="normits_id")

    confs = [normits_conf]

    for conf in confs:
        trans_conf = cs.ZoningTranslationInputs(zone_1=oa_conf, zone_2=conf)

        trans = cs.ZoneTranslation(trans_conf).spatial_translation()

        pop_cent = oa_centroids(oa_conf, oa_normits, 'oa21cd', pop_weight, f'{conf.zone_2.name}_id')
        emp_cent = oa_centroids(oa_conf, oa_normits, 'oa21cd', emp_weight, f'{conf.zone_2.name}_id')
        hh_cent = oa_centroids(oa_conf, oa_normits, 'oa21cd', hh_weight, f'{conf.zone_2.name}_id')











    lookup = pd.read_csv(r"I:\Data\Zone Translations\norms2018_to_lsoa_correspondence.csv", index_col=1)
    lsoa_shape = gpd.read_file(r"Y:\Data Strategy\GIS Shapefiles\LSOA & Scottish Data Zones 2011\LSOA & Scottish Data Zones 2011.shp")
    lsoa_shape.set_index('LSOA11CD', inplace=True)
    spat_cent_x = pd.DataFrame(data=lsoa_shape.centroid.x, columns=['x'])
    spat_cent_y = pd.DataFrame(data=lsoa_shape.centroid.y, columns=['y'])
    pop_centroids = pd.read_csv(r"C:\Users\Predator\Downloads\LSOA_Dec_2011_PWC_in_England_and_Wales_2022_1923591000694358693.csv", index_col=1)
    pop_cent_x = pd.concat([spat_cent_x[spat_cent_x.index.str.startswith('S')], pop_centroids])['x']
    pop_cent_y = pd.concat([spat_cent_y[spat_cent_y.index.str.startswith('S')], pop_centroids])['y']
    emp_centroids = pd.read_csv(r"I:\Transfer\IS\lsoa_emp_weighted_centroids.csv", index_col=0)
    emp_cent_x = pd.concat([spat_cent_x[spat_cent_x.index.str.startswith('S')], emp_centroids])[
        'x']
    emp_cent_y = pd.concat([spat_cent_y[spat_cent_y.index.str.startswith('S')], emp_centroids])[
        'y']
    norm_emp_x = weighted_centroid(emp_cent_x, emp_weight, lookup, 'x')
    norm_emp_y = weighted_centroid(emp_cent_y, emp_weight, lookup, 'y')
    norm_pop_x = weighted_centroid(pop_cent_x, pop_weight, lookup, 'x')
    norm_pop_y = weighted_centroid(pop_cent_y, pop_weight, lookup, 'y')
    norms_emp_centroids = pd.concat([norm_emp_x, norm_emp_y], axis=1)[['x','y']]
    norms_pop_centroids = pd.concat([norm_pop_x, norm_pop_y], axis=1)[['x','y']]
    norms_emp_centroids['geometry'] = norms_emp_centroids.apply(lambda row: Point(row['x'], row['y']), axis=1)
    gdf_emp = gpd.GeoDataFrame(norms_emp_centroids, geometry='geometry', crs=lsoa_shape.crs)
    norms_pop_centroids['geometry'] = norms_pop_centroids.apply(lambda row: Point(row['x'], row['y']), axis=1)
    gdf_pop = gpd.GeoDataFrame(norms_pop_centroids, geometry='geometry', crs=lsoa_shape.crs)
    gdf_emp.to_file(r"E:\misc_scripts\outputs\emp_centroids_improved")
    gdf_pop.to_file(r"E:\misc_scripts\outputs\norms_pop_centroids_fixed")


    oa_emp_weight = pd.read_csv(r"I:\Data\Zone Translations\weighting vectors\oa_emp_2011_weighting.csv")
    oa_shape = gpd.read_file(r"Y:\Data Strategy\GIS Shapefiles\oa_2011\infuse_oa_lyr_2011.shp")
    oa_lsoa_lookup =pd.read_csv(r"I:\Data\Zone Translations\cache\lsoa2011_oa11\lsoa2011_to_oa11_spatial.csv")
    output = oa_centroids(oa_shape, oa_lsoa_lookup, oa_emp_weight)
    output.to_csv('path/to/file')


    print('debugging')
