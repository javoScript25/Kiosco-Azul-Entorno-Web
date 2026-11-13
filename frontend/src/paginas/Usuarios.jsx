import { useEffect, useState } from 'react'
import { api } from '../api.js'
import Campo from '../componentes/Campo.jsx'

const VACIO = { nombre_usuario: '', nombre: '', apellido: '', email: '', rol: 'OPERADOR', activo: true, password: '' }

// HU-02: administrar usuarios y roles (solo la Dueña).
export default function Usuarios({ yo }) {
  const [lista, setLista] = useState([])
  const [form, setForm] = useState(VACIO)
  const [editando, setEditando] = useState(null)
  const [error, setError] = useState(null)
  const [aviso, setAviso] = useState('')

  const cargar = () => api('/usuarios/').then(setLista)
  useEffect(() => {
    cargar()
  }, [])

  async function guardar(e) {
    e.preventDefault()
    setError(null)
    setAviso('')
    const datos = { ...form }
    if (editando && !datos.password) delete datos.password
    try {
      if (editando) await api(`/usuarios/${editando}/`, { metodo: 'PATCH', datos })
      else await api('/usuarios/', { metodo: 'POST', datos })
      setAviso('Usuario guardado.')
      setForm(VACIO)
      setEditando(null)
      cargar()
    } catch (err) {
      setError(err)
    }
  }

  const poner = (campo) => (e) => setForm({ ...form, [campo]: e.target.value })
  return (
    <div className="row g-4">
      <div className="col-lg-7">
        <p className="text-uppercase small fw-bold text-primary mb-1">1.0 Acceso</p>
        <h1 className="fw-bold">Usuarios y roles</h1>
        <p className="text-secondary">
          La Dueña es ADMINISTRADOR y la Empleada es OPERADOR. Un usuario sin acceso no puede ingresar, pero sus
          operaciones se conservan.
        </p>
        {aviso && <div className="alert alert-success py-2">{aviso}</div>}
        <div className="ka-tarjeta table-responsive">
          <table className="table m-0">
            <thead>
              <tr><th>Usuario</th><th>Rol</th><th>Estado</th><th></th></tr>
            </thead>
            <tbody>
              {lista.map((u) => (
                <tr key={u.id_usuario}>
                  <td>
                    <strong>{u.nombre_usuario}</strong>
                    {u.id_usuario === yo.id_usuario && <span className="badge text-bg-primary ms-2">Vos</span>}
                    <br />
                    <small className="text-secondary">{[u.nombre, u.apellido].filter(Boolean).join(' ') || u.email}</small>
                  </td>
                  <td>{u.rol === 'ADMINISTRADOR' ? 'Administrador (Dueña)' : 'Operador (Empleada)'}</td>
                  <td>{u.activo ? 'Activo' : <span className="badge text-bg-secondary">Sin acceso</span>}</td>
                  <td className="text-end">
                    <button className="btn btn-sm btn-outline-primary" onClick={() => {
                      setEditando(u.id_usuario)
                      setForm({ ...VACIO, ...u, password: '' })
                      setError(null)
                    }}>
                      Editar
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
      <div className="col-lg-5">
        <h2 className="h4 mt-lg-5">{editando ? `Editar a ${form.nombre_usuario}` : 'Agregar usuario'}</h2>
        <form className="ka-tarjeta p-4" onSubmit={guardar} noValidate>
          {error && <div className="alert alert-danger py-2">{error.message}</div>}
          <Campo etiqueta="Nombre de usuario" nombre="nombre_usuario" value={form.nombre_usuario}
            onChange={poner('nombre_usuario')} errores={error?.campos} />
          <div className="row">
            <div className="col-6">
              <Campo etiqueta="Nombre" nombre="nombre" value={form.nombre} onChange={poner('nombre')} errores={error?.campos} />
            </div>
            <div className="col-6">
              <Campo etiqueta="Apellido" nombre="apellido" value={form.apellido} onChange={poner('apellido')} errores={error?.campos} />
            </div>
          </div>
          <Campo etiqueta="Correo" nombre="email" type="email" value={form.email} onChange={poner('email')} errores={error?.campos} />
          <Campo etiqueta="Rol" nombre="rol" value={form.rol} onChange={poner('rol')} errores={error?.campos}>
            <option value="OPERADOR">Operador (Empleada)</option>
            <option value="ADMINISTRADOR">Administrador (Dueña)</option>
          </Campo>
          <Campo etiqueta={editando ? 'Nueva contraseña (opcional)' : 'Contraseña'} nombre="password" type="password"
            autoComplete="new-password" value={form.password} onChange={poner('password')} errores={error?.campos}
            ayuda="Mínimo 10 caracteres; no solo números ni una clave común." />
          <label className="form-check mb-3">
            <input className="form-check-input" type="checkbox" checked={form.activo}
              onChange={(e) => setForm({ ...form, activo: e.target.checked })} />{' '}
            Puede ingresar
          </label>
          <div className="d-flex gap-2">
            <button className="btn btn-primary">Guardar usuario</button>
            {editando && (
              <button type="button" className="btn btn-link" onClick={() => {
                setEditando(null)
                setForm(VACIO)
                setError(null)
              }}>
                Cancelar
              </button>
            )}
          </div>
        </form>
      </div>
    </div>
  )
}
