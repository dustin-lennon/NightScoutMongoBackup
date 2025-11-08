"""Configuration module for NightScout Backup Bot using Pydantic Settings."""

from typing import Any, Literal

from dotenv_vault import load_dotenv  # type: ignore[import-untyped]
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Load environment variables from .env file or .env.vault (if DOTENV_KEY is set)
load_dotenv()


class Settings(BaseSettings):
    """Application settings loaded from environment variables and .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Discord Configuration
    discord_token: str = Field(..., description="Discord bot token")
    discord_client_id: str = Field(..., description="Discord application client ID")
    discord_public_key: str | None = Field(None, description="Discord public key for interactions")
    backup_channel_id: str = Field(..., description="Channel ID where backup threads are created")

    # Optional Discord Configuration
    bot_report_channel_id: str | None = Field(None, description="Channel ID for bot status reports")
    bot_owner_ids: str = Field("", description="Comma-separated Discord user IDs of bot owners")

    # MongoDB Atlas Configuration
    mongo_host: str = Field(..., description="MongoDB Atlas cluster hostname")
    mongo_username: str = Field(..., description="MongoDB username")
    mongo_password: str = Field(..., description="MongoDB password")
    mongo_db: str = Field(..., description="MongoDB database name")
    mongo_api_key: str | None = Field(None, description="MongoDB Atlas API key")
    mongo_db_max_size: int | None = Field(None, description="Maximum size of the MongoDB database in MB")

    # AWS S3 Configuration
    aws_access_key_id: str = Field(..., description="AWS access key ID")
    aws_secret_access_key: str = Field(..., description="AWS secret access key")
    aws_region: str = Field("us-east-1", description="AWS region")
    s3_backup_bucket: str = Field(..., description="S3 bucket name for backups")

    # Backup Configuration
    enable_nightly_backup: bool = Field(True, description="Enable/disable scheduled nightly backups")
    backup_hour: int = Field(2, ge=0, le=23, description="Hour for nightly backup (24-hour format)")
    backup_minute: int = Field(0, ge=0, le=59, description="Minute for nightly backup")
    compression_method: Literal["gzip", "brotli"] = Field(
        "gzip", description="Compression method: 'gzip' (default) or 'brotli'"
    )

    # Monitoring (Optional)
    sentry_dsn: str | None = Field(None, description="Sentry DSN for error tracking")
    sentry_auth_token: str | None = Field(None, description="Sentry auth token")
    node_env: str = Field("development", description="Environment: development or production")

    # Testing Servers
    test_guilds: str | None = Field(None, description="Comma-separated guild IDs for testing")

    # Linode Server SSH Configuration
    linode_ssh_host: str | None = Field(None, description="Linode server IP address for remote PM2 commands")
    linode_ssh_user: str = Field("root", description="SSH username for Linode server")
    linode_ssh_key_path: str | None = Field(None, description="Path to SSH private key (defaults to ~/.ssh/id_rsa)")
    pm2_dexcom_app_name: str = Field("Dexcom", description="PM2 application name to manage")

    @field_validator("bot_owner_ids", mode="before")
    @classmethod
    def parse_owner_ids(cls, v: str) -> str:
        """Validate and clean bot owner IDs."""
        if not v:
            return ""
        # Remove whitespace and validate format
        return ",".join(id.strip() for id in v.split(",") if id.strip())

    @property
    def test_guild_ids(self) -> list[int] | None:
        """Get list of test guild IDs as integers."""
        if not self.test_guilds:
            return None
        try:
            return [int(id.strip()) for id in self.test_guilds.split(",") if id.strip()]
        except ValueError:
            return None

    @property
    def mongo_connection_string(self) -> str:
        """Generate MongoDB connection string with URL-encoded credentials.

        Format matches MongoDB Atlas connection string:
        mongodb+srv://username:password@host/?retryWrites=true&w=majority

        The database is specified separately when accessing client[database_name].
        """
        from urllib.parse import quote_plus

        # URL-encode username and password to handle special characters
        encoded_username = quote_plus(self.mongo_username)
        encoded_password = quote_plus(self.mongo_password)

        return f"mongodb+srv://{encoded_username}:{encoded_password}" f"@{self.mongo_host}/?retryWrites=true&w=majority"

    @property
    def owner_id_list(self) -> list[str]:
        """Get list of bot owner IDs."""
        if not self.bot_owner_ids:
            return []
        return [id.strip() for id in self.bot_owner_ids.split(",") if id.strip()]

    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.node_env.lower() == "production"


# Global settings instance - only initialize when actually used
_settings: Settings | None = None


def get_settings() -> Settings:
    """Get or create settings instance (lazy loading)."""
    global _settings
    if _settings is None:
        _settings = Settings()  # type: ignore[call-arg]
    return _settings


# For backwards compatibility, create a property-like accessor
class _SettingsProxy:
    def __getattr__(self, name: str) -> Any:
        return getattr(get_settings(), name)


settings = _SettingsProxy()
