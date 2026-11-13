import { useEffect, useState } from 'react'
import { api } from '../api.js'
import Campo from '../componentes/Campo.jsx'

// HU-03: administrar categorías (la Empleada solo las consulta).
export default function Categorias({ esAdmin }) {
  const [lista, setLista] = useState([])
  const [form, setForm] = useState({ nombre: '', descripcion: '' })
  const [editando, setEditando] = useState(null) // id de la categoría en edición
  const [error, setError] = useState(null)
  const [aviso, setAviso] = useState('')

  const cargar = () => api('/categorias/').then(setLista)
  useEffect(() => {
    cargar()
  }, [])

  async function guardar(e) {
    e.preventDefault()
    setError(null)
    try {
      if (editando) await api(`/categorias/${editando}/`, { metodo: 'PATCH', datos: form })
      else await api('/categorias/', { metodo: 'POST', datos: form })
      setForm({ nombre: '', descripcion: '' })
      setEditando(null)
      setAviso('Categoría guardada.')
      cargar()
    } catch (err) {
      setError(err)
    }
  }

  async function cambiarEstado(c) {
    setAviso('')
    try {
      await api(`/categorias/${c.id_categoria}/`, { metodo: 'PATCH', datos: { activa: !c.activa } })
      setAviso(c.activa ? 'Categoría desactivada.' : 'Categoría reactivada.')
      cargar()
    } catch (err) {
      setAviso(err.message)
    }
  }

  return (
    <div className="row g-4">
      <div className={esAdmin ? 'col-lg-7' : 'col-12'}>
        <p className="text-uppercase small fw-bold text-primary mb-1">Catálogo</p>
        <h1 className="fw-bold">Categorías</h1>
        {aviso && <div className="alert alert-info py-2">{aviso}</div>}
        <div className="ka-tarjeta">
          <ul className="list-group list-group-flush">
            {lista.map((c) => (
              <li key={c.id_categoria} className="list-group-item d-flex justify-content-between gap-2 flex-wrap">
                <span>
                  <strong>{c.nombre}</strong>
                  {!c.activa && <span className="badge text-bg-secondary ms-2">Inactiva</span>}
                  <br />
                  <small className="text-secondary">{c.descripcion}</small>
                </span>
                {esAdmin && (
                  <span className="d-flex gap-2 align-items-center">
                    <button className="btn btn-sm btn-outline-primary" onClick={() => {
                      setEditando(c.id_categoria)
                      setForm({ nombre: c.nombre, descripcion: c.descripcion })
                      setError(null)
                    }}>
                      Editar
                    </button>
                    <button className={'btn btn-sm ' + (c.activa ? 'btn-outline-danger' : 'btn-outline-success')}
                      onClick={() => cambiarEstado(c)}>
                      {c.activa ? 'Desactivar' : 'Reactivar'}
                    </button>
                  </span>
                )}
              </li>
            ))}
          </ul>
        </div>
      </div>
      {esAdmin && (
        <div className="col-lg-5">
          <h2 className="h4 mt-lg-5">{editando ? 'Editar categoría' : 'Agregar categoría'}</h2>
          <form className="ka-tarjeta p-4" onSubmit={guardar}>
            {error && !Object.keys(error.campos).length && <div className="alert alert-danger py-2">{error.message}</div>}
            <Campo etiqueta="Nombre" nombre="nombre" value={form.nombre} errores={error?.campos}
              onChange={(e) => setForm({ ...form, nombre: e.target.value })} />
            <Campo etiqueta="Descripción (opcional)" nombre="descripcion" value={form.descripcion} errores={error?.campos}
              onChange={(e) => setForm({ ...form, descripcion: e.target.value })} />
            <div className="d-flex gap-2">
              <button className="btn btn-primary">Guardar</button>
              {editando && (
                <button type="button" className="btn btn-link" onClick={() => {
                  setEditando(null)
                  setForm({ nombre: '', descripcion: '' })
                }}>
                  Cancelar
                </button>
              )}
            </div>
          </form>
        </div>
      )}
    </div>
  )
}
