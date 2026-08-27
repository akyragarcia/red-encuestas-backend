from datetime import datetime
from fastapi import APIRouter, Depends
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
