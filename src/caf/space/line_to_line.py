# -*- coding: utf-8 -*-
import pandas as pd
import geopandas as gpd
import shapely
import numpy as np
from pydantic.dataclasses import dataclass
from pydantic import BeforeValidator
from caf.toolkit.config_base import BaseConfig
from pathlib import Path
from tqdm import tqdm
from typing import Union, Annotated

# pylint: disable=import-error,wrong-import-position
# Local imports here
# pylint: enable=import-error,wrong-import-position

# # # CONSTANTS # # #


# # # CLASSES # # #
def _read_gpd(gpd_path: Path | gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    if isinstance(gpd_path, gpd.GeoDataFrame):
        return gpd_path
    return gpd.read_file(gpd_path, engine="pyogrio")


@dataclass
class ConvergenceValues:
    rmse: float
    crow_fly_length: float
    full_length: float
    angle: float


@dataclass
class LinkInfo:
    identifier: Union[str, list[str]]
    gdf: Annotated[gpd.GeoDataFrame, BeforeValidator(_read_gpd)]
    name: str

    @property
    def list_ident(self):
        return [self.identifier] if isinstance(self.identifier, str) else self.identifier


class Line2LineConf(BaseConfig):
    target: LinkInfo
    reference: LinkInfo

    """
    target: The line layer you want info for. This layer will be iterated through, with matches 
    found in reference for each line in target.
    reference: The line layer which will be matched to target.
    """


# # # FUNCTIONS # # #


def calc_angle(line):
    """Calculate the angle of a line in degrees."""
    start = shapely.get_point(line, 0)
    end = shapely.get_point(line, -1)
    x = end.x - start.x
    y = end.y - start.y
    return np.mod(np.arctan2(y, x) * (180 / np.pi), 360)


def relative_angle(feat_1, feat_2):
    """Calculate the relative angle between two features."""
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
    """Calculate the root mean square distance between two lines."""
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
    """Project a line onto another line, returning the last segment."""
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
    """
    Preprocess a link.

    Sets the crs to the input and then calculates some metrics.

    Returned GeoDataFrame contains:

    - start: Start point of the link geometry
    - end: End point of the link geometry
    - angle: Angle of the link geometry in degrees
    - buffer: Buffered geometry of the link
    - crow_fly: Crow fly distance between start and end points
    - straightness: Ratio of crow fly distance to link length
    - geometry: Original link geometry
    """
    gdf = link_info.gdf
    if gdf.crs != crs:
        gdf.to_crs(crs, inplace=True)
    inner = gdf.copy()
    if isinstance(link_info.identifier, list):
        inner["id"] = (
            inner[link_info.identifier[0]].astype(str)
            + "_"
            + inner[link_info.identifier[1]].astype(str)
        )
    else:
        inner.rename(columns={link_info.identifier: "id"}, inplace=True)
    inner.set_index("id", inplace=True)
    inner["start"] = shapely.get_point(inner.geometry, 0)
    inner["end"] = shapely.get_point(inner.geometry, -1)
    # MultiLineStrings break this - temp fix should be looked into
    inner = inner[~inner["end"].isna()]
    inner["angle"] = inner.geometry.apply(calc_angle)
    inner["buffer"] = inner.buffer(buffer_dist, cap_style="flat")
    inner["crow_fly"] = shapely.get_point(inner.geometry, 0).distance(
        shapely.get_point(inner.geometry, -1)
    )
    inner["length"] = inner.geometry.length
    inner["straightness"] = inner["crow_fly"] / inner.length
    return inner[
        ["start", "end", "angle", "buffer", "crow_fly", "length", "straightness", "geometry"]
    ].sort_index()


def init_join(targ, ref, angle_threshold=60):
    """
    Initial join between target and reference links.

    This will join all links in ref within the buffer of targ, and filter for the
    relative angle between them to be less than the angle_threshold.
    Parameters
    ----------
    targ
    ref
    angle_threshold

    Returns
    -------

    """
    joined = gpd.GeoDataFrame(targ[["angle", "straightness"]], geometry=targ["buffer"]).sjoin(
        ref[["angle", "geometry"]]
    )
    joined["angle"] = joined.apply(
        lambda row: relative_angle(row["angle_left"], row["angle_right"]), axis=1
    )
    # Adjust angle to allow larger angles on bendy links
    joined.rename(columns={"id_right": "id_ref"}, inplace=True)
    joined["mod_angle"] = joined["angle"] * joined["straightness"] ** 2
    return joined.loc[
        np.absolute(joined["mod_angle"]) < angle_threshold,
        "id_ref",
    ]


def find_con(longer, shorter, longer_suffix: str = "", shorter_suffix: str = ""):
    """Find convergence between two links."""
    line = project_line(
        longer[f"geometry{longer_suffix}"],
        shorter[f"start{shorter_suffix}"],
        shorter[f"end{shorter_suffix}"],
    )
    shorter_angle = shorter[f"angle{shorter_suffix}"]
    shorter_geometry = shorter[f"geometry{shorter_suffix}"]
    if line.length < shorter_geometry.length * 0.9:
        shorter_geometry = project_line(
            shorter_geometry, shapely.get_point(line, 0), shapely.get_point(line, -1)
        )
        shorter_angle = calc_angle(shorter_geometry)
    score = rmse(line, shorter_geometry, 10)
    angle = relative_angle(line, shorter_angle)
    shorter_len = shorter[f"crow_fly{shorter_suffix}"]
    longer_len = longer[f"crow_fly{longer_suffix}"]
    full_len = shorter_geometry.length
    return pd.Series(
        [
            score,
            shorter_len,
            longer_len,
            shorter[f"geometry{shorter_suffix}"].length,
            longer[f"geometry{longer_suffix}"].length,
            full_len,
            angle,
        ],
        index=[
            "distance",
            f"crow_fly{shorter_suffix}",
            f"crow_fly{longer_suffix}",
            f"length{shorter_suffix}",
            f"length{longer_suffix}",
            "overlap_length",
            "angle",
        ],
    )


def main(conf: Line2LineConf):
    target_processed = preprocess(Line2LineConf.target)
    target_processed.index.name = "id_targ"
    ref_processed = preprocess(Line2LineConf.reference)
    ref_processed.index.name = "id_ref"
    joined = init_join(target_processed, ref_processed)
    missing_targ = target_processed.drop(joined.index.unique())
    big_join = (
        target_processed.join(joined)
        .set_index("id_ref", append=True)
        .join(ref_processed, lsuffix="_targ", rsuffix="_ref")
    )
    ref_first = big_join.loc[big_join["length_targ"] < big_join["length_ref"]]
    targ_first = big_join.loc[big_join["length_targ"] >= big_join["length_ref"]]
    results_a = ref_first.apply(
        lambda row: find_con(
            row.loc[["geometry_ref", "crow_fly_ref"]],
            row.loc[
                ["geometry_targ", "angle_targ", "start_targ", "end_targ", "crow_fly_targ"]
            ],
            "_ref",
            "_targ",
        ),
        axis=1,
    )
    results_b = targ_first.apply(
        lambda row: find_con(
            row.loc[["geometry_targ", "crow_fly_targ"]],
            row.loc[["geometry_ref", "angle_ref", "start_ref", "end_ref", "crow_fly_ref"]],
            "_targ",
            "_ref",
        ),
        axis=1,
    )
    results = pd.concat([results_a, results_b])
    return (
        results.reset_index(level="id_targ")
        .sort_values(by=["id_targ", "distance"])
        .set_index("id_targ", append=True)
    )


def process_missing(lookup, gdf, threshold):
    # Completely missing will be assigned np.inf. User can decide what
    # threshold to try another method beneath.
    missing_ind = lookup[lookup["convergence"] > threshold].index
    missing = gdf.loc[missing_ind].copy()
    matching = gdf.drop(missing_ind).copy()


if __name__ == "__main__":
    home_dir = Path(r"E:\tmjt_data\out\lookup")
    itn = gpd.read_file(
        r"O:\10.Internal_Requests\24 MRNmatchingNoHAM2023\MRN\mrnpaths.shp", engine="pyogrio"
    )
    # itn = itn[itn["rdclass"] != "ZC"]
    # osm = gpd.read_file(home_dir / "manchester_os").set_index('unique_id')
    # osm = LinkInfo(gdf=osm, identifier='unique_id', name='osm')
    itn = LinkInfo(gdf=itn, identifier="path_id", name="mrn")
    noham = gpd.read_file(
        r"O:\10.Internal_Requests\24 MRNmatchingNoHAM2023\NoHAM\NoHAM_Base.shp",
        engine="pyogrio",
    )
    noham = LinkInfo(
        gdf=noham[(noham["A"] > 10000) & (noham["B"] > 10000)],
        identifier=["A", "B"],
        name="noham",
    )
    out = main(noham, itn, True)
    out.to_csv(home_dir / "sat_rami_lookup.csv")
    print("debugging")
