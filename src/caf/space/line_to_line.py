"""Calculate the correspondence between two sets of line geometries."""

# Built-Ins
import argparse
import functools
import logging
import pathlib
import warnings
from typing import Annotated, Literal, Sequence, Union

# Third Party
import caf.toolkit as ctk
import geopandas as gpd
import numpy as np
import pandas as pd
import pydantic
import shapely
from caf.toolkit.config_base import BaseConfig
from pydantic.dataclasses import dataclass

# Local Imports
import caf.space as cspace
from caf.space import inputs

# # # CONSTANTS # # #

if __name__ == "__main__":
    # Reproduce __name__ using package and file path
    _NAME = ".".join((__package__, pathlib.Path(__file__).stem))
else:
    _NAME = __name__

LOG = logging.getLogger(_NAME)
_CONFIG = pathlib.Path("line_to_line.yml")

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
    file: inputs.GeoDataFile
    name: str

    _gdf: gpd.GeoDataFrame | None = None

    __pydantic_config__ = pydantic.ConfigDict(arbitrary_types_allowed=True)

    @property
    def gdf(self) -> gpd.GeoDataFrame:
        """Link data GeoDataFrame."""
        if self._gdf is None:
            self._gdf = self.file.read()
        return self._gdf

    @gdf.setter
    def gdf(self, value: gpd.GeoDataFrame) -> None:
        if not isinstance(value, gpd.GeoDataFrame):
            raise TypeError(f"gdf should be a GeoDataFrame not {type(value)}")
        self._gdf = value

    @property
    def list_ident(self):
        return [self.identifier] if isinstance(self.identifier, str) else self.identifier


def _check_filename(value: str | None, *, suffixes: tuple[str, ...]) -> str | None:
    if value is None:
        return value

    value = str(value)
    if not value.strip().lower().endswith(suffixes):
        raise ValueError(f"invalid suffix for '{value}', expected one of {suffixes}")
    return value


class Line2LineConf(BaseConfig):
    model_config = pydantic.ConfigDict(arbitrary_types_allowed=True)

    target: LinkInfo | list[LinkInfo]
    reference: LinkInfo
    output_folder: pydantic.DirectoryPath
    output_network_filename: Annotated[
        str | None,
        pydantic.AfterValidator(
            functools.partial(_check_filename, suffixes=(".gpkg", ".shp", ".geojson"))
        ),
    ] = None
    original_geometries_output: Annotated[
        str | None,
        pydantic.BeforeValidator(functools.partial(_check_filename, suffixes=(".gpkg",))),
    ] = None
    angle_threshold: int = 60

    """
    target: The line layer you want info for. This layer will be iterated through, with matches 
    found in reference for each line in target.
    reference: The line layer which will be matched to target.
    """

    @property
    def output_network_path(self) -> pathlib.Path:
        """Path to save output network GeoSpatial file to."""
        if self.output_network_filename is None:
            name = f"{self.reference.name}-combined.gpkg"
        else:
            name = self.output_network_filename
        return self.output_folder / name

    @property
    def output_original_geometries(self) -> pathlib.Path | None:
        """Optional path to output original geometries to, with reference ID column."""
        if self.original_geometries_output is None:
            return None
        return self.output_folder / self.original_geometries_output


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
    LOG.debug("Preprocessing %s", link_info.name)
    gdf = link_info.gdf
    if gdf.crs != crs:
        gdf.to_crs(crs, inplace=True)
    inner = gdf.copy()
    _set_id_column(inner, link_info.identifier)

    inner.set_index("id", inplace=True, verify_integrity=True)

    if (inner.geom_type != "LineString").any():
        _check_geom_type(inner, ("LineString", "MultiLineString"))
        inner.geometry = inner.line_merge(directed=True)
        warnings.warn(
            "Merged geometries containing multiple linestrings into"
            f" single for each feature for {link_info.name}",
            RuntimeWarning,
            stacklevel=2,
        )
        _check_geom_type(inner, ("LineString",), error=False)

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
        [
            "start",
            "end",
            "angle",
            "buffer",
            "crow_fly",
            "length",
            "straightness",
            "geometry",
        ]
    ].sort_index()


def _set_id_column(
    data: gpd.GeoDataFrame, identifier: str | Sequence[str]
) -> gpd.GeoDataFrame:
    if isinstance(identifier, str):
        data["id"] = data[identifier]
    elif len(identifier) == 1:
        data["id"] = data[identifier[0]]
    elif len(identifier) == 0:
        raise ValueError("no identifier provided")
    else:
        data["id"] = sum(
            ("_" + data[i].astype(str) for i in identifier[1:]),
            start=data[identifier[0]].astype(str),
        )

    nans = data["id"].isna() | (data["id"].astype(str).str.strip() == "")
    if nans.any():
        raise ValueError(f"identifier column(s) contain {nans.sum():,} null values")
    return data


def _check_geom_type(
    data: gpd.GeoDataFrame, valid_types: Sequence[str], *, error: bool = True
):
    if data.geom_type.isin(valid_types).all():
        return

    counts = np.unique(
        data.geom_type[~data.geom_type.isin(valid_types)],
        return_counts=True,
    )
    message = f"geometries should be {', '.join(valid_types)} not: " + ", ".join(
        f"{i} ({j:,})" for i, j in zip(*counts)
    )
    if error:
        raise TypeError(message)
    warnings.warn(message, RuntimeWarning, stacklevel=3)


def init_join(targ, ref, angle_threshold=60):
    """
    Initial join between target and reference links.

    This will join all links in ref within the buffer of targ, and filter for the
    relative angle between them to be less than the angle_threshold.
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
    mask = np.absolute(joined["mod_angle"]) < angle_threshold

    LOG.debug(
        "Dropped %s correspondence links with angles (straightness adjusted) > %s",
        (~mask).sum(),
        angle_threshold,
    )
    return joined.loc[mask, "id_ref"]


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
        {
            "distance": score,
            f"crow_fly{shorter_suffix}": shorter_len,
            f"crow_fly{longer_suffix}": longer_len,
            f"length{shorter_suffix}": shorter[f"geometry{shorter_suffix}"].length,
            f"length{longer_suffix}": longer[f"geometry{longer_suffix}"].length,
            "overlap_length": full_len,
            "angle": angle,
            "hausdorff_distance": shapely.hausdorff_distance(line, shorter_geometry),
            "frechet_distance": shapely.frechet_distance(line, shorter_geometry),
        }
    )


def combine(
    reference: LinkInfo,
    targets: Sequence[tuple[LinkInfo, pd.DataFrame]],
    original_geometries_output: pathlib.Path | None = None,
) -> gpd.GeoDataFrame:
    """Combine target datasets back to reference geometries."""
    combined = reference.gdf.copy()
    combined = _set_id_column(combined, reference.identifier)
    combined = combined.rename(columns={"id": "id_ref"}).set_index("id_ref")

    for target, replace in targets:
        data = _set_id_column(target.gdf.copy(), target.identifier)
        data = data.rename(columns={"id": "id_targ"}).set_index("id_targ")

        merge_group = _group_merge(
            data,
            replace[["overlap_length", "length_ref"]],
            target.name,
            original_geometries_output,
        )
        combined = combined.join(merge_group, how="left", validate="1:1")

    return combined


def _group_merge(
    data: gpd.GeoDataFrame,
    correspondence: pd.DataFrame,
    name: str,
    target_output: pathlib.Path | None,
    weights_column: str = "overlap_length",
) -> pd.DataFrame:
    """Merge ref and target datasets together and group by reference ID."""
    merged = data.join(
        correspondence.reset_index("id_ref"), how="left", validate="1:m"
    ).reset_index()

    def join(values: pd.Series) -> str:
        values = values.astype(str)
        return ", ".join(f"{i} ({j})" for i, j in zip(*np.unique(values, return_counts=True)))

    if target_output is not None:
        merge_group = merged.groupby("id_targ").aggregate(
            {
                **dict.fromkeys(data.columns, "first"),
                **dict.fromkeys(correspondence.columns, "sum"),
                "id_ref": (join, "count"),
            }
        )
        merge_group.columns = [
            f"{i}-{j}" if i == "id_ref" else i for i, j in merge_group.columns
        ]
        merge_group = gpd.GeoDataFrame(merge_group, crs=data.crs)

        merge_group.to_file(target_output, layer=name)
        LOG.info("Written %s geometries to %s", name, target_output)

    def overlap_weighted(group: pd.Series) -> float:
        return np.average(group, weights=merged.loc[group.index, weights_column])

    numeric_columns = data.select_dtypes(np.number).columns.tolist()
    merge_group = merged.groupby("id_ref").aggregate(
        {
            "id_targ": (join, "count"),
            **dict.fromkeys(numeric_columns, ("sum", "mean", overlap_weighted)),
            **dict.fromkeys(
                filter(lambda x: x not in ("geometry", *numeric_columns), data.columns),
                ("count", join),
            ),
        }
    )
    merge_group.columns = [f"{name} - {i}-{j}" for i, j in merge_group.columns]
    return merge_group


def main(conf: Line2LineConf):
    LOG.debug("Running %s with parameters:\n%s", _NAME, conf.to_yaml())
    ref_processed = preprocess(conf.reference)
    ref_processed.index.name = "id_ref"

    if isinstance(conf.target, list):
        targets = conf.target
    else:
        targets = [conf.target]

    lookups: list[pd.DataFrame] = []

    for target in targets:
        LOG.info("Producing %s and %s link correspondence", conf.reference.name, target.name)
        results = _link_correspondence(
            target,
            ref_processed,
            conf.reference.name,
            angle_threshold=conf.angle_threshold,
        )
        results = _filter_results(results)

        out_path = conf.output_folder / f"{target.name}-{conf.reference.name}.csv"
        results.to_csv(out_path)
        LOG.info("Written %s", out_path)
        lookups.append(results)

        LOG.info(
            "%s reference overlap length summary\n%s",
            target.name,
            _length_stats(results, "id_targ"),
        )

    LOG.info("Adding attributes to %s", conf.reference.name)
    combined = combine(
        conf.reference,
        list(zip(targets, lookups, strict=True)),
        original_geometries_output=conf.output_original_geometries,
    )

    if conf.reference.file.layer is None:
        layer: str | int = "combined"
    else:
        layer = conf.reference.file.layer
    conf.output_network_path.parent.mkdir(exist_ok=True, parents=True)
    combined.to_file(conf.output_network_path, layer=layer)
    LOG.info("Written: %s", conf.output_network_path.resolve())


def _link_correspondence(
    target: LinkInfo, reference: gpd.GeoDataFrame, ref_name: str, angle_threshold: int
) -> pd.DataFrame:
    target_processed = preprocess(target)
    target_processed.index.name = "id_targ"

    joined = init_join(target_processed, reference, angle_threshold=angle_threshold)

    big_join = (
        target_processed.join(joined, validate="1:m")
        .set_index("id_ref", append=True)
        .join(reference, lsuffix="_targ", rsuffix="_ref", validate="m:1")
    )

    missing = big_join.index.get_level_values("id_ref").isna()
    if missing.sum() > 0:
        warnings.warn(
            f"{missing.sum():,} ({missing.sum() / len(target_processed):.1%})"
            f" features from {target.name} failed to find"
            f" a corresponding link in {ref_name}",
            RuntimeWarning,
            stacklevel=2,
        )
        big_join = big_join.loc[~missing]

    ref_first = big_join.loc[big_join["length_targ"] < big_join["length_ref"]]
    targ_first = big_join.loc[big_join["length_targ"] >= big_join["length_ref"]]
    results_a = ref_first.apply(
        lambda row: find_con(
            row.loc[["geometry_ref", "crow_fly_ref"]],
            row.loc[
                [
                    "geometry_targ",
                    "angle_targ",
                    "start_targ",
                    "end_targ",
                    "crow_fly_targ",
                ]
            ],
            "_ref",
            "_targ",
        ),
        axis=1,
    )
    results_b = targ_first.apply(
        lambda row: find_con(
            row.loc[["geometry_targ", "crow_fly_targ"]],
            row.loc[
                [
                    "geometry_ref",
                    "angle_ref",
                    "start_ref",
                    "end_ref",
                    "crow_fly_ref",
                ]
            ],
            "_targ",
            "_ref",
        ),
        axis=1,
    )
    results = pd.concat([results_a, results_b])
    results = (
        results.reset_index(level="id_targ")
        .sort_values(by=["id_targ", "distance"])
        .set_index("id_targ", append=True)
    )

    return results


def _filter_results(results: pd.DataFrame) -> pd.DataFrame:
    """Remove excess links from correspondence results based on overlap.

    Assumes results are already sorted based on convergence score.
    """
    lengths = results.groupby(level="id_targ").agg(
        {"length_targ": "first", "overlap_length": "sum"}
    )
    excess = lengths.loc[lengths["overlap_length"] > lengths["length_targ"]]
    if len(excess) == 0:
        LOG.debug("No excess link correspondence found")
        return results

    drop_indices = []
    for link in excess.itertuples():
        cumsum = results.loc[pd.IndexSlice[:, link.Index], "overlap_length"].cumsum()
        extras = cumsum.index[cumsum > link.length_targ].tolist()
        # Keep first link which is bigger than target but drop all others
        drop_indices.extend(extras[1:])

    if len(drop_indices) == 0:
        LOG.debug("No excess links dropeed, some overlaps > target length")
        return results

    LOG.info(
        "Filtered out %s (%s) excess correspondence rows which exceed target link length",
        len(drop_indices),
        f"{len(drop_indices) / len(results):.1%}",
    )
    return results.drop(index=drop_indices)


def _length_stats(
    results: pd.DataFrame,
    target_id: str,
    overlap_col: str = "overlap_length",
    target_length_col: str = "length_targ",
    within_check: float = 0.1,
) -> str:
    """Summary of comparison between reference overlap and target link length."""
    lengths = results.groupby(level=target_id).agg(
        {target_length_col: "first", overlap_col: "sum"}
    )
    stats: dict[str, int] = {
        "Overlap > Target": (lengths[overlap_col] > lengths[target_length_col]).sum(),
        "Overlap < Target": (lengths[overlap_col] < lengths[target_length_col]).sum(),
        f"Within {within_check:.0%}": (
            np.abs(lengths[overlap_col] - lengths[target_length_col]) < within_check
        ).sum(),
        "Overlap 0": (lengths[overlap_col] == 0).sum(),
        "Target 0": (lengths[target_length_col] == 0).sum(),
        "Overlap <0 or NaN": (lengths[overlap_col].isna() | (lengths[overlap_col] < 0)).sum(),
        "Target <0 or NaN": (
            lengths[target_length_col].isna() | (lengths[target_length_col] < 0)
        ).sum(),
    }

    width = max(map(len, stats.keys()))
    return "\n".join(
        f"{i:<{width}.{width}} : {j} ({j / len(lengths):.1%})" for i, j in stats.items()
    )


def _run() -> None:
    parser = argparse.ArgumentParser(
        _NAME,
        description=__doc__,
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "config",
        type=pathlib.Path,
        default=_CONFIG,
        help="path to line to line YAML config file",
    )

    args = parser.parse_args()
    config_path: pathlib.Path = args.config
    if not config_path.is_file():
        raise FileNotFoundError(config_path)

    config = Line2LineConf.load_yaml(config_path)

    details = ctk.ToolDetails(_NAME, cspace.__version__)
    log_path = config.output_folder / f"{_NAME}.log"

    with ctk.LogHelper(__package__, details, log_file=log_path):
        main(config)


if __name__ == "__main__":
    _run()
