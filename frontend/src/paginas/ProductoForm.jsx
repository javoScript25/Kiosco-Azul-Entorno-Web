import { useEffect, useState } from 'react'
import { api, formatoCantidad, formatoFecha, formatoPesos } from '../api.js'
import Campo from '../componentes/Campo.jsx'
import { ir } from '../navegacion.js'

const VACIO = {
  codigo_barras: '', nombre: '', id_categoria: '', descripcion: '', unidad_medida: 'UNIDAD',
  precio_costo: '', precio_venta: '', stock_minimo: '0', preventista: '',
}

// HU-04 (alta, modificación y baja lógica) y HU-16 (historial de precios).
// La Empleada ve el producto en modo consulta, sin costo.
export default function ProductoForm({ id, esAdmin }) {
  const [datos, setDatos] = useState(VACIO)
  const [producto, setProducto] = useState(null)
  const [categorias, setCategorias] = useState([])
  const [historial, setHistorial] = useState([])
  const [error, setError] = useState(null)
  const [ok, setOk] = useState('')

  useEffect(() => {
    api('/categorias/').then(setCategorias)
    if (!id) return
    api(`/productos/${id}/`)
      .then((p) => {
        setProducto(p)
        setDatos({ ...VACIO, ...p })
      })
      .catch(setError)
    if (esAdmin) api(`/productos/${id}/historial-precios/`).then(setHistorial)
  }, [id, esAdmin])

  async function guardar(e) {
    e.preventDefault()
    setError(null)
    setOk('')
    const cuerpo = { ...datos }
    for (const k of ['id_producto', 'categoria', 'cantidad_actual', 'en_alerta', 'activo']) delete cuerpo[k]
    try {
      if (id) {
        const p = await api(`/productos/${id}/`, { metodo: 'PATCH', datos: cuerpo })
        setProducto(p)
        setOk('Cambios guardados.')
        api(`/productos/${id}/historial-precios/`).then(setHistorial)
      } else {
        const p = await api('/productos/', { metodo: 'POST', datos: cuerpo })
        ir('/productos/' + p.id_producto)
      }
    } catch (err) {
      setError(err)
    }
  }

  async function cambiarEstado() {
    const p = await api(`/productos/${id}/`, { metodo: 'PATCH', datos: { activo: !producto.activo } })
    setProducto(p)
    setOk(p.activo ? 'Producto reactivado.' : 'Producto dado de baja: ya no aparece para vender.')
  }

  const poner = (campo) => (e) => setDatos({ ...datos, [campo]: e.target.value })
  if (id && !producto)
    return error ? <div className="alert alert-warning">{error.message}</div> : <p className="text-secondary">Cargando…</p>

  if (!esAdmin)
    return (
      <div style={{ maxWidth: 640 }}>
        <a href="#/productos">← Volver a productos</a>
        <p className="text-uppercase small fw-bold text-primary mt-3 mb-1">
          {producto.categoria} · {producto.codigo_barras}
        </p>
        <h1 className="fw-bold">{producto.nombre}</h1>
        <div className="ka-tarjeta p-4">
          <dl className="row m-0">
            <dt className="col-6">Precio de venta</dt>
            <dd className="col-6">
              {formatoPesos(producto.precio_venta)}
              {producto.unidad_medida === 'KG' && ' por kilo'}
            </dd>
            <dt className="col-6">Stock actual</dt>
            <dd className={'col-6' + (producto.en_alerta ? ' ka-alerta' : '')}>
              {formatoCantidad(producto.cantidad_actual, producto.unidad_medida)}
            </dd>
            <dt className="col-6">Stock mínimo</dt>
            <dd className="col-6">{formatoCantidad(producto.stock_minimo, producto.unidad_medida)}</dd>
            <dt className="col-6">Descripción</dt>
            <dd className="col-6">{producto.descripcion || 'Sin descripción.'}</dd>
          </dl>
        </div>
      </div>
    )

  const activas = categorias.filter((c) => c.activa || c.id_categoria === datos.id_categoria)
  return (
    <div className="row g-4">
      <div className="col-lg-7">
        <a href="#/productos">← Volver a productos</a>
        <h1 className="fw-bold mt-3">{id ? 'Editar producto' : 'Agregar producto'}</h1>
        <p className="text-secondary">
          {id
            ? 'Si cambiás el costo o el precio de venta, el cambio queda en el historial de precios.'
            : 'El producto se crea con stock 0: el stock entra cuando se registra la mercadería recibida.'}
        </p>
        <form className="ka-tarjeta p-4" onSubmit={guardar} noValidate>
          {error && <div className="alert alert-danger py-2">{error.message}</div>}
          {ok && <div className="alert alert-success py-2">{ok}</div>}
          <div className="row">
            <div className="col-md-6">
              <Campo etiqueta="Código de barras" nombre="codigo_barras" value={datos.codigo_barras}
                onChange={poner('codigo_barras')} errores={error?.campos}
                ayuda="Pasá el lector o usá un código interno para productos por peso." />
            </div>
            <div className="col-md-6">
              <Campo etiqueta="Nombre" nombre="nombre" value={datos.nombre} onChange={poner('nombre')} errores={error?.campos} />
            </div>
            <div className="col-md-6">
              <Campo etiqueta="Categoría" nombre="id_categoria" value={datos.id_categoria}
                onChange={(e) => setDatos({ ...datos, id_categoria: Number(e.target.value) || '' })} errores={error?.campos}>
                <option value="">Elegí una categoría</option>
                {activas.map((c) => (
                  <option key={c.id_categoria} value={c.id_categoria}>{c.nombre}</option>
                ))}
              </Campo>
            </div>
            <div className="col-md-6">
              <Campo etiqueta="Se vende" nombre="unidad_medida" value={datos.unidad_medida}
                onChange={poner('unidad_medida')} errores={error?.campos}>
                <option value="UNIDAD">Por unidad</option>
                <option value="KG">Por kilo</option>
              </Campo>
            </div>
            <div className="col-md-4">
              <Campo etiqueta="Precio de costo ($)" nombre="precio_costo" type="number" min="0" step="0.01"
                value={datos.precio_costo} onChange={poner('precio_costo')} errores={error?.campos} />
            </div>
            <div className="col-md-4">
              <Campo etiqueta="Precio de venta ($)" nombre="precio_venta" type="number" min="0" step="0.01"
                value={datos.precio_venta} onChange={poner('precio_venta')} errores={error?.campos} />
            </div>
            <div className="col-md-4">
              <Campo etiqueta="Stock mínimo" nombre="stock_minimo" type="number" min="0" step="0.001"
                value={datos.stock_minimo} onChange={poner('stock_minimo')} errores={error?.campos} />
            </div>
            <div className="col-md-6">
              <Campo etiqueta="Preventista (opcional)" nombre="preventista" value={datos.preventista}
                onChange={poner('preventista')} errores={error?.campos} />
            </div>
            <div className="col-md-6">
              <Campo etiqueta="Descripción (opcional)" nombre="descripcion" value={datos.descripcion}
                onChange={poner('descripcion')} errores={error?.campos} />
            </div>
          </div>
          <div className="d-flex gap-2 flex-wrap">
            <button className="btn btn-primary">Guardar producto</button>
            {id && (
              <button type="button" className={'btn ' + (producto.activo ? 'btn-outline-danger' : 'btn-outline-success')}
                onClick={cambiarEstado}>
                {producto.activo ? 'Dar de baja' : 'Reactivar'}
              </button>
            )}
          </div>
        </form>
      </div>
      {id && (
        <div className="col-lg-5">
          <div className="ka-tarjeta p-4 mb-3">
            <div className="text-secondary">Stock actual</div>
            <div className={'ka-dato' + (producto.en_alerta ? ' ka-alerta' : '')}>
              {formatoCantidad(producto.cantidad_actual, producto.unidad_medida)}
            </div>
            <small className="text-secondary">Cambia con recepciones, ventas y ajustes.</small>
            {!producto.activo && <div className="badge text-bg-secondary d-block mt-2">Dado de baja</div>}
          </div>
          <h2 className="h5">Historial de precios</h2>
          {historial.length === 0 ? (
            <p className="text-secondary">Sin cambios de precio.</p>
          ) : (
            <div className="ka-tarjeta table-responsive">
              <table className="table table-sm m-0">
                <thead>
                  <tr><th>Fecha</th><th>Costo</th><th>Venta</th><th>Usuario</th></tr>
                </thead>
                <tbody>
                  {historial.map((h) => (
                    <tr key={h.id_historial_precio}>
                      <td>{formatoFecha(h.fecha_hora)}</td>
                      <td>{formatoPesos(h.costo_anterior)} → {formatoPesos(h.costo_nuevo)}</td>
                      <td>{formatoPesos(h.venta_anterior)} → {formatoPesos(h.venta_nuevo)}</td>
                      <td>{h.usuario}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
