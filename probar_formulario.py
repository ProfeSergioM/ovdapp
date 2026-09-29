# -*- coding: utf-8 -*-
"""Prueba aislada del formulario REAV, sin cargar las demas apps de ovdapp.

    python probar_formulario.py      ->  http://localhost:8090
"""
from app import app
from apps import formularioreav

app.layout = formularioreav.layout

if __name__ == '__main__':
    app.run_server(debug=True, port=8090)
