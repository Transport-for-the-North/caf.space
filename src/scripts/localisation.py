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
from caf.space import zone_correspondence
from caf.space.inputs import (
    ZoneSystemInfo,
    TransZoneSystemInfo,
    LowerZoneSystemInfo,
    ZoningTranslationInputs,
)
from caf.space import ZoneTranslation

##### CONSTANTS #####s

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
        """Case insensitive and more flexible strings accepted. Default to geopackage if no match."""
        value = str(value).strip().lower()
        for i in cls:
            if value == i.value:
                return i

        if value in _SHAPEFILE_FORMATS:
            return cls.SHAPEFILE
        if value in _GPKG_FORMATS:
            return cls.GEOPACKAGE
        return cls.GEOPACKAGE

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
        """Read data from csv."""
        data = pd.read_csv(self.csv)

        return data


@dataclasses.dataclass
class ZoneLookup:
    """Lookup table to go from zone_name to zone_id."""

    name: str
    csv: pydantic.FilePath

    def read_data(self) -> pd.DataFrame:
        """Read data from csv."""
        data = pd.read_csv(self.csv)

        return data


class _Config(ctk.BaseConfig):
    """Config for running localisation zoning script."""

    core_zoning_path: pydantic.DirectoryPath
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

    @functools.cached_property
    def core_folder(self) -> pathlib.Path:
        """Folder to save core zoning outputs to."""
        folder = (
            self.core_zoning_path / f"{self.localisation_area.area_name}_local"
        )
        folder.mkdir(exist_ok=True)
        return folder


class CoreZoningConfig(ctk.BaseConfig):
    """"Config used to write zoning_meta.yml for core zoning output, with name, shapefile path and shapefile id column."""

    name: str
    shapefile_path: pathlib.Path
    shapefile_id_col: str


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

    if bound.empty:
        raise ValueError(
            "No boundary zones were selected for localisation. "
            f"Check selected zones {selected_area.selected_zones} for "
            f"column name {selected_area.selected_colname} in {boundary_zones.name} "
            f" with shapefile at {boundary_zones.shapefile}."
        )

    buffer_bound = bound_zones[
        bound_zones.geometry.intersects(bound.union_all().buffer(5))
        & ~bound_zones.geometry.within(bound.union_all())
    ]

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
            "Selected zones from %s that fall within %s boundary. "
            "%s zone(s) were dropped because their overlap with the boundary was lower than the overlap threshold (%s). "
            "Their IDs are: %s and the maximum overlap is %s",
            zone_system.name,
            boundary.name,
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
        [
            internal_bound.assign(boundary="internal"),
            buffer_bound.assign(boundary="buffer"),
        ],
        ignore_index=True,
    )
    combined_boundaries.to_file(combined_path, driver=file.driver)

    return internal_path, combined_path


def build_localisation_zones(
    boundary_zones: ZoneSystemInfo,
    internal_zone_system: ZoneSystemInfo,
    buffer_zone_system: ZoneSystemInfo,
    external_zone_system: ZoneSystemInfo,
    *,
    internal_and_buffer_bound_path: pathlib.Path,
    internal_bound_path: pathlib.Path,
) -> gpd.GeoDataFrame:
    """Create final localisation zones.

    First select zones within boundaries, then use the boundaries to cut out internal zones from buffer zones and
    cut out buffer and internal zones from external zones, to ensure no slivers remain when the different zone systems do not nest perfectly.
    Finally, combine all three for new zone system.
    """
    buffer_zones_in_buffer = select_zones_in_boundary(
        to_trans_zone_system(
            boundary_zones,
            override_shapefile=internal_and_buffer_bound_path,
        ),
        to_trans_zone_system(buffer_zone_system),
    )
    buffer_zones_in_internal = select_zones_in_boundary(
        to_trans_zone_system(
            boundary_zones,
            override_shapefile=internal_bound_path,
        ),
        to_trans_zone_system(buffer_zone_system),
    )
    external_zones_in_boundary = select_zones_in_boundary(
        to_trans_zone_system(
            boundary_zones,
            override_name="boundary",
            override_shapefile=internal_and_buffer_bound_path,
        ),
        to_trans_zone_system(external_zone_system),
    )
    internal_zones = select_zones_in_boundary(
        to_trans_zone_system(
            boundary_zones,
            override_shapefile=internal_bound_path,
        ),
        to_trans_zone_system(internal_zone_system),
    )

    # Remove internal boundary from buffer zones
    buffer_zones = buffer_zones_in_buffer[
        ~buffer_zones_in_buffer["zone_name"].isin(buffer_zones_in_internal["zone_name"])
    ]
    # Remove buffer+internal boundary from external zones
    external_zones = gpd.read_file(
        external_zone_system.shapefile,
        columns=[external_zone_system.id_col, "geometry"],
    )
    external_zones = external_zones[
        ~external_zones[external_zone_system.id_col].isin(
            external_zones_in_boundary["zone_name"]
        )
    ]

    external_zones = external_zones.rename(columns={external_zone_system.id_col: "zone_name"})
    external_zones["zone_system"] = external_zone_system.name
    external_zones = external_zones[["zone_name", "zone_system", external_zones.geometry.name]]

    return pd.concat([external_zones, buffer_zones, internal_zones], ignore_index=True)


def write_core_zoning_lookup(
    output_path: pathlib.Path,
    zones: gpd.GeoDataFrame,
    internal_zone_system_name: str,
    prefix_map: dict[str, int],
    config: CoreZoningConfig,
) -> gpd.GeoDataFrame:
    """Write lookup zone name to zone id for core zoning, write zoning_meta.yml, and return the updated zones GeoDataFrame.

    The zone id is an integer created by combining a prefix based on the zone system (internal, buffer, external) and a sequential number within each zone system.
    The sequential number will be filled to 5 digits, allowing for a maximum of 999,999 zones in each zone system.
    """
    ids = zones[["zone_name", "zone_system"]].copy()

    # Check that all zone systems have a prefix defined
    missing_prefixes = set(ids["zone_system"]) - set(prefix_map)
    if missing_prefixes:
        raise ValueError(
            "Prefix map is missing entries for zone_system(s): "
            f"{', '.join(sorted(missing_prefixes))}"
        )
    ids["prefix"] = ids["zone_system"].map(prefix_map)

    # Combine prefix and sequence number (format: prefix + 5-digit sequential number)
    ids["seq_num"] = ids.groupby("zone_system").cumcount() + 1
    if ids["seq_num"].gt(99999).any():
        too_long = ids.loc[ids["seq_num"].gt(99999), "zone_system"].unique()
        raise ValueError(
            "Sequential numbering exceeded 99999 for zone_system(s): "
            f"{', '.join(too_long)}. "
            "Cannot format with 5-digit zero-padding anymore."
        )
    ids["zone_id"] = (
        ids["prefix"].astype(str) + ids["seq_num"].astype(str).str.zfill(5)
    ).astype(int)

    # Keep only zone_name and zone_id
    ids = ids[["zone_name", "zone_id"]]

    # Create core_zoning lookup integer zone_id to zone_name
    zones = zones.merge(ids, on="zone_name")
    zoning = zones.copy()
    zoning["internal"] = zoning["zone_system"] == internal_zone_system_name
    zoning["external"] = zoning["zone_system"] != internal_zone_system_name
    zoning = zoning[["zone_id", "zone_name", "internal", "external"]]

    zoning.to_csv(output_path / "zoning.csv", index=False)
    config.save_yaml(output_path / "zoning_meta.yml")

    return zones


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
    else:
        config = ZoningTranslationInputs(
            zone_1=new_zs,
            zone_2=target_zs,
            lower_zoning=lower_zone_system,
            method=method,
        )
        lookup = ZoneTranslation(config).weighted_translation()

    if output_path is not None:
        lookup.to_csv(output_path)

    return lookup


def create_combined_lookup(
    new_zone_system: ZoneSystemInfo,
    target_zone_system: ZoneSystemInfo,
    *,
    emp_zone_system: LowerZoneSystemInfo | None = None,
    pop_zone_system: LowerZoneSystemInfo | None = None,
    lookup_additionals: LookupAdditionals | None = None,
    zone_lookup: ZoneLookup | None = None,
    output_path: pathlib.Path | None = None,
) -> pd.DataFrame:
    """Create combined lookup of spatial translation and population and/or employment weighted translations.

    Optional additional columns.
    Only writes to csv if output_path is given, always returns the combined lookup as a DataFrame.
    """

    factor_cols = [
        f"{new_zone_system.name}_to_{target_zone_system.name}",
        f"{target_zone_system.name}_to_{new_zone_system.name}",
    ]
    id_cols = [f"{new_zone_system.name}_id", f"{target_zone_system.name}_id"]

    lookup = create_translation_lookup(new_zone_system, target_zone_system)
    lookup_og = {"spatial": lookup}
    lookup = lookup.rename(columns={col: f"{col}_spatial" for col in factor_cols})

    if emp_zone_system is not None:
        lookup_emp = create_translation_lookup(
            new_zone_system, target_zone_system, emp_zone_system, method="emp"
        )
        lookup_og["emp"] = lookup_emp
        lookup_emp = lookup_emp.rename(columns={col: f"{col}_emp" for col in factor_cols})
        lookup = lookup.merge(lookup_emp, how="outer", on=id_cols)

    if pop_zone_system is not None:
        lookup_pop = create_translation_lookup(
            new_zone_system, target_zone_system, pop_zone_system, method="pop"
        )
        lookup_og["pop"] = lookup_pop
        lookup_pop = lookup_pop.rename(columns={col: f"{col}_pop" for col in factor_cols})
        lookup = lookup.merge(lookup_pop, how="outer", on=id_cols)

    # Check differences / non-matches:
    non_matched = lookup[lookup.isna().any(axis=1)]
    if not non_matched.empty:
        LOG.warning(
            "Certain zones were not matched in each of the lookups and will be dropped from all."
        )
        lookup = normalise_lookup(
            lookup_og, non_matched, new_zone_system.name, target_zone_system.name
        )


    if lookup_additionals is not None:
        if zone_lookup is None:
            LOG.warning(
                "No zone lookup provided, unable to join additional columns to lookup."
            )
        else:
            lookup.rename(columns={f"{target_zone_system.name}_id": f"{target_zone_system.name}_id_string"}, inplace=True)
            lookup = add_lookup_cols(
                lookup, lookup_additionals, zone_lookup, f"{target_zone_system.name}_id_string"
            )

    if output_path is not None:
        lookup.to_csv(
            output_path / f"lookup_{new_zone_system.name}_to_{target_zone_system.name}.csv",
            index=False,
        )
        LOG.info(
            "Combined lookup with spatial and weighted translations and additional columns written to %s",
            output_path,
        )

    return lookup


def normalise_lookup(
    lookup_dict: dict[str, pd.DataFrame],
    non_matched: pd.DataFrame,
    from_name: str,
    to_name: str,
) -> pd.DataFrame:
    """Normalise a lookup with multiple translation types to make sure all factors round to 1 after removing nan values."""
    id_cols = [f"{from_name}_id", f"{to_name}_id"]
    non_matched_pairs = set(non_matched[id_cols].apply(tuple, axis=1))

    # Process rows that were not fully matched by rounding each available translation type.
    rounded_non_matched_parts = []
    for translation_type, lookup_data in lookup_dict.items():
        remaining = lookup_data.loc[
            ~lookup_data[id_cols].apply(tuple, axis=1).isin(non_matched_pairs)
        ]

        rounded = zone_correspondence.round_zone_correspondence(
            remaining,
            zone_names=(from_name, to_name),
        )
        rounded = rounded.rename(
            columns={
                f"{from_name}_to_{to_name}": f"{from_name}_to_{to_name}_{translation_type}",
                f"{to_name}_to_{from_name}": f"{to_name}_to_{from_name}_{translation_type}",
            }
        )
        rounded_non_matched_parts.append(rounded)

    lookup_rounded = functools.reduce(
        lambda left, right: left.merge(right, on=id_cols, how="outer"),
        rounded_non_matched_parts,
    )
    return lookup_rounded


def add_lookup_cols(
    lookup: pd.DataFrame,
    additionals: LookupAdditionals,
    zone_lookup: ZoneLookup,
    join_name: str,
) -> pd.DataFrame:
    """Add additional columns to lookup by joining through zone name."""
    adds = additionals.read_data()
    adds = adds.drop_duplicates()
    zone_id_to_name = zone_lookup.read_data()[["zone_id", "zone_name"]]
    adds = adds.merge(
        zone_id_to_name,
        how="inner",
        left_on=additionals.id_col,
        right_on="zone_id",
    )
    new_lookup = lookup.merge(
        adds,
        how="left",
        left_on=join_name,
        right_on="zone_name",
    )
    return new_lookup.drop(["zone_id", "zone_name"], axis=1)


def main() -> None:
    """Produce new zone system for normits localisation."""
    parameters = _Config.load_yaml(_CONFIG_FILE)
    details = ctk.ToolDetails(_NAME, "0.1.0")
    log_file = pathlib.Path(parameters.output_folder / f"{_NAME}.log")

    with ctk.LogHelper(_NAME, details, log_file=log_file):
        LOG.debug("Config\n%s", parameters.to_yaml())
        LOG.info(
            "Creating localisation zones for %s, with %s as the internal zoning system, %s as the buffer zoning system, and %s as the external zoning system.",
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
            file=parameters.output_format,
        )

        # Select zones within boundaries and cut out internal from buffer and internal+buffer from external,
        # Combine all three for new zone system
        LOG.info(
            "Selecting zones that fall within the boundaries and building new zone system, this might take a while.",
        )
        new_zones = build_localisation_zones(
            parameters.zone_systems.boundary_zones,
            parameters.zone_systems.internal_zones,
            parameters.zone_systems.buffer_zones,
            parameters.zone_systems.external_zones,
            internal_and_buffer_bound_path=internal_and_buffer_bound_path,
            internal_bound_path=internal_bound_path,
        )

        # Create integer zone_id for new zoning and write core zoning lookup + zoning_meta.
        new_zones_path = parameters.output_folder / (
            f"zoning_{parameters.localisation_area.area_name}_local_"
            f"{parameters.zone_systems.internal_zones.name}.{parameters.output_format.suffix}"
        )
        zoning_meta = CoreZoningConfig(
            name=f"{parameters.localisation_area.area_name}_local",
            shapefile_path=new_zones_path,
            shapefile_id_col="zone_id",
        )
        prefix_map = {
            parameters.zone_systems.internal_zones.name: 10,
            parameters.zone_systems.buffer_zones.name: 20,
            parameters.zone_systems.external_zones.name: 30,
        }
        new_zones = write_core_zoning_lookup(
            parameters.core_folder,
            new_zones,
            parameters.zone_systems.internal_zones.name,
            prefix_map,
            zoning_meta
        )
        new_zones.to_file(
            new_zones_path,
            driver=parameters.output_format.driver,
        )

        # create lookup if target zone system is provided
        if parameters.zone_systems.target_zones is not None:
            LOG.info(
                "Creating lookup for new zone system to target zone system, this might take a while."
            )
            # Create final lookup from new zone system to target zone system
            new_zs = ZoneSystemInfo(
                name=f"{parameters.localisation_area.area_name}_local",
                shapefile=new_zones_path,
                id_col="zone_id",
            )
            # Check if a combined lookup is necessary:
            if all(
                i is None
                for i in [
                    parameters.zone_systems.weight_zones_emp,
                    parameters.zone_systems.weight_zones_pop,
                    parameters.lookup_additionals,
                ]
            ):
                lookup = create_translation_lookup(
                    new_zs, parameters.zone_systems.target_zones
                )
            else:
                lookup = create_combined_lookup(
                    new_zs,
                    parameters.zone_systems.target_zones,
                    emp_zone_system=parameters.zone_systems.weight_zones_emp,
                    pop_zone_system=parameters.zone_systems.weight_zones_pop,
                    lookup_additionals=parameters.lookup_additionals,
                    zone_lookup=parameters.zone_lookup,
                )
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
