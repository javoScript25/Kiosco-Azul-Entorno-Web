// Campo de formulario con su etiqueta y el mensaje de error que devuelve la API.
export default function Campo({ etiqueta, nombre, errores, ayuda, children, ...props }) {
  const error = errores?.[nombre]
  const id = 'campo-' + nombre
  return (
    <div className="mb-3">
      <label htmlFor={id} className="form-label fw-semibold">
        {etiqueta}
      </label>
      {children ? (
        <select id={id} name={nombre} className={'form-select' + (error ? ' is-invalid' : '')} {...props}>
          {children}
        </select>
      ) : (
        <input id={id} name={nombre} className={'form-control' + (error ? ' is-invalid' : '')} {...props} />
      )}
      {error ? <div className="invalid-feedback">{error}</div> : ayuda && <div className="form-text">{ayuda}</div>}
    </div>
  )
}
