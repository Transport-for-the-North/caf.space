""" Output view component for displaying translation config. """

from dash import html

def create_output_view():
    """Create the output view component."""
    return html.Div(
        id="output_view",
        children=[
            html.Div(id="translation_output", style={
                "whiteSpace": "pre-wrap",
                "backgroundColor": "#f9f9f9",
                "padding": "10px",
                "border": "1px solid #ccc",
                "borderRadius": "4px",
                "minHeight": "200px"
            })
        ],
        style={"marginTop": "20px"}
    )