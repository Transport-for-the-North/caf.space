import pandas as pd
import caf.space as cs


def weighted_centroids(lower_shape: cs.LowerZoneSystemInfo,
                       upper_shape: cs.TransZoneSystemInfo):
    """
    Summary
    -------
    Create centroids based on weighting data.

    Parameters
    ----------

    lower_shape: cs.LowerZoneSystemInfo
        Info on the lower shape used for weighting.
    upper_shape: cs.TransZoneSystemInfo
        Info on shape to produce weighted centroids for.

    Returns
    -------

    pd.DataFrame: A dataframe of centroids, with columns for 'x' and 'y'.
    The zone ids will be in the index.
    """
    trans_conf = cs.ZoningTranslationInputs(zone_1=upper_shape,
                                            zone_2=lower_shape._lower_to_higher()
                                        )
    lookup = cs.ZoneTranslation(trans_conf).spatial_translation(return_gdf=True)
    lower_weight = pd.read_csv(lower_shape.weight_data, index_col=lower_shape.weight_id_col)
    lower_weight.index.name = f"{lower_shape.name}_id"
    cent = lookup.join(lower_weight)
    cent['val'] *= cent[f'{lower_shape.name}_to_{upper_shape.name}']
    cent['x_weight'] = cent.centroid.x * cent[lower_shape.data_col]
    cent['y_weight'] = cent.centroid.y * cent[lower_shape.data_col]
    grouped = cent.groupby(f"{upper_shape.name}_id")[[lower_shape.data_col, 'x_weight', 'y_weight']].sum()
    grouped['x'] = grouped['x_weight'] / grouped[lower_shape.data_col]
    grouped['y'] = grouped['y_weight'] / grouped[lower_shape.data_col]
    return grouped[['x','y']]

if __name__ == "__main__":
    emp_weight = pd.read_csv(r"I:\Data\Zone Translations\weighting vectors\oa_emp_2021_weighting.csv", index_col=0)
    pop_weight = pd.read_csv(r"I:\Data\Zone Translations\weighting vectors\oa_pop_2021_weighting.csv", index_col=0)
    hh_weight = pd.read_csv(r"I:\Data\Zone Translations\weighting vectors\oa_hh_2021_weighting.csv", index_col=0)
    # oa_shape = gpd.read_file(r"Y:\Data Strategy\GIS Shapefiles\Output_Areas\OA_2021\OA_2021_EW_BFC_V8.shp")
    oa_conf = cs.LowerZoneSystemInfo(name="oa_21", shapefile=r"Y:\Data Strategy\GIS Shapefiles\Output_Areas\OA_2021\OA_2021_EW_BFC_V8.shp", id_col="OA21CD",
                                     weight_data=r"I:\Data\Zone Translations\weighting vectors\oa_pop_2021_weighting.csv",
                                     data_col='val',
                                     weight_id_col='oa21cd',
                                     weight_data_year=2021)
    ##### Above here stays the same #####
    ##### Put confs for zone systems here

    normits_conf = cs.TransZoneSystemInfo(name='normits_v3.3', shapefile=r"Y:\Data Strategy\GIS Shapefiles\NorMITs 2024 zone system\NorMITs zone\v3.3\NorMITs_zoning_v3.3.shp",
                                          id_col="normits_id")

    noham_conf = cs.TransZoneSystemInfo(name='noham', shapefile=r"Y:\Data Strategy\GIS Shapefiles\NoHAM Zones\North_Zones_v2.10\noham_zones_freeze_2.10.shp", id_col='id')

    confs = [noham_conf]

    for conf in confs:
        # trans_conf = cs.ZoningTranslationInputs(zone_1=oa_conf, zone_2=conf, sliver_tolerance=0.8)

        # trans = pd.read_csv(r"I:\Data\Zone Translations\cache\noham_oa_21\noham_to_oa_21_spatial.csv")

        pop_cent = weighted_centroids(oa_conf, conf)
        pop_cent.to_csv(r"E:\temp\noham_pop_centroids.csv")
        emp_cent = weighted_centroids(oa_conf, 'oa21cd', emp_weight, conf)
        emp_cent.to_csv(r"E:\temp\noham_emp_centroids.csv")
        hh_cent = weighted_centroids(oa_conf, 'oa21cd', hh_weight, conf)
