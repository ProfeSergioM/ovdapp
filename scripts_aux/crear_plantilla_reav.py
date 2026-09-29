# -*- coding: utf-8 -*-
"""
Crea la plantilla REAV (docxtpl) que usa apps/formularioreav.py.

Toma un REAV generado por Electric Eye como base (conserva estilos gob,
encabezado con logo y pie de página) y reemplaza el cuerpo por texto con
campos Jinja {{ ... }}. Tambien genera las cuatro imagenes de alerta tecnica.

Uso:
    python scripts_aux/crear_plantilla_reav.py [ruta_reav_base.docx]

Despues de crearla, la plantilla se puede editar directamente en Word:
basta con respetar los nombres de los campos {{ ... }} y las lineas {%p ... %}.
"""
import os
import re
import shutil
import sys
import tempfile
import zipfile

from PIL import Image, ImageDraw, ImageFont

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIR_PLANTILLAS = os.path.join(RAIZ, 'assets', 'plantillas')
BASE_POR_DEFECTO = os.path.join(RAIZ, 'assets', 'dynamic_borrar', '11627450.docx')

NIVELES = [('verde', 'VERDE', '#00FF00'), ('amarilla', 'AMARILLA', '#FFFF00'),
           ('naranja', 'NARANJA', '#FF9900'), ('roja', 'ROJA', '#FF0000')]


# ----------------------------------------------------------------------------
# Imagenes de alerta
# ----------------------------------------------------------------------------
def _fuente(negrita, tam):
    candidatas = (['Carlito-Bold.ttf', 'calibrib.ttf', 'arialbd.ttf', 'DejaVuSans-Bold.ttf'] if negrita
                  else ['Carlito-Regular.ttf', 'calibri.ttf', 'arial.ttf', 'DejaVuSans.ttf'])
    for nombre in candidatas:
        try:
            return ImageFont.truetype(nombre, tam)
        except OSError:
            continue
    return ImageFont.load_default()


def crear_imagenes_alerta():
    ancho, alto = 605, 160
    gris = (100, 100, 100)
    for i, (clave, texto, _) in enumerate(NIVELES):
        img = Image.new('RGB', (ancho, alto), 'white')
        d = ImageDraw.Draw(img)
        f_reg, f_bold = _fuente(False, 50), _fuente(True, 50)
        d.text((2, 0), 'alerta técnica ', font=f_reg, fill=gris)
        x = 2 + d.textlength('alerta técnica ', font=f_reg)
        d.text((x, 0), texto, font=f_bold, fill=gris)
        # franja institucional azul/roja
        d.rectangle([2, 55, 226, 60], fill=(15, 105, 180))
        d.rectangle([226, 55, ancho - 2, 60], fill=(226, 44, 44))
        # cajas de nivel y flecha sobre el nivel activo
        caja = (ancho - 4) / 4.0
        for j, (_, _, color) in enumerate(NIVELES):
            x0 = 2 + j * caja
            d.rectangle([x0, 102, x0 + caja, 152], fill=color, outline=gris, width=1)
        cx = 2 + i * caja + caja / 2
        d.polygon([(cx - 50, 78), (cx + 50, 78), (cx, 100)], fill=gris)
        img.save(os.path.join(DIR_PLANTILLAS, 'alerta_%s.png' % clave))


# ----------------------------------------------------------------------------
# Cuerpo de la plantilla (WordprocessingML con campos Jinja)
# ----------------------------------------------------------------------------
def _r(texto, negrita=False, estilo='gob3', salto=False):
    rpr = '<w:rPr><w:rStyle w:val="%s"/>%s</w:rPr>' % (estilo, '<w:b/>' if negrita else '')
    br = '<w:br/>' if salto else ''
    return '<w:r>%s<w:t xml:space="preserve">%s</w:t>%s</w:r>' % (rpr, texto, br)


def _p(runs, jc='both', antes=None, despues=None, interlineado=True, tabs=False):
    sp = ''
    if interlineado or antes is not None or despues is not None:
        attrs = []
        if interlineado:
            attrs.append('w:line="280" w:lineRule="exact"')
        if antes is not None:
            attrs.append('w:before="%d"' % antes)
        if despues is not None:
            attrs.append('w:after="%d"' % despues)
        sp = '<w:spacing %s/>' % ' '.join(attrs)
    tb = '<w:tabs><w:tab w:val="left" w:pos="4253"/></w:tabs>' if tabs else ''
    return '<w:p><w:pPr>%s%s<w:jc w:val="%s"/></w:pPr>%s</w:p>' % (tb, sp, jc, ''.join(runs))


def _control(etiqueta):
    """Parrafo que solo contiene una etiqueta {%p ... %} (docxtpl lo elimina)."""
    return '<w:p><w:r><w:t xml:space="preserve">%s</w:t></w:r></w:p>' % etiqueta


def _fila(etiqueta, valor, condicion):
    """Fila 'ETIQUETA:<tab>valor' que se omite si la condicion es falsa."""
    return (_control('{%%p if %s %%}' % condicion)
            + _p([_r(etiqueta), '<w:r><w:rPr><w:rStyle w:val="gob3"/></w:rPr><w:tab/></w:r>', _r(valor)],
                 jc='left', antes=0, despues=0, tabs=True)
            + _control('{%p endif %}'))


def cuerpo_plantilla():
    b = []
    b.append(_p([_r('Reporte Especial de Actividad Volcánica (REAV)', True, 'gob')],
                jc='center', antes=0, despues=0))
    b.append(_p([_r('{{ region }}, {{ volcan }}', estilo='gob2')], jc='center', antes=40))
    b.append(_p([_r('{{ fecha_emision_txt }}, {{ hora_emision }} Hora local (Chile continental)')],
                jc='center', antes=40, despues=240))
    b.append(_p([_r('El '), _r('Servicio Nacional de Geología y Minería de Chile (Sernageomin)', True),
                 _r(' da a conocer la siguiente información PRELIMINAR, obtenida a través de los equipos de '
                    'monitoreo de la Red Nacional de Vigilancia Volcánica (RNVV), procesados y analizados '
                    'en el Observatorio Volcanológico de los Andes del Sur (Ovdas):')]))
    b.append(_p([_r('{{ frase_dia }} a las {{ hora_local }} hora local ({{ hora_utc }} UTC), las estaciones '
                    'de monitoreo instaladas en las inmediaciones del '),
                 _r('{{ volcan }}', True), _r(' registraron {{ descripcion_evento }}.')]))
    b.append(_p([_r('Las características del sismo luego de su análisis son las siguientes:')], despues=120))
    b.append(_fila('TIEMPO DE ORIGEN:', '{{ hora_local }} hora local ({{ hora_utc }} UTC)', 'hora_local'))
    b.append(_fila('LATITUD:', '{{ latitud }}', 'latitud'))
    b.append(_fila('LONGITUD:', '{{ longitud }}', 'longitud'))
    b.append(_fila('PROFUNDIDAD:', '{{ profundidad }} km', 'profundidad'))
    b.append(_fila('MAGNITUD LOCAL (ML):', '{{ magnitud }}', 'magnitud'))
    b.append(_fila('DESPLAZAMIENTO REDUCIDO:', '{{ dr }} (cm*cm)', 'dr'))
    b.append(_fila('SEÑAL ACÚSTICA:', '{{ acustica }} Pascales (Pa) reducidos a 1 km', 'acustica'))
    # mapa opcional
    b.append(_control('{%p if mapa %}'))
    b.append(_p([_r('{{ mapa }}')], jc='center', antes=120, interlineado=False))
    b.append(_control('{%p endif %}'))
    # actividad superficial opcional
    b.append(_control('{%p if superficial %}'))
    b.append(_p([_r('Así también, las características de la actividad superficial asociada son las siguientes:')],
                antes=240, despues=120))
    b.append(_fila('ALTURA DE COLUMNA MÁXIMA:', '{{ altura }} metros sobre punto de emisión', 'altura'))
    b.append(_fila('DIRECCIÓN DE DISPERSIÓN:', '{{ direccion }}', 'direccion'))
    b.append(_control('{%p if foto %}'))
    b.append(_p([_r('{{ foto }}')], jc='center', antes=120, interlineado=False))
    b.append(_control('{%p endif %}'))
    b.append(_control('{%p endif %}'))
    # observaciones
    b.append(_p([_r('OBSERVACIONES:', True)], antes=240, despues=120))
    b.append(_control('{%p for parrafo in observaciones %}'))
    b.append(_p([_r('{{ parrafo }}')], despues=120))
    b.append(_control('{%p endfor %}'))
    # alerta
    b.append(_p([_r('La alerta técnica volcánica {{ frase_alerta }}:')], antes=120))
    b.append(_p([_r('{{ imagen_alerta }}')], jc='center', antes=120, despues=120, interlineado=False))
    b.append(_p([_r('Sernageomin realiza vigilancia en línea e informa de manera oportuna sobre eventuales '
                    'cambios en la actividad volcánica del país.')], despues=240))
    b.append(_p([_r('Servicio Nacional de Geología y Minería (Sernageomin)', True, salto=True),
                 _r('Red Nacional de Vigilancia Volcánica (RNVV)', salto=True),
                 _r('Observatorio Volcanológico de los Andes del Sur (Ovdas)')], jc='right'))
    return ''.join(b)


def crear_plantilla(base):
    salida = os.path.join(DIR_PLANTILLAS, 'REAV_plantilla.docx')
    tmp = tempfile.mkdtemp()
    with zipfile.ZipFile(base) as z:
        z.extractall(tmp)

    ruta_doc = os.path.join(tmp, 'word', 'document.xml')
    with open(ruta_doc, encoding='utf-8') as f:
        xml = f.read()

    # imagenes del cuerpo (mapa, foto y alerta de ejemplo): se eliminan
    ids_cuerpo = set(re.findall(r'r:embed="([^"]+)"', xml.split('<w:sectPr')[0]))
    inicio = xml.index('<w:body>') + len('<w:body>')
    fin = xml.index('<w:sectPr')
    xml = xml[:inicio] + cuerpo_plantilla() + xml[fin:]
    with open(ruta_doc, 'w', encoding='utf-8') as f:
        f.write(xml)

    ruta_rels = os.path.join(tmp, 'word', '_rels', 'document.xml.rels')
    with open(ruta_rels, encoding='utf-8') as f:
        rels = f.read()
    for rid in ids_cuerpo:
        m = re.search(r'<Relationship Id="%s"[^>]*Target="([^"]+)"[^>]*/>' % rid, rels)
        if m:
            rels = rels.replace(m.group(0), '')
            destino = os.path.join(tmp, 'word', m.group(1))
            if os.path.exists(destino):
                os.remove(destino)
    with open(ruta_rels, 'w', encoding='utf-8') as f:
        f.write(rels)

    # logo del encabezado, para mostrarlo tambien en la pagina web
    for nombre in os.listdir(os.path.join(tmp, 'word', 'media')):
        if nombre.startswith('image2'):
            shutil.copy(os.path.join(tmp, 'word', 'media', nombre),
                        os.path.join(DIR_PLANTILLAS, 'logo_encabezado.png'))

    rutas = []
    for carpeta, _, archivos in os.walk(tmp):
        for a in archivos:
            completo = os.path.join(carpeta, a)
            rutas.append((os.path.relpath(completo, tmp).replace(os.sep, '/'), completo))
    rutas.sort(key=lambda r: (r[0] != '[Content_Types].xml', r[0]))
    with zipfile.ZipFile(salida, 'w', zipfile.ZIP_DEFLATED) as z:
        for relativa, completo in rutas:
            z.write(completo, relativa)
    shutil.rmtree(tmp)
    return salida


if __name__ == '__main__':
    os.makedirs(DIR_PLANTILLAS, exist_ok=True)
    base = sys.argv[1] if len(sys.argv) > 1 else BASE_POR_DEFECTO
    crear_imagenes_alerta()
    print('Plantilla creada en', crear_plantilla(base))
