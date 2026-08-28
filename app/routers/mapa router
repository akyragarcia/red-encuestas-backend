from fastapi import APIRouter, Depends, Query
from sqlmodel import Session
from sqlalchemy import text
from app.database import get_session
from app.deps import requiere_rol
from app.models import Usuario

router = APIRouter(prefix="/mapa", tags=["mapa"])


@router.get("/{pregunta_id}")
def mapa_por_pregunta(
    pregunta_id: str,
    municipio: int | None = Query(default=None),
    distrito_local: int | None = Query(default=None),
    usuario: Usuario = Depends(requiere_rol("admin", "supervisor")),
    session: Session = Depends(get_session),
):
    """
    Junta, para una pregunta del cuestionario:
      - Cada sección con su respuesta dominante y el conteo de cada opción (para
        pintar el mapa de fondo)
      - Cada encuesta individual con su punto exacto y su respuesta (para los pines)

    Todo filtrado a lo que el usuario puede ver (supervisor: solo sus brigadistas;
    admin: todo), igual que en /visitas.
    """
    filtros_seccion = []
    params: dict = {"pregunta_id": pregunta_id}
    if municipio is not None:
        filtros_seccion.append("municipio = :municipio")
        params["municipio"] = municipio
    if distrito_local is not None:
        filtros_seccion.append("distrito_local = :distrito_local")
        params["distrito_local"] = distrito_local
    where_seccion = ("WHERE " + " AND ".join(filtros_seccion)) if filtros_seccion else ""

    # Aislamiento por rol: igual criterio que en /visitas (ver visitas_router.py).
    filtro_usuario_sql = ""
    if usuario.rol == "supervisor":
        filtro_usuario_sql = """
            AND v.brigadista_id IN (
                SELECT u.id FROM usuario u
                WHERE u.coordinador_id IN (SELECT id FROM usuario WHERE supervisor_id = :supervisor_id)
            )
        """
        params["supervisor_id"] = usuario.id

    secciones_sql = f"""
        SELECT s.id, s.seccion, s.municipio, s.distrito_local, ST_AsGeoJSON(s.geom) AS geom_json
        FROM seccion s
        {where_seccion}
    """
    secciones = session.exec(text(secciones_sql), params=params).all()

    respuestas_sql = f"""
        SELECT v.seccion, v.respuestas::jsonb->>:pregunta_id AS respuesta, COUNT(*) AS n
        FROM visita v
        WHERE v.seccion IS NOT NULL AND v.respuestas::jsonb ? :pregunta_id {filtro_usuario_sql}
        GROUP BY v.seccion, respuesta
    """
    conteos = session.exec(text(respuestas_sql), params=params).all()

    por_seccion: dict[int, dict] = {}
    for seccion_num, respuesta, n in conteos:
        info = por_seccion.setdefault(seccion_num, {"conteos": {}, "total": 0})
        info["conteos"][respuesta] = n
        info["total"] += n

    secciones_resp = []
    for s in secciones:
        info = por_seccion.get(s.seccion, {"conteos": {}, "total": 0})
        dominante = max(info["conteos"], key=info["conteos"].get) if info["conteos"] else None
        secciones_resp.append({
            "seccion": s.seccion,
            "municipio": s.municipio,
            "distrito_local": s.distrito_local,
            "geometria": s.geom_json,  # GeoJSON en texto, listo para Leaflet
            "dominante": dominante,
            "total_encuestas": info["total"],
            "conteos": info["conteos"],
        })

    puntos_sql = f"""
        SELECT v.id, v.lat, v.lng, v.respuestas::jsonb->>:pregunta_id AS respuesta,
               v.fecha_inicio, u.nombre AS brigadista_nombre
        FROM visita v
        JOIN usuario u ON u.id = v.brigadista_id
        WHERE v.lat IS NOT NULL AND v.respuestas::jsonb ? :pregunta_id {filtro_usuario_sql}
    """
    puntos = session.exec(text(puntos_sql), params=params).all()
    puntos_resp = [
        {
            "id": p.id,
            "lat": p.lat,
            "lng": p.lng,
            "respuesta": p.respuesta,
            "hora": p.fecha_inicio,
            "brigadista_nombre": p.brigadista_nombre,
        }
        for p in puntos
    ]

    return {"secciones": secciones_resp, "puntos": puntos_resp}
