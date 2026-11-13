import { useEffect, useState } from 'react'
import { api, formatoCantidad, formatoFecha } from '../api.js'

// Inicio: estado de la caja y alertas de stock mínimo (HU-14).
export default function Inicio({ usuario }) {
  const [caja, setCaja] = useState(undefined)
  const [alertas, setAlertas] = useState([])
  const [error, setError] = useState('')

  useEffect(() => {
    api('/cajas/actual/').then(setCaja).catch((e) => (e.status === 404 ? setCaja(null) : setError(e.message)))
    api('/stock/?solo_alertas=true').then(setAlertas).catch((e) => setError(e.message))
  }, [])

  return (
    <>
      <p className="text-uppercase small fw-bold text-primary mb-1">Kiosco Azul</p>
      <h1 className="fw-bold">Hola, {usuario.nombre.split(' ')[0]}.</h1>
      {error && <div className="alert alert-danger">{error}</div>}

      <div className="row g-3 my-2">
        <div className="col-md-6">
          <a href="#/caja" className="ka-tarjeta p-4 d-block text-decoration-none text-reset h-100">
            <div className="text-secondary">Caja</div>
            {caja === undefined ? (
              <div className="ka-dato">…</div>
            ) : caja ? (
              <>
                <div className="ka-dato text-success">Abierta</div>
                <small className="text-secondary">
                  Desde {formatoFecha(caja.fecha_hora_apertura)} por {caja.usuario}
                </small>
              </>
            ) : (
              <>
                <div className="ka-dato">Cerrada</div>
                <small className="text-primary">Abrí la caja para empezar el turno →</small>
              </>
            )}
          </a>
        </div>
        <div className="col-md-6">
          <a href="#/productos" className="ka-tarjeta p-4 d-block text-decoration-none text-reset h-100">
            <div className="text-secondary">Productos con stock mínimo</div>
            <div className={'ka-dato' + (alertas.length ? ' ka-alerta' : '')}>{alertas.length}</div>
            <small className="text-secondary">Hay que reponerlos</small>
          </a>
        </div>
      </div>

      <h2 className="h4 mt-4">Alertas de stock mínimo</h2>
      <div className="ka-tarjeta">
        {alertas.length === 0 ? (
          <p className="p-4 m-0 text-secondary">Ningún producto activo llegó a su stock mínimo.</p>
        ) : (
          <ul className="list-group list-group-flush">
            {alertas.map((p) => (
              <li key={p.id_producto} className="list-group-item d-flex justify-content-between flex-wrap gap-2">
                <a href={`#/productos/${p.id_producto}`} className="text-reset text-decoration-none">
                  <strong>{p.nombre}</strong>
                  <br />
                  <small className="text-secondary">
                    {p.categoria} · {p.codigo_barras}
                  </small>
                </a>
                <span className="ka-alerta align-self-center">
                  Quedan {formatoCantidad(p.cantidad_actual, p.unidad_medida)} (mínimo{' '}
                  {formatoCantidad(p.stock_minimo, p.unidad_medida)})
                </span>
              </li>
            ))}
          </ul>
        )}
      </div>
    </>
  )
}
