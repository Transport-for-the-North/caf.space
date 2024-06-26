import caf.space as cs
import os

# # #  CONSTANTS # # #
OUTPUT_PATH = r"C:\Users\Tenet\Documents\GitHub\caf.space_lin\tests\outputs"

LINE_FILE_NAME = r"noham2018"
LINE_SHAPEFILE = r"O:\7.Network_Builder\02 Network Builder\Network_Builder_v1\4.NoHAM_IPBA-June21\Scenario\IPBA_Final\Base_Revised\NoHAM_2018.shp"
LINE_ID_COLS = ['A', 'B']

POLY_FILE_NAME = r"lta"
POLY_SHAPEFILE = r"Y:\Data Strategy\GIS Shapefiles\LTAs\Local_Transport_Authorities_v0.1.shp"
POLY_ID_COL = r"LTA"


# # # RUN caf.space # # #
line_conf = cs.inputs.LineInfo(
    name=LINE_FILE_NAME,
    shapefile=LINE_SHAPEFILE,
    id_cols=LINE_ID_COLS
)
zone_conf = cs.inputs.TransZoneSystemInfo(
    name=POLY_FILE_NAME,
    shapefile=POLY_SHAPEFILE,
    id_col=POLY_ID_COL,
)
conf = cs.inputs.ZoningTranslationInputs(
    zone_1=line_conf,
    zone_2=zone_conf
)
trans_class = cs.ZoneTranslation(conf)

trans = trans_class.spatial_translation()

# # # SAVE OUTPUT # # #
output_path = os.path.join(OUTPUT_PATH,rf"{LINE_FILE_NAME}_{POLY_FILE_NAME}.csv")
trans.to_csv(output_path)
print('debugging')