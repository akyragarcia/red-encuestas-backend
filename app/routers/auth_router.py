from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select
from app.database import get_session
from app.models import Usuario
from app.security import verificar_password, crear_token
from app.schemas import LoginRequest, TokenResponse

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
def login(datos: LoginRequest, session: Session = Depends(get_session)):
    usuario = session.exec(select(Usuario).where(Usuario.codigo == datos.codigo)).first()
    if not usuario or not usuario.activo or not verificar_password(datos.password, usuario.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Código o contraseña incorrectos")
    token = crear_token(usuario.id, usuario.rol)
    return TokenResponse(access_token=token, rol=usuario.rol, nombre=usuario.nombre, brigada_nombre=usuario.brigada_nombre)
