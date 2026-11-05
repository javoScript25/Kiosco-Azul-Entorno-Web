"""Comprueba el contenido del ZIP recién extraído, sin ejecutar el proyecto."""

import hashlib
import json
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent


def main():
    manifest = json.loads((BASE / "ENTREGA_COMPLETA.json").read_text(encoding="utf-8"))
    for item in manifest["artefactos"]:
        path = (BASE / item["ruta"]).resolve()
        if not path.is_relative_to(BASE):
            raise SystemExit("Ruta inválida en el manifiesto.")
        data = path.read_bytes()
        if (
            len(data) != item["bytes"]
            or hashlib.sha256(data).hexdigest() != item["sha256"]
        ):
            raise SystemExit("No coincide: " + item["ruta"])
    print(
        f"Verificados {len(manifest['artefactos'])} archivos. Commit: {manifest['commit']}"
    )
    print("Esto comprueba integridad; obtené el ZIP de una fuente confiable.")


if __name__ == "__main__":
    main()
