from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select
from app.database import get_session
from app.deps import requiere_rol
from app.models import Usuario, TurnoAsistencia, Visita

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/resumen")
def resumen(
    usuario: Usuario = Depends(requiere_rol("supervisor", "admin")),
    session: Session = Depends(get_session),
):
    """
    Junta, por cada coordinador visible para quien pregunta, los números del día de hoy:
    asistencia de su brigada y avance de encuestas. Es lo que alimenta las tablas de
    supervisor y administrador -- ellos nunca calculan esto por su cuenta, solo lo piden aquí.
    """
    hoy = datetime.utcnow().strftime("%Y-%m-%d")

    if usuario.rol == "admin":
        coordinadores = session.exec(select(Usuario).where(Usuario.rol == "coordinador")).all()
    else:  # supervisor
        coordinadores = session.exec(select(Usuario).where(Usuario.rol == "coordinador", Usuario.supervisor_id == usuario.id)).all()

    filas = []
    for coord in coordinadores:
        brigadistas = session.exec(select(Usuario).where(Usuario.coordinador_id == coord.id, Usuario.rol == "brigadista")).all()
        brigadista_ids = [b.id for b in brigadistas]

        turno_hoy = session.exec(
            select(TurnoAsistencia).where(TurnoAsistencia.coordinador_id == coord.id, TurnoAsistencia.fecha == hoy)
        ).first()

        presentes_hoy = 0
        tardes_hoy = 0
        hora_inicio = None
        hora_cierre = None
        if turno_hoy:
            hora_inicio = turno_hoy.hora_inicio
            hora_cierre = turno_hoy.hora_cierre
            for b in turno_hoy.brigadistas:
                if b["estado"] in ("a_tiempo", "tarde"):
                    presentes_hoy += 1
                if b["estado"] == "tarde":
                    tardes_hoy += 1

        encuestas_hoy = []
        if brigadista_ids:
            encuestas_hoy = session.exec(
                select(Visita).where(Visita.brigadista_id.in_(brigadista_ids), Visita.fecha == hoy)
            ).all()
        completas = sum(1 for v in encuestas_hoy if v.resultado == "completa")
        parciales = sum(1 for v in encuestas_hoy if v.resultado == "parcial")

        filas.append({
            "coordinador_id": coord.id,
            "coordinador_nombre": coord.nombre,
            "brigada_nombre": coord.brigada_nombre,
            "total_brigadistas": len(brigadistas),
            "presentes_hoy": presentes_hoy,
            "tardes_hoy": tardes_hoy,
            "encuestas_completas_hoy": completas,
            "encuestas_parciales_hoy": parciales,
            "hora_inicio": hora_inicio,
            "hora_cierre": hora_cierre,
            "turno_id": turno_hoy.id if turno_hoy else None,
        })

    return filas


@router.get("/coordinador/{coordinador_id}")
def detalle_coordinador(
    coordinador_id: int,
    usuario: Usuario = Depends(requiere_rol("supervisor", "admin")),
    session: Session = Depends(get_session),
):
    """
    Detalle de una brigada específica: fotos de inicio/cierre del turno de hoy, y por
    cada brigadista, si ya mandó encuestas hoy (y cuántas) o sigue sin sincronizar.
    Se recalcula cada vez que se pide -- así, si sincronizan más tarde, la próxima
    vez que se consulte ya sale actualizado, sin que nadie tenga que avisar nada.
    """
    coord = session.get(Usuario, coordinador_id)
    if not coord or coord.rol != "coordinador":
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Coordinador no encontrado")
    if usuario.rol == "supervisor" and coord.supervisor_id != usuario.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Ese coordinador no es tuyo")

    hoy = datetime.utcnow().strftime("%Y-%m-%d")
    turno_hoy = session.exec(
        select(TurnoAsistencia).where(TurnoAsistencia.coordinador_id == coord.id, TurnoAsistencia.fecha == hoy)
    ).first()

    brigadistas = session.exec(select(Usuario).where(Usuario.coordinador_id == coord.id, Usuario.rol == "brigadista")).all()

    estado_asistencia_por_id = {}
    if turno_hoy:
        for b in turno_hoy.brigadistas:
            estado_asistencia_por_id[b["id"]] = {"estado": b["estado"], "hora_llegada": b["hora_llegada"]}

    filas_brigadistas = []
    for b in brigadistas:
        encuestas = session.exec(select(Visita).where(Visita.brigadista_id == b.id, Visita.fecha == hoy)).all()
        completas = sum(1 for v in encuestas if v.resultado == "completa")
        parciales = sum(1 for v in encuestas if v.resultado == "parcial")
        ultima = max((v.sincronizado_en for v in encuestas), default=None)
        asistencia = estado_asistencia_por_id.get(b.id)
        filas_brigadistas.append({
            "id": b.id,
            "nombre": b.nombre,
            "estado_asistencia": asistencia["estado"] if asistencia else "sin_registro",
            "hora_llegada": asistencia["hora_llegada"] if asistencia else None,
            "encuestas_total": len(encuestas),
            "encuestas_completas": completas,
            "encuestas_parciales": parciales,
            "sincronizado": len(encuestas) > 0,
            "ultima_sincronizacion": ultima,
        })

    return {
        "coordinador_id": coord.id,
        "coordinador_nombre": coord.nombre,
        "brigada_nombre": coord.brigada_nombre,
        "turno_id": turno_hoy.id if turno_hoy else None,
        "hora_inicio": turno_hoy.hora_inicio if turno_hoy else None,
        "hora_cierre": turno_hoy.hora_cierre if turno_hoy else None,
        "tiene_foto_inicio": bool(turno_hoy and turno_hoy.foto_inicio_path),
        "tiene_foto_cierre": bool(turno_hoy and turno_hoy.foto_cierre_path),
        "brigadistas": filas_brigadistas,
    }
