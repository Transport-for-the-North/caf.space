from pathlib import Path
import sys
from dash import Dash, html, dcc, Input, Output, State, callback
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
        State("z1_zone_name", "value"),
        State("z1_shapefile", "value"),
        State("z1_col_name", "value"),
        State("z2_zone_name", "value"),
        State("z2_shapefile", "value"),
        State("z2_col_name", "value"),
        State("output_folder", "value"),
        State("cache_path", "value"),
    )
    def create_yaml(
        n_clicks,
        z1_zone_name,
        z1_shapefile,
        z1_col_name,
        z2_zone_name,
        z2_shapefile,
        z2_col_name,
        output_folder,
        cache_path,
    ):
        """Run translation using `ZoneTranslation` and display output path or errors."""
        if not n_clicks:
            return ""

        if not all([z1_zone_name, z1_shapefile, z1_col_name, z2_zone_name, z2_shapefile, z2_col_name]):
            return "Please select all inputs before running translation."

        try:
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
            for raw in (output_folder, cache_path):
                if raw and (p := Path(raw).resolve()).exists():
                    cache_dir = p
                    break
                if raw:
                    cache_dir = Path(raw).resolve()
                    break

            cache_dir.mkdir(parents=True, exist_ok=True)

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


    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True)