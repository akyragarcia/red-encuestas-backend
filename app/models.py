from datetime import datetime
from typing import Optional
from sqlalchemy import Column, JSON
from sqlmodel import SQLModel, Field

# Roles válidos: "brigadista", "coordinador", "supervisor", "admin"


class Usuario(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    nombre: str
    codigo: str = Field(unique=True, index=True)  # código corto de acceso, más fácil que email en campo
    password_hash: str
    rol: str
    activo: bool = Field(default=True)

    # Jerarquía: un brigadista pertenece a un coordinador; un coordinador reporta a un supervisor.
    coordinador_id: Optional[int] = Field(default=None, foreign_key="usuario.id")
    supervisor_id: Optional[int] = Field(default=None, foreign_key="usuario.id")
    brigada_nombre: Optional[str] = None

    # Zona de referencia para la regla de geocerca (se asigna manualmente por ahora;
    # a futuro se conecta con el mapa de disponibilidad territorial por sección).
    zona_lat: Optional[float] = None
    zona_lng: Optional[float] = None

    creado_en: datetime = Field(default_factory=datetime.utcnow)


class Visita(SQLModel, table=True):
    # id como texto: se genera EN LA TABLET (uuid local) para que funcione sin depender
    # de que el servidor asigne un id -- así el offline-first no se rompe.
    id: str = Field(primary_key=True)
    brigadista_id: int = Field(foreign_key="usuario.id")

    lat: Optional[float] = None
    lng: Optional[float] = None
    gps_precision: Optional[float] = None
    gps_es_simulado: bool = Field(default=False)

    fecha_inicio: datetime
    fecha_fin: Optional[datetime] = None
    fecha: str  # YYYY-MM-DD, para agrupar y filtrar rápido

    resultado: Optional[str] = None  # completa | parcial | no_abrio | rechazo | no_valido
    subrazon: Optional[str] = None
    respuestas: dict = Field(default_factory=dict, sa_column=Column(JSON))
    ultima_pregunta_id: Optional[str] = None

    audio_path: Optional[str] = None
    audio_duracion_seg: Optional[int] = None

    # Lista de códigos de alerta disparados por las reglas anti-simulación, ej. ["duracion_corta", "fuera_zona"]
    alertas: list = Field(default_factory=list, sa_column=Column(JSON))
    prioridad_alerta: Optional[str] = None  # "alta" | "media" | None

    sincronizado_en: datetime = Field(default_factory=datetime.utcnow)


class TurnoAsistencia(SQLModel, table=True):
    id: str = Field(primary_key=True)
    coordinador_id: int = Field(foreign_key="usuario.id")
    brigada_nombre: str
    fecha: str  # YYYY-MM-DD

    hora_inicio: datetime
    foto_inicio_path: Optional[str] = None

    hora_cierre: Optional[datetime] = None
    foto_cierre_path: Optional[str] = None

    # Lista de { id, nombre, estado, hora_llegada, foto_tarde_path, motivo_tarde }
    brigadistas: list = Field(default_factory=list, sa_column=Column(JSON))

    sincronizado_en: datetime = Field(default_factory=datetime.utcnow)
