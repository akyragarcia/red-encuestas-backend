from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class LoginRequest(BaseModel):
    codigo: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    rol: str
    nombre: str


class VisitaEntrada(BaseModel):
    id: str  # id generado en la tablet
    brigadista_id: int
    lat: Optional[float] = None
    lng: Optional[float] = None
    gps_precision: Optional[float] = None
    gps_es_simulado: bool = False
    fecha_inicio: datetime
    fecha_fin: Optional[datetime] = None
    resultado: Optional[str] = None
    subrazon: Optional[str] = None
    respuestas: dict = {}
    ultima_pregunta_id: Optional[str] = None
    audio_duracion_seg: Optional[int] = None


class TurnoBrigadistaEntrada(BaseModel):
    id: int
    nombre: str


class TurnoCrearEntrada(BaseModel):
    id: str  # id generado en la tablet del coordinador
    coordinador_id: int
    brigada_nombre: str
    hora_inicio: datetime
    brigadistas: list[TurnoBrigadistaEntrada]


class TurnoLlegadaEntrada(BaseModel):
    brigadista_id: int
    a_tiempo: bool
    motivo_tarde: Optional[str] = None


class TurnoCerrarEntrada(BaseModel):
    hora_cierre: datetime
