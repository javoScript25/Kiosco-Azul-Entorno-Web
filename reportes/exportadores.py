"""Salida a Excel y PDF (RF-17). Dibujan el mismo diccionario que la pantalla."""
from io import BytesIO
from xml.sax.saxutils import escape

from django.utils import timezone
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from .utiles import NUMERICOS, formatear

FORMATOS_EXCEL = {
    "pesos": '"$" #,##0.00',
    "cantidad": "#,##0.###",
    "entero": "#,##0",
    "porcentaje": '0.0" %"',
    "fecha": "DD/MM/YYYY",
    "fechahora": "DD/MM/YYYY HH:MM",
}


# Azul tenue de las cabeceras, armado con números (sin códigos hex que se rompen al copiar y pegar).
_R, _G, _B = 229, 237, 248
AZUL_TENUE_XLSX = "%02X%02X%02X" % (_R, _G, _B)
AZUL_TENUE_PDF = colors.Color(_R / 255, _G / 255, _B / 255)


def periodo_texto(reporte):
    return f"Período: del {reporte['desde']:%d/%m/%Y} al {reporte['hasta']:%d/%m/%Y}"


def nombre_archivo(reporte, extension):
    return f"reporte-{reporte['tipo']}-{reporte['desde']:%Y%m%d}-{reporte['hasta']:%Y%m%d}.{extension}"


# ----------------------------------------------------------------- Excel ---

def _poner(hoja, fila, columna, celda):
    destino = hoja.cell(row=fila, column=columna)
    valor, tipo = celda
    if valor is None or valor == "":
        destino.value = "—"
    elif tipo == "texto":
        destino.value = str(valor)
        # Un texto que empieza con "=" se guardaría como fórmula (inyección):
        # se fuerza a texto plano.
        destino.data_type = "s"
    elif tipo == "fechahora":
        destino.value = timezone.localtime(valor).replace(tzinfo=None)
    else:
        destino.value = valor
    if tipo in FORMATOS_EXCEL and valor not in (None, ""):
        destino.number_format = FORMATOS_EXCEL[tipo]
    if tipo in NUMERICOS:
        destino.alignment = Alignment(horizontal="right")
    return destino


def a_excel(reporte):
    libro = Workbook()
    hoja = libro.active
    hoja.title = "Resumen"
    hoja["A1"] = f"Kiosco Azul - Reporte de {reporte['titulo'].lower()}"
    hoja["A1"].font = Font(bold=True, size=14)
    hoja["A2"] = periodo_texto(reporte)
    fila = 4
    for kpi in reporte["kpis"]:
        hoja.cell(row=fila, column=1, value=kpi["titulo"]).font = Font(bold=True)
        _poner(hoja, fila, 2, kpi["celda"])
        hoja.cell(row=fila, column=3, value=kpi["nota"])
        fila += 1
    hoja.column_dimensions["A"].width = 32
    hoja.column_dimensions["B"].width = 20
    hoja.column_dimensions["C"].width = 60

    relleno = PatternFill("solid", fgColor=AZUL_TENUE_XLSX)
    for numero, tabla in enumerate(reporte["tablas"], 1):
        if not tabla["filas"]:
            continue
        titulo = "".join(c for c in f"{numero} {tabla['titulo']}" if c not in '[]:*?/\\')[:31]
        pagina = libro.create_sheet(titulo)
        for j, col in enumerate(tabla["columnas"], 1):
            cab = pagina.cell(row=1, column=j, value=col["nombre"])
            cab.font = Font(bold=True)
            cab.fill = relleno
        for i, datos in enumerate(tabla["filas"], 2):
            for j, celda in enumerate(datos, 1):
                _poner(pagina, i, j, celda)
        for j, col in enumerate(tabla["columnas"], 1):
            ancho = max([len(col["nombre"])] + [len(formatear(f[j - 1])) for f in tabla["filas"]])
            pagina.column_dimensions[get_column_letter(j)].width = min(max(ancho + 2, 12), 50)
        pagina.freeze_panes = "A2"

    salida = BytesIO()
    libro.save(salida)
    return salida.getvalue()


# ------------------------------------------------------------------- PDF ---

def a_pdf(reporte):
    salida = BytesIO()
    documento = SimpleDocTemplate(
        salida, pagesize=landscape(A4), leftMargin=1.5 * cm, rightMargin=1.5 * cm,
        topMargin=1.5 * cm, bottomMargin=1.5 * cm,
        title=f"Reporte de {reporte['titulo'].lower()}", author="Kiosco Azul",
    )
    estilos = getSampleStyleSheet()
    chico = ParagraphStyle("chico", parent=estilos["BodyText"], fontSize=8, leading=10)
    chico_der = ParagraphStyle("chico_der", parent=chico, alignment=2)
    ancho = documento.width

    def parrafo(texto, estilo=chico):
        # Paragraph interpreta marcas: se escapa para que "<" en un concepto no rompa el PDF.
        return Paragraph(escape(str(texto)), estilo)

    elementos = [
        Paragraph(escape(f"Kiosco Azul - Reporte de {reporte['titulo'].lower()}"), estilos["Title"]),
        Paragraph(escape(periodo_texto(reporte)), estilos["BodyText"]),
        Spacer(1, 10),
    ]
    if reporte["kpis"]:
        datos = [[parrafo(k["titulo"]), parrafo(formatear(k["celda"]), chico_der), parrafo(k["nota"])]
                 for k in reporte["kpis"]]
        tabla = Table(datos, colWidths=[ancho * 0.25, ancho * 0.2, ancho * 0.55])
        tabla.setStyle(TableStyle([
            ("GRID", (0, 0), (-1, -1), 0.4, colors.lightgrey),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ]))
        elementos += [tabla, Spacer(1, 12)]

    for t in reporte["tablas"]:
        if not t["filas"]:
            continue
        elementos.append(Paragraph(escape(t["titulo"]), estilos["Heading3"]))
        if t["nota"]:
            elementos.append(parrafo(t["nota"]))
        cabecera = [parrafo(c["nombre"], chico_der if c["tipo"] in NUMERICOS else chico) for c in t["columnas"]]
        cuerpo = [
            [parrafo(formatear(c), chico_der if c.tipo in NUMERICOS else chico) for c in fila]
            for fila in t["filas"]
        ]
        tabla = Table([cabecera] + cuerpo, colWidths=[ancho / len(t["columnas"])] * len(t["columnas"]), repeatRows=1)
        tabla.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), AZUL_TENUE_PDF),
            ("GRID", (0, 0), (-1, -1), 0.4, colors.lightgrey),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ]))
        elementos += [tabla, Spacer(1, 12)]

    documento.build(elementos)
    return salida.getvalue()
