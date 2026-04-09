"""Create a new zone system for normits localisation.

This is done by combining two existing zone systems, one within a specified boundary (internal)
and the other outside of that boundary (external).
An optional buffer zone system can be used for zones directly adjacent to the boundary.
"""

##### IMPORTS #####

import functools
import logging
import pathlib
from typing import Literal
import pydantic
from pydantic import dataclasses
import pandas as pd
import geopandas as gpd

import caf.toolkit as ctk
from caf.space.inputs import ZoneSystemInfo

##### CONSTANTS #####

_NAME = pathlib.Path(__file__).stem
LOG = logging.getLogger(_NAME)
_CONFIG_FILE = pathlib.Path(__file__).with_suffix(".yml")


##### CLASSES & FUNCTIONS #####


@dataclasses.dataclass
class Area:
    """Data for selected localisation area."""

    area_name: str
    selected_lad: list[str]
    selected_colname: str


@dataclasses.dataclass
class ZoneSystems:
    """Data for the zone systems to be used."""

    boundary_zones: ZoneSystemInfo
    internal_zones: ZoneSystemInfo
    external_zones: ZoneSystemInfo
    buffer_zones: ZoneSystemInfo | None = None


class _Config(ctk.BaseConfig):
    """Config for running localisation zoning script."""

    output_path: pydantic.DirectoryPath
    localisation_area: Area
    zone_systems: ZoneSystems

    @functools.cached_property
    def output_folder(self) -> pathlib.Path:
        """Folder to save outputs to."""
        folder = self.output_path / f"{self.localisation_area.area_name}_localisation_zones"
        folder.mkdir(exist_ok=True)
        return folder


def join_zones_to_bound(
    zones: gpd.GeoDataFrame,
    boundary: gpd.GeoDataFrame,
    how: Literal["inside", "outside"],
    id_col: str,
    zone_name: str,
) -> gpd.GeoDataFrame:
    """ "Select zones that are either inside or outside of a boundary."""
    zones_cent = zones.copy()
    zones_cent.geometry = zones_cent.centroid
    zones_cent = zones_cent.sjoin(boundary, how="left", predicate="within")

    if how == "inside":
        zones = zones.loc[zones_cent["index_right"].notna()]
    elif how == "outside":
        zones = zones.loc[zones_cent["index_right"].isna()]

    zones = zones.rename(columns={id_col: "id"})
    zones["zoning"] = zone_name

    return zones


def produce_zoning(
    ext_zones: ZoneSystemInfo,
    int_zones: ZoneSystemInfo,
    buff_zones: ZoneSystemInfo | None,
    int_bound: gpd.GeoDataFrame,
    buff_bound: gpd.GeoDataFrame | None,
) -> gpd.GeoDataFrame:
    """
    Produce a composite zone system from two zone systems, where one zone system
    is used for zones within a boundary, the other without. An optional buffer
    zone system can be used for a buffer zone (zones directly adjacent to the internal boundary).

    This process is written with output areas (oa/lsoa/msoa) in mind, and as such it is assumed the
    two zone systems nest within each other. The zones should also nest within
    the boundary, but failing that, the centroids of each zone system decides
    whether they are within or without the boundary.

    Parameters
    ----------
    ext_zones: ZoneSystemInfo
        The zone system to use outside the boundary. Generally this would be
        the more aggregate zone system. e.g. lad.
    int_zones: ZoneSystemInfo
        The zone system to use inside the boundary. Generally this would be the
        less aggregate zone system, e.g. lsoa.
    buff_zones: ZoneSystemInfo | None
        The zone system to use inside the buffer area. Generally this would be
        a zone system of an aggregation in between the external and internal
        zone systems, e.g. msoa.
        If this is given, a buffer zone will be created of all external zones
        directly adjacent to the internal boundary. If no buffer zone system is
        given, there will be only internal and external zones without a buffer zone.
    int_bound: GeoDataFrame
        The boundary defining where to use each zone system. This should be a
        polygon layer, ideally a single polygon feature, but it can be many.
        Internal is the extent of this layer, and external is outside this layer.
    buff_bound: GeoDataFrame | None
        The boundary defining the buffer zone. This should be a polygon layer of zones
        adjacent to the internal boundary.

    Returns
    -------
    gpd.GeoDataFrame: A geodataframe of the combined zone system. This will
        contain three columns, an id, a zone system name, and geometry. The zone system name
        is used to indicate which zone system the zone is from.
    """
    ext_gdf = gpd.read_file(ext_zones.shapefile, columns=[ext_zones.id_col, "geometry"])
    int_gdf = gpd.read_file(int_zones.shapefile, columns=[int_zones.id_col, "geometry"])

    output_gdfs = []

    if buff_zones is not None:
        buff_gdf = gpd.read_file(buff_zones.shapefile, columns=[buff_zones.id_col, "geometry"])
        buff_zones = join_zones_to_bound(
            buff_gdf, buff_bound, "inside", buff_zones.id_col, buff_zones.name
        )
        output_gdfs.append(buff_zones)
        buff_int_bound = gpd.GeoDataFrame(
            pd.concat([int_bound, buff_bound]), geometry="geometry"
        )
    else:
        buff_int_bound = int_bound

    ext_zones = join_zones_to_bound(
        ext_gdf, buff_int_bound, "outside", ext_zones.id_col, ext_zones.name
    )
    output_gdfs.append(ext_zones)

    int_zones = join_zones_to_bound(
        int_gdf, int_bound, "inside", int_zones.id_col, int_zones.name
    )
    output_gdfs.append(int_zones)

    return gpd.GeoDataFrame(pd.concat(output_gdfs), geometry="geometry")


def main() -> None:
    """Produce new zone system for normits localisation."""
    parameters = _Config.load_yaml(_CONFIG_FILE)
    details = ctk.ToolDetails(_NAME, "0.1.0")
    log_file = pathlib.Path(parameters.output_folder / f"{_NAME}.log")

    with ctk.LogHelper(_NAME, details, log_file=log_file):
        LOG.debug("Config\n%s", parameters.to_yaml())
        LOG.info(
            "Creating localisation zones for %s, with %s as the interal zoning system and %s as the external zoning system.",
            parameters.localisation_area.area_name,
            parameters.zone_systems.internal_zones.name,
            parameters.zone_systems.external_zones.name,
        )

        bound_zones = gpd.read_file(
            parameters.zone_systems.boundary_zones.shapefile,
            columns=[
                parameters.zone_systems.boundary_zones.id_col,
                parameters.localisation_area.selected_colname,
            ],
        )
        bound = bound_zones[
            bound_zones[parameters.localisation_area.selected_colname].isin(
                parameters.localisation_area.selected_lad
            )
        ]
        if parameters.zone_systems.buffer_zones is not None:
            LOG.info(
                "Buffer zone system provided, will create buffer zones for boundary zones directly adjacent to internal boundary."
            )
            buffer_bound = bound_zones[bound_zones.geometry.touches(bound.union_all())]
        else:
            buffer_bound = None

        new_zones = produce_zoning(
            parameters.zone_systems.external_zones,
            parameters.zone_systems.internal_zones,
            parameters.zone_systems.buffer_zones,
            bound,
            buffer_bound,
        )

        new_zones.to_file(
            parameters.output_folder
            / (
                f"zoning_localisation_{parameters.localisation_area.area_name}_"
                f"{parameters.zone_systems.internal_zones.name}.shp"
            ),
            driver="ESRI Shapefile",
        )

        LOG.info(
            "Finished creating localisation zones for %s. There are %s zones in the new zone system.",
            parameters.localisation_area.area_name,
            len(new_zones),
        )


##### MAIN #####
if __name__ == "__main__":
    main()
