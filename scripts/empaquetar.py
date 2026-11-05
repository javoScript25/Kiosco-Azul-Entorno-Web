"""Crea un ZIP docente exclusivamente desde archivos confirmados en Git."""

import argparse
import hashlib
import io
import json
import platform
import subprocess
import tarfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent


def git(*args):
    return subprocess.check_output(["git", "-C", str(BASE), *args])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--alumnos", action="store_true",
                        help="Excluir README.md y AGENTS.md de la entrega.")
    options = parser.parse_args()
    if git("status", "--porcelain", "--", ".").strip():
        raise SystemExit("Confirmá primero los cambios de la plantilla en Git.")
    root = Path(git("rev-parse", "--show-toplevel").decode().strip())
    prefix = BASE.relative_to(root).as_posix()
    prefix = "" if prefix == "." else prefix + "/"
    commit = git("rev-parse", "HEAD").decode().strip()
    args = ["archive", "--format=tar", "HEAD"]
    if prefix:
        args.append(prefix)
    archivos = {}
    archive_data = subprocess.check_output(["git", "-C", str(root), *args])
    with tarfile.open(fileobj=io.BytesIO(archive_data)) as archive:
        for member in archive.getmembers():
            if not member.isfile():
                continue
            name = member.name[len(prefix) :]
            if name == "ENTREGA_COMPLETA.json":
                continue  # Se genera un manifiesto nuevo para este commit.
            if options.alumnos and Path(name).name.lower() in {"readme.md", "agents.md"}:
                continue
            parts = Path(name).parts
            if any(
                part
                in {".git", "dist", "backups", "staticfiles", "__pycache__", ".venv"}
                for part in parts
            ):
                continue
            if Path(name).name.startswith(".env") and Path(name).name != ".env.example":
                raise SystemExit(
                    "Hay configuración privada versionada: revisar antes de distribuir."
                )
            if Path(name).suffix.lower() in {".dump", ".sqlite3", ".pem", ".key"}:
                raise SystemExit(
                    "Se detectó un archivo privado o base: revisar el repositorio."
                )
            archivos[name] = archive.extractfile(member).read()
    manifest = {
        "version_esquema": 1,
        "perfil": "alumnos" if options.alumnos else "completo",
        "commit": commit,
        "rama": git("branch", "--show-current").decode().strip(),
        "fecha_utc": datetime.now(timezone.utc).isoformat(),
        "plataforma_empaquetado": platform.platform(),
        "origen_respaldo": "Código confirmado en Git; sin base, cuentas ni configuración privada.",
        "imagenes": "Digest fijado en Dockerfile y archivos compose.",
        "verificacion": "python scripts/verificar_entrega.py",
        "artefactos": [
            {
                "ruta": name,
                "bytes": len(data),
                "sha256": hashlib.sha256(data).hexdigest(),
            }
            for name, data in sorted(archivos.items())
        ],
    }
    suffix = "-alumnos" if options.alumnos else ""
    destination = BASE / "dist" / ("plantilla-pp2-" + commit[:8] + suffix + ".zip")
    destination.parent.mkdir(exist_ok=True)
    with zipfile.ZipFile(destination, "x", zipfile.ZIP_DEFLATED) as out:
        for name, data in sorted(archivos.items()):
            out.writestr("plantilla-pp2/" + name, data)
        out.writestr(
            "plantilla-pp2/ENTREGA_COMPLETA.json",
            json.dumps(manifest, ensure_ascii=False, indent=2),
        )
    print(destination)
    print("SHA-256:", hashlib.sha256(destination.read_bytes()).hexdigest())


if __name__ == "__main__":
    main()
