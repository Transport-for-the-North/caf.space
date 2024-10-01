# -*- coding: utf-8 -*-
import pandas as pd
import geopandas as gpd
import shapely
import numpy as np
from dataclasses import dataclass
from pathlib import Path
from tqdm import tqdm
from typing import Union

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


@dataclass
class LinkInfo:
    identifier: Union[str, list[str]]
    gdf: gpd.GeoDataFrame
    name: str

    @property
    def list_ident(self):
        return [self.identifier] if isinstance(self.identifier, str) else self.identifier


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
        points.append(
            line_1.interpolate(seg / sections, normalized=True).distance(
                line_2.interpolate(seg / sections, normalized=True)
            )
        )
    points = np.array(points)
    rmse = np.sqrt((points**2).sum()) / sections
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


def preprocess(link_info: LinkInfo, buffer_dist=50, crs="EPSG:27700"):
    gdf = link_info.gdf
    if gdf.crs != crs:
        gdf.to_crs(crs, inplace=True)
    inner = gdf.copy()
    if isinstance(link_info.identifier, list):
        inner.set_index(link_info.identifier, inplace=True)
    inner["start"] = shapely.get_point(inner.geometry, 0)
    inner["end"] = shapely.get_point(inner.geometry, -1)
    inner["angle"] = inner.geometry.apply(calc_angle)
    inner["buffer"] = inner.buffer(buffer_dist, cap_style="flat")
    inner["crow_fly"] = shapely.get_point(inner.geometry, 0).distance(
        shapely.get_point(inner.geometry, -1)
    )
    inner["straightness"] = inner["crow_fly"] / inner.length
    return inner[
        ["start", "end", "angle", "buffer", "crow_fly", "straightness", "geometry"]
    ].sort_index()


def init_join(targ, ref, angle_threshold=60):
    joined = gpd.GeoDataFrame(targ[["angle", "straightness"]], geometry=targ["buffer"]).sjoin(
        ref[["angle", "geometry"]]
    )
    joined["angle"] = joined.apply(
        lambda row: relative_angle(row["angle_left"], row["angle_right"]), axis=1
    )
    if "index_right" in joined.columns:
        joined.rename(columns={"index_right": "ref_A"}, inplace=True)
        # Adjust angle to allow larger angles on bendy links
        joined["mod_angle"] = joined["angle"] * joined["straightness"] ** 2
        return joined.loc[
            np.absolute(joined["mod_angle"]) < angle_threshold,
            ["ref_A", "angle", "straightness"],
        ]
    else:
        joined.rename(columns={"a": "ref_A", "b": "ref_B"}, inplace=True)
        # Adjust angle to allow larger angles on bendy links
        joined["mod_angle"] = joined["angle"] * joined["straightness"] ** 2
        return joined.loc[
            np.absolute(joined["mod_angle"]) < angle_threshold,
            ["ref_A", "ref_B", "angle", "straightness"],
        ]


def find_con(longer, shorter):
    line = project_line(longer.geometry, shorter.start, shorter.end)
    shorter_angle = shorter.angle
    shorter_geometry = shorter.geometry
    if line.length < shorter.geometry.length * 0.9:
        if line.length < shorter.geometry.length / 2:
            return ConvergenceValues(np.inf, 0, 0, 0)
        shorter_geometry = project_line(
            shorter_geometry, shapely.get_point(line, 0), shapely.get_point(line, -1)
        )
        shorter_angle = calc_angle(shorter_geometry)
    score = rmse(line, shorter_geometry, 10)
    angle = relative_angle(line, shorter_angle)
    # dis = line.distance(shorter.geometry)
    # haus_dis = line.hausdorff_distance(shorter.geometry)
    match_len = shorter["crow_fly"]
    full_len = shorter_geometry.length
    return ConvergenceValues(score, match_len, full_len, angle)


def main(
    ref_links: LinkInfo,
    target_links: LinkInfo,
):
    target_processed = preprocess(target_links)
    ref_processed = preprocess(ref_links)
    joined = init_join(target_processed, ref_processed)
    missing_targ = target_processed.drop(joined.index.unique())
    out_out = {}
    actual_length = {}
    for multi in tqdm(joined.index.unique()):
        feature = target_processed.loc[multi]
        links_iter = joined.loc[multi]
        if len(links_iter) == 0:
            print('debugging')
        out = {}
        for link in links_iter.iterrows():
            link = link[1]
            ref_A = [link["ref_A"]]
            try:
                ref_B = [link["ref_B"]]
            except KeyError:
                ref_B = []
            refs = tuple(ref_A + ref_B)
            straightness = link["straightness"]
            ref_link = ref_processed.loc[refs]
            if len(ref_link) > 1:
                ref_link = ref_link.iloc[0].squeeze()
            else:
                ref_link = ref_link.squeeze()
            if ref_link.geometry.length > feature.geometry.length:
                stats = find_con(ref_link, feature)
            else:
                stats = find_con(feature, ref_link)
            if len(refs) == 1:
                refs = refs[0]
            out[refs] = (
                stats.rmse,
                stats.full_length,
                stats.crow_fly_length,
                stats.angle,
                stats.angle,
                straightness,
            )
        else:
            out = pd.DataFrame.from_dict(
                out,
                orient="index",
                columns=[
                    "convergence",
                    "ref_length",
                    "ref_crow_fly",
                    "segment_angle",
                    "angle",
                    "targ_straightness",
                ],
            )
            if len(multi) == 1:
                multi = multi[0]
            out.sort_values(by='convergence', inplace=True)
            temp_length = 0
            out_ind = []
            for idx in range(len(out)):
                temp_length += out.iloc[idx]['ref_length']
                if temp_length < feature.geometry.length:
                    out_ind.append(out.index[idx])
                else:
                    break
            # filtered = out[out["convergence"] == out["convergence"].min()]
            out_out[multi] = out.loc[out_ind]
            actual_length[multi] = feature.geometry.length
    actual_length = pd.Series(actual_length, name='target_link_length')
    df = pd.concat(out_out).reset_index()
    df.index = pd.MultiIndex.from_tuples(df['level_2'])
    df.set_index(['level_0', 'level_1'], inplace=True, append=True)
    df.drop('level_2', axis=1, inplace=True)
    targ_names = target_links.list_ident
    ref_names = ref_links.list_ident
    df.index.names = ref_names +targ_names
    actual_length.index.names = targ_names
    df = actual_length.to_frame().join(df)
    df['overlap'] = df['ref_length'] / df['target_link_length']
    return df, missing_targ

def process_missing(lookup, gdf, threshold):
    # Completely missing will be assigned np.inf. User can decide what
    # threshold to try another method beneath.
    missing_ind = lookup[lookup['convergence'] > threshold].index
    missing = gdf.loc[missing_ind].copy()
    matching = gdf.drop(missing_ind).copy()


if __name__ == "__main__":
    home_dir = Path(r"E:\tmjt_data\out\lookup")
    itn = gpd.read_file(r"T:\AK\ForJourneyTimes\JTOutput\tmjt_gb_lsoa.gpkg", engine='pyogrio')
    # itn = itn[itn["rdclass"] != "ZC"]
    # osm = gpd.read_file(home_dir / "manchester_os").set_index('unique_id')
    # osm = LinkInfo(gdf=osm, identifier='unique_id', name='osm')
    itn = LinkInfo(gdf=itn, identifier=['a', 'b'], name='itn')
    noham = gpd.read_file(r"T:\AK\ForJourneyTimes\SATURNNetwork\NoHAM_Base.shp", engine='pyogrio')
    noham = LinkInfo(gdf=noham[(noham['A']>10000) & (noham['B']>10000)], identifier=['A','B'], name='noham')
    out, missing = main(itn, noham)
    out.to_csv(home_dir / "sat_rami_lookup.csv")
    print('debugging')
