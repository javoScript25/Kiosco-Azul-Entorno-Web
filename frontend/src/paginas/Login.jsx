import { useState } from 'react'
import { api } from '../api.js'

// HU-01: iniciar sesión.
export default function Login({ alIngresar }) {
  const [datos, setDatos] = useState({ nombre_usuario: '', password: '' })
  const [error, setError] = useState('')
  const [enviando, setEnviando] = useState(false)

  async function enviar(e) {
    e.preventDefault()
    setEnviando(true)
    setError('')
    try {
      alIngresar(await api('/auth/login/', { metodo: 'POST', datos }))
    } catch (err) {
      setError(err.message)
    } finally {
      setEnviando(false)
    }
  }

  const vacio = !datos.nombre_usuario.trim() || !datos.password
  return (
    <div className="ka-login d-grid align-items-center p-3">
      <form className="ka-tarjeta p-4 mx-auto shadow" style={{ maxWidth: 400, width: '100%' }} onSubmit={enviar}>
        <div className="d-flex align-items-center gap-2 mb-4">
          <span className="ka-sello">KA</span>
          <div>
            <h1 className="h4 m-0">Kiosco Azul</h1>
            <small className="text-secondary">Sistema de gestión del kiosco</small>
          </div>
        </div>
        {error && (
          <div className="alert alert-danger py-2" role="alert">
            {error}
          </div>
        )}
        <label className="form-label fw-semibold" htmlFor="usuario">
          Usuario
        </label>
        <input
          id="usuario"
          className="form-control mb-3"
          autoComplete="username"
          autoFocus
          value={datos.nombre_usuario}
          onChange={(e) => setDatos({ ...datos, nombre_usuario: e.target.value })}
        />
        <label className="form-label fw-semibold" htmlFor="clave">
          Contraseña
        </label>
        <input
          id="clave"
          type="password"
          className="form-control mb-4"
          autoComplete="current-password"
          value={datos.password}
          onChange={(e) => setDatos({ ...datos, password: e.target.value })}
        />
        <button className="btn btn-primary w-100" disabled={vacio || enviando}>
          {enviando ? 'Ingresando…' : 'Ingresar'}
        </button>
      </form>
    </div>
  )
}
