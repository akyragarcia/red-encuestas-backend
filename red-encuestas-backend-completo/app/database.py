from sqlmodel import SQLModel, Session, create_engine
from app.config import settings


def _url_para_sqlalchemy(url: str) -> str:
    """
    Railway (y la mayoría de proveedores) dan la URL como "postgresql://...".
    Usamos el driver psycopg v3 (más compatible con versiones nuevas de Python
    sin necesitar compilar nada), así que la ajustamos a "postgresql+psycopg://".
    Si es SQLite (usado solo en pruebas locales), se deja igual.
    """
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+psycopg://", 1)
    return url


engine = create_engine(_url_para_sqlalchemy(settings.database_url), echo=False)


def crear_tablas():
    SQLModel.metadata.create_all(engine)


def get_session():
    with Session(engine) as session:
        yield session
