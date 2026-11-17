"""Tests for the inputs module."""

# Built-Ins
from pathlib import Path

# Third Party
import geopandas as gpd
import pandas as pd
import pytest
from shapely.geometry import Point

# Local Imports
import caf.space as cspace


@pytest.fixture(name="points_gdf")
def fixture_points_gdf() -> gpd.GeoDataFrame:
    """Simple points GeoDataFrame used for GeoDataFile read tests."""
    return gpd.GeoDataFrame(
        {"point_id": [1, 2, 3], "value": [10, 20, 30]},
        geometry=[Point(0, 0), Point(1, 0), Point(2, 0)],
        crs="EPSG:27700",
    )


@pytest.fixture(name="points_shapefile")
def fixture_points_shapefile(main_dir: Path, points_gdf: gpd.GeoDataFrame) -> Path:
    """Write test points to a Shapefile and return the path."""
    path = main_dir / "test_points.shp"
    points_gdf.to_file(path)
    return path


@pytest.fixture(name="points_geojson")
def fixture_points_geojson(main_dir: Path, points_gdf: gpd.GeoDataFrame) -> Path:
    """Write test points to a GeoJSON file and return the path."""
    path = main_dir / "test_points.geojson"
    points_gdf.to_file(path, driver="GeoJSON")
    return path


@pytest.fixture(name="points_geopackage")
def fixture_points_geopackage(
    main_dir: Path, points_gdf: gpd.GeoDataFrame
) -> tuple[Path, str]:
    """Write test points to a GeoPackage and return path/layer."""
    path = main_dir / "test_points.gpkg"
    layer = "points"
    points_gdf.to_file(path, layer=layer, driver="GPKG")
    return path, layer


class TestGeoDataFile:
    """Test GeoDataFile class."""

    @pytest.mark.parametrize("fixture_name", ["points_shapefile", "points_geojson"])
    def test_reads_points_data(
        self,
        request: pytest.FixtureRequest,
        fixture_name: str,
        points_gdf: gpd.GeoDataFrame,
    ) -> None:
        """GeoDataFile should read point data for file-based formats."""
        path = request.getfixturevalue(fixture_name)
        actual = cspace.GeoDataFile(path=path, columns=["point_id", "value"]).read()

        assert actual.geom_type.eq("Point").all()
        pd.testing.assert_series_equal(
            actual["point_id"].reset_index(drop=True),
            points_gdf["point_id"].reset_index(drop=True),
            check_dtype=False,
        )
        pd.testing.assert_series_equal(
            actual["value"].reset_index(drop=True),
            points_gdf["value"].reset_index(drop=True),
            check_dtype=False,
        )

    def test_reads_points_data_from_geopackage(
        self,
        points_geopackage: tuple[Path, str],
        points_gdf: gpd.GeoDataFrame,
    ) -> None:
        """GeoDataFile should read point data from a specific GeoPackage layer."""
        path, layer = points_geopackage
        actual = cspace.GeoDataFile(
            path=path, layer=layer, columns=["point_id", "value"]
        ).read()

        assert actual.geom_type.eq("Point").all()
        pd.testing.assert_series_equal(
            actual["point_id"].reset_index(drop=True),
            points_gdf["point_id"].reset_index(drop=True),
            check_dtype=False,
        )
        pd.testing.assert_series_equal(
            actual["value"].reset_index(drop=True),
            points_gdf["value"].reset_index(drop=True),
            check_dtype=False,
        )

    @pytest.mark.parametrize("fixture_name", ["points_shapefile", "points_geojson"])
    def test_raises_for_missing_columns(
        self, request: pytest.FixtureRequest, fixture_name: str
    ) -> None:
        """GeoDataFile should raise if requested columns are not present."""
        path = request.getfixturevalue(fixture_name)

        with pytest.raises(ValueError, match="Column\\(s\\).*not found"):
            cspace.GeoDataFile(path=path, columns=["point_id", "missing_col"]).read()

    def test_raises_for_missing_columns_in_geopackage(
        self,
        points_geopackage: tuple[Path, str],
    ) -> None:
        """GeoDataFile should raise for missing columns in GeoPackage layers."""
        path, layer = points_geopackage

        with pytest.raises(ValueError, match="Column\\(s\\).*not found"):
            cspace.GeoDataFile(
                path=path, layer=layer, columns=["point_id", "missing_col"]
            ).read()
