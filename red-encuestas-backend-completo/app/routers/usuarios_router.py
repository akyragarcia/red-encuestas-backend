from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlmodel import Session, select
from app.database import get_session
from app.deps import requiere_rol
from app.models import Usuario
from app.security import hashear_password

router = APIRouter(prefix="/usuarios", tags=["usuarios"])


class UsuarioCrear(BaseModel):
    nombre: str
    codigo: str
    password: str
    rol: str  # brigadista | coordinador | supervisor | admin
    coordinador_id: int | None = None
    supervisor_id: int | None = None
    brigada_nombre: str | None = None


@router.post("", status_code=status.HTTP_201_CREATED)
def crear_usuario(
    datos: UsuarioCrear,
    _admin: Usuario = Depends(requiere_rol("admin")),
    session: Session = Depends(get_session),
):
    if datos.rol not in ("brigadista", "coordinador", "supervisor", "admin"):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Rol inválido")
    existente = session.exec(select(Usuario).where(Usuario.codigo == datos.codigo)).first()
    if existente:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Ese código ya está en uso")

    usuario = Usuario(
        nombre=datos.nombre,
        codigo=datos.codigo,
        password_hash=hashear_password(datos.password),
        rol=datos.rol,
        coordinador_id=datos.coordinador_id,
        supervisor_id=datos.supervisor_id,
        brigada_nombre=datos.brigada_nombre,
    )
    session.add(usuario)
    session.commit()
    session.refresh(usuario)
    return {"id": usuario.id, "nombre": usuario.nombre, "rol": usuario.rol}


@router.get("")
def listar_usuarios(
    _admin: Usuario = Depends(requiere_rol("admin")),
    session: Session = Depends(get_session),
):
    usuarios = session.exec(select(Usuario)).all()
    return [
        {"id": u.id, "nombre": u.nombre, "codigo": u.codigo, "rol": u.rol, "activo": u.activo, "brigada_nombre": u.brigada_nombre}
        for u in usuarios
    ]


@router.patch("/{usuario_id}/desactivar")
def desactivar_usuario(
    usuario_id: int,
    _admin: Usuario = Depends(requiere_rol("admin")),
    session: Session = Depends(get_session),
):
    usuario = session.get(Usuario, usuario_id)
    if not usuario:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No existe")
    usuario.activo = False
    session.add(usuario)
    session.commit()
    return {"ok": True}
