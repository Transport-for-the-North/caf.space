from dash import html, dcc
from componants.output_view import create_output_view
from componants.form_components import (
    create_dropdown,
    create_text_input,
    create_number_input,
    create_file_input,
    create_checkbox,
    create_section
)


def create_main_layout():
    """Create the main Zone translation parameters layout."""
    
    return html.Div(
        [
            # Header
            html.Div(
                [
                    html.H2("Zone translation parameters", style={"margin": "0", "fontSize": "18px"}),
                ],
                style={
                    "padding": "12px 16px",
                    "backgroundColor": "#f5f5f5",
                    "borderBottom": "1px solid #ddd"
                }
            ),
            
            # Main content area
            html.Div(
                [
                    # Parameters section
                    html.Div(
                        [
                            # Top level parameters
                            html.Div(
                                [
                                    create_file_input(
                                        "Cache Path",
                                        "cache_path",
                                        placeholder="c:/Data/Zone Translations/cache"
                                    ),
                                    create_file_input(
                                        "Output Folder",
                                        "output_folder",
                                        placeholder="path/to/output/folder"
                                    ),
                                ],
                                style={
                                    "display": "grid",
                                    "gridTemplateColumns": "1fr 1fr",
                                    "gap": "20px"
                                }
                            ),
                            
                            
                            # Zone 1 Section
                            create_section(
                                "Zone 1",
                                [
                                    create_file_input("Shapefile", "z1_shapefile"),
                                    create_text_input(
                                        "Zone system name",
                                        "z1_zone_name",
                                        value="zone_name"
                                    ),
                                    create_dropdown(
                                        "ID Column Name", 
                                        "z1_col_name", 
                                        options=[]
                                        )
                                ],
                                cols=2
                            ),
                            
                            # Zone 2 Section
                            create_section(
                                "Zone 2",
                                [
                                    create_file_input("Shapefile", "z2_shapefile"),
                                    create_text_input(
                                        "Zone system name",
                                        "z2_zone_name",
                                        value="zone_name"
                                    ),
                                    create_dropdown(
                                        "ID Column Name", 
                                        "z2_col_name", 
                                        options=[])
                                ],
                                cols=2
                            ),

                            create_section(
                                "Run translation",
                                [
                                    html.Button("Run translation", id="run_translation_button")
                                ],
                                cols=1
                            ),

                            create_section(
                                "Translation output",
                                [
                                    create_output_view()
                                ],
                                cols=1
                            ),
                            
                            
                        ],
                        style={"padding": "20px"}
                    ),
                ],
                style={"padding": "20px"}
            )
        ],
        style={
            "fontFamily": "Arial, sans-serif",
            "fontSize": "12px",
            "backgroundColor": "#fafafa",
            "minHeight": "100vh"
        }
    )