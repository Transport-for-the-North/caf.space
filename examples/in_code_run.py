import caf.space as cs
import geopandas as gpd

# Creating instances of TransZoneSystemInfo for primary zone systems; the ones we want translations between

normits = cs.TransZoneSystemInfo(name='normits_v3.3',
                                 shapefile=r"Y:\Data Strategy\GIS Shapefiles\NorMITs 2024 zone system\NorMITs zone\v3.3\NorMITs_zoning_v3.3.shp",
                                 id_col='normits_id')
noham = cs.TransZoneSystemInfo(name='noham_v3.7',
                               shapefile=r"P:\02_NorTMS Rebase\01_Highway\03.Data\06. Confirmed Zone Structure\2.NoHAM_zone_updates-TfN\NoHAM_zones_v3.7\NoHAM_Zones_v3.7.shp",
                               id_col="ZONE ID_v3")
norms = cs.TransZoneSystemInfo(name='norms_v3.3',
                               shapefile=r"P:\02_NorTMS Rebase\02_Rail\02_Data_Sys_to_TfN\1.NorTMS_zones\NorTMS_zones_v3.3\NorTMS_zoning_3.3_OA21.shp",
                               id_col='unique_id')
luti = cs.TransZoneSystemInfo(name='LUTI_v4',
                              shapefile=r"\\10.1.0.42\luti\Zoning\NLUTI\v4\NLUTI_v4.gpkg",
                              id_col='zone_id')
lsoa = cs.TransZoneSystemInfo(name='lsoa21',
                                   shapefile=r"Y:\Data Strategy\GIS Shapefiles\NorMITs 2024 zone system\GB LSOA2021 and DZ2011 Clipped\gb_lsoa2021ew_dz2011sg_area_types.shp",
                                   id_col="lsoa21cd")

# Creating lower zone systems, used for weighting in weighted translations.
# In these examples the weighting data is included in the lower zone shapefile.
# If it is not, a path to a csv containing weighting data must be included as 'weight_data'.

emp = cs.LowerZoneSystemInfo(name='oa',
                             shapefile=r"I:\Transfer\IS\gb_oa2021ew_oa2011sg_pop=emp_scot.shp",
                             id_col="OA21CD",
                             data_col="Emp",
                             weight_data_year=2021)

pop = emp.copy()
pop.data_col = 'Pop'


# Iterate through zone systems, producing translations from normits to each other.
for zoning in [noham, norms, luti, lsoa]:

    # For a spatial trans the only necessary arguments are zone_1 and zone_2.
    # Here I also add sliver_tolerance, which defaults to 0.98. For other arguments of
    # ZoningTranslationInputs you may want to provide, see documentation https://cafspace.readthedocs.io/en/stable/index.html

    spatial_conf = cs.ZoningTranslationInputs(zone_1=normits,
                                              zone_2=zoning,
                                              sliver_tolerance=0.95)

    # For weighted translations you must also provide an instance of lower_zoning, which was created
    # above, and a method name. The method name is freeform string, and will be used in the file name
    # in the space cache. Here one is made for emp, and another for pop weighting.

    emp_conf = cs.ZoningTranslationInputs(zone_1=normits,
                                          zone_2=zoning,
                                          lower_zoning=emp,
                                          sliver_tolerance=0.95,
                                          method='emp')

    pop_conf = cs.ZoningTranslationInputs(zone_1=normits,
                                          zone_2=zoning,
                                          lower_zoning=pop,
                                          sliver_tolerance=0.95,
                                          method='pop')

    # Translations are performed by passing the configs created above to the ZoneTranslation class,
    # and then calling either the spatial_translation or weighted_translation method.
    # Here the indices of the returned translation vector is also set.
    spatial_trans = cs.ZoneTranslation(spatial_conf).spatial_translation().set_index([f'{zoning.name}_id', f'{normits.name}_id'])

    emp_trans = cs.ZoneTranslation(emp_conf).weighted_translation().set_index([f'{zoning.name}_id', f'{normits.name}_id'])

    pop_trans = cs.ZoneTranslation(pop_conf).weighted_translation().set_index([f'{zoning.name}_id', f'{normits.name}_id'])

    # In this instance the three differently weighted translations are joined to form a 'full' translation,
    # which is then saved.

    full = spatial_trans.join(emp_trans, lsuffix='_spatial').join(pop_trans, lsuffix='_emp', rsuffix='_pop')

    full.to_csv(rf"E:\noham\rebase\{normits.name}_{zoning.name}_trans.csv")

# N.B. it is known that the way arguments and attributes are provided to classes and methods doesn't make a lot
# of sense, and this will be refactored in future.



