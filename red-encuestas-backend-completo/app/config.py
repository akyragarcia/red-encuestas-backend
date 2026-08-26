from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql://red:cambia_esta_clave@localhost:5432/red_encuestas"
    jwt_secret: str = "cambia-esto"
    jwt_expira_horas: int = 12

    geocerca_radio_m: int = 200
    geocerca_radio_alta_prioridad_m: int = 1000

    duracion_minima_alerta_seg: int = 120
    duracion_minima_alta_prioridad_seg: int = 45

    hueco_inactividad_min: int = 45

    storage_dir: str = "./storage"
    cors_origins: str = "http://localhost:5173"

    class Config:
        env_file = ".env"

    @property
    def cors_origins_lista(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()
