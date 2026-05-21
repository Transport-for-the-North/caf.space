"""Create a new zone system for normits localisation.

This is done by combining two existing zone systems, one within a specified boundary (internal)
and the other outside of that boundary (external).
An optional buffer zone system can be used for zones directly adjacent to the boundary.
"""

##### IMPORTS #####

import enum
import functools
import logging
import pathlib
import pydantic
from pydantic import dataclasses
import pandas as pd
import geopandas as gpd

import caf.toolkit as ctk
from caf.space.inputs import ZoneSystemInfo, TransZoneSystemInfo, LowerZoneSystemInfo
from caf.space import ZoneTranslation, ZoningTranslationInputs

##### CONSTANTS #####

_NAME = pathlib.Path(__file__).stem
LOG = logging.getLogger(_NAME)
_CONFIG_FILE = pathlib.Path(__file__).with_suffix(".yml")
_SHAPEFILE_FORMATS = {"shp", "shapefile", "esri shapefile"}
_GPKG_FORMATS = {"gpkg", "geopackage"}

##### CLASSES & FUNCTIONS #####


class FileFormat(enum.StrEnum):
    """GIS file formats."""

    GEOPACKAGE = enum.auto()
    SHAPEFILE = enum.auto()

    @classmethod
    def _missing_(cls, value) -> "FileFormat":
        """Case insensitive and more flexible strings accepted."""
        value = str(value).strip().lower()
        for i in cls:
            if value == i.value:
                return i

        if value in _SHAPEFILE_FORMATS:
            return cls.SHAPEFILE
        if value in _GPKG_FORMATS:
            return cls.GEOPACKAGE
        return None

    @property
    def driver(self) -> str:
        """File format IO driver."""
        lookup = {FileFormat.GEOPACKAGE: "GPKG", FileFormat.SHAPEFILE: "ESRI Shapefile"}
        return lookup[self]

    @property
    def suffix(self) -> str:
        """Path suffix (extension) for this format."""
        lookup = {FileFormat.GEOPACKAGE: "gpkg", FileFormat.SHAPEFILE: "shp"}
        return lookup[self]


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
    target_zones: ZoneSystemInfo | None
    weight_zones_emp: LowerZoneSystemInfo | None
    weight_zones_pop: LowerZoneSystemInfo | None

@dataclasses.dataclass
class LookupAdditionals:
    """Data to be added to the final zone lookup."""

    name: str
    csv: pydantic.FilePath
    id_col: str

    def read_data(self) -> pd.DataFrame:
        data = pd.read_csv(self.csv)

        return data

@dataclasses.dataclass
class ZoneLookup:
    """Lookup table to go from zone_name to zone_id."""
    
    name: str
    csv: pydantic.FilePath

    def read_data(self) -> pd.DataFrame:
        data = pd.read_csv(self.csv)

        return data

class _Config(ctk.BaseConfig):
    """Config for running localisation zoning script."""

    output_path: pydantic.DirectoryPath
    output_format: FileFormat
    localisation_area: Area
    zone_systems: ZoneSystems
    lookup_additionals: LookupAdditionals | None = None
    zone_lookup: ZoneLookup | None = None 

    @functools.cached_property
    def output_folder(self) -> pathlib.Path:
        """Folder to save outputs to."""
        folder = self.output_path / f"{self.localisation_area.area_name}_localisation_zones"
        folder.mkdir(exist_ok=True)
        return folder


def select_boundaries(
    boundary_zones: ZoneSystemInfo, selected_area: Area
) -> tuple[gpd.GeoDataFrame, gpd.GeoDataFrame | None]:
    """
    Return 2 GeoDataFrames for internal and buffer boundary zones for the selected area.

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
        bound_zones[selected_area.selected_colname].isin(selected_area.selected_zones)
    ]
    buffer_bound = bound_zones[bound_zones.geometry.touches(bound.union_all())]

    return bound, buffer_bound


def select_zones_in_boundary(
    boundary: TransZoneSystemInfo,
    zone_system: TransZoneSystemInfo,
    overlap_threshold: float = 0.5,
) -> gpd.GeoDataFrame:
    """
    Select zones from a zone system that fall within a boundary.

    The boundary may consist of multiple zones with a unique zone id. In some cases a zone from the zone system may fall in between two or more zones of the boundary.
    In this case, the zone gets assigned to the boundary zone that it has the largest overlap with.

    When a zone falls only partially within the boundary, it is removed if the overlap with the boundary is lower than the overlap threshold.
    """
    config = ZoningTranslationInputs(zone_1=zone_system, zone_2=boundary, rounding=False)
    trans = ZoneTranslation(config).spatial_translation()

    factor_col = f"{zone_system.name}_to_{boundary.name}"
    id_col = f"{zone_system.name}_id"

    # Assign zones to boundary zone with which they have the largest overlap
    selection_idx = trans.groupby(id_col)[factor_col].idxmax()
    selection = trans.loc[selection_idx].reset_index(drop=True)

    # Drop zones with overlap lower than the overlap threshold
    dropped_zones = selection[selection[factor_col] < overlap_threshold]
    selection = selection[selection[factor_col] >= overlap_threshold]

    if len(dropped_zones) > 0:
        LOG.warning(
            "%s zone(s) were dropped because their overlap with the boundary was lower than the overlap threshold (%s). "
            "Their IDs are: %s and the maximum overlap is %s",
            len(dropped_zones),
            overlap_threshold,
            (", ".join(str(zoneid) for zoneid in dropped_zones[id_col].values)),
            round(dropped_zones[factor_col].max(), 3),
        )

    # Join the translation factors to the zone geometries
    zone_gdf = gpd.read_file(zone_system.shapefile, columns=[zone_system.id_col, "geometry"])
    zones = zone_gdf.merge(selection, left_on=zone_system.id_col, right_on=id_col)
    zones = zones.rename(columns={zone_system.id_col: "zone_name"})
    zones["zone_system"] = zone_system.name
    zones = zones[["zone_name", "zone_system", zones.geometry.name]]

    return zones


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
    file: FileFormat,
) -> tuple[pathlib.Path, pathlib.Path]:
    """Write internal and combined internal+buffer boundary files."""
    internal_path = output_folder / f"internal_boundaries.{file.suffix}"
    combined_path = output_folder / f"internal_and_buffer_boundary.{file.suffix}"

    internal_bound.to_file(internal_path, driver=file.driver)

    combined_boundaries = pd.concat(
        [internal_bound.assign(boundary="internal"), buffer_bound.assign(boundary="buffer")],
        ignore_index=True,
    )
    combined_boundaries.to_file(combined_path, driver=file.driver)

    return internal_path, combined_path


def build_localisation_zones(
    internal_zones: gpd.GeoDataFrame,
    buffer_zones: gpd.GeoDataFrame,
    external_zone_system: ZoneSystemInfo,
    boundary_filter_zones: gpd.GeoDataFrame,
) -> gpd.GeoDataFrame:
    """Create final localisation zones by removing overlaps from internal and buffer zones."""
    external_zones = gpd.read_file(
        external_zone_system.shapefile,
        columns=[external_zone_system.id_col, "geometry"],
    )

    external_zones = gpd.overlay(external_zones, buffer_zones, how="difference")
    buffer_zones = gpd.overlay(buffer_zones, internal_zones, how="difference")

    # Remove boundary zones from external zones, otherwise some slivers might remain within the buffer area
    external_zones = external_zones[
        ~external_zones[external_zone_system.id_col].isin(
            boundary_filter_zones[external_zone_system.id_col]
        )
    ]
    external_zones = external_zones.rename(columns={external_zone_system.id_col: "zone_name"})
    external_zones["zone_system"] = external_zone_system.name
    external_zones = external_zones[["zone_name", "zone_system", external_zones.geometry.name]]

    return pd.concat([external_zones, buffer_zones, internal_zones], ignore_index=True)

#def write_core_zoning_lookup(
#        output_path: pathlib.Path,
#        new_zone_system: ZoneSystemInfo
#) -> None:
#    """Write lookup zone name to zone id for core zoning."""

def create_translation_lookup(
    new_zone_system: ZoneSystemInfo,
    target_zone_system: ZoneSystemInfo,
    lower_zone_system: LowerZoneSystemInfo | None = None,
    method: str | None = None,
    output_path: pathlib.Path | None = None,
) -> pd.DataFrame:
    """Return and, if path is given, write spatial or weighted translation lookup new zone system to target zone system."""

    new_zs = to_trans_zone_system(new_zone_system)
    target_zs = to_trans_zone_system(target_zone_system)

    if lower_zone_system is None:
        config = ZoningTranslationInputs(zone_1=new_zs, zone_2=target_zs)
        lookup = ZoneTranslation(config).spatial_translation()
    elif lower_zone_system is not None:
        config = ZoningTranslationInputs(zone_1=new_zs, zone_2=target_zs, lower_zoning=lower_zone_system, method=method)
        lookup = ZoneTranslation(config).weighted_translation()

    if output_path is not None:
        lookup.to_csv(output_path)
   
    return lookup

def create_combined_lookup(
    new_zone_system: ZoneSystemInfo,
    target_zone_system: ZoneSystemInfo,
    emp_zone_system: LowerZoneSystemInfo | None = None,
    pop_zone_system: LowerZoneSystemInfo | None = None,
    lookup_additionals: LookupAdditionals | None = None,
    zone_lookup: ZoneLookup | None = None,
    output_path: pathlib.Path | None = None
) -> pd.DataFrame:
    """Create and write combined lookup of spatial translation and population and/or employment weighted translations. Optional additional columns."""

    lookup_spatial = create_translation_lookup(new_zone_system, target_zone_system)
    lookup = lookup_spatial.rename(columns={col: f"{col}_spatial" for col in lookup_spatial.columns[-2:]})

    if emp_zone_system is not None:
        lookup_emp = create_translation_lookup(new_zone_system, target_zone_system, emp_zone_system, method="emp")
        lookup_emp = lookup_emp.rename(columns={col: f"{col}_emp" for col in lookup_emp.columns[-2:]})
        lookup = lookup.merge(lookup_emp, how="outer", on=[f"{new_zone_system.name}_id", f"{target_zone_system.name}_id"])
        # Check differences / non-matches:
        non_matched_emp = lookup[lookup.iloc[:, -4:].isna().any(axis=1)]
        LOG.warning(
            "Following zone(s) do not have a match between the spatial and employment weighted translation: %s",
            ", ".join(non_matched_emp[f"{target_zone_system.name}_name"].unique())
        )

    if pop_zone_system is not None:
        lookup_pop = create_translation_lookup(new_zone_system, target_zone_system, pop_zone_system, method="pop")
        lookup_pop = lookup_pop.rename(columns={col: f"{col}_pop" for col in lookup_pop.columns[-2:]})
        lookup = lookup.merge(lookup_pop, how="outer", on=[f"{new_zone_system.name}_name", f"{target_zone_system.name}_name"], suffixes=(None, "_pop"))
        # Check differences / non-matches:
        non_matched_pop = lookup[lookup.iloc[:, -4:].isna().any(axis=1)]
        LOG.warning(
            "Following zone(s) do not have a match between the spatial and population weighted translation: %s",
            ", ".join(non_matched_pop[f"{target_zone_system.name}_name"].unique())
        )

    if lookup_additionals is not None:
        if zone_lookup is None:
            LOG.warning("No zone lookup provided, unable to join additional columns to lookup.")
        else:
            adds = lookup_additionals.read_data()
            zone_id_to_name = zone_lookup.read_data()
            adds = adds.merge(zone_id_to_name, left_on=lookup_additionals.id_col, right_on="zone_name")
            lookup = lookup.merge(adds, left_on= f"{target_zone_system.name}_name", right_on="zone_name")

    if output_path is not None:
        lookup.to_csv(output_path)

    return lookup


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
            parameters.zone_systems.boundary_zones, parameters.localisation_area
        )
        internal_bound_path, internal_and_buffer_bound_path = write_boundary_files(
            parameters.output_folder,
            int_bound,
            buf_bound,
            driver,
            extension,
        )

        # Select buffer and internal zones
        buffer_zones = select_zones_in_boundary(
            to_trans_zone_system(
                parameters.zone_systems.boundary_zones,
                override_shapefile=internal_and_buffer_path,
            ),
            to_trans_zone_system(parameters.zone_systems.buffer_zones),
        )
        internal_zones = select_zones_in_boundary(
            to_trans_zone_system(
                parameters.zone_systems.boundary_zones,
                override_shapefile=internal_bound_path,
            ),
            to_trans_zone_system(parameters.zone_systems.internal_zones),
        )

        # Cut internal zones out of buffer zones and cut buffer zones out of external zones, combine all three for new zone system
        new_zones = build_localisation_zones(
            internal_zones,
            buffer_zones,
            parameters.zone_systems.external_zones,
            pd.concat([int_bound, buf_bound], ignore_index=True),
        )

        new_zones_path = parameters.output_folder / (
            f"zoning_{parameters.localisation_area.area_name}_local_"
            f"{parameters.zone_systems.internal_zones.name}.{extension}"
        )
        new_zones.to_file(
            new_zones_path,
            driver=driver,
        )

        if parameters.zone_systems.target_zones is not None:
            # Create final lookup from new zone system to target zone system
            new_zs = ZoneSystemInfo(
                name=f"{parameters.localisation_area.area_name}_local", shapefile=new_zones_path, id_col="zone_name"
            )
            # Check if a combined lookup is necessary:
            if all(i is None for i in [
                parameters.zone_systems.weight_zones_emp,
                parameters.zone_systems.weight_zones_pop,
                parameters.lookup_additionals
            ]):
                lookup = create_translation_lookup(new_zs, parameters.zone_systems.target_zones)
            else:
                lookup = create_combined_lookup(
                    new_zs,
                    parameters.zone_systems.target_zones,
                    parameters.zone_systems.weight_zones_emp,
                    parameters.zone_systems.weight_zones_pop,
                    parameters.lookup_additionals,
                    parameters.zone_lookup
                )
            # TODO: add the conversion to zone_id integers instead of zone_name
            lookup.to_csv(
                (
                    parameters.output_folder
                    / (
                        f"lookup_{parameters.localisation_area.area_name}_local_"
                        f"{parameters.zone_systems.target_zones.name}.csv"
                    )
                )
            )

        LOG.info(
            "Finished creating localisation zones for %s. There are %s zones in the new zone system.",
            parameters.localisation_area.area_name,
            len(new_zones),
        )


##### MAIN #####
if __name__ == "__main__":
    main()
