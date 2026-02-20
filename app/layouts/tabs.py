"""
Tab layout definitions for the LTA Request Analysis Dashboard.
"""

from dash import html, dcc


def create_tab_layouts(df):
    return dcc.tabs([
        dcc.Tab(label="Tab 1", children=[
            html.Div([html.H3("Content for Tab 1")]),
        ]),
        dcc.Tab(label="Tab 2", children=[
            html.Div([html.H3("Content for Tab 2")]),
        ])
    ])