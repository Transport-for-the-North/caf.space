from pathlib import Path
import sys

# Ensure repository root is on sys.path so `caf` package can be imported
# when this module is executed from inside the `app` folder.
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
# Also add `src/` if package sources are under a top-level `src` dir
SRC_DIR = ROOT / "src"
if SRC_DIR.exists():
    sys.path.insert(0, str(SRC_DIR))

from dash import Dash, html, dcc, Input, Output, callback
from caf.space import zone_translation, inputs
from layouts.main import create_main_layout
import geopandas as gpd


def create_app():
    app = Dash(__name__)

    app.layout = create_main_layout()

    @callback(
        Output("z1_col_name", "options"),
        Input("z1_shapefile", "value")
    )
    def update_z1_col_options(filepath):
        """Update Zone 1 column dropdown based on selected shapefile."""
        if not filepath or not Path(filepath).exists():
            return []
        try:
            columns = gpd.read_file(filepath).columns.tolist()
            return [{"label": col, "value": col} for col in columns]
        except Exception as e:
            print(f"Error reading shapefile: {e}")
            return []

    @callback(
        Output("z2_col_name", "options"),
        Input("z2_shapefile", "value")
    )
    def update_z2_col_options(filepath):
        """Update Zone 2 column dropdown based on selected shapefile."""
        if not filepath or not Path(filepath).exists():
            return []
        try:
            columns = gpd.read_file(filepath).columns.tolist()
            return [{"label": col, "value": col} for col in columns]
        except Exception as e:
            print(f"Error reading shapefile: {e}")
            return []
        
    @callback(
        Output("translation_output", "children"),
        Input("run_translation_button", "n_clicks"),
        Input("z1_zone_name", "value"),
        Input("z1_shapefile", "value"),
        Input("z1_col_name", "value"),
        Input("z2_zone_name", "value"),
        Input("z2_shapefile", "value"),
        Input("z2_col_name", "value"),
    )
    def create_yaml(n_clicks, z1_zone_name, z1_shapefile, z1_col_name, z2_zone_name, z2_shapefile, z2_col_name):
        """Run translation using `ZoneTranslation` and display output path or errors."""
        if not n_clicks:
            return ""

        if not all([z1_zone_name, z1_shapefile, z1_col_name, z2_zone_name, z2_shapefile, z2_col_name]):
            return "Please select all inputs before running translation."

        try:
            # Construct minimal zone system inputs. Use model_construct to avoid
            # strict validation during UI-driven runs; keep Path types for code that expects them.
            zone1 = inputs.TransZoneSystemInfo.model_construct(
                name=str(z1_zone_name),
                shapefile=Path(z1_shapefile),
                id_col=str(z1_col_name),
                point_shapefile=None,
            )
            zone2 = inputs.TransZoneSystemInfo.model_construct(
                name=str(z2_zone_name),
                shapefile=Path(z2_shapefile),
                id_col=str(z2_col_name),
                point_shapefile=None,
            )

            cache_dir = Path(".")
            # If user provided a cache_path input in the UI, prefer that; fall back to default in inputs.
            try:
                cache_elem = Path(dcc.callback_context.states.get("cache_path.value", "") or "")
            except Exception:
                cache_elem = None
            if cache_elem and cache_elem.exists():
                cache_dir = cache_elem

            params = inputs.ZoningTranslationInputs.model_construct(
                zone_1=zone1,
                zone_2=zone2,
                cache_path=cache_dir,
            )

            trans = zone_translation.ZoneTranslation(params)
            result = trans.spatial_translation()

            names = trans.names
            out_path = params.cache_path / f"{names[0]}_{names[1]}"
            out_name = f"{names[0]}_to_{names[1]}_spatial.csv"
            return f"Translation completed and saved to: {out_path / out_name}"
        except Exception as exc:  # pylint: disable=broad-except
            return f"Error running translation: {exc}"

    # Note: spatial run helper removed; implement as a callback when
    # integration with your translation/config classes is available.

    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True)