import json
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from sqlmodel import Session, select
from app.database import get_session
from app.deps import usuario_actual, requiere_rol
from app.models import Usuario, TurnoAsistencia
from app.schemas import TurnoCrearEntrada, TurnoLlegadaEntrada, TurnoCerrarEntrada
from app.storage import guardar_archivo

router = APIRouter(prefix="/turnos", tags=["turnos"])


@router.post("", status_code=status.HTTP_201_CREATED)
def crear_turno(
    datos: str = Form(...),
    foto_inicio: UploadFile | None = File(default=None),
    usuario: Usuario = Depends(requiere_rol("coordinador", "admin")),
    session: Session = Depends(get_session),
):
    entrada = TurnoCrearEntrada(**json.loads(datos))
    if usuario.rol == "coordinador" and usuario.id != entrada.coordinador_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "No puedes crear turnos de otro coordinador")

    ya_existe = session.get(TurnoAsistencia, entrada.id)
    if ya_existe:
        return {"ok": True, "detalle": "Ya estaba sincronizado"}

    foto_path = None
    if foto_inicio is not None:
        foto_path = guardar_archivo(foto_inicio.file.read(), "fotos", "jpg")

    turno = TurnoAsistencia(
        id=entrada.id,
        coordinador_id=entrada.coordinador_id,
        brigada_nombre=entrada.brigada_nombre,
        fecha=entrada.hora_inicio.strftime("%Y-%m-%d"),
        hora_inicio=entrada.hora_inicio,
        foto_inicio_path=foto_path,
        brigadistas=[
            {"id": b.id, "nombre": b.nombre, "estado": "pendiente", "hora_llegada": None, "foto_tarde_path": None, "motivo_tarde": None}
            for b in entrada.brigadistas
        ],
    )
    session.add(turno)
    session.commit()
    return {"ok": True}


@router.patch("/{turno_id}/llegada")
def marcar_llegada(
    turno_id: str,
    datos: str = Form(...),
    foto_tarde: UploadFile | None = File(default=None),
    usuario: Usuario = Depends(requiere_rol("coordinador", "admin")),
    session: Session = Depends(get_session),
):
    entrada = TurnoLlegadaEntrada(**json.loads(datos))
    turno = session.get(TurnoAsistencia, turno_id)
    if not turno:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Turno no encontrado")
    if usuario.rol == "coordinador" and usuario.id != turno.coordinador_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "No es tu turno")

    foto_path = None
    if foto_tarde is not None:
        foto_path = guardar_archivo(foto_tarde.file.read(), "fotos", "jpg")

    brigadistas = list(turno.brigadistas)
    for b in brigadistas:
        if b["id"] == entrada.brigadista_id:
            b["estado"] = "a_tiempo" if entrada.a_tiempo else "tarde"
            b["hora_llegada"] = datetime.utcnow().isoformat()
            if not entrada.a_tiempo:
                b["foto_tarde_path"] = foto_path
                b["motivo_tarde"] = entrada.motivo_tarde
    turno.brigadistas = brigadistas
    session.add(turno)
    session.commit()
    return {"ok": True}


@router.patch("/{turno_id}/cerrar")
def cerrar_turno(
    turno_id: str,
    datos: str = Form(...),
    foto_cierre: UploadFile | None = File(default=None),
    usuario: Usuario = Depends(requiere_rol("coordinador", "admin")),
    session: Session = Depends(get_session),
):
    entrada = TurnoCerrarEntrada(**json.loads(datos))
    turno = session.get(TurnoAsistencia, turno_id)
    if not turno:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Turno no encontrado")
    if usuario.rol == "coordinador" and usuario.id != turno.coordinador_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "No es tu turno")

    if foto_cierre is not None:
        turno.foto_cierre_path = guardar_archivo(foto_cierre.file.read(), "fotos", "jpg")
    turno.hora_cierre = entrada.hora_cierre
    session.add(turno)
    session.commit()
    return {"ok": True}


@router.get("")
def listar_turnos(
    fecha: str | None = None,
    usuario: Usuario = Depends(usuario_actual),
    session: Session = Depends(get_session),
):
    query = select(TurnoAsistencia)
    if usuario.rol == "coordinador":
        query = query.where(TurnoAsistencia.coordinador_id == usuario.id)
    elif usuario.rol == "supervisor":
        coordinadores = session.exec(select(Usuario.id).where(Usuario.supervisor_id == usuario.id)).all()
        query = query.where(TurnoAsistencia.coordinador_id.in_(coordinadores)) if coordinadores else query.where(False)
    elif usuario.rol == "brigadista":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "No tienes acceso a esto")
    # admin: ve todo

    if fecha:
        query = query.where(TurnoAsistencia.fecha == fecha)
    return session.exec(query.order_by(TurnoAsistencia.hora_inicio.desc())).all()
