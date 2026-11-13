import { useEffect, useState } from 'react'
import { api, formatoFecha, formatoPesos } from '../api.js'
import Campo from '../componentes/Campo.jsx'

// HU-06: abrir la caja con un monto inicial. Movimientos y arqueo llegan en los sprints 5 y 6.
export default function Caja() {
  const [caja, setCaja] = useState(undefined)
  const [monto, setMonto] = useState('')
  const [error, setError] = useState(null)
  const [enviando, setEnviando] = useState(false)

  useEffect(() => {
    api('/cajas/actual/').then(setCaja).catch((e) => (e.status === 404 ? setCaja(null) : setError(e)))
  }, [])

  async function abrir(e) {
    e.preventDefault()
    setEnviando(true)
    setError(null)
    try {
      setCaja(await api('/cajas/', { metodo: 'POST', datos: { monto_inicial: monto } }))
    } catch (err) {
      setError(err)
    } finally {
      setEnviando(false)
    }
  }

  if (caja === undefined) return <p className="text-secondary">Cargando…</p>

  return (
    <div style={{ maxWidth: 560 }}>
      <p className="text-uppercase small fw-bold text-primary mb-1">3.0 Caja</p>
      {caja ? (
        <>
          <h1 className="fw-bold">Caja abierta</h1>
          <div className="ka-tarjeta p-4 mt-3">
            <dl className="row m-0">
              <dt className="col-6">Abierta por</dt>
              <dd className="col-6">{caja.usuario}</dd>
              <dt className="col-6">Desde</dt>
              <dd className="col-6">{formatoFecha(caja.fecha_hora_apertura)}</dd>
              <dt className="col-6">Monto inicial</dt>
              <dd className="col-6">{formatoPesos(caja.monto_inicial)}</dd>
              <dt className="col-6">Efectivo esperado</dt>
              <dd className="col-6 fw-bold">{formatoPesos(caja.efectivo_esperado)}</dd>
            </dl>
          </div>
          <p className="text-secondary small mt-3">
            Los ingresos, egresos, arqueos y el cierre de caja se suman en los próximos sprints.
          </p>
        </>
      ) : (
        <>
          <h1 className="fw-bold">Abrir caja</h1>
          <p className="text-secondary">Contá el efectivo con el que empieza el turno y cargalo.</p>
          <form className="ka-tarjeta p-4" onSubmit={abrir}>
            {error && !error.campos?.monto_inicial && <div className="alert alert-danger py-2">{error.message}</div>}
            <Campo
              etiqueta="Monto inicial ($)"
              nombre="monto_inicial"
              type="number"
              min="0"
              step="0.01"
              placeholder="20000"
              autoFocus
              value={monto}
              onChange={(e) => setMonto(e.target.value)}
              errores={error?.campos}
            />
            <button className="btn btn-primary" disabled={monto === '' || enviando}>
              {enviando ? 'Abriendo…' : 'Abrir caja'}
            </button>
          </form>
        </>
      )}
    </div>
  )
}
