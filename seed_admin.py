"""
Crea el primer usuario Administrador UIE, necesario porque crear usuarios normalmente
requiere ya ser administrador. Correr UNA VEZ después de levantar la base de datos:

    python seed_admin.py
"""

from sqlmodel import Session, select
from app.database import engine, crear_tablas
from app.models import Usuario
from app.security import hashear_password

crear_tablas()

with Session(engine) as session:
    existente = session.exec(select(Usuario).where(Usuario.codigo == "admin")).first()
    if existente:
        print("Ya existe un usuario con código 'admin'. No se creó nada nuevo.")
    else:
        admin = Usuario(
            nombre="Administrador UIE",
            codigo="admin",
            password_hash=hashear_password("cambia-esta-clave"),
            rol="admin",
        )
        session.add(admin)
        session.commit()
        print("Usuario admin creado. Código: admin — Contraseña: cambia-esta-clave")
        print("Cámbiala en cuanto entres, esto es solo para arrancar.")
