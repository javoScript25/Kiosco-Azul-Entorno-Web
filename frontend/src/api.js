// Cliente de la API REST de Kiosco Azul.
// Usa la sesión de Django (cookie) y envía el token CSRF en cada escritura.

let tokenCsrf = null

export class ErrorApi extends Error {
  constructor(status, datos) {
    super(datos?.mensaje || 'No se pudo completar la operación.')
    this.status = status
    this.codigo = datos?.error || 'error'
    this.campos = datos?.campos || {}
  }
}

async function obtenerCsrf() {
  if (!tokenCsrf) {
    const r = await fetch('/api/auth/csrf/', { credentials: 'same-origin' })
    tokenCsrf = (await r.json()).csrf
  }
  return tokenCsrf
}

export async function api(ruta, { metodo = 'GET', datos } = {}) {
  const opciones = { method: metodo, credentials: 'same-origin', headers: { Accept: 'application/json' } }
  if (metodo !== 'GET') {
    opciones.headers['Content-Type'] = 'application/json'
    opciones.headers['X-CSRFToken'] = await obtenerCsrf()
    if (datos !== undefined) opciones.body = JSON.stringify(datos)
  }
  let respuesta
  try {
    respuesta = await fetch('/api' + ruta, opciones)
  } catch {
    throw new ErrorApi(0, { mensaje: 'No hay conexión con el servidor. ¿Está encendido Docker?' })
  }
  if (respuesta.status === 204) return null
  const cuerpo = await respuesta.json().catch(() => null)
  if (!respuesta.ok) throw new ErrorApi(respuesta.status, cuerpo)
  return cuerpo
}

// Al iniciar o cerrar sesión Django cambia el token CSRF: se vuelve a pedir.
export function olvidarCsrf() {
  tokenCsrf = null
}

const pesos = new Intl.NumberFormat('es-AR', { style: 'currency', currency: 'ARS' })
const numero = new Intl.NumberFormat('es-AR', { maximumFractionDigits: 3 })

export const formatoPesos = (v) => pesos.format(Number(v || 0))
export const formatoCantidad = (v, unidad) => `${numero.format(Number(v || 0))} ${unidad === 'KG' ? 'kg' : 'u.'}`
export const formatoFecha = (v) =>
  new Date(v).toLocaleString('es-AR', { dateStyle: 'short', timeStyle: 'short' })
