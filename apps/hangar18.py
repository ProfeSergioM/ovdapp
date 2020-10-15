# -*- coding: utf-8 -*-
"""
Created on Wed Oct  7 12:39:36 2020

@author: sergio
"""
import dash
import json
import numpy as np
import dash_leaflet as dl
from dash_extensions import Download
from dash_extensions.snippets import send_bytes
import plotly.graph_objects as go
import dash_html_components as html
import dash_core_components as dcc
import dash_bootstrap_components as dbc
from dash.dependencies import Input, Output,ALL,State
from app import app
import sys
import pandas as pd
from obspy.clients.iris import Client
sys.path.append('//172.16.40.10/sismologia/pyovdas_lib/')
import ovdas_getfromdb_lib as gdb
import ovdas_doc_lib as odl
import ovdas_figure_lib as ffig
import ovdas_future_lib as ffut
external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']
PLOTLY_LOGO = "https://images.plot.ly/logo/new-branding/plotly-logomark.png"
import datetime as dt
from random import random
tileurl =  'http://www.google.cn/maps/vt?lyrs=s@189&gl=cn&x={x}&y={y}&z={z}'

SIDEBAR_STYLE = {
    "position": "fixed",
    "top": 0,
    "left": 0,
    "bottom": 0,
    "width": "16rem",
    "padding": "2rem 1rem",
    "background-color": " #141d26",
}

# the styles for the main content position it to the right of the sidebar and
# add some padding.
CONTENT_STYLE = {
    "margin-left": "18rem",
    "margin-right": "2rem",
    "padding": "2rem 1rem",
}

sidebar = html.Div(
    [
        html.H2("Hangar 18", className="display-4"),
        html.Hr(),
        html.P(
            "Información crítica asociada al monitoreo 24/7", className="lead"
        ),
        dbc.ButtonGroup(
    [
        dbc.Button("Inicio",id='inicio-button-hangar18'),
        dbc.Button("Criterios REAV",id="seccion-reavs-hangar18")
    ],
    vertical=True,style={'width':'100%'}
),
    ],
    style=SIDEBAR_STYLE,
)




content = html.Div(id="contenido-hangar18", style=CONTENT_STYLE)

layout = html.Div([sidebar, content])


@app.callback(
    Output("contenido-hangar18", "children"), 
    [Input("inicio-button-hangar18", "n_clicks"),Input("seccion-reavs-hangar18", "n_clicks")]
)
def on_button_click(n_inicio,n_reavs):
    ctx = dash.callback_context
    button_id = ctx.triggered[0]['prop_id'].split('.')[0]
    
    if (button_id == "inicio-button-hangar18") or (ctx.triggered[0]['prop_id'] =='.'):
        return "Bienvenido!"
    elif button_id == "seccion-reavs-hangar18":
        
        lista_criterios_general = dbc.ListGroup(
    [
        dbc.ListGroupItem("Registro de un evento sísmico tipo VT o HB con un valor de magnitud local (ML) igual o superior a 3.0", color="info"),
        dbc.ListGroupItem(("Registro de un evento sísmico tipo LP, EX, TR, TO,"+ 
                          "VLP o HB con un valor de desplazamiento reducido (DR) igual o superior a 500 cm*cm"), color="info"),
        dbc.ListGroupItem("Registro de un enjambre sísmico, es decir, la clasificación de 100 eventos sísmicos distribuidos en un periodo de tres horas", color="info")
    ]
    )

        lista_criterios_NevChillan = dbc.ListGroup(
    [dbc.ListGroupItemHeading("C.V. Nevados de Chillán"),
        dbc.ListGroupItem("Emisión de columna eruptiva por sobre los 2000 m sobre el punto de emisión", color="info"),
  ]
    )
        lista_criterios_particular = dbc.ListGroup(
            dbc.ListGroupItem(
                    [
                        
                              lista_criterios_NevChillan
           ,
                    ]
                )
  
    )
            
        list_group = dbc.ListGroup(
            [
                dbc.ListGroupItem(
                    [
                        dbc.ListGroupItemHeading("Criterios EN GENERAL (para todos los sistemas volcánicos)"),
                        lista_criterios_general,
                    ]
                ),
                dbc.ListGroupItem(
                    [
                        dbc.ListGroupItemHeading("Criterios EN PARTICULAR (para un sistema volcánico en específico)"),
                        lista_criterios_particular
                    ]
                ),
            ]
        )
        
        contenido = html.Div([list_group])
        return contenido
   