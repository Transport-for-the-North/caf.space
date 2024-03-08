# -*- coding: utf-8 -*-
import pandas as pd
import geopandas as gpd
import shapely
import numpy as np
from dataclasses import dataclass
from pathlib import Path
import warnings
import tqdm
# pylint: disable=import-error,wrong-import-position
# Local imports here
# pylint: enable=import-error,wrong-import-position

# # # CONSTANTS # # #

# # # CLASSES # # #
@dataclass
class ConvergenceValues:
    rmse: float
    crow_fly_length: float
    full_length: float
    angle: float

# # # FUNCTIONS # # #

def calc_angle(line):
    start = shapely.get_point(line, 0)
    end = shapely.get_point(line, -1)
    x = end.x - start.x
    y = end.y - start.y
    return np.mod(np.arctan2(y, x) * (180 / np.pi), 360)

def relative_angle(feat_1, feat_2):
    if isinstance(feat_1, shapely.LineString):
        angle_1 = calc_angle(feat_1)
    else:
        angle_1 = feat_1
    if isinstance(feat_2, shapely.LineString):
        angle_2 = calc_angle(feat_2)
    else:
        angle_2 = feat_2
    angle = np.absolute(angle_2 - angle_1)
    if angle > 180:
        angle = 360 - angle
    return angle



def rmse(line_1: shapely.LineString, line_2: shapely.LineString, sections: int = 10):
    points = []
    for seg in range(sections + 1):
        points.append(line_1.interpolate(seg / sections, normalized=True).distance(line_2.interpolate(seg / sections, normalized=True)))
    points = np.array(points)
    rmse = np.sqrt((points ** 2).sum()) / sections
    return rmse

def project_line(longer, shorter_start, shorter_end):
    start = longer.interpolate(longer.project(shorter_start))
    end = longer.interpolate(longer.project(shorter_end))
    line_frag = shapely.ops.split(longer, end.buffer(0.01)).geoms[0]
    lines = shapely.ops.split(line_frag, start.buffer(0.1)).geoms
    # if this is the end of the line, there is only one entry
    if len(lines) == 1:
        return lines[0]
    else:
        return lines[-1]


def preprocess(gdf, use_index=False, a='A', b='B', buffer_dist=50, crs="EPSG:27700"):
    if gdf.crs != crs:
        gdf.to_crs(crs, inplace=True)
    inner = gdf.copy()
    if use_index is False:
        inner.set_index([a,b], inplace=True)
    if 'MultiLineString' in inner.geometry.geom_type.unique():
        inner = inner.explode(index_parts=True).reset_index(level=[a, b]).drop(1)
        inner.set_index([a,b], inplace=True)
    inner['start'] = shapely.get_point(inner.geometry, 0)
    inner['end'] = shapely.get_point(inner.geometry, -1)
    inner['angle'] = inner.geometry.apply(calc_angle)
    inner['buffer'] = inner.buffer(buffer_dist, cap_style='flat')
    inner['crow_fly'] = shapely.get_point(inner.geometry, 0).distance(shapely.get_point(inner.geometry, -1))
    inner['straightness'] = inner['crow_fly'] / inner.length
    return inner[['start', 'end', 'angle', 'buffer', 'crow_fly', 'straightness', 'geometry']].sort_index()

def init_join(sat, itn, angle_threshold=60):
    joined = gpd.GeoDataFrame(sat[['angle', 'straightness']], geometry=sat['buffer']).sjoin(itn[['angle','geometry']])
    joined['angle'] = joined.apply(lambda row: relative_angle(row['angle_left'], row['angle_right']), axis=1)
    if 'index_right' in joined.columns:
        joined.rename(columns={'index_right': 'ref_A'}, inplace=True)
        # Adjust angle to allow larger angles on bendy links
        joined['mod_angle'] = joined['angle'] * joined['straightness'] ** 2
        return joined.loc[
            np.absolute(joined['mod_angle']) < angle_threshold, ['ref_A', 'angle',
                                                                 'straightness']]
    else:
        joined.rename(columns={'index_right0': 'ref_A', 'index_right1': 'ref_B'}, inplace=True)
        # Adjust angle to allow larger angles on bendy links
        joined['mod_angle'] = joined['angle'] * joined['straightness'] ** 2
        return joined.loc[np.absolute(joined['mod_angle']) < angle_threshold, ['ref_A', 'ref_B', 'angle', 'straightness']]

def find_con(longer, shorter):
    line = project_line(longer.geometry, shorter.start, shorter.end)
    shorter_angle = shorter.angle
    shorter_geometry = shorter.geometry
    if line.length < shorter.geometry.length * 0.9:
        if line.length < shorter.geometry.length / 2:
            return None
        shorter_geometry = project_line(shorter_geometry, shapely.get_point(line, 0), shapely.get_point(line, -1))
        shorter_angle = calc_angle(shorter.geometry)
    score = rmse(line, shorter.geometry, 10)
    angle = relative_angle(line, shorter_angle)
    # dis = line.distance(shorter.geometry)
    # haus_dis = line.hausdorff_distance(shorter.geometry)
    match_len = shorter['crow_fly']
    full_len = shorter_geometry.length
    return ConvergenceValues(score, match_len, full_len, angle)

if __name__ == "__main__":
    home_dir = Path(r"C:\Users\IsaacScott\projects\trafficmaster")
    itn = gpd.read_file(home_dir / "man_itn.gpkg")
    itn = itn[itn['rdclass'] !='ZC']
    osm = gpd.read_file(home_dir / "manchester_os").set_index('unique_id')
    itn_processed = preprocess(itn, a='a', b='b').reset_index()
    itn_processed.set_index(['a', 'b'], inplace=True)
    osm_processed = preprocess(osm, use_index=True)
    joined = init_join(itn_processed, osm_processed).sort_index()
    out_out = {}
    returned_lengths = {}
    actual_length = {}
    for multi in tqdm.tqdm(joined.index.unique()):
        feature = itn_processed.loc[multi]
        ref_links = joined.loc[multi, ['ref_A', 'angle', 'straightness']]
        out = {}
        for link in ref_links.iterrows():
            ref_A = link[1]['ref_A']
            angle = link[1]['angle']
            straightness = link[1]['straightness']
            ref_link = osm_processed.loc[ref_A]
            if ref_link.geometry.length > feature.geometry.length:
                stats = find_con(ref_link, feature)
            else:
                stats = find_con(feature, ref_link)
            # hausdorff measure the furthest a feature ever is, so crow fly is better
            if stats is None:
                continue
            # if stats.crow_fly_length > 0:
            #     convergence = np.sqrt(stats.distance**2 + stats.hausdorff_distance**2) / stats.crow_fly_length
            #     # TODO need to take angle into account too - a short intersecting line can score well
            # else:
            #     convergence = np.inf
            out[ref_A] = (stats.rmse, stats.full_length, stats.crow_fly_length, stats.angle, angle, straightness)
        out = pd.DataFrame.from_dict(out, orient='index', columns=['convergence', 'full_length', 'crow_fly_length', 'segment_angle', 'angle', 'straightness'])
        filtered = out[out['convergence'] == out['convergence'].min()]
        out_out[multi] = filtered
        actual_length[multi] = feature.geometry.length
        returned_lengths[multi] = osm_processed.loc[filtered.index].length
    df = pd.concat(out_out).reset_index()
    print('debugging')