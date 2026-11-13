import { useEffect, useState } from 'react'
import { api, olvidarCsrf } from './api.js'
import Login from './paginas/Login.jsx'
import Inicio from './paginas/Inicio.jsx'
import Productos from './paginas/Productos.jsx'
import ProductoForm from './paginas/ProductoForm.jsx'
import Categorias from './paginas/Categorias.jsx'
import Usuarios from './paginas/Usuarios.jsx'
import Caja from './paginas/Caja.jsx'
import { ir } from './navegacion.js'

// Navegación simple por "#/ruta": no necesita configurar nada en el servidor.
function useRuta() {
  const leer = () => window.location.hash.replace(/^#/, '') || '/'
  const [ruta, setRuta] = useState(leer)
  useEffect(() => {
    const cambio = () => setRuta(leer())
    window.addEventListener('hashchange', cambio)
    return () => window.removeEventListener('hashchange', cambio)
  }, [])
  return ruta
}

const MENU = [
  { ruta: '/', texto: 'Inicio' },
  { ruta: '/caja', texto: 'Caja' },
  { ruta: '/productos', texto: 'Productos y stock' },
  { ruta: '/categorias', texto: 'Categorías' },
  { ruta: '/usuarios', texto: 'Usuarios', soloAdministrador: true },
]

export default function App() {
  const ruta = useRuta()
  const [usuario, setUsuario] = useState(undefined) // undefined = verificando sesión

  useEffect(() => {
    api('/auth/yo/').then(setUsuario).catch(() => setUsuario(null))
  }, [])

  async function salir() {
    await api('/auth/logout/', { metodo: 'POST' }).catch(() => {})
    olvidarCsrf()
    setUsuario(null)
    ir('/')
  }

  if (usuario === undefined) return <p className="p-5 text-center text-secondary">Cargando…</p>
  if (usuario === null)
    return (
      <Login
        alIngresar={(u) => {
          olvidarCsrf()
          setUsuario(u)
        }}
      />
    )

  const esAdmin = usuario.rol === 'ADMINISTRADOR'
  const seccion = '/' + (ruta.split('/')[1] || '')
  let pagina
  if (ruta === '/') pagina = <Inicio usuario={usuario} />
  else if (ruta === '/caja') pagina = <Caja />
  else if (ruta === '/productos') pagina = <Productos esAdmin={esAdmin} />
  else if (ruta === '/productos/nuevo') pagina = <ProductoForm esAdmin={esAdmin} />
  else if (ruta.startsWith('/productos/')) pagina = <ProductoForm id={ruta.split('/')[2]} esAdmin={esAdmin} />
  else if (ruta === '/categorias') pagina = <Categorias esAdmin={esAdmin} />
  else if (ruta === '/usuarios' && esAdmin) pagina = <Usuarios yo={usuario} />
  else pagina = <div className="alert alert-warning">La página no existe o no tenés permiso para verla.</div>

  return (
    <>
      <nav className="navbar navbar-expand ka-barra px-3 py-2">
        <a className="navbar-brand d-flex align-items-center gap-2 text-white fw-bold" href="#/">
          <span className="ka-sello">KA</span> Kiosco Azul
        </a>
        <ul className="navbar-nav me-auto flex-wrap">
          {MENU.filter((m) => !m.soloAdministrador || esAdmin).map((m) => (
            <li className="nav-item" key={m.ruta}>
              <a className={'nav-link' + (seccion === m.ruta ? ' active fw-semibold' : '')} href={'#' + m.ruta}>
                {m.texto}
              </a>
            </li>
          ))}
        </ul>
        <span className="text-white small me-3 text-end d-none d-md-block">
          {usuario.nombre}
          <br />
          <span className="opacity-75">{esAdmin ? 'Administrador (Dueña)' : 'Operador (Empleada)'}</span>
        </span>
        <button className="btn btn-outline-light btn-sm" onClick={salir}>
          Cerrar sesión
        </button>
      </nav>
      <main className="container py-4">{pagina}</main>
    </>
  )
}
