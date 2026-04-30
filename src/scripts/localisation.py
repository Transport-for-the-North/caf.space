"""Create a new zone system for normits localisation.

This is done by combining two existing zone systems, one within a specified boundary (internal)
and the other outside of that boundary (external).
An optional buffer zone system can be used for zones directly adjacent to the boundary.
"""

##### IMPORTS #####

import functools
import logging
import pathlib
import pydantic
from pydantic import dataclasses
import pandas as pd
import geopandas as gpd

import caf.toolkit as ctk
from caf.space.inputs import ZoneSystemInfo, TransZoneSystemInfo
from caf.space import ZoneTranslation, ZoningTranslationInputs

##### CONSTANTS #####

_NAME = pathlib.Path(__file__).stem
LOG = logging.getLogger(_NAME)
_CONFIG_FILE = pathlib.Path(__file__).with_suffix(".yml")
_SHAPEFILE_FORMATS = {"shp", "shapefile", "esri shapefile"}
_GPKG_FORMATS = {"gpkg", "geopackage"}

##### CLASSES & FUNCTIONS #####


@dataclasses.dataclass
class Area:
    """Data for selected localisation area."""

    area_name: str
    selected_zones: list[str]
    selected_colname: str


@dataclasses.dataclass
class ZoneSystems:
    """Data for the zone systems to be used."""

    boundary_zones: ZoneSystemInfo
    internal_zones: ZoneSystemInfo
    external_zones: ZoneSystemInfo
    buffer_zones: ZoneSystemInfo


class _Config(ctk.BaseConfig):
    """Config for running localisation zoning script."""

    output_path: pydantic.DirectoryPath
    output_format: str
    localisation_area: Area
    zone_systems: ZoneSystems

    @functools.cached_property
    def output_folder(self) -> pathlib.Path:
        """Folder to save outputs to."""
        folder = self.output_path / f"{self.localisation_area.area_name}_localisation_zones"
        folder.mkdir(exist_ok=True)
        return folder


def select_boundaries(boundary_zones: ZoneSystemInfo, selected_area: Area) -> tuple[gpd.GeoDataFrame, gpd.GeoDataFrame | None]:
    """
    Returns 2 GeoDataFrames for internal and buffer boundary zones for the selected area.
    
    The internal boundary zones consist of the selected area, and the buffer boundary zones are those that are directly adjacent to the internal boundary zones.
    The final internal and buffer boundaries may consist of multiple zones with a unique zone id. 
    """
    bound_zones = gpd.read_file(
        boundary_zones.shapefile,
        columns=[
            boundary_zones.id_col,
            selected_area.selected_colname,
        ],
    )
    bound = bound_zones[
        bound_zones[selected_area.selected_colname].isin(
            selected_area.selected_zones
        )
    ]
    buffer_bound = bound_zones[bound_zones.geometry.touches(bound.union_all())]

    return bound, buffer_bound


def select_zones_in_boundary(boundary: TransZoneSystemInfo, zone_system: TransZoneSystemInfo, overlap_threshold: float = 0.5) -> gpd.GeoDataFrame:
    """
    Select zones from a zone system that fall within a boundary. 

    The boundary may consist of multiple zones with a unique zone id. In some cases a zone from the zone system may fall in between two or more zones of the boundary. 
    In this case, the zone gets assigned to the boundary zone that it has the largest overlap with.

    When a zone falls only partially within the boundary, it only gets selected if the overlap with the boundary exceeds the overlap threshold. 
    """
    config = ZoningTranslationInputs(
        zone_1=zone_system, zone_2=boundary, rounding=False
    )
    trans = ZoneTranslation(config).spatial_translation()

    factor_col = f"{zone_system.name}_to_{boundary.name}"
    id_col = f"{zone_system.name}_id"
    drop_col = f"{boundary.name}_to_{zone_system.name}"

    # Assign zones to boundary zone with which they have the largest overlap
    selection_idx = trans.groupby(id_col)[factor_col].idxmax()
    selection = trans.loc[selection_idx].reset_index(drop=True)

    # Keep only zones which exceed the overlap threshold
    selection = selection[selection[factor_col] > overlap_threshold]
    
    # Join the translation factors to the zone geometries
    zone_gdf = gpd.read_file(zone_system.shapefile, columns=[zone_system.id_col, "geometry"])
    zones = zone_gdf.merge(selection, left_on=zone_system.id_col, right_on=id_col).drop(columns=[drop_col])
    zones = zones.rename(columns = {zone_system.id_col: "zone_id"})

    return zones

def get_output_driver_and_extension(output_format: str) -> tuple[str, str]:
    """Return driver and file extension for the configured output format."""
    normalized = output_format.casefold()

    if normalized in _SHAPEFILE_FORMATS:
        return "ESRI Shapefile", "shp"

    if normalized in _GPKG_FORMATS:
        return "GPKG", "gpkg"

    LOG.warning("Output format %s not recognised, defaulting to geopackage.", output_format)
    return "GPKG", "gpkg"

def to_trans_zone_system(
    zone_info: ZoneSystemInfo,
    override_name: str | None = None,
    override_shapefile: pathlib.Path | None = None,
) -> TransZoneSystemInfo:
    """Convert a ZoneSystemInfo to a TransZoneSystemInfo, with optional overrides."""
    data = zone_info.model_dump()

    if override_name is not None:
        data["name"] = override_name

    if override_shapefile is not None:
        data["shapefile"] = override_shapefile

    return TransZoneSystemInfo(**data)

def write_boundary_files(
    output_folder: pathlib.Path,
    internal_bound: gpd.GeoDataFrame,
    buffer_bound: gpd.GeoDataFrame,
    driver: str,
    extension: str,
) -> tuple[pathlib.Path, pathlib.Path]:
    """Write internal and combined internal+buffer boundary files."""
    internal_path = output_folder / f"internal_boundaries.{extension}"
    combined_path = output_folder / f"internal_and_buffer_boundary.{extension}"


    internal_bound.to_file(internal_path, driver=driver)

    combined_boundaries = pd.concat(
        [internal_bound.assign(boundary="internal"), buffer_bound.assign(boundary="buffer")],
        ignore_index=True,
    )
    combined_boundaries.to_file(combined_path, driver=driver)

    return internal_path, combined_path

def build_localisation_zones(
    internal_zones: gpd.GeoDataFrame,
    buffer_zones: gpd.GeoDataFrame,
    external_zone_system: ZoneSystemInfo,
    boundary_filter_zones: gpd.GeoDataFrame,
    output_folder: pathlib.Path,
    driver: str,
    extension: str,
    debug: bool = False  # to be removed
) -> gpd.GeoDataFrame:
    """Create final localisation zones by removing overlaps from internal and buffer zones."""
    external_zones = gpd.read_file(
        external_zone_system.shapefile,
        columns=[external_zone_system.id_col, "geometry"],
    )

    external_zones = gpd.overlay(external_zones, buffer_zones, how="difference")
    buffer_zones = gpd.overlay(buffer_zones, internal_zones, how="difference")

    # remove boundary zones from external zones, some bits can remain if the buffer zones don't fully cover the same area
    external_zones = external_zones[~external_zones[external_zone_system.id_col].isin(boundary_filter_zones[external_zone_system.id_col])]
    external_zones = external_zones.rename(columns = {external_zone_system.id_col: "zone_id"})

    if debug:
        external_zones.to_file(output_folder / f"external_zones_cut.{extension}", driver)
        buffer_zones.to_file(output_folder / f"buffer_zones_cut.{extension}", driver)

    return pd.concat([external_zones, buffer_zones, internal_zones], ignore_index=True)


def main() -> None:
    """Produce new zone system for normits localisation."""
    parameters = _Config.load_yaml(_CONFIG_FILE)
    details = ctk.ToolDetails(_NAME, "0.1.0")
    log_file = pathlib.Path(parameters.output_folder / f"{_NAME}.log")
    driver, extension = get_output_driver_and_extension(parameters.output_format)

    with ctk.LogHelper(_NAME, details, log_file=log_file):
        LOG.debug("Config\n%s", parameters.to_yaml())
        LOG.info(
            "Creating localisation zones for %s, with %s as the interal zoning system, %s as the buffer zoning system, and %s as the external zoning system.",
            parameters.localisation_area.area_name,
            parameters.zone_systems.internal_zones.name,
            parameters.zone_systems.buffer_zones.name,
            parameters.zone_systems.external_zones.name,
        )

        # Create boundaries for selecting internal and buffer zones
        # and write to files for use in selecting zones
        int_bound, buf_bound = select_boundaries(
            parameters.zone_systems.boundary_zones,
            parameters.localisation_area
            )
        internal_bound_path, internal_and_buffer_path = write_boundary_files(
            parameters.output_folder,
            int_bound,
            buf_bound,
            driver,
            extension,
        )

        # select buffer zones
        buffer_zones = select_zones_in_boundary(
            to_trans_zone_system(
                parameters.zone_systems.boundary_zones,
                override_shapefile=internal_and_buffer_path
            ),
            to_trans_zone_system(parameters.zone_systems.buffer_zones)
        )
        internal_zones = select_zones_in_boundary(
            to_trans_zone_system(
                parameters.zone_systems.boundary_zones,
                override_shapefile=internal_bound_path,
            ),
            to_trans_zone_system(parameters.zone_systems.internal_zones),
        )


        # TEMP: write for checking
        buffer_zones.to_file(parameters.output_folder / f"buffer_zones_with_factors.{extension}", driver=driver)
        # TEMP: write for checking
        internal_zones.to_file(parameters.output_folder / f"internal_zones_with_factors.{extension}", driver=driver)

        # Cut internal zones out of buffer zones and cut buffer zones out of external zones, combine all three for new zone system
        new_zones = build_localisation_zones(
            internal_zones,
            buffer_zones,
            parameters.zone_systems.external_zones,
            pd.concat([int_bound, buf_bound], ignore_index=True),
            parameters.output_folder,
            driver,
            extension,
            debug=True  # to be removed
        )

        new_zones.to_file(
            parameters.output_folder
            / (
                f"zoning_localisation_{parameters.localisation_area.area_name}_"
                f"{parameters.zone_systems.internal_zones.name}.{extension}"
            ),
            driver=driver,
        )

        LOG.info(
            "Finished creating localisation zones for %s. There are %s zones in the new zone system.",
            parameters.localisation_area.area_name,
            len(new_zones),
        )


##### MAIN #####
if __name__ == "__main__":
    main()
