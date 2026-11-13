// Navegación por "#/ruta" (no necesita configurar nada en el servidor).
export const ir = (ruta) => {
  window.location.hash = ruta
}
