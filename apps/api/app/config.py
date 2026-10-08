"""Applikationskonfiguration. Secrets leveres via miljø/.env — aldrig Git."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    environment: str = "local"
    database_url: str = "sqlite:///./.local.db"

    # CORS begrænses til godkendte origins (Technical Master §12).
    cors_origins: str = "http://localhost:3000"

    # Supabase Auth: JWT valideres server-side (Technical Master §13).
    supabase_jwt_secret: str = ""

    # Storage-adapter (Technical Master §7): local til udvikling/test,
    # supabase (private buckets) i staging/production.
    storage_backend: str = "local"
    storage_local_root: str = "./.storage"
    supabase_url: str = ""
    supabase_service_role_key: str = ""
    supabase_storage_bucket: str = "documents"

    # AI-provider (Technical Master §10): "openai_compat" eller "anthropic".
    ai_provider: str = "openai_compat"
    ai_provider_base_url: str = ""
    ai_provider_api_key: str = ""
    ai_model_id: str = ""
    # Model til relevanstrinnet (ja/nej pr. dokument). Tom = standard: med
    # anthropic en billig model, ellers AI_MODEL_ID. Den dyre model bruges så
    # kun på dokumenter, der faktisk er relevante.
    ai_relevance_model_id: str = ""

    max_upload_bytes: int = 20_000_000
    fetch_timeout_seconds: float = 20.0
    fetch_max_bytes: int = 5_000_000
    # Artikler pr. RSS-kilde pr. kørsel — holder én kørsel afgrænset, så den
    # kan nå at blive færdig på free tier.
    rss_max_items: int = 10
    # Ældre dokumenter, der genlæses med leverandørprompten pr. kørsel
    # (pipeline/backfill.py). Afgrænser tid og AI-forbrug pr. kørsel.
    reread_per_run: int = 25

    # Delt hemmelighed, som den planlagte udløser (GitHub Actions) sender i
    # X-Worker-Token for at starte en kørsel. Tom = kun Admin-login kan.
    worker_trigger_token: str = ""

    # Fuldt automatisk publicering: AI godkender sine egne claims og
    # publicerer case og signal uden menneskelig kontrol. Alt markeres som
    # AI-publiceret. False = human-in-the-loop som i masterfilerne.
    auto_publish: bool = False

    # Offentlig URL på API-hosten (Render sætter RENDER_EXTERNAL_URL selv).
    # Under en kørsel pinger API'et sig selv her, så free tier ikke lægger
    # instansen i dvale midt i arbejdet.
    render_external_url: str = ""

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def auth_dev_bypass(self) -> bool:
        """Kun lokal udvikling uden konfigureret auth: alle kald som Admin.

        Aldrig aktiv uden for environment=local. Staging/production sætter
        environment til staging/production, hvilket slår bypasset fra.
        """
        return self.environment == "local" and not self.supabase_jwt_secret


@lru_cache
def get_settings() -> Settings:
    return Settings()
