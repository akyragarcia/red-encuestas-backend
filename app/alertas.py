"""
Reglas anti-simulación acordadas:
- Duración mínima: <2min alerta, <45s alta prioridad (ajustable cuando se defina el cuestionario final)
- Geocerca por sección: ~150-200m, >1km = alta prioridad
- Hueco de inactividad: 45-60min entre encuestas del mismo brigadista (excepto horario de comida)
- Mock location: si el dispositivo reporta que el GPS viene de una app de ubicación falsa

NOTA sobre geocerca: todavía no existe la integración con el mapa de secciones (eso vive en el
proyecto de QGIS/disponibilidad territorial, aparte). Mientras tanto, la geocerca solo se checa
si el usuario tiene una zona de referencia asignada manualmente (Usuario.zona_lat/zona_lng);
si no la tiene, esta regla simplemente no se evalúa (no genera falsos positivos).
"""

import math
from datetime import datetime, time
from app.config import settings
from app.models import Usuario, Visita

HORA_COMIDA_INICIO = time(14, 0)
HORA_COMIDA_FIN = time(15, 0)


def distancia_metros(lat1, lng1, lat2, lng2) -> float:
    """Distancia aproximada entre dos puntos GPS (fórmula haversine)."""
    R = 6371000
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lng2 - lng1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


def _sin_zona_horaria(dt):
    """Quita la información de zona horaria si la trae, para poder comparar fechas
    sin importar si vienen de la base de datos (naive) o recién parseadas del JSON (aware)."""
    return dt.replace(tzinfo=None) if dt.tzinfo is not None else dt


def calcular_alertas(visita: Visita, brigadista: Usuario, visita_anterior: Visita | None) -> tuple[list[str], str | None]:
    alertas: list[str] = []
    prioridad_max = None

    def marcar(codigo: str, prioridad: str):
        nonlocal prioridad_max
        alertas.append(codigo)
        if prioridad == "alta":
            prioridad_max = "alta"
        elif prioridad == "media" and prioridad_max != "alta":
            prioridad_max = "media"

    # --- Duración mínima (solo aplica a encuestas completas) ---
    if visita.resultado == "completa" and visita.fecha_fin:
        duracion_seg = (_sin_zona_horaria(visita.fecha_fin) - _sin_zona_horaria(visita.fecha_inicio)).total_seconds()
        if duracion_seg < settings.duracion_minima_alta_prioridad_seg:
            marcar("duracion_corta", "alta")
        elif duracion_seg < settings.duracion_minima_alerta_seg:
            marcar("duracion_corta", "media")

    # --- Geocerca (solo si el brigadista tiene zona de referencia asignada) ---
    if visita.lat and visita.lng and getattr(brigadista, "zona_lat", None) and getattr(brigadista, "zona_lng", None):
        d = distancia_metros(visita.lat, visita.lng, brigadista.zona_lat, brigadista.zona_lng)
        if d > settings.geocerca_radio_alta_prioridad_m:
            marcar("fuera_zona", "alta")
        elif d > settings.geocerca_radio_m:
            marcar("fuera_zona", "media")

    # --- Hueco de inactividad respecto a la visita anterior del mismo brigadista ---
    if visita_anterior and visita_anterior.fecha_fin:
        inicio_actual = _sin_zona_horaria(visita.fecha_inicio)
        fin_anterior = _sin_zona_horaria(visita_anterior.fecha_fin)
        gap_min = (inicio_actual - fin_anterior).total_seconds() / 60
        if gap_min > settings.hueco_inactividad_min:
            hora_gap_inicio = fin_anterior.time()
            en_horario_comida = HORA_COMIDA_INICIO <= hora_gap_inicio <= HORA_COMIDA_FIN
            if not en_horario_comida:
                marcar("hueco_inactividad", "media")

    # --- Ubicación falsa (mock location), reportada por el dispositivo ---
    if visita.gps_es_simulado:
        marcar("mock_location", "alta")

    return alertas, prioridad_max
