import json
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from fastapi.responses import FileResponse
from sqlmodel import Session, select
from sqlalchemy import text
from app.database import get_session
from app.deps import usuario_actual, requiere_rol
from app.models import Usuario, Visita
from app.schemas import VisitaEntrada
from app.storage import guardar_archivo, ruta_absoluta
from app.alertas import calcular_alertas

router = APIRouter(prefix="/visitas", tags=["visitas"])


def _calcular_seccion(session: Session, lat: float | None, lng: float | None) -> int | None:
    """Busca en qué sección electoral cae este punto, usando la tabla `seccion`
    (importada una vez desde el shapefile con importar_secciones.py). Si esa tabla
    todavía no existe o no hay coordenadas, regresa None sin tronar -- el resto del
    sistema sigue funcionando igual, solo sin ese dato."""
    if lat is None or lng is None:
        return None
    try:
        fila = session.exec(
            text("SELECT seccion FROM seccion WHERE ST_Contains(geom, ST_SetSRID(ST_MakePoint(:lng, :lat), 4326)) LIMIT 1"),
            params={"lng": lng, "lat": lat},
        ).first()
        return fila[0] if fila else None
    except Exception:
        return None


def _brigadistas_bajo_supervisor(session: Session, supervisor_id: int) -> list[int]:
    coordinadores = session.exec(select(Usuario.id).where(Usuario.supervisor_id == supervisor_id)).all()
    if not coordinadores:
        return []
    brigadistas = session.exec(select(Usuario.id).where(Usuario.coordinador_id.in_(coordinadores))).all()
    return list(brigadistas)


@router.post("", status_code=status.HTTP_201_CREATED)
def recibir_visita(
    datos: str = Form(...),  # JSON serializado (VisitaEntrada) -- multipart no manda JSON directo
    audio: UploadFile | None = File(default=None),
    usuario: Usuario = Depends(usuario_actual),
    session: Session = Depends(get_session),
):
    entrada = VisitaEntrada(**json.loads(datos))

    if usuario.rol not in ("brigadista", "admin"):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Solo un brigadista puede subir encuestas")
    if usuario.rol == "brigadista" and usuario.id != entrada.brigadista_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "No puedes subir encuestas de otro brigadista")

    ya_existe = session.get(Visita, entrada.id)
    if ya_existe:
        return {"ok": True, "detalle": "Ya estaba sincronizada"}  # idempotente: reintentos de sync no duplican

    audio_path = None
    if audio is not None:
        contenido = audio.file.read()
        audio_path = guardar_archivo(contenido, "audio", "webm")

    visita = Visita(
        id=entrada.id,
        brigadista_id=entrada.brigadista_id,
        lat=entrada.lat,
        lng=entrada.lng,
        gps_precision=entrada.gps_precision,
        gps_es_simulado=entrada.gps_es_simulado,
        fecha_inicio=entrada.fecha_inicio,
        fecha_fin=entrada.fecha_fin,
        fecha=entrada.fecha_inicio.strftime("%Y-%m-%d"),
        resultado=entrada.resultado,
        subrazon=entrada.subrazon,
        respuestas=entrada.respuestas,
        ultima_pregunta_id=entrada.ultima_pregunta_id,
        audio_path=audio_path,
        audio_duracion_seg=entrada.audio_duracion_seg,
        seccion=_calcular_seccion(session, entrada.lat, entrada.lng),
    )

    visita_anterior = session.exec(
        select(Visita)
        .where(Visita.brigadista_id == entrada.brigadista_id, Visita.fecha_inicio < entrada.fecha_inicio)
        .order_by(Visita.fecha_inicio.desc())
    ).first()

    alertas, prioridad = calcular_alertas(visita, usuario, visita_anterior)
    visita.alertas = alertas
    visita.prioridad_alerta = prioridad

    session.add(visita)
    session.commit()
    return {"ok": True, "alertas": alertas, "prioridad_alerta": prioridad}


@router.get("")
def listar_visitas(
    fecha: str | None = None,
    solo_alertas: bool = False,
    usuario: Usuario = Depends(usuario_actual),
    session: Session = Depends(get_session),
):
    query = select(Visita)

    if usuario.rol == "brigadista":
        query = query.where(Visita.brigadista_id == usuario.id)
    elif usuario.rol == "supervisor":
        ids = _brigadistas_bajo_supervisor(session, usuario.id)
        query = query.where(Visita.brigadista_id.in_(ids)) if ids else query.where(False)
    elif usuario.rol == "coordinador":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "El coordinador no tiene acceso a las encuestas")
    # admin: sin filtro, ve todo

    if fecha:
        query = query.where(Visita.fecha == fecha)
    if solo_alertas:
        query = query.where(Visita.prioridad_alerta.is_not(None))

    visitas = session.exec(query.order_by(Visita.fecha_inicio.desc())).all()

    # Se enriquece cada visita con el nombre del brigadista y de su brigada,
    # para que el panel de supervisor/administrador no tenga que adivinar quién es quién.
    resultado = []
    cache_brigadistas: dict[int, Usuario] = {}
    cache_coordinadores: dict[int, Usuario] = {}
    for v in visitas:
        brigadista = cache_brigadistas.setdefault(v.brigadista_id, session.get(Usuario, v.brigadista_id))
        brigada_nombre = None
        if brigadista and brigadista.coordinador_id:
            coordinador = cache_coordinadores.setdefault(brigadista.coordinador_id, session.get(Usuario, brigadista.coordinador_id))
            brigada_nombre = coordinador.brigada_nombre if coordinador else None
        duracion_seg = None
        if v.fecha_fin:
            duracion_seg = int((v.fecha_fin - v.fecha_inicio).total_seconds())
        resultado.append({
            "id": v.id,
            "brigadista_id": v.brigadista_id,
            "brigadista_nombre": brigadista.nombre if brigadista else "Desconocido",
            "brigada_nombre": brigada_nombre,
            "lat": v.lat,
            "lng": v.lng,
            "fecha_inicio": v.fecha_inicio,
            "fecha_fin": v.fecha_fin,
            "duracion_seg": duracion_seg,
            "resultado": v.resultado,
            "subrazon": v.subrazon,
            "respuestas": v.respuestas,
            "tiene_audio": v.audio_path is not None,
            "alertas": v.alertas,
            "prioridad_alerta": v.prioridad_alerta,
            "seccion": v.seccion,
        })
    return resultado


@router.get("/{visita_id}/audio")
def obtener_audio(
    visita_id: str,
    usuario: Usuario = Depends(requiere_rol("admin")),
    session: Session = Depends(get_session),
):
    visita = session.get(Visita, visita_id)
    if not visita or not visita.audio_path:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No hay audio para esta visita")
    return FileResponse(ruta_absoluta(visita.audio_path), media_type="audio/webm")
