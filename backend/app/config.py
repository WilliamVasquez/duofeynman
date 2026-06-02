"""Configuración central de la app. Lee variables desde .env."""
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # DB
    DB_HOST: str = "localhost"
    DB_PORT: int = 3306
    DB_USER: str = "root"
    DB_PASSWORD: str = ""
    DB_NAME: str = "duofeynman"

    # Seguridad
    SECRET_KEY: str = "dev-only-change-me"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 10080
    ALGORITHM: str = "HS256"

    # LanguageTool
    LANGUAGETOOL_URL: str = "https://api.languagetool.org/v2"

    # Vosk STT (offline)
    VOSK_MODEL_PATH: str = "models/vosk-en-small"

    # Piper TTS (offline fallback) — binario standalone + modelo
    PIPER_BINARY_PATH: str = "piper/piper.exe"
    PIPER_MODEL_PATH: str = "models/piper/en_US-amy-medium.onnx"

    # Voz TTS por defecto (clave en VOICES_EDGE)
    DEFAULT_VOICE: str = "aria"

    # App
    APP_ENV: str = "development"
    CORS_ORIGINS: str = "http://localhost:5500,http://127.0.0.1:5500,http://localhost:8000"

    @property
    def database_url(self) -> str:
        return (
            f"mysql+pymysql://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}?charset=utf8mb4"
        )

    @property
    def cors_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    @property
    def is_production(self) -> bool:
        return self.APP_ENV.lower() in ("production", "prod")


# Valores de SECRET_KEY conocidos como inseguros. Si APP_ENV=production y la
# clave es alguna de éstas, abortamos el arranque para evitar exponer la app.
_INSECURE_SECRETS = {
    "dev-only-change-me",
    "cambiar_esto_por_una_clave_random_larga",
    "secret",
    "change-me",
    "",
}


def _validate_settings(s: "Settings") -> None:
    """Valida la config crítica al arranque. Falla rápido si algo es inseguro."""
    import sys

    if s.is_production:
        if s.SECRET_KEY in _INSECURE_SECRETS or len(s.SECRET_KEY) < 32:
            print(
                "\n⛔ ARRANQUE ABORTADO: SECRET_KEY es inseguro o muy corto.\n"
                "   Generá uno nuevo con:\n"
                '   python -c "import secrets; print(secrets.token_urlsafe(48))"\n'
                "   Y pegalo en .env como SECRET_KEY=...\n",
                file=sys.stderr,
            )
            sys.exit(1)
        if "*" in s.CORS_ORIGINS:
            print(
                "\n⛔ ARRANQUE ABORTADO: CORS_ORIGINS contiene '*' en producción.\n"
                "   Especificá los dominios exactos, ej:\n"
                "   CORS_ORIGINS=https://tu-dominio.com,https://www.tu-dominio.com\n",
                file=sys.stderr,
            )
            sys.exit(1)
        if not s.DB_PASSWORD or s.DB_PASSWORD in ("", "root", "password", "tu_password_mysql"):
            print(
                "\n⛔ ARRANQUE ABORTADO: DB_PASSWORD es inseguro o el default del template.\n",
                file=sys.stderr,
            )
            sys.exit(1)


@lru_cache
def get_settings() -> Settings:
    s = Settings()
    _validate_settings(s)
    return s


settings = get_settings()
