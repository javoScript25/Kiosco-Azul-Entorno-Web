import { useEffect, useState } from 'react'
import { api, formatoCantidad, formatoPesos } from '../api.js'
import { ir } from '../navegacion.js'

// HU-05 (búsqueda y lector de código de barras) y HU-14 (stock y alertas).
export default function Productos({ esAdmin }) {
  const [filtros, setFiltros] = useState({ buscar: '', categoria: '', solo_alertas: false, inactivos: false })
  const [pagina, setPagina] = useState(1)
  const [datos, setDatos] = useState(null)
  const [categorias, setCategorias] = useState([])
  const [codigo, setCodigo] = useState('')
  const [aviso, setAviso] = useState('')
  const [error, setError] = useState('')

  useEffect(() => {
    api('/categorias/').then((c) => setCategorias(c.filter((x) => x.activa)))
  }, [])

  useEffect(() => {
    const p = new URLSearchParams({ page: pagina })
    if (filtros.buscar.trim()) p.set('buscar', filtros.buscar.trim())
    if (filtros.categoria) p.set('categoria', filtros.categoria)
    if (filtros.solo_alertas) p.set('solo_alertas', 'true')
    if (filtros.inactivos) p.set('inactivos', 'true')
    const espera = setTimeout(() => {
      api('/productos/?' + p).then(setDatos).catch((e) => setError(e.message))
    }, 250)
    return () => clearTimeout(espera)
  }, [filtros, pagina])

  const cambiar = (campo, valor) => {
    setPagina(1)
    setFiltros({ ...filtros, [campo]: valor })
  }

  // El lector de código de barras escribe el código y presiona Enter.
  async function buscarCodigo(e) {
    e.preventDefault()
    if (!codigo.trim()) return
    setAviso('')
    try {
      const p = await api('/productos/codigo/' + encodeURIComponent(codigo.trim()) + '/')
      ir('/productos/' + p.id_producto)
    } catch (err) {
      setAviso(err.message)
      setCodigo('')
    }
  }

  const paginas = datos ? Math.ceil(datos.count / 20) : 0
  return (
    <>
      <div className="d-flex justify-content-between align-items-end flex-wrap gap-2 mb-3">
        <div>
          <p className="text-uppercase small fw-bold text-primary mb-1">Catálogo y stock</p>
          <h1 className="fw-bold m-0">Productos</h1>
        </div>
        {esAdmin && (
          <a className="btn btn-primary" href="#/productos/nuevo">
            Agregar producto
          </a>
        )}
      </div>

      <form className="ka-tarjeta p-3 mb-3" onSubmit={buscarCodigo}>
        <label className="form-label fw-semibold" htmlFor="lector">
          Lector de código de barras
        </label>
        <div className="input-group">
          <input
            id="lector"
            className="form-control"
            placeholder="Pasá el lector o escribí el código y presioná Enter"
            value={codigo}
            onChange={(e) => setCodigo(e.target.value)}
          />
          <button className="btn btn-outline-primary">Buscar código</button>
        </div>
        {aviso && <div className="text-danger small mt-2">{aviso}</div>}
      </form>

      <div className="ka-tarjeta p-3 mb-3">
        <div className="row g-2 align-items-center">
          <div className="col-md-5">
            <input
              className="form-control"
              type="search"
              placeholder="Buscar por nombre, código o categoría"
              aria-label="Buscar"
              value={filtros.buscar}
              onChange={(e) => cambiar('buscar', e.target.value)}
            />
          </div>
          <div className="col-md-3">
            <select
              className="form-select"
              aria-label="Categoría"
              value={filtros.categoria}
              onChange={(e) => cambiar('categoria', e.target.value)}
            >
              <option value="">Todas las categorías</option>
              {categorias.map((c) => (
                <option key={c.id_categoria} value={c.id_categoria}>
                  {c.nombre}
                </option>
              ))}
            </select>
          </div>
          <div className="col-md-4 d-flex gap-3 flex-wrap">
            <label className="form-check">
              <input
                className="form-check-input"
                type="checkbox"
                checked={filtros.solo_alertas}
                onChange={(e) => cambiar('solo_alertas', e.target.checked)}
              />{' '}
              Solo con stock mínimo
            </label>
            {esAdmin && (
              <label className="form-check">
                <input
                  className="form-check-input"
                  type="checkbox"
                  checked={filtros.inactivos}
                  onChange={(e) => cambiar('inactivos', e.target.checked)}
                />{' '}
                Incluir dados de baja
              </label>
            )}
          </div>
        </div>
      </div>

      {error && <div className="alert alert-danger">{error}</div>}
      {!datos ? (
        <p className="text-secondary">Cargando…</p>
      ) : datos.count === 0 ? (
        <div className="ka-tarjeta p-4 text-center">
          <h2 className="h5">No encontramos coincidencias</h2>
          <p className="text-secondary m-0">Probá con otro nombre, código o categoría.</p>
        </div>
      ) : (
        <div className="ka-tarjeta table-responsive">
          <table className="table table-hover m-0">
            <caption className="px-3">
              {datos.count} producto{datos.count === 1 ? '' : 's'}
            </caption>
            <thead>
              <tr>
                <th>Producto</th>
                <th>Categoría</th>
                <th className="text-end">Precio</th>
                <th className="text-end">Stock</th>
              </tr>
            </thead>
            <tbody>
              {datos.results.map((p) => (
                <tr key={p.id_producto} className="cursor" onClick={() => ir('/productos/' + p.id_producto)}>
                  <td>
                    <strong>{p.nombre}</strong>
                    <br />
                    <small className="text-secondary">
                      {p.codigo_barras}
                      {!p.activo && <span className="badge text-bg-secondary ms-2">Dado de baja</span>}
                    </small>
                  </td>
                  <td>{p.categoria}</td>
                  <td className="text-end">
                    {formatoPesos(p.precio_venta)}
                    {p.unidad_medida === 'KG' && ' /kg'}
                  </td>
                  <td className={'text-end' + (p.en_alerta ? ' ka-alerta' : '')}>
                    {formatoCantidad(p.cantidad_actual, p.unidad_medida)}
                    {p.en_alerta && ' · reponer'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {paginas > 1 && (
        <nav className="d-flex justify-content-center gap-2 mt-3" aria-label="Páginas">
          <button className="btn btn-outline-primary btn-sm" disabled={pagina === 1} onClick={() => setPagina(pagina - 1)}>
            Anterior
          </button>
          <span className="align-self-center small">
            Página {pagina} de {paginas}
          </span>
          <button
            className="btn btn-outline-primary btn-sm"
            disabled={pagina === paginas}
            onClick={() => setPagina(pagina + 1)}
          >
            Siguiente
          </button>
        </nav>
      )}
    </>
  )
}
