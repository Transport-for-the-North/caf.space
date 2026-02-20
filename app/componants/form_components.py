"""
Reusable form components for the Zone Translation parameters interface.
"""

from dash import html, dcc


def create_text_input(label, input_id, placeholder="", value=""):
    """Create a labeled text input component."""
    return html.Div(
        [
            html.Label(label, style={"fontWeight": "bold", "fontSize": "12px"}),
            dcc.Input(
                id=input_id,
                type="text",
                placeholder=placeholder,
                value=value,
                style={
                    "width": "100%",
                    "padding": "6px",
                    "border": "1px solid #ccc",
                    "borderRadius": "4px",
                    "boxSizing": "border-box",
                    "fontSize": "12px"
                }
            )
        ],
        style={"marginBottom": "12px"}
    )


def create_number_input(label, input_id, value=0, min_val=None):
    """Create a labeled number input component."""
    return html.Div(
        [
            html.Label(label, style={"fontWeight": "bold", "fontSize": "12px"}),
            dcc.Input(
                id=input_id,
                type="number",
                value=value,
                min=min_val,
                style={
                    "width": "80px",
                    "padding": "6px",
                    "border": "1px solid #ccc",
                    "borderRadius": "4px",
                    "fontSize": "12px"
                }
            )
        ],
        style={"marginBottom": "12px"}
    )


def create_file_input(label, input_id, placeholder=""):
    """Create a labeled file path input with browse button."""
    return html.Div(
        [
            html.Label(label, style={"fontWeight": "bold", "fontSize": "12px"}),
            html.Div(
                [
                    dcc.Input(
                        id=input_id,
                        type="text",
                        placeholder=placeholder,
                        style={
                            "flex": "1",
                            "padding": "6px",
                            "border": "1px solid #ccc",
                            "borderRadius": "4px 0 0 4px",
                            "boxSizing": "border-box",
                            "fontSize": "12px"
                        }
                    ),
                    html.Button(
                        "...",
                        id=f"{input_id}_button",
                        n_clicks=0,
                        style={
                            "padding": "6px 12px",
                            "border": "1px solid #ccc",
                            "borderLeft": "none",
                            "borderRadius": "0 4px 4px 0",
                            "backgroundColor": "#f5f5f5",
                            "cursor": "pointer",
                            "fontSize": "12px"
                        }
                    )
                ],
                style={"display": "flex", "gap": "0"}
            )
        ],
        style={"marginBottom": "12px"}
    )


def create_checkbox(label, checkbox_id, checked=False):
    """Create a labeled checkbox component."""
    return html.Div(
        [
            dcc.Checklist(
                id=checkbox_id,
                options=[{"label": " " + label, "value": 1}],
                value=[1] if checked else [],
                style={"fontSize": "12px"}
            )
        ],
        style={"marginBottom": "12px"}
    )


def create_section(title, children, cols=2):
    """Create a styled section with title and group of form elements."""
    return html.Div(
        [
            html.H4(
                title,
                style={
                    "borderBottom": "2px solid #ddd",
                    "paddingBottom": "8px",
                    "marginBottom": "12px",
                    "marginTop": "16px",
                    "fontSize": "14px",
                    "fontWeight": "bold"
                }
            ),
            html.Div(
                children,
                style={
                    "display": "grid",
                    "gridTemplateColumns": f"repeat({cols}, 1fr)",
                    "gap": "16px"
                }
            )
        ],
        style={"marginBottom": "20px"}
    )

def create_dropdown(label, dropdown_id, options, value=None, multi=False):
    """Create a labeled dropdown component."""
    return html.Div(
        [
            html.Label(label, style={"fontWeight": "bold", "fontSize": "12px"}),
            dcc.Dropdown(
                id=dropdown_id,
                options=[{"label": opt, "value": opt} for opt in options],
                value= value,
                multi=multi
            )
        ],
        style={"marginBottom": "12px"}
    )


def RunButton():
    """
    Create download buttons component.
    
    Returns:
        html.Div: Download buttons component
    """
    return html.Div([
        html.Button('Run Zone Translation', id='zone-run-button', n_clicks=0,
                   style={'margin': '10px', 'padding': '10px 20px', 'backgroundColor': '#0d0f3d', 'color': '#00dec6', 'border': 'none', 'borderRadius': '5px', 'cursor': 'pointer'}),
    ], style={'marginTop': '20px'})