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
    buffer_zones: ZoneSystemInfo | None = None


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

    return zones

def main() -> None:
    """Produce new zone system for normits localisation."""
    parameters = _Config.load_yaml(_CONFIG_FILE)
    details = ctk.ToolDetails(_NAME, "0.1.0")
    log_file = pathlib.Path(parameters.output_folder / f"{_NAME}.log")

    with ctk.LogHelper(_NAME, details, log_file=log_file):
        LOG.debug("Config\n%s", parameters.to_yaml())
        LOG.info(
            "Creating localisation zones for %s, with %s as the interal zoning system, %s as the buffer zoning system, and %s as the external zoning system.",
            parameters.localisation_area.area_name,
            parameters.zone_systems.internal_zones.name,
            parameters.zone_systems.buffer_zones.name,
            parameters.zone_systems.external_zones.name,
        )

        extension: str = "gpkg"
        driver: str = "GPKG"

        if parameters.output_format.lower() in ["shp", "shapefile", "esri shapefile"]:
            extension = "shp"
            driver = "ESRI Shapefile"
        elif parameters.output_format.lower() not in ["gpkg", "geopackage"]:
            LOG.warning(
                "Output format %s not recognised, defaulting to geopackage.",
                parameters.output_format,
            )

        # Create boundaries for selecting internal and buffer zones
        # AM: Could write boundaries to files directly inside the function?
        int_bound, buf_bound = select_boundaries(
            parameters.zone_systems.boundary_zones,
            parameters.localisation_area
            )
        int_bound_filename = f"internal_boundaries.{extension}"
        int_buf_bound_filename = f"internal_and_buffer_boundary.{extension}"
        int_bound.to_file(parameters.output_folder 
                            / int_bound_filename,
                            driver=driver
                            )
        # Combine internal and buffer boundaries for selecting buffer zones, added column indicating which is which
        int_bound["boundary"] = "internal"
        buf_bound["boundary"] = "buffer"
        pd.concat([int_bound, buf_bound]).to_file(parameters.output_folder
                            / int_buf_bound_filename,
                            driver=driver
                            )

        # select buffer zones
        trans_buffer_zones = TransZoneSystemInfo(**parameters.zone_systems.buffer_zones.model_dump())
        trans_bound_zones = TransZoneSystemInfo(
            name=parameters.zone_systems.boundary_zones.name,
            shapefile=parameters.output_folder / int_buf_bound_filename,
            id_col=parameters.zone_systems.boundary_zones.id_col
        )
        buffer_zones = select_zones_in_boundary(trans_bound_zones, trans_buffer_zones)
        # TEMP: write for checking
        buffer_zones.to_file(parameters.output_folder / f"buffer_zones_with_factors.{extension}", driver=driver)

        # select internal zones
        trans_int_zones = TransZoneSystemInfo(**parameters.zone_systems.internal_zones.model_dump())
        trans_int_bound_zones = TransZoneSystemInfo(
            name=parameters.zone_systems.boundary_zones.name,
            shapefile=parameters.output_folder / int_bound_filename,
            id_col=parameters.zone_systems.boundary_zones.id_col
        )
        internal_zones = select_zones_in_boundary(trans_int_bound_zones, trans_int_zones)
        # TEMP: write for checking
        internal_zones.to_file(parameters.output_folder / f"internal_zones_with_factors.{extension}", driver=driver)

        # Cut internal zones out of buffer zones and cut buffer zones out of external zones, combine all three for new zone system
        # AM: this in a separate function?
        external_zones = gpd.read_file(parameters.zone_systems.external_zones.shapefile, columns=[parameters.zone_systems.external_zones.id_col, "geometry"])
        external_zones = gpd.overlay(external_zones, buffer_zones, how="difference")
        buffer_zones = gpd.overlay(buffer_zones, internal_zones, how="difference")
        # TEMP: write for checking
        external_zones.to_file(parameters.output_folder / f"external_zones_cut.{extension}", driver=driver)        
        buffer_zones.to_file(parameters.output_folder / f"buffer_zones_cut.{extension}", driver=driver)

        new_zones = pd.concat([external_zones, buffer_zones, internal_zones])
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
