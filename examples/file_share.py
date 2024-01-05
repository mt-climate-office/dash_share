
from dash import Dash, html, dcc, callback, Output, Input
import dash_bootstrap_components as dbc
from dash_share import FileShare, update_component_state, DashShare
import plotly.express as px
import pandas as pd
from pathlib import Path

from urllib.parse import parse_qs
import json

df = pd.read_csv('https://raw.githubusercontent.com/plotly/datasets/master/gapminder_unfiltered.csv')

app = Dash(__name__)


html.Div(
    [
        dbc.Button("Open modal", id="open", n_clicks=0),
        dbc.Modal(
            [
                dbc.ModalHeader(dbc.ModalTitle("Header")),
                dbc.ModalBody("This is the content of the modal"),
                dbc.ModalFooter(
                    dbc.Button(
                        "Close", id="close", className="ms-auto", n_clicks=0
                    )
                ),
            ],
            id="modal",
            is_open=False,
        ),
    ]
)
layout = dbc.Container(
    [
        html.H1(children='Title of Dash App', style={'textAlign':'center'}, id='title'),
        dcc.Dropdown(df.country.unique(), 'Canada', id='dropdown-selection'), 
        dbc.Button("Share Me!", "share", n_clicks=0),
        dcc.Graph(id='graph-content'),
        dcc.Location(id='url'),
    ],
    fluid=True,
    style={
        "height": "100%",
        "backgroundColor": "#E9ECEF",
        "padding": "1.5rem 1.5rem 1.5rem 1.5rem",
        "overflow-y": "clip",
    },
        )

def parse_query_string(query_string):
    query_string = query_string.replace("?", "")
    parsed_data = parse_qs(query_string)
    result_dict = {key: value[0] for key, value in parsed_data.items()}
    return result_dict


class FileShare2(DashShare):
    def load(self, input, state):
        q = parse_query_string(input)
        if "state" in q:
            with open(f'./share/{q["state"]}.json', "rb") as file:
                state = json.load(file)
            state = update_component_state(
                state, None, **{self.modal_id: {"is_open": False}}
            )
        return state

    def save(self, input, state, hash):
        out_dir = Path("./share")
        if not out_dir.exists():
            out_dir.mkdir()
        if input is not None and input > 0:
            state = update_component_state(
                state,
                None,
                graph_content={"figure": {}}
            )

            with open(f"./{out_dir}/{hash}.json", "w") as json_file:
                json.dump(state, json_file, indent=4)
        return input


share = FileShare2(
    app=app,
    load_input=("url", "search"),
    save_input=("share", "n_clicks"),
    save_output=("share", "n_clicks"),
    url_input="url",
)

app.layout = lambda: share.update_layout(layout=layout)
share.register_callbacks()

@callback(
    Output('graph-content', 'figure'),
    Input('dropdown-selection', 'value')
)
@share.pause_update
def update_graph(value):
    print(value)
    dff = df[df.country==value]
    return px.line(dff, x='year', y='pop')


@callback(
    Output('title', 'children'),
    Input('dropdown-selection', 'value')
)
def update_title(value):
    return f"You have selected {value}"


if __name__ == '__main__':
    app.run(debug=True)