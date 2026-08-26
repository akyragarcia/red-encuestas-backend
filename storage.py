"""
Guardado de archivos (audio de encuestas, fotos de asistencia).

TODO: esto guarda en disco local del servidor. Cuando conecten un bucket tipo S3,
solo hay que cambiar las dos funciones de este archivo (guardar_archivo / ruta_publica) --
el resto del backend no necesita tocarse, porque siempre le habla a este módulo.
"""

import os
import uuid
from app.config import settings


def guardar_archivo(contenido: bytes, subcarpeta: str, extension: str) -> str:
    carpeta = os.path.join(settings.storage_dir, subcarpeta)
    os.makedirs(carpeta, exist_ok=True)
    nombre = f"{uuid.uuid4().hex}.{extension}"
    ruta_completa = os.path.join(carpeta, nombre)
    with open(ruta_completa, "wb") as f:
        f.write(contenido)
    return os.path.join(subcarpeta, nombre)  # ruta relativa, se guarda así en la base de datos


def ruta_absoluta(ruta_relativa: str) -> str:
    return os.path.join(settings.storage_dir, ruta_relativa)
