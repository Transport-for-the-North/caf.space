import pandas as pd
import caf.space as cs


if __name__ == "__main__":
    emp_weight = pd.read_csv(
        r"I:\Data\Zone Translations\weighting vectors\oa_emp_2021_weighting.csv", index_col=0
    )
    pop_weight = pd.read_csv(
        r"I:\Data\Zone Translations\weighting vectors\oa_pop_2021_weighting.csv", index_col=0
    )
    hh_weight = pd.read_csv(
        r"I:\Data\Zone Translations\weighting vectors\oa_hh_2021_weighting.csv", index_col=0
    )
    # oa_shape = gpd.read_file(r"Y:\Data Strategy\GIS Shapefiles\Output_Areas\OA_2021\OA_2021_EW_BFC_V8.shp")
    oa_conf = cs.LowerZoneSystemInfo(
        name="oa_21",
        shapefile=r"Y:\Data Strategy\GIS Shapefiles\Output_Areas\OA_2021\OA_2021_EW_BFC_V8.shp",
        id_col="OA21CD",
        weight_data=r"I:\Data\Zone Translations\weighting vectors\oa_pop_2021_weighting.csv",
        data_col="val",
        weight_id_col="oa21cd",
        weight_data_year=2021,
    )
    ##### Above here stays the same #####
    ##### Put confs for zone systems here

    normits_conf = cs.TransZoneSystemInfo(
        name="normits_v3.3",
        shapefile=r"Y:\Data Strategy\GIS Shapefiles\NorMITs 2024 zone system\NorMITs zone\v3.3\NorMITs_zoning_v3.3.shp",
        id_col="normits_id",
    )

    noham_conf = cs.TransZoneSystemInfo(
        name="noham",
        shapefile=r"Y:\Data Strategy\GIS Shapefiles\NoHAM Zones\North_Zones_v2.10\noham_zones_freeze_2.10.shp",
        id_col="id",
    )

    conf = cs.ZoningTranslationInputs(zone_1=noham_conf, lower_zoning=oa_conf)

    cents = cs.ZoneTranslation(conf).weighted_centroids()

    print("debugging")
