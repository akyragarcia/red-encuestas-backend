from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.database import crear_tablas
from app.routers import auth_router, visitas_router, turnos_router, usuarios_router

app = FastAPI(title="RED Encuestas — API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_lista,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup():
    crear_tablas()


@app.get("/")
def salud():
    return {"ok": True, "servicio": "RED Encuestas API"}


app.include_router(auth_router.router)
app.include_router(visitas_router.router)
app.include_router(turnos_router.router)
app.include_router(usuarios_router.router)
