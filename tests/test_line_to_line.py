"""Tests for line-to-line functionality."""

# Built-Ins
from pathlib import Path

# Third Party
import geopandas as gpd
import pandas as pd
import pytest
from shapely.geometry import Point

# Local Imports
from caf.space import GeoDataFile, line_to_line


def test_geodatafile_raises_for_missing_columns_in_gpkg(tmp_path: Path):
    """GeoDataFile should fail fast when requested columns do not exist."""
    data = gpd.GeoDataFrame(
        {"a": [0, 1, 2]},
        geometry=[Point(0, 0), Point(1, 0), Point(2, 0)],
        crs="EPSG:27700",
    )
    path = tmp_path / "test.gpkg"
    layer = "test_layer"
    data.to_file(path, layer=layer, driver="GPKG")

    with pytest.raises(ValueError, match="Column\\(s\\).*not found"):
        GeoDataFile(path=path, layer=layer, columns=["a", "missing_column"]).read()


@pytest.mark.parametrize(
    "overlap_values,error_pattern",
    [
        ([12.0], "greater than target length"),
        ([0.0], "zero overlap length"),
        ([float('nan')], "invalid overlap length values"),
    ],
)
def test_warn_on_quality_issues(overlap_values, error_pattern):
    """Quality warnings should be raised for each problematic overlap type."""
    index = pd.MultiIndex.from_tuples([("ref_1", "target_1")], names=["id_ref", "id_targ"])
    results = pd.DataFrame(
        {"length_targ": [10.0], "overlap_length": overlap_values},
        index=index,
    )

    with pytest.warns(RuntimeWarning, match=error_pattern):
        line_to_line._warn_on_quality_issues(results, "target")


def test_length_stats_handles_empty_results():
    """Length stats should not fail when no correspondence rows are present."""
    empty_index = pd.MultiIndex.from_arrays(
        [pd.Index([], dtype="object"), pd.Index([], dtype="object")],
        names=["id_ref", "id_targ"],
    )
    results = pd.DataFrame(
        {"length_targ": pd.Series(dtype=float), "overlap_length": pd.Series(dtype=float)},
        index=empty_index,
    )

    stats = line_to_line._length_stats(results, "id_targ")
    assert stats == "No correspondence results to summarise."
