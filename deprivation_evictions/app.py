# Code to create the dashboard
# Built and edited by Stephania Tello Zamudio and Andrew Dunn

import pandas as pd
from urllib.request import urlopen
import json
from dash import Dash, dcc, html, Input, Output
import dash_bootstrap_components as dbc

# Import the graphs
from .graphs.bivariate_map import bivariate_map, create_legend
from .graphs.scatter_plot import make_scatter_plot
from .graphs.radar_graph import create_radar_graph
from .graphs.general_map import general_map

# Load the processed data
df = pd.read_csv('deprivation_evictions/data_bases/final_data/processed_data.csv')

# Do final edits to the data for the visualizations
df = df.sort_values('zipcode')
df = df.round(3)

# Boundaries by Zip code - Chicago (Geojson)
boundaries_url = "https://data.cityofchicago.org/api/geospatial/gdcf-axmw?method=export&format=GeoJSON"

with urlopen(boundaries_url) as response:
    zipcodes = json.load(response)

app = Dash(__name__, external_stylesheets=[dbc.themes.FLATLY])

# ----------------- GENERAL MAP -----------------------
gen_map = general_map(df, 'Evictions per capita', zipcodes)

# ----------------- BIVARIATE MAP ---------------------
colors = ['rgb(222, 224, 210)', 'rgb(189, 206, 181)', 'rgb(153, 189, 156)', 
          'rgb(110, 173, 138)', 'rgb(65, 157, 129)', 'rgb(25, 137, 125)', 
          'rgb(18, 116, 117)', 'rgb(28, 72, 93)', 'rgb(20, 29, 67)']

map_fig = bivariate_map(df, colors, zipcodes, "Deprivation Index", "Evictions per capita")
map_legend = create_legend(colors)

# ----------------- INTERACTIVE SCATTER PLOT ---------------------
indicator_dropdown = dcc.Dropdown(options = ['Deprivation Index',
                                             'Violent Crime',
                                             'Non-Violent Crime', 
                                             'Rent-to-Income Ratio',
                                             'Time to the Loop',
                                             'Distance to the Loop',
                                             ], value = 'Violent Crime',
                                             )

scatter_fig = make_scatter_plot(df, 'Deprivation Index')


# ----------------- INTERACTIVE RADAR PLOT ---------------------
zip_dropdown = dcc.Dropdown(options = df['zipcode'].unique(), value = '60601')
radar_fig = create_radar_graph(df, 60615, 'zipcode')

# ----------------- APP LAYOUT ------------------------

app.layout = dbc.Container(
    [
        dbc.Row(
            dbc.Col(
                html.H1("Neighborhood Deprivation and Evictions in Chicago", className="text-center mb-4"),
            )
        ), 
        dbc.Row(
            dbc.Col(
                html.H1("APWhy Team: Andrew Dunn, Gregory Ho, Santiago Segovia, Stephania Tello Zamudio",
                            style={"font-style": "italic", "font-size": 16, "text-align": 'center'})           
            )
        ),
        dbc.Row(
            dbc.Col(
                html.P("Evictions in the United States have become a pressing issue, especially as the country faces a growing \
                       affordable housing crisis. Many Americans struggle to find homes they can afford, and as a result, they \
                       may find themselves at risk of eviction. This can be due to a variety of factors, such as job loss, \
                       unexpected expenses, or rising housing costs. Unfortunately, evictions can further exacerbate the \
                       lack of affordable housing, as displaced tenants may struggle to find another place to live.\
                        This project looks to understand what neighborhood characteristics are associated with evictions in \
                        the city of Chicago. In order to do that, we construct an index to measure neighborhood deprivation, \
                        using a similar approach as the Multi-dimensional Poverty Index.",
                            style={"font-size": 16, "text-align": 'left', 'marginTop': 15})
                
            )
        ),
        dbc.Row(
            dbc.Col(
                html.P("For the construction of the deprivation index we analyzed three factors that can characterize neighborhoods:\
                       1) Safety, described by the per capita amount of violent and non violent crimes; 2) Housing affordability, \
                       measured by the ratio of median rent and income; and 3) Transport accessibility, which looks at the distance \
                       and travel time to the central business district (the Loop).",
                            style={"font-size": 16, "text-align": 'left'})             
            )
        ),
        dbc.Row(
            dbc.Col(
                html.P("Use the buttons to select which data to view in the map:",
                            style={"font-size": 16, "text-align": 'left'})             
            )
        ),
        dbc.Row(dbc.RadioItems(id = 'ind_evic', 
                               options = ["Evictions per capita", "Deprivation Index"],
                               value = "Evictions per capita",
                               inline = True)
        ),
        dbc.Row(
            dcc.Graph(id="gen_map", figure=gen_map,
                    style={'height': '700', 'width': '100%', 'marginBottom': 25, 'marginTop': 25})
        ),
        dbc.Row(html.H3("How does neighborhood deprivation relate to evictions?",
                        style={'marginBottom': 10, 'marginTop': 10}),
        ),
        dbc.Row(
            dbc.Col(
                html.P("We take both of the maps above and combine them into a singular bivariate map.",
                            style={"font-size": 16, "text-align": 'left'})             
            )
        ),
        dbc.Row(
            [
            dbc.Col(
                dcc.Graph(id="map", figure=map_fig,
                          style={'height': '700','width': '100%', 'marginBottom': 25, 'marginTop': 25}),
                width={"size":9}
            ),
            dbc.Col(
                dcc.Graph(id="legend", figure=map_legend, style={'width': '100%'}),
                width={"size":3}
            )
            ]
        ),
        dbc.Row(
            dbc.Col(
                html.Div(children=[
                    html.H3(children='Comparison of Attributes by Zip Code to City Averages',
                            style={'marginBottom': 10, 'marginTop': 20}),
                    html.P("The graph below compares the indicators which compose the deprivation index of an individual zip code \
                           to the overall average of all zip codes. All indicators are normalized such that their average is 0 and \
                           their standard deviation is 1. Doing this normalization makes the units for each of the indicators \
                           equivalent and allows them to be compared against each other. Higher values for each indicator indicate \
                           higher levels of deprivation; lower values for each indicator indicate lowers levels of deprivation.",
                            style={"font-size": 16, "text-align": 'left', 'marginTop': 15}),
                    html.P("Use the drop-down menu to select a zip code to compare to the city average:",
                            style={"font-size": 16, "text-align": 'left', 'marginTop': 15}),
                    zip_dropdown,
                    dcc.Graph(id="radar_graph", figure = radar_fig,
                              style={'width': '90%', "display": "inline-block", 
                                     'marginTop': 15, 'marginBottom': 10})
                ])
            ), justify="center"
        ),
        dbc.Row(
            dbc.Col(
                html.H3("Comparison of Evictions to Key Deprivation Indicators",
                        style={'marginBottom': 10, 'marginTop': 20}),
            )
        ),
        dbc.Row(
            dbc.Col(
                html.P("The scatter plot below compares the distribution of the deprivation index to the distribution of evictions. \
                       Each dot in the scatter plot represents the values for a zip code. Use the drop-down to further compare the  \
]                       the distribution of the individual indicators which compose the index against evictions All indicators are \
                       normalized such that their average is 0 and their standard deviation is 1. We overlay an OLS prediction line \
                       to visualize the linear relationship between the two variables.",
                        style={"font-size": 16, "text-align": 'left', 'marginTop': 15}),
            )
        ),
        dbc.Row(
            dbc.Col(
                html.P("Select the deprivation index or indicator to compare against per-capita evictions:",
                        style={"font-size": 16, "text-align": 'left', 'marginTop': 15}),
            )
        ),
        dbc.Row(
            dbc.Col(
                html.Div(children=[
                    indicator_dropdown,
                    dcc.Graph(id="scatter_graph", figure = scatter_fig,)
                ])
            )
        ),
        dbc.Row(
            dbc.Col(
                # html.P("For more info on the research, visit the methodology doc at this URL:",
                #         style={"font-size": 16, "text-align": 'left', 'marginTop': 15}),
                        
                html.A("For more info on the research, visit the methodology doc",
                    href = "https://github.com/uchicago-capp122-spring23/30122-project-apwhy/blob/main/Methodology.pdf",
                    style={"font-size": 16, "text-align": 'left', 'marginTop': 15}),
            )
        ),
    ],
    className="mt-4",
)


# ---------------- APP INTERACTION ---------------------

# Dropdown for general map
@app.callback(
        Output(component_id = 'gen_map', component_property='figure'),
        Input(component_id='ind_evic', component_property= 'value')
)
def update_graph(ind_evic):
    return general_map(df, ind_evic, zipcodes)

# Dropdown for radar graph
@app.callback(
    Output(component_id = 'radar_graph', component_property = 'figure'),
    Input(component_id = zip_dropdown, component_property = 'value')
)
def update_graph(selected_zip):
    selected_zip = int(selected_zip)
    return create_radar_graph(df, selected_zip, 'zipcode')

# Dropdown for scatter plot
@app.callback(
    Output(component_id = 'scatter_graph', component_property = 'figure'),
    Input(component_id = indicator_dropdown, component_property = 'value')
)
def update_graph(selected_x_var):
    return make_scatter_plot(df, selected_x_var)


if __name__ == '__main__':
    app.run_server(debug=True, port=32951)