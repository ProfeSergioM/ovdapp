# -*- coding: utf-8 -*-
"""
Formulario REAV con el aspecto del documento Word.

La pagina muestra una hoja carta con el mismo texto y orden del REAV. Los
campos editables aparecen dentro del texto (en celeste), los campos que se
calculan solos aparecen en verde, y lo que queda vacio no se incluye en el
documento. Al descargar, se rellena la plantilla
assets/plantillas/REAV_plantilla.docx con docxtpl.

Requisito adicional:  pip install docxtpl
Ruta sugerida:        /apps/formularioreav
"""
import base64
import datetime as dt
import io
import os

import dash
import dash_bootstrap_components as dbc
from dash import dcc, html, Input, Output, State, ctx

from app import app

SUF = '-freav'
RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIR_PLANTILLAS = os.path.join(RAIZ, 'assets', 'plantillas')
PLANTILLA = os.path.join(DIR_PLANTILLAS, 'REAV_plantilla.docx')

# ----------------------------------------------------------------------------
# Catalogos
# ----------------------------------------------------------------------------
# Lista minima para el prototipo. En produccion puede venir de
# gdb.get_metadata_volcan('*', rep='y'), como en holaRAV.py.
VOLCANES = [
    ('Volcán Láscar', 'Región de Antofagasta'),
    ('Volcán Tupungatito', 'Región Metropolitana'),
    ('Complejo Volcánico Planchón-Peteroa', 'Región del Maule'),
    ('Complejo Volcánico Laguna del Maule', 'Región del Maule'),
    ('Complejo Volcánico Nevados de Chillán', 'Región de Ñuble'),
    ('Volcán Antuco', 'Región del Biobío'),
    ('Volcán Copahue', 'Región del Biobío'),
    ('Volcán Lonquimay', 'Región de La Araucanía'),
    ('Volcán Llaima', 'Región de La Araucanía'),
    ('Volcán Villarrica', 'Región de La Araucanía'),
    ('Volcán Mocho-Choshuenco', 'Región de Los Ríos'),
    ('Complejo Volcánico Puyehue-Cordón Caulle', 'Región de Los Ríos'),
    ('Volcán Osorno', 'Región de Los Lagos'),
    ('Volcán Calbuco', 'Región de Los Lagos'),
    ('Volcán Chaitén', 'Región de Los Lagos'),
    ('Volcán Hudson', 'Región de Aysén'),
]
REGION_POR_VOLCAN = dict(VOLCANES)

# Redaccion a revisar con el texto oficial de cada tipo de evento.
TIPOS_EVENTO = [
    ('LP', 'un sismo asociado a la dinámica de fluidos al interior del sistema volcánico (Largo Periodo)'),
    ('VT', 'un sismo asociado al fracturamiento de material rocoso (Volcano-Tectónico)'),
    ('HB', 'un sismo de tipo Híbrido, asociado al fracturamiento de material rocoso y a la dinámica de fluidos'),
    ('TR', 'un episodio de tremor volcánico, asociado a la dinámica de fluidos al interior del sistema volcánico'),
    ('EX', 'un sismo asociado a una explosión'),
]
DESCRIPCION_EVENTO = dict(TIPOS_EVENTO)

DIRECCIONES = ['Norte (N)', 'Nor-Este (NE)', 'Este (E)', 'Sur-Este (SE)', 'Sur (S)',
               'Sur-Oeste (SO)', 'Oeste (O)', 'Nor-Oeste (NO)']

NIVELES = [('verde', 'VERDE', '#00FF00'), ('amarilla', 'AMARILLA', '#FFFF00'),
           ('naranja', 'NARANJA', '#FF9900'), ('roja', 'ROJA', '#FF0000')]

DIAS = ['lunes', 'martes', 'miércoles', 'jueves', 'viernes', 'sábado', 'domingo']
MESES = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio', 'agosto',
         'septiembre', 'octubre', 'noviembre', 'diciembre']

# Valores del REAV de ejemplo (Nevados de Chillán, 17-06-2021) para probar rapido.
EJEMPLO = {
    'volcan': 'Complejo Volcánico Nevados de Chillán', 'region': 'Región de Ñuble',
    'fecha_em': '2021-06-17', 'hora_em': '02:29', 'fecha_ev': '2021-06-17', 'hora_ev': '02:16',
    'tipo': 'LP', 'lat': '36,866', 'lon': '71,373', 'prof': '0,6', 'ml': '', 'dr': '567,7',
    'acu': '', 'obs': 'El evento fue acompañado de una emisión de gases observada en las cámaras '
                      'de vigilancia instaladas en las inmediaciones del complejo volcánico.',
}


def _primer_domingo(anio, mes):
    d = dt.date(anio, mes, 1)
    return d + dt.timedelta(days=(6 - d.weekday()) % 7)


def utc_chile(fecha):
    """Diferencia horaria de Chile continental segun la regla vigente desde 2019:
    horario de invierno (UTC-4) desde el primer domingo de abril hasta el primer
    domingo de septiembre. Fechas anteriores a 2019 u horarios excepcionales
    deben revisarse a mano en el selector."""
    if fecha is None:
        return None
    if _primer_domingo(fecha.year, 4) <= fecha < _primer_domingo(fecha.year, 9):
        return '-4'
    return '-3'


def _utc_por_defecto():
    """Diferencia horaria del computador que corre la app (Chile continental)."""
    off = dt.datetime.now().astimezone().utcoffset()
    horas = int(round(off.total_seconds() / 3600.0)) if off is not None else -3
    return str(horas) if horas in (-3, -4) else '-3'


# ----------------------------------------------------------------------------
# Componentes de la hoja
# ----------------------------------------------------------------------------
def campo(nombre, placeholder='', ancho='8em', tipo='text', clase=''):
    return dbc.Input(id=nombre + SUF, type=tipo, placeholder=placeholder,
                     className='freav-campo ' + clase, style={'width': ancho},
                     persistence=True, persistence_type='session')


def selector(nombre, opciones, valor=None, ancho='12em', placeholder=None):
    ops = [{'label': o[1], 'value': o[0]} if isinstance(o, tuple) else {'label': o, 'value': o}
           for o in opciones]
    return dbc.Select(id=nombre + SUF, options=ops, value=valor, placeholder=placeholder,
                      className='freav-campo freav-select', style={'width': ancho},
                      persistence=True, persistence_type='session')


def auto(nombre, texto=''):
    """Texto que se calcula a partir de otros campos."""
    return html.Span(texto, id=nombre + SUF, className='freav-auto',
                     title='Se completa automáticamente')


def fila(etiqueta, *contenido):
    return html.Div([html.Span(etiqueta, className='freav-etiqueta'),
                     html.Span(list(contenido), className='freav-valor')], className='freav-fila')


def zona_imagen(nombre, texto):
    return dcc.Upload(id=nombre + SUF, accept='image/*', multiple=False,
                      className='freav-upload',
                      children=html.Div(texto, id=nombre + '-vista' + SUF, className='freav-upload-texto'))


def widget_alerta():
    return html.Div([
        html.Div([html.Span('alerta técnica '), html.B('VERDE', id='alerta-texto' + SUF)],
                 className='freav-alerta-titulo'),
        html.Div(className='freav-alerta-franja'),
        html.Div([html.Div(className='freav-flecha', id='flecha-%s%s' % (k, SUF)) for k, _, _ in NIVELES],
                 className='freav-alerta-flechas'),
        html.Div([html.Div(id='caja-%s%s' % (k, SUF), n_clicks=0, className='freav-caja',
                           style={'backgroundColor': color}, title='Seleccionar alerta ' + t.lower())
                  for k, t, color in NIVELES], className='freav-alerta-cajas'),
    ], className='freav-alerta', title='Haga clic en un color para elegir el nivel')


hoja = html.Div([
    html.Img(src=app.get_asset_url('plantillas/logo_encabezado.png'), className='freav-logo'),

    html.Div('Reporte Especial de Actividad Volcánica (REAV)', className='freav-titulo'),
    html.Div([campo('region', 'Región', '14em', clase='freav-centro'), ', ',
              selector('volcan', [v for v, _ in VOLCANES], ancho='22em', placeholder='Seleccione volcán')],
             className='freav-subtitulo'),
    html.Div([campo('fecha_em', tipo='date', ancho='10em'), ', ',
              campo('hora_em', tipo='time', ancho='6.5em'), ' Hora local (Chile continental)',
              html.Button('ahora', id='ahora' + SUF, className='freav-mini', n_clicks=0,
                          title='Usar la fecha y hora actuales')],
             className='freav-fecha'),

    html.P(['El ', html.B('Servicio Nacional de Geología y Minería de Chile (Sernageomin)'),
            ' da a conocer la siguiente información PRELIMINAR, obtenida a través de los equipos de '
            'monitoreo de la Red Nacional de Vigilancia Volcánica (RNVV), procesados y analizados en el '
            'Observatorio Volcanológico de los Andes del Sur (Ovdas):']),
    html.P([auto('frase_dia', '[fecha del evento]'), ' a las ', auto('hora_txt', '[hora]'),
            ' hora local (', auto('utc_txt', '[UTC]'), ' UTC), las estaciones de monitoreo instaladas en '
            'las inmediaciones del ', html.B(auto('volcan_txt', '[volcán]')), ' registraron ',
            selector('tipo', TIPOS_EVENTO, 'LP', ancho='auto'), '.'], className='freav-izq'),
    html.P('Las características del sismo luego de su análisis son las siguientes:'),

    html.Div([
        fila('TIEMPO DE ORIGEN:', campo('fecha_ev', tipo='date', ancho='10em'), ' ',
             campo('hora_ev', tipo='time', ancho='6.5em'), ' hora local (', auto('utc_fila', '--:--'), ' UTC)'),
        fila('LATITUD:', campo('lat', '36,866', '6em'), '° S'),
        fila('LONGITUD:', campo('lon', '71,373', '6em'), '° O'),
        fila('PROFUNDIDAD:', campo('prof', '0,6', '5em'), ' km'),
        fila('MAGNITUD LOCAL (ML):', campo('ml', 'opcional', '5em')),
        fila('DESPLAZAMIENTO REDUCIDO:', campo('dr', 'opcional', '6em'), ' (cm*cm)'),
        fila('SEÑAL ACÚSTICA:', campo('acu', 'opcional', '5em'), ' Pascales (Pa) reducidos a 1 km'),
    ], className='freav-bloque'),

    zona_imagen('mapa', 'Mapa de localización (opcional): arrastre una imagen o haga clic'),

    dbc.Checklist(id='superficial' + SUF, switch=True, value=[], className='freav-interruptor',
                  options=[{'label': 'Incluir actividad superficial asociada', 'value': 'si'}],
                  persistence=True, persistence_type='session'),
    html.Div([
        html.P('Así también, las características de la actividad superficial asociada son las siguientes:'),
        html.Div([
            fila('ALTURA DE COLUMNA MÁXIMA:', campo('altura', '800', '5em'), ' metros sobre punto de emisión'),
            fila('DIRECCIÓN DE DISPERSIÓN:', selector('direccion', DIRECCIONES, ancho='12em',
                                                      placeholder='Seleccione')),
        ], className='freav-bloque'),
        zona_imagen('foto', 'Fotografía (opcional): arrastre una imagen o haga clic'),
    ], id='bloque-superficial' + SUF, style={'display': 'none'}),

    html.P(html.B('OBSERVACIONES:'), className='freav-obs-titulo'),
    dbc.Textarea(id='obs' + SUF, rows=5, className='freav-campo freav-area',
                 placeholder='Escriba aquí las observaciones', persistence=True, persistence_type='session'),

    html.P(['La alerta técnica volcánica ',
            selector('frase_alerta', [('se mantiene en', 'se mantiene en'), ('cambia a', 'cambia a')],
                     'se mantiene en', ancho='9.5em'), ':'], className='freav-p-alerta'),
    widget_alerta(),

    html.P('Sernageomin realiza vigilancia en línea e informa de manera oportuna sobre eventuales cambios '
           'en la actividad volcánica del país.'),
    html.P([html.B('Servicio Nacional de Geología y Minería (Sernageomin)'), html.Br(),
            'Red Nacional de Vigilancia Volcánica (RNVV)', html.Br(),
            'Observatorio Volcanológico de los Andes del Sur (Ovdas)'], className='freav-firma'),
    html.Div([html.B('Rudecindo Ortega #03850, Temuco - CHILE'),
              ' - Fono:(56-2) 249 63300 - Página Web: www.sernageomin.cl'], className='freav-pie'),
], className='freav-hoja')

barra = html.Div([
    html.Div([html.Span('Formulario REAV', className='freav-barra-titulo'),
              html.Span([html.Span(className='freav-muestra freav-muestra-campo'), ' editable  ',
                         html.Span(className='freav-muestra freav-muestra-auto'), ' automático  ·  '
                         'lo que quede vacío no aparece en el documento'], className='freav-leyenda')]),
    html.Div([
        html.Span('Horario', className='freav-barra-etq'),
        dbc.Select(id='utc' + SUF, value=_utc_por_defecto(), style={'width': '11.5em'}, size='sm',
                   options=[{'label': 'UTC−3 (verano)', 'value': '-3'},
                            {'label': 'UTC−4 (invierno)', 'value': '-4'}]),
        dbc.Button('Cargar ejemplo', id='ejemplo' + SUF, color='secondary', size='sm', n_clicks=0),
        dbc.Button('Descargar .docx', id='descargar' + SUF, color='primary', size='sm', n_clicks=0),
    ], className='freav-barra-acciones'),
    html.Div(id='mensaje' + SUF, className='freav-mensaje'),
], className='freav-barra')

layout = html.Div([
    barra,
    html.Div(hoja, className='freav-escritorio'),
    dcc.Store(id='nivel' + SUF, data='verde', storage_type='session'),
    dcc.Download(id='archivo' + SUF),
    html.Div(id='inicio' + SUF, style={'display': 'none'}),
], className='freav-raiz')


# ----------------------------------------------------------------------------
# Utilidades
# ----------------------------------------------------------------------------
def _parse_fecha_hora(fecha, hora):
    try:
        return dt.datetime.strptime('%s %s' % (fecha, hora), '%Y-%m-%d %H:%M')
    except (TypeError, ValueError):
        return None


def _numero(texto):
    """Devuelve el texto con coma decimal, o None si esta vacio o no es numero."""
    if texto is None or str(texto).strip() == '':
        return None
    limpio = str(texto).strip().replace(',', '.').lstrip('-')
    try:
        float(limpio)
    except ValueError:
        return False
    return limpio.replace('.', ',')


def _frase_dia(evento, emision):
    """'Hoy jueves 17 de junio' si coincide con la emision; si no, 'El miércoles 16 de junio'."""
    base = '%s %d de %s' % (DIAS[evento.weekday()], evento.day, MESES[evento.month - 1])
    if emision is not None and emision.date() == evento.date():
        return 'Hoy ' + base
    return 'El ' + base


def _imagen(contenido):
    if not contenido:
        return None
    return io.BytesIO(base64.b64decode(contenido.split(',', 1)[1]))


def generar_docx(d):
    """Rellena la plantilla con el diccionario d y devuelve los bytes del .docx."""
    from docxtpl import DocxTemplate, InlineImage
    from docx.shared import Mm

    tpl = DocxTemplate(PLANTILLA)
    em = _parse_fecha_hora(d['fecha_em'], d['hora_em'])
    ev = _parse_fecha_hora(d['fecha_ev'], d['hora_ev'])
    utc = ev - dt.timedelta(hours=int(d['utc']))
    superficial = bool(d['superficial'])

    mapa, foto = _imagen(d['mapa']), _imagen(d['foto']) if superficial else None
    contexto = {
        'region': d['region'].strip(),
        'volcan': d['volcan'],
        'fecha_emision_txt': '%d de %s de %d' % (em.day, MESES[em.month - 1], em.year),
        'hora_emision': em.strftime('%H:%M'),
        'frase_dia': _frase_dia(ev, em),
        'hora_local': ev.strftime('%H:%M'),
        'hora_utc': utc.strftime('%H:%M'),
        'descripcion_evento': DESCRIPCION_EVENTO.get(d['tipo'], ''),
        'latitud': '%s° S' % _numero(d['lat']),
        'longitud': '%s° O' % _numero(d['lon']),
        'profundidad': _numero(d['prof']),
        'magnitud': _numero(d['ml']),
        'dr': _numero(d['dr']),
        'acustica': _numero(d['acu']),
        'mapa': InlineImage(tpl, mapa, width=Mm(150)) if mapa else None,
        'superficial': superficial,
        'altura': _numero(d['altura']) if superficial else None,
        'direccion': d['direccion'] if superficial else None,
        'foto': InlineImage(tpl, foto, width=Mm(130)) if foto else None,
        'observaciones': [t.strip() for t in d['obs'].splitlines() if t.strip()],
        'frase_alerta': d['frase_alerta'],
        'imagen_alerta': InlineImage(tpl, os.path.join(DIR_PLANTILLAS, 'alerta_%s.png' % d['nivel']),
                                     width=Mm(76)),
    }
    tpl.render(contexto, autoescape=True)
    salida = io.BytesIO()
    tpl.save(salida)
    return salida.getvalue()


# ----------------------------------------------------------------------------
# Callbacks
# ----------------------------------------------------------------------------
@app.callback(
    [Output('fecha_em' + SUF, 'value'), Output('hora_em' + SUF, 'value')],
    [Input('inicio' + SUF, 'children'), Input('ahora' + SUF, 'n_clicks'), Input('ejemplo' + SUF, 'n_clicks')],
    [State('fecha_em' + SUF, 'value'), State('hora_em' + SUF, 'value')])
def fijar_emision(_, n_ahora, n_ejemplo, fecha, hora):
    if ctx.triggered_id == 'ejemplo' + SUF:
        return EJEMPLO['fecha_em'], EJEMPLO['hora_em']
    if ctx.triggered_id != 'ahora' + SUF and fecha and hora:
        return dash.no_update, dash.no_update
    ahora = dt.datetime.now()
    return ahora.strftime('%Y-%m-%d'), ahora.strftime('%H:%M')


@app.callback(Output('utc' + SUF, 'value'), Input('fecha_ev' + SUF, 'value'), prevent_initial_call=True)
def utc_desde_fecha(fecha):
    try:
        return utc_chile(dt.datetime.strptime(fecha, '%Y-%m-%d').date())
    except (TypeError, ValueError):
        return dash.no_update


@app.callback(Output('region' + SUF, 'value'),
              Input('volcan' + SUF, 'value'),
              State('region' + SUF, 'value'), prevent_initial_call=True)
def region_desde_volcan(volcan, region_actual):
    return REGION_POR_VOLCAN.get(volcan, region_actual)


@app.callback(
    [Output('frase_dia' + SUF, 'children'), Output('hora_txt' + SUF, 'children'),
     Output('utc_txt' + SUF, 'children'), Output('utc_fila' + SUF, 'children'),
     Output('volcan_txt' + SUF, 'children')],
    [Input('fecha_ev' + SUF, 'value'), Input('hora_ev' + SUF, 'value'),
     Input('fecha_em' + SUF, 'value'), Input('hora_em' + SUF, 'value'),
     Input('utc' + SUF, 'value'), Input('volcan' + SUF, 'value')])
def textos_automaticos(fecha_ev, hora_ev, fecha_em, hora_em, utc, volcan):
    volcan_txt = volcan or '[volcán]'
    ev = _parse_fecha_hora(fecha_ev, hora_ev)
    if ev is None:
        return '[fecha del evento]', '[hora]', '[UTC]', '--:--', volcan_txt
    em = _parse_fecha_hora(fecha_em, hora_em)
    hora_utc = (ev - dt.timedelta(hours=int(utc))).strftime('%H:%M')
    return _frase_dia(ev, em), ev.strftime('%H:%M'), hora_utc, hora_utc, volcan_txt


@app.callback(Output('bloque-superficial' + SUF, 'style'), Input('superficial' + SUF, 'value'))
def mostrar_superficial(valor):
    return {'display': 'block'} if valor else {'display': 'none'}


def _vista_previa(contenido, texto):
    if not contenido:
        return texto
    return html.Img(src=contenido, className='freav-img')


@app.callback(Output('mapa-vista' + SUF, 'children'), Input('mapa' + SUF, 'contents'))
def vista_mapa(contenido):
    return _vista_previa(contenido, 'Mapa de localización (opcional): arrastre una imagen o haga clic')


@app.callback(Output('foto-vista' + SUF, 'children'), Input('foto' + SUF, 'contents'))
def vista_foto(contenido):
    return _vista_previa(contenido, 'Fotografía (opcional): arrastre una imagen o haga clic')


@app.callback(Output('nivel' + SUF, 'data'),
              [Input('caja-%s%s' % (k, SUF), 'n_clicks') for k, _, _ in NIVELES]
              + [Input('ejemplo' + SUF, 'n_clicks')],
              prevent_initial_call=True)
def elegir_nivel(*_):
    if ctx.triggered_id == 'ejemplo' + SUF:
        return 'amarilla'
    return ctx.triggered_id.replace('caja-', '').replace(SUF, '')


@app.callback([Output('alerta-texto' + SUF, 'children')]
              + [Output('flecha-%s%s' % (k, SUF), 'className') for k, _, _ in NIVELES],
              Input('nivel' + SUF, 'data'))
def dibujar_nivel(nivel):
    texto = dict((k, t) for k, t, _ in NIVELES).get(nivel, 'VERDE')
    return [texto] + ['freav-flecha activa' if k == nivel else 'freav-flecha' for k, _, _ in NIVELES]


# La region se completa sola al cambiar el volcan; la emision y el nivel se
# cargan en sus propios callbacks (Dash no permite dos callbacks con la misma salida).
CAMPOS_EJEMPLO = ['volcan', 'fecha_ev', 'hora_ev', 'tipo', 'lat', 'lon', 'prof', 'ml', 'dr', 'acu', 'obs']


@app.callback([Output(c + SUF, 'value') for c in CAMPOS_EJEMPLO],
              Input('ejemplo' + SUF, 'n_clicks'), prevent_initial_call=True)
def cargar_ejemplo(_):
    return [EJEMPLO[c] for c in CAMPOS_EJEMPLO]


OBLIGATORIOS = ['region', 'volcan', 'fecha_em', 'hora_em', 'fecha_ev', 'hora_ev', 'lat', 'lon', 'obs']
NUMERICOS = ['lat', 'lon', 'prof', 'ml', 'dr', 'acu', 'altura']
TODOS = ['region', 'volcan', 'fecha_em', 'hora_em', 'fecha_ev', 'hora_ev', 'tipo', 'lat', 'lon', 'prof',
         'ml', 'dr', 'acu', 'altura', 'direccion', 'obs', 'frase_alerta']


@app.callback(
    [Output('archivo' + SUF, 'data'), Output('mensaje' + SUF, 'children')]
    + [Output(c + SUF, 'invalid') for c in TODOS],
    [Input('descargar' + SUF, 'n_clicks')] + [Input(c + SUF, 'value') for c in TODOS],
    [State(c + SUF, 'invalid') for c in TODOS]
    + [State('utc' + SUF, 'value'), State('superficial' + SUF, 'value'), State('nivel' + SUF, 'data'),
       State('mapa' + SUF, 'contents'), State('foto' + SUF, 'contents')],
    prevent_initial_call=True)
def descargar(_, *valores):
    n = len(TODOS)
    d = dict(zip(TODOS, valores[:n]))
    marcados = valores[n:2 * n]
    d['utc'], d['superficial'], d['nivel'], d['mapa'], d['foto'] = valores[2 * n:]

    malos = set(c for c in OBLIGATORIOS if not d.get(c) or not str(d[c]).strip())
    malos |= set(c for c in NUMERICOS if _numero(d.get(c)) is False)

    # Mientras se escribe: solo se quita el rojo de los campos ya corregidos.
    if ctx.triggered_id != 'descargar' + SUF:
        return [dash.no_update, dash.no_update] + [bool(m) and c in malos for c, m in zip(TODOS, marcados)]

    invalidos = [c in malos for c in TODOS]
    if malos:
        msg = dbc.Alert('Revise los campos marcados en rojo (obligatorios o con un número mal escrito).',
                        color='danger', className='freav-alerta-msg', duration=6000)
        return [dash.no_update, msg] + invalidos

    try:
        contenido = generar_docx(d)
    except Exception as e:  # se informa en pantalla para no perder el trabajo
        msg = dbc.Alert('No se pudo generar el documento: %s' % e, color='danger', className='freav-alerta-msg')
        return [dash.no_update, msg] + invalidos

    ev = _parse_fecha_hora(d['fecha_ev'], d['hora_ev'])
    nombre = 'REAV_%s_%s.docx' % (d['volcan'].split(' ')[-1].replace('/', '-'), ev.strftime('%Y%m%d_%H%M'))
    msg = dbc.Alert('Documento generado: %s' % nombre, color='success', className='freav-alerta-msg',
                    duration=4000)
    return [dcc.send_bytes(contenido, nombre), msg] + invalidos
