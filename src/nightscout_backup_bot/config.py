"""Configuration module for NightScout Backup Bot using Pydantic Settings."""

from enum import Enum
from typing import ClassVar

from dotenv_vault import load_dotenv  # type: ignore[import-untyped]
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Load environment variables from .env file or .env.vault (if DOTENV_KEY is set)
_ = load_dotenv()


class CompressionMethod(str, Enum):
    """Supported compression methods for backup files."""

    GZIP = "gzip"
    BROTLI = "brotli"


class Settings(BaseSettings):
    """Application settings loaded from environment variables and .env file."""

    model_config: ClassVar[SettingsConfigDict] = SettingsConfigDict(
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
    compression_method: CompressionMethod = Field(
        CompressionMethod.GZIP, description="Compression method: 'gzip' (default) or 'brotli'"
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

    # PM2 Config
    app_env: str = Field("development", description="Application environment: 'development' or 'production'")

    # Dexcom/NightScout PM2 Config (via SSH)
    nightscout_pm2_app_name: str = Field("dexcom", description="PM2 app name for the NightScout site")
    nightscout_pm2_ssh_user: str | None = Field(None, description="SSH user for NightScout server")
    nightscout_pm2_ssh_host: str | None = Field(None, description="SSH host for NightScout server")
    nightscout_pm2_ssh_key_path: str | None = Field(None, description="Path to SSH key for NightScout server")
    nightscout_pm2_cmd: str = Field("npx pm2", description="PM2 command/path on NightScout server")

    # Bot PM2 Config
    bot_pm2_app_name: str = Field("nightscout-backup-bot-dev", description="PM2 app name for the bot itself")
    bot_pm2_mode: str = Field("local", description="Execution mode for bot PM2 commands: 'local' or 'ssh'")
    bot_pm2_ssh_user: str | None = Field(None, description="SSH user for bot's production server")
    bot_pm2_ssh_host: str | None = Field(None, description="SSH host for bot's production server")
    bot_pm2_ssh_key_path: str | None = Field(None, description="Path to SSH key for bot's production server")
    bot_pm2_cmd: str = Field("npx pm2", description="PM2 command/path for the bot")

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
        from urllib.parse import quote

        # URL-encode username and password to handle special characters
        encoded_username = quote(self.mongo_username, safe="")
        encoded_password = quote(self.mongo_password, safe="")

        return f"mongodb+srv://{encoded_username}:{encoded_password}@{self.mongo_host}/?retryWrites=true&w=majority"

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
        # Pydantic Settings loads values from environment variables automatically
        # Using model_validate to avoid type checker errors about missing arguments
        _settings = Settings.model_validate({})  # type: ignore[call-overload]
    return _settings


# Module-level settings instance for direct access and IDE autocomplete
settings: Settings = get_settings()
