"""Armado de los cinco reportes de la Dueña (proceso 6.0, RF-17, HU-15 y HU-17).

Cada función devuelve un diccionario con la misma forma, y la pantalla, el
Excel y el PDF lo dibujan igual:

    kpis     [{titulo, celda, nota, tendencia}]
    graficos [{tipo, titulo, descripcion, formato, etiquetas, series}]
    tablas   [{titulo, columnas, filas, nota}]      filas = listas de Celda
    vacio    True si no hay datos en el período ("Sin datos")
"""
from collections import defaultdict
from decimal import Decimal

from django.db.models import Count, DecimalField, ExpressionWrapper, F, Q, Sum
from django.db.models.functions import TruncDate

from . import modelos as m
from .utiles import (
    Celda,
    lista_de_dias,
    limites,
    nombre_usuario,
    periodo_anterior,
    rotulo,
    tendencia,
)

CERO = Decimal("0")
UNIDADES = {"KG": "kg", "UNIDAD": "u"}

# Los alias de annotate/aggregate no pueden llamarse como un campo del modelo
# (total, cantidad, monto, venta...), por eso se usan n, suma, v, c, q.
MONTO = ExpressionWrapper(
    F("cantidad") * F("precio_unitario"),
    output_field=DecimalField(max_digits=22, decimal_places=5),
)
COSTO = ExpressionWrapper(
    F("cantidad") * F("costo_unitario"),
    output_field=DecimalField(max_digits=22, decimal_places=5),
)

# Qué filtros opcionales tiene cada reporte (documentación, flujo F68).
FILTROS_POR_TIPO = {
    "ventas": ("medio_pago",),
    "ganancias": ("categoria", "producto"),
    "mas-vendidos": ("categoria",),
    "caja": (),
    "stock": ("categoria", "producto"),
}


def _d(valor):
    return CERO if valor is None else Decimal(valor)


def _col(nombre, tipo="texto"):
    return {"nombre": nombre, "tipo": tipo}


def _kpi(titulo, valor, tipo, nota="", sentido=None):
    return {"titulo": titulo, "celda": Celda(valor, tipo), "nota": nota, "tendencia": sentido}


def _tabla(titulo, columnas, filas, nota=""):
    return {"titulo": titulo, "columnas": columnas, "filas": filas, "nota": nota}


def _pct(parte, todo):
    return float(parte / todo * 100) if (todo and parte is not None) else None


def _filtrar_producto(qs, categoria, texto, prefijo="producto__"):
    if categoria:
        qs = qs.filter(**{prefijo + "categoria": categoria})
    if texto:
        qs = qs.filter(
            Q(**{prefijo + "nombre__icontains": texto}) | Q(**{prefijo + "codigo_barras": texto})
        )
    return qs


def _vacio(**extra):
    base = {"kpis": [], "graficos": [], "tablas": [], "vacio": True}
    base.update(extra)
    return base


# ---------------------------------------------------------------- ventas ---

def _ventas(ini, fin, medio_pago=None):
    qs = m.Venta.objects.filter(estado=m.CONFIRMADA, fecha_hora__gte=ini, fecha_hora__lt=fin)
    if medio_pago:
        cobradas = m.Pago.objects.filter(
            medio_pago=medio_pago, estado=m.PAGO_CONFIRMADO
        ).values("venta_id")
        qs = qs.filter(pk__in=cobradas)
    return qs


def _ventas_por_dia(qs):
    filas = (
        qs.annotate(dia=TruncDate("fecha_hora"))
        .values("dia")
        .annotate(n=Count("pk"), suma=Sum("total"))
        .order_by("dia")
    )
    return {f["dia"]: (f["n"], _d(f["suma"])) for f in filas}


def reporte_ventas(desde, hasta, medio_pago=None, **_):
    ini, fin = limites(desde, hasta)
    a_desde, a_hasta = periodo_anterior(desde, hasta)
    actual = _ventas(ini, fin, medio_pago)
    anterior = _ventas(*limites(a_desde, a_hasta), medio_pago)

    por_dia = _ventas_por_dia(actual)
    por_dia_ant = _ventas_por_dia(anterior)
    cantidad = sum(n for n, _t in por_dia.values())
    total = sum((t for _n, t in por_dia.values()), CERO)
    cantidad_ant = sum(n for n, _t in por_dia_ant.values())
    total_ant = sum((t for _n, t in por_dia_ant.values()), CERO)

    if not cantidad:
        return _vacio()

    pagos = list(
        m.Pago.objects.filter(venta__in=actual, estado=m.PAGO_CONFIRMADO)
        .values("medio_pago__nombre")
        .annotate(n=Count("pk"), suma=Sum("monto"))
        .order_by("-suma")
    )
    cobrado = sum((_d(p["suma"]) for p in pagos), CERO)
    pendientes = (
        m.Pago.objects.filter(
            estado=m.PAGO_PENDIENTE, venta__fecha_hora__gte=ini, venta__fecha_hora__lt=fin
        )
        .exclude(venta__estado=m.CANCELADA)
        .aggregate(n=Count("pk"), suma=Sum("monto"))
    )

    sentido_n, nota_n = tendencia(cantidad, cantidad_ant)
    sentido_t, nota_t = tendencia(total, total_ant)
    kpis = [
        _kpi("Ventas realizadas", cantidad, "entero", nota_n, sentido_n),
        _kpi("Total vendido", total, "pesos", nota_t, sentido_t),
        _kpi("Ticket promedio", total / cantidad, "pesos", "Total vendido por venta"),
        _kpi(
            "Transferencias pendientes",
            _d(pendientes["suma"]),
            "pesos",
            f"{pendientes['n']} pago(s) sin confirmar, no incluidos en el cobrado",
        ),
    ]

    dias = lista_de_dias(desde, hasta)
    dias_ant = lista_de_dias(a_desde, a_hasta)
    graficos = [
        {
            "tipo": "linea",
            "titulo": "Ventas por día",
            "descripcion": "Total vendido cada día del período, comparado con el período anterior.",
            "formato": "pesos",
            "etiquetas": [d.strftime("%d/%m") for d in dias],
            "series": [
                {"nombre": "Este período", "datos": [float(por_dia.get(d, (0, CERO))[1]) for d in dias]},
                {
                    "nombre": f"Período anterior ({a_desde:%d/%m} al {a_hasta:%d/%m})",
                    "datos": [float(por_dia_ant.get(d, (0, CERO))[1]) for d in dias_ant],
                    "punteada": True,
                },
            ],
        }
    ]
    if pagos:
        graficos.append(
            {
                "tipo": "dona",
                "titulo": "Cobrado por medio de pago",
                "descripcion": "Reparto de lo cobrado entre los medios de pago.",
                "formato": "pesos",
                "etiquetas": [rotulo(p["medio_pago__nombre"]) for p in pagos],
                "series": [{"nombre": "Cobrado", "datos": [float(_d(p["suma"])) for p in pagos]}],
            }
        )

    tabla_dias = [
        [Celda(d, "fecha"), Celda(n, "entero"), Celda(t, "pesos"), Celda(t / n, "pesos")]
        for d, (n, t) in sorted(por_dia.items())
    ]
    tabla_pagos = [
        [
            Celda(rotulo(p["medio_pago__nombre"]), "texto"),
            Celda(p["n"], "entero"),
            Celda(_d(p["suma"]), "pesos"),
            Celda(_pct(_d(p["suma"]), cobrado), "porcentaje"),
        ]
        for p in pagos
    ]
    tablas = [
        _tabla(
            "Ventas por día",
            [_col("Día", "fecha"), _col("Ventas", "entero"), _col("Total", "pesos"), _col("Ticket promedio", "pesos")],
            tabla_dias,
        ),
        _tabla(
            "Cobrado por medio de pago",
            [_col("Medio de pago"), _col("Pagos", "entero"), _col("Monto", "pesos"), _col("% del cobrado", "porcentaje")],
            tabla_pagos,
            "Una venta puede cobrarse con más de un medio. Solo suma el dinero ya confirmado.",
        ),
    ]
    return {"kpis": kpis, "graficos": graficos, "tablas": tablas, "vacio": False}


# ------------------------------------------------------------- ganancias ---

def _lineas(ini, fin, categoria=None, producto=""):
    qs = m.DetalleVenta.objects.filter(
        venta__estado=m.CONFIRMADA, venta__fecha_hora__gte=ini, venta__fecha_hora__lt=fin
    )
    return _filtrar_producto(qs, categoria, producto)


def _ganancia_por_dia(lineas):
    filas = (
        lineas.annotate(dia=TruncDate("venta__fecha_hora"))
        .values("dia")
        .annotate(v=Sum(MONTO), c=Sum(COSTO))
        .order_by("dia")
    )
    return {f["dia"]: (_d(f["v"]), _d(f["c"])) for f in filas}


def reporte_ganancias(desde, hasta, categoria=None, producto="", **_):
    ini, fin = limites(desde, hasta)
    a_desde, a_hasta = periodo_anterior(desde, hasta)
    lineas = _lineas(ini, fin, categoria, producto)

    por_dia = _ganancia_por_dia(lineas)
    por_dia_ant = _ganancia_por_dia(_lineas(*limites(a_desde, a_hasta), categoria, producto))
    vendido = sum((v for v, _c in por_dia.values()), CERO)
    costo = sum((c for _v, c in por_dia.values()), CERO)
    ganancia = vendido - costo
    ganancia_ant = sum((v - c for v, c in por_dia_ant.values()), CERO)

    if not por_dia:
        return _vacio()

    sentido, nota = tendencia(ganancia, ganancia_ant)
    kpis = [
        _kpi("Vendido", vendido, "pesos", "Precio de venta de cada línea"),
        _kpi("Costo de lo vendido", costo, "pesos", "Costo guardado al momento de vender"),
        _kpi("Ganancia", ganancia, "pesos", nota, sentido),
        _kpi("Margen", _pct(ganancia, vendido), "porcentaje", "Ganancia sobre lo vendido"),
    ]

    dias = lista_de_dias(desde, hasta)
    dias_ant = lista_de_dias(a_desde, a_hasta)

    def gan(mapa, dia):
        v, c = mapa.get(dia, (CERO, CERO))
        return float(v - c)

    graficos = [
        {
            "tipo": "linea",
            "titulo": "Ganancia por día",
            "descripcion": "Ganancia de cada día del período, comparada con el período anterior.",
            "formato": "pesos",
            "etiquetas": [d.strftime("%d/%m") for d in dias],
            "series": [
                {"nombre": "Este período", "datos": [gan(por_dia, d) for d in dias]},
                {
                    "nombre": f"Período anterior ({a_desde:%d/%m} al {a_hasta:%d/%m})",
                    "datos": [gan(por_dia_ant, d) for d in dias_ant],
                    "punteada": True,
                },
            ],
        }
    ]

    def agrupar(campo):
        filas = lineas.values(*campo).annotate(v=Sum(MONTO), c=Sum(COSTO))
        resultado = []
        for f in filas:
            v, c = _d(f["v"]), _d(f["c"])
            resultado.append((f, v, c, v - c))
        return sorted(resultado, key=lambda x: x[3], reverse=True)

    por_categoria = [
        [Celda(f["producto__categoria__nombre"], "texto"), Celda(v, "pesos"), Celda(c, "pesos"),
         Celda(g, "pesos"), Celda(_pct(g, v), "porcentaje")]
        for f, v, c, g in agrupar(["producto__categoria__nombre"])
    ]
    por_producto = [
        [Celda(f["producto__nombre"], "texto"), Celda(v, "pesos"), Celda(c, "pesos"),
         Celda(g, "pesos"), Celda(_pct(g, v), "porcentaje")]
        for f, v, c, g in agrupar(["producto_id", "producto__nombre"])[:20]
    ]
    columnas = [_col("Nombre"), _col("Vendido", "pesos"), _col("Costo", "pesos"),
                _col("Ganancia", "pesos"), _col("Margen", "porcentaje")]
    tablas = [
        _tabla("Ganancia por categoría", [dict(columnas[0], nombre="Categoría")] + columnas[1:], por_categoria),
        _tabla("Los 20 productos con más ganancia", [dict(columnas[0], nombre="Producto")] + columnas[1:],
               por_producto, "La ganancia usa el costo que tenía cada producto cuando se vendió."),
    ]
    return {"kpis": kpis, "graficos": graficos, "tablas": tablas, "vacio": False}


# ---------------------------------------------------------- más vendidos ---

def reporte_mas_vendidos(desde, hasta, categoria=None, **_):
    ini, fin = limites(desde, hasta)
    lineas = _lineas(ini, fin, categoria)
    filas = list(
        lineas.values("producto_id", "producto__nombre", "producto__unidad_medida")
        .annotate(q=Sum("cantidad"), mm=Sum(MONTO))
    )
    if not filas:
        return _vacio()

    filas = [
        {"nombre": f["producto__nombre"], "unidad": UNIDADES.get(f["producto__unidad_medida"], ""),
         "q": _d(f["q"]), "m": _d(f["mm"])}
        for f in filas
    ]
    por_cantidad = sorted(filas, key=lambda f: (f["q"], f["m"]), reverse=True)[:10]
    por_monto = sorted(filas, key=lambda f: (f["m"], f["q"]), reverse=True)[:10]
    total = sum((f["m"] for f in filas), CERO)

    kpis = [
        _kpi("Productos distintos vendidos", len(filas), "entero"),
        _kpi("Más vendido por cantidad", por_cantidad[0]["nombre"], "texto"),
        _kpi("Más vendido por monto", por_monto[0]["nombre"], "texto",
             f"{_pct(por_monto[0]['m'], total):.1f} % de lo vendido".replace(".", ",")),
    ]
    graficos = [
        {
            "tipo": "barras-h",
            "titulo": "Los 10 productos que más facturaron",
            "descripcion": "Monto vendido de los diez productos que más dinero generaron.",
            "formato": "pesos",
            "etiquetas": [f["nombre"] for f in por_monto],
            "series": [{"nombre": "Monto vendido", "datos": [float(f["m"]) for f in por_monto]}],
        }
    ]
    cols = [_col("#", "entero"), _col("Producto"), _col("Cantidad", "cantidad"), _col("Unidad"), _col("Monto", "pesos")]
    nota = "La cantidad mezcla unidades y kilos: para comparar productos distintos conviene mirar el monto."
    tablas = [
        _tabla("Los 10 más vendidos por cantidad", cols,
               [[Celda(i, "entero"), Celda(f["nombre"], "texto"), Celda(f["q"], "cantidad"),
                 Celda(f["unidad"], "texto"), Celda(f["m"], "pesos")] for i, f in enumerate(por_cantidad, 1)], nota),
        _tabla("Los 10 más vendidos por monto", cols,
               [[Celda(i, "entero"), Celda(f["nombre"], "texto"), Celda(f["q"], "cantidad"),
                 Celda(f["unidad"], "texto"), Celda(f["m"], "pesos")] for i, f in enumerate(por_monto, 1)]),
    ]
    return {"kpis": kpis, "graficos": graficos, "tablas": tablas, "vacio": False}


# ------------------------------------------------------------------ caja ---

def reporte_caja(desde, hasta, **_):
    ini, fin = limites(desde, hasta)
    turnos = list(
        m.AperturaCaja.objects.filter(fecha_hora_apertura__gte=ini, fecha_hora_apertura__lt=fin)
        .select_related("usuario").order_by("fecha_hora_apertura")
    )
    if not turnos:
        return _vacio()

    ids = [t.pk for t in turnos]
    movimientos = list(
        m.MovimientoCaja.objects.filter(apertura_caja__in=ids)
        .select_related("usuario").order_by("fecha_hora")
    )
    arqueos = list(
        m.ArqueoCaja.objects.filter(apertura_caja__in=ids)
        .select_related("usuario").order_by("fecha_hora")
    )
    mov_por_turno, arq_por_turno = defaultdict(list), defaultdict(list)
    for mov in movimientos:
        mov_por_turno[mov.apertura_caja_id].append(mov)
    for arq in arqueos:
        arq_por_turno[arq.apertura_caja_id].append(arq)

    def suma(lista, tipo):
        return sum((x.monto for x in lista if x.tipo == tipo), CERO)

    filas_turnos, cierres = [], []
    for t in turnos:
        movs, arqs = mov_por_turno[t.pk], arq_por_turno[t.pk]
        cierre = next((a for a in arqs if a.tipo == m.ARQUEO_CIERRE), None)
        ultimo = cierre or (arqs[-1] if arqs else None)
        diferencia = (ultimo.efectivo_contado - ultimo.efectivo_esperado) if ultimo else None
        if cierre:
            cierres.append((t, cierre.efectivo_contado - cierre.efectivo_esperado))
        filas_turnos.append([
            Celda(t.fecha_hora_apertura, "fechahora"), Celda(nombre_usuario(t.usuario), "texto"),
            Celda(rotulo(t.estado), "texto"), Celda(t.monto_inicial, "pesos"),
            Celda(suma(movs, m.MOV_INGRESO), "pesos"), Celda(suma(movs, m.MOV_EGRESO), "pesos"),
            Celda(suma(movs, m.MOV_RETIRO), "pesos"),
            Celda(ultimo.efectivo_esperado if ultimo else None, "pesos"),
            Celda(ultimo.efectivo_contado if ultimo else None, "pesos"),
            Celda(diferencia, "pesos"),
        ])

    diferencia_total = sum((d for _t, d in cierres), CERO)
    con_diferencia = sum(1 for _t, d in cierres if d != 0)
    kpis = [
        _kpi("Turnos de caja", len(turnos), "entero", f"{len(cierres)} cerrado(s)"),
        _kpi("Ingresos de efectivo", suma(movimientos, m.MOV_INGRESO), "pesos", "Movimientos que no son ventas"),
        _kpi("Egresos y retiros", suma(movimientos, m.MOV_EGRESO) + suma(movimientos, m.MOV_RETIRO), "pesos",
             "Pagos a preventistas, gastos y retiros"),
        _kpi("Diferencia en los cierres", diferencia_total, "pesos",
             f"{con_diferencia} cierre(s) con diferencia (contado menos esperado)"),
    ]

    graficos = []
    if cierres:
        graficos.append({
            "tipo": "barras",
            "titulo": "Diferencia de cada cierre",
            "descripcion": "Efectivo contado menos efectivo esperado en cada cierre de caja. Cero significa que cerró justo.",
            "formato": "pesos",
            "etiquetas": [f"{t.fecha_hora_apertura:%d/%m} {nombre_usuario(t.usuario)}" for t, _ in cierres],
            "series": [{"nombre": "Diferencia", "datos": [float(d) for _t, d in cierres]}],
        })

    tablas = [
        _tabla("Turnos de caja",
               [_col("Apertura", "fechahora"), _col("Abrió"), _col("Estado"), _col("Monto inicial", "pesos"),
                _col("Ingresos", "pesos"), _col("Egresos", "pesos"), _col("Retiros", "pesos"),
                _col("Esperado", "pesos"), _col("Contado", "pesos"), _col("Diferencia", "pesos")],
               filas_turnos, "Esperado, contado y diferencia corresponden al cierre, o al último arqueo si el turno sigue abierto."),
        _tabla("Arqueos",
               [_col("Fecha", "fechahora"), _col("Tipo"), _col("Hizo el arqueo"), _col("Esperado", "pesos"),
                _col("Contado", "pesos"), _col("Diferencia", "pesos")],
               [[Celda(a.fecha_hora, "fechahora"), Celda(rotulo(a.tipo), "texto"), Celda(nombre_usuario(a.usuario), "texto"),
                 Celda(a.efectivo_esperado, "pesos"), Celda(a.efectivo_contado, "pesos"),
                 Celda(a.efectivo_contado - a.efectivo_esperado, "pesos")] for a in arqueos]),
        _tabla("Movimientos de caja",
               [_col("Fecha", "fechahora"), _col("Tipo"), _col("Concepto"), _col("Monto", "pesos"), _col("Registró")],
               [[Celda(x.fecha_hora, "fechahora"), Celda(rotulo(x.tipo), "texto"), Celda(x.concepto, "texto"),
                 Celda(x.monto, "pesos"), Celda(nombre_usuario(x.usuario), "texto")] for x in movimientos]),
    ]
    return {"kpis": kpis, "graficos": graficos, "tablas": tablas, "vacio": False}


# ----------------------------------------------------------------- stock ---

def reporte_stock(desde, hasta, categoria=None, producto="", **_):
    ini, fin = limites(desde, hasta)
    productos = _filtrar_producto(m.Producto.objects.filter(activo=True), categoria, producto, prefijo="")
    activos = productos.count()
    alertas = list(
        productos.filter(cantidad_actual__lte=F("stock_minimo"))
        .select_related("categoria")
        .annotate(faltante=F("stock_minimo") - F("cantidad_actual"))
        .order_by("-faltante", "nombre")
    )
    sin_stock = productos.filter(cantidad_actual__lte=0).count()

    movs = _filtrar_producto(
        m.MovimientoStock.objects.filter(fecha_hora__gte=ini, fecha_hora__lt=fin), categoria, producto
    )
    entran = (m.STOCK_ENTRADA, m.STOCK_AJUSTE_POSITIVO)
    por_motivo = defaultdict(lambda: [0, CERO, CERO])
    for f in movs.values("motivo", "tipo").annotate(n=Count("pk"), q=Sum("cantidad")):
        fila = por_motivo[f["motivo"]]
        fila[0] += f["n"]
        fila[1 if f["tipo"] in entran else 2] += _d(f["q"])

    if not activos and not por_motivo:
        return _vacio()

    perdida = _d(
        movs.filter(tipo=m.STOCK_AJUSTE_NEGATIVO, motivo__in=m.MOTIVOS_PERDIDA).aggregate(
            t=Sum(ExpressionWrapper(
                F("cantidad") * F("producto__precio_costo"),
                output_field=DecimalField(max_digits=22, decimal_places=5),
            ))
        )["t"]
    )
    kpis = [
        _kpi("Productos activos", activos, "entero"),
        _kpi("Con stock mínimo o menos", len(alertas), "entero", "Hay que reponerlos"),
        _kpi("Sin stock", sin_stock, "entero", "Productos agotados"),
        _kpi("Pérdida estimada", perdida, "pesos", "Pérdidas, vencimientos y roturas, al último costo"),
    ]

    ajustes = {k: v for k, v in por_motivo.items() if k not in m.MOTIVOS_REGULARES}
    graficos = []
    if ajustes:
        motivos = sorted(ajustes)
        graficos.append({
            "tipo": "barras",
            "titulo": "Ajustes de stock por motivo",
            "descripcion": "Cantidad que entró y que salió por cada motivo de ajuste, sin contar ventas ni recepciones.",
            "formato": "cantidad",
            "etiquetas": [rotulo(k) for k in motivos],
            "series": [
                {"nombre": "Entra", "datos": [float(ajustes[k][1]) for k in motivos]},
                {"nombre": "Sale", "datos": [float(ajustes[k][2]) for k in motivos]},
            ],
        })

    recientes = list(
        movs.exclude(motivo__in=m.MOTIVOS_REGULARES)
        .select_related("producto", "usuario").order_by("-fecha_hora")[:100]
    )
    tablas = [
        _tabla("Productos para reponer",
               [_col("Producto"), _col("Categoría"), _col("Stock", "cantidad"), _col("Mínimo", "cantidad"),
                _col("Faltan", "cantidad"), _col("Unidad")],
               [[Celda(p.nombre, "texto"), Celda(str(p.categoria), "texto"), Celda(p.cantidad_actual, "cantidad"),
                 Celda(p.stock_minimo, "cantidad"), Celda(p.faltante, "cantidad"),
                 Celda(UNIDADES.get(p.unidad_medida, ""), "texto")] for p in alertas]),
        _tabla("Movimientos de stock por motivo",
               [_col("Motivo"), _col("Movimientos", "entero"), _col("Entra", "cantidad"), _col("Sale", "cantidad")],
               [[Celda(rotulo(k), "texto"), Celda(v[0], "entero"), Celda(v[1], "cantidad"), Celda(v[2], "cantidad")]
                for k, v in sorted(por_motivo.items())]),
        _tabla("Pérdidas y ajustes",
               [_col("Fecha", "fechahora"), _col("Producto"), _col("Motivo"), _col("Movimiento"),
                _col("Cantidad", "cantidad"), _col("Usuario"), _col("Observación")],
               [[Celda(x.fecha_hora, "fechahora"), Celda(x.producto.nombre, "texto"), Celda(rotulo(x.motivo), "texto"),
                 Celda("Entra" if x.tipo in entran else "Sale", "texto"), Celda(x.cantidad, "cantidad"),
                 Celda(nombre_usuario(x.usuario), "texto"), Celda(x.observacion, "texto")] for x in recientes],
               "Los últimos 100 movimientos que no son ventas ni recepciones."),
    ]
    return {"kpis": kpis, "graficos": graficos, "tablas": tablas, "vacio": False}


# ------------------------------------------------------------- registro ---

REPORTES = {
    "ventas": ("Ventas", reporte_ventas),
    "ganancias": ("Ganancias", reporte_ganancias),
    "mas-vendidos": ("Más vendidos", reporte_mas_vendidos),
    "caja": ("Caja", reporte_caja),
    "stock": ("Stock", reporte_stock),
}


def armar_reporte(tipo, desde, hasta, **filtros):
    nombre, funcion = REPORTES[tipo]
    permitidos = FILTROS_POR_TIPO[tipo]
    reporte = funcion(desde, hasta, **{k: v for k, v in filtros.items() if k in permitidos})
    reporte.update(tipo=tipo, titulo=nombre, desde=desde, hasta=hasta)
    return reporte
