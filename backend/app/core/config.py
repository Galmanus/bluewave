import logging
import sys

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Environment
    ENV: str = "development"
    LOG_LEVEL: str = "INFO"

    # Database
    DATABASE_URL: str = ""
    DATABASE_URL_SYNC: str = ""
    DB_POOL_SIZE: int = 20
    DB_MAX_OVERFLOW: int = 10

    # JWT
    JWT_SECRET: str = ""
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # CORS
    CORS_ORIGINS: str = ""

    # AI
    ANTHROPIC_API_KEY: str = ""
    AI_MODEL: str = "claude-sonnet-4-20250514"

    # LangSmith (optional — observability for AI calls)
    LANGSMITH_API_KEY: str = ""
    LANGSMITH_PROJECT: str = "bluewave"
    LANGSMITH_TRACING_ENABLED: bool = True

    # Email (Resend — optional)
    RESEND_API_KEY: str = ""
    EMAIL_FROM: str = "noreply@bluewave.app"
    APP_URL: str = "http://localhost:5174"

    # X/Twitter API (optional — for trend intelligence and social publishing)
    X_BEARER_TOKEN: str = ""
    TWITTER_API_KEY: str = ""
    TWITTER_API_SECRET: str = ""
    TWITTER_ACCESS_TOKEN: str = ""
    TWITTER_ACCESS_SECRET: str = ""

    # LinkedIn API (optional — for social publishing)
    LINKEDIN_CLIENT_ID: str = ""
    LINKEDIN_CLIENT_SECRET: str = ""

    # S3/CDN storage (optional — default is local filesystem)
    S3_ENDPOINT_URL: str = ""
    S3_ACCESS_KEY_ID: str = ""
    S3_SECRET_ACCESS_KEY: str = ""
    S3_BUCKET: str = "bluewave-assets"
    S3_REGION: str = "us-east-1"
    S3_PUBLIC_URL: str = ""
    STORAGE_BACKEND: str = "local"

    # Rate limits (AI actions per month, 0 = unlimited)
    FREE_TIER_AI_LIMIT: int = 50
    PRO_TIER_AI_LIMIT: int = 0  # unlimited

    # Sentry (optional)
    SENTRY_DSN: str = ""

    # Redis (optional)
    REDIS_URL: str = "redis://redis:6379/0"

    # Stripe (international payments)
    STRIPE_SECRET_KEY: str = ""
    STRIPE_PUBLISHABLE_KEY: str = ""
    STRIPE_WEBHOOK_SECRET: str = ""
    STRIPE_PRICE_IDS: str = ""  # JSON: {"pro":"price_xxx","business":"price_yyy"}

    # Mercado Pago (Brazilian payments — Pix, cartão, boleto)
    MERCADOPAGO_ACCESS_TOKEN: str = ""
    MERCADOPAGO_PUBLIC_KEY: str = ""
    MERCADOPAGO_WEBHOOK_SECRET: str = ""

    class Config:
        env_file = ".env"

    @property
    def cors_origins(self) -> list[str]:
        if self.CORS_ORIGINS:
            return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]
        if self.ENV == "development":
            return ["http://localhost:5173", "http://localhost:5174"]
        return []

    def validate_production_settings(self) -> None:
        """Validate critical settings for production. Call at startup."""
        logger = logging.getLogger("bluewave.config")

        if self.ENV != "production":
            return

        errors: list[str] = []

        # JWT_SECRET must be strong in production
        if not self.JWT_SECRET:
            errors.append("JWT_SECRET is required")
        elif len(self.JWT_SECRET) < 32:
            errors.append("JWT_SECRET must be at least 32 characters")
        elif any(w in self.JWT_SECRET.lower() for w in ("change-me", "secret", "changeme")):
            errors.append("JWT_SECRET contains insecure default value")

        # DATABASE_URL must be set
        if not self.DATABASE_URL:
            errors.append("DATABASE_URL is required")

        # CORS must be configured
        if not self.CORS_ORIGINS:
            errors.append("CORS_ORIGINS must be set in production")

        if errors:
            for e in errors:
                logger.critical("Configuration error: %s", e)
            sys.exit(1)


settings = Settings()
