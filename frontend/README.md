# Kiosco Azul · Frontend (React + Vite + Bootstrap)

Consume la API REST de Django (`/api/`). Requiere Node.js 18 o más nuevo.

```powershell
cd frontend
npm install      # la primera vez
npm run dev      # http://localhost:5173
```

Antes, el sistema tiene que estar encendido (`docker compose up -d` en la carpeta del proyecto).
Vite reenvía `/api` a `http://localhost:8000`, así la sesión y el CSRF de Django funcionan sin CORS.

| Carpeta | Contenido |
|---|---|
| `src/api.js` | Cliente de la API: sesión, token CSRF, errores y formatos |
| `src/App.jsx` | Sesión, menú según el rol y rutas `#/...` |
| `src/paginas/` | Login, Inicio, Caja, Productos, ProductoForm, Categorías, Usuarios |
| `src/componentes/` | Campo de formulario con el error que devuelve la API |
