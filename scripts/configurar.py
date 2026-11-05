"""Genera configuración local sin sobrescribir archivos existentes."""

from pathlib import Path
import os
import secrets

root = Path(__file__).resolve().parent.parent
path = root / ".env"
if path.exists():
    print("Ya existe .env. Se conserva sin cambios.")
else:
    content = (root / ".env.example").read_text(encoding="utf-8")
    content = content.replace(
        "DJANGO_SECRET_KEY=\n", "DJANGO_SECRET_KEY=" + secrets.token_hex(32) + "\n"
    )
    content = content.replace(
        "POSTGRES_PASSWORD=\n", "POSTGRES_PASSWORD=" + secrets.token_hex(24) + "\n"
    )
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as stream:
        stream.write(content)
    print("Configuración creada. No compartas .env ni lo subas a Git.")
