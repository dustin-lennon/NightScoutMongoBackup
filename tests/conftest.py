"""Test configuration and fixtures."""

import os
import sys
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, Mock

import pytest
from dotenv import load_dotenv

# Load test environment variables BEFORE any application code imports
# This ensures tests never use production credentials
TEST_ENV_FILE = Path(__file__).parent.parent / ".env.test"
if TEST_ENV_FILE.exists():
    load_dotenv(TEST_ENV_FILE, override=True)
else:
    raise FileNotFoundError(
        f"Test environment file not found: {TEST_ENV_FILE}\n" "Tests require .env.test file with safe fake credentials."
    )

# Tell Pydantic to use .env.test instead of .env
# This environment variable is checked by pydantic-settings
os.environ["SETTINGS_ENV_FILE"] = str(TEST_ENV_FILE)

# Mock dotenv_vault module before any application code imports it
# This prevents it from loading production .env when config.py is imported
mock_dotenv_vault = Mock()
mock_dotenv_vault.load_dotenv = Mock(return_value=None)
sys.modules["dotenv_vault"] = mock_dotenv_vault

# Import Settings after loading test environment  # noqa: E402
import nightscout_backup_bot.config  # noqa: E402
from nightscout_backup_bot.config import Settings  # noqa: E402

# Create a test settings instance using environment variables from .env.test
_test_settings = Settings()  # type: ignore[call-arg]

# Monkey-patch get_settings to return our test settings
# This must happen BEFORE any test modules import application code
nightscout_backup_bot.config._settings = _test_settings  # type: ignore[assignment]
nightscout_backup_bot.config.get_settings = lambda: _test_settings


@pytest.fixture
def mock_settings() -> Settings:
    """Create mock settings for testing."""
    return Settings(  # type: ignore[call-arg]
        discord_token="test_token",
        discord_client_id="123456789",
        backup_channel_id="987654321",
        mongo_host="test.mongodb.net",
        mongo_username="testuser",
        mongo_password="testpass",
        mongo_db="testdb",
        aws_access_key_id="test_access_key",
        aws_secret_access_key="test_secret_key",
        s3_backup_bucket="test-bucket",
    )


# Global autouse fixture to prevent real MongoDB connections in ALL tests
@pytest.fixture(autouse=True, scope="function")
def mock_get_settings_globally(mock_settings: Settings, monkeypatch: pytest.MonkeyPatch) -> None:
    """
    Automatically patch get_settings() for ALL tests.

    This prevents any test from accidentally loading real production credentials
    and connecting to the production MongoDB database.
    """
    # Patch get_settings at the source - in the config module
    # This will affect all imports that use get_settings() or the settings proxy
    import nightscout_backup_bot.config

    monkeypatch.setattr(nightscout_backup_bot.config, "get_settings", lambda: mock_settings)
    # Also reset the global _settings to None to ensure get_settings is called
    monkeypatch.setattr(nightscout_backup_bot.config, "_settings", mock_settings)


@pytest.fixture
def temp_backup_dir(tmp_path: Path) -> Path:
    """Create temporary backup directory for tests."""
    backup_dir = tmp_path / "backups"
    backup_dir.mkdir(exist_ok=True)
    return backup_dir


@pytest.fixture
def mock_mongo_client() -> AsyncMock:
    """Create mock MongoDB client."""
    from unittest.mock import MagicMock

    client = AsyncMock()
    client.admin.command = AsyncMock(return_value={"ok": 1})
    # close() is synchronous in real Motor client
    client.close = MagicMock()
    return client


@pytest.fixture
def mock_mongo_database() -> AsyncMock:
    """Create mock MongoDB database."""
    db = AsyncMock()
    db.list_collection_names = AsyncMock(return_value=["entries", "treatments", "devicestatus"])
    return db


@pytest.fixture
def mock_s3_client() -> AsyncMock:
    """Create mock S3 client."""
    client = AsyncMock()
    client.upload_fileobj = AsyncMock()
    client.list_objects_v2 = AsyncMock(return_value={"Contents": []})
    client.delete_object = AsyncMock()
    return client


@pytest.fixture
def mock_discord_channel() -> MagicMock:
    """Create mock Discord text channel."""
    channel = MagicMock()
    channel.id = 987654321
    channel.name = "backup-channel"
    return channel


@pytest.fixture
def mock_discord_thread() -> MagicMock:
    """Create mock Discord thread."""
    thread = MagicMock()
    thread.id = 123456789
    thread.name = "Backup: 2025-11-07 12:00:00 UTC"
    thread.send = AsyncMock()
    return thread


@pytest.fixture
def mock_discord_interaction() -> MagicMock:
    """Create mock Discord interaction."""
    interaction = MagicMock()
    interaction.author.id = 111111111
    interaction.author.name = "TestUser"
    interaction.channel_id = 987654321
    interaction.response.send_message = AsyncMock()
    interaction.response.defer = AsyncMock()
    interaction.followup.send = AsyncMock()
    return interaction


@pytest.fixture
def sample_mongo_data() -> dict[str, Any]:
    """Create sample MongoDB export data."""
    return {
        "metadata": {
            "database": "testdb",
            "export_date": "2025-11-07T12:00:00",
            "collections_count": 3,
            "total_documents": 150,
        },
        "collections": {
            "entries": [{"_id": "1", "sgv": 120, "date": 1699363200000}] * 100,
            "treatments": [{"_id": "2", "insulin": 5.0, "date": 1699363200000}] * 30,
            "devicestatus": [{"_id": "3", "uploaderBattery": 85, "date": 1699363200000}] * 20,
        },
    }
