"""Unit tests for bot initialization and configuration."""

from collections.abc import Generator
from unittest.mock import MagicMock, patch

import pytest

from nightscout_backup_bot.bot import NightScoutBackupBot, create_bot
from nightscout_backup_bot.config import settings


@pytest.fixture(autouse=True)
def cleanup_bot_commands() -> Generator[None, None, None]:
    """Clean up Discord command registrations after bot tests to prevent test pollution."""
    yield
    # Clear any registered commands after each test
    # This prevents "command already registered" errors when tests run in sequence
    import gc

    gc.collect()  # Force garbage collection to clean up bot instances


@pytest.mark.asyncio
async def test_bot_initialization() -> None:
    """Test bot initializes with correct configuration."""
    bot = NightScoutBackupBot()

    # Check intents are properly configured
    assert bot.intents.message_content, "Message content intent should be enabled"
    assert bot.intents.guilds, "Guilds intent should be enabled"

    # Check backup service is initialized
    assert bot.backup_service is not None, "Backup service should be initialized"


@pytest.mark.asyncio
async def test_create_bot_function() -> None:
    """Test create_bot function returns configured bot."""
    with patch("nightscout_backup_bot.bot.setup_logging"):
        bot = create_bot()

        assert isinstance(bot, NightScoutBackupBot), "Should return NightScoutBackupBot instance"
        assert bot.backup_service is not None, "Backup service should be initialized"


@pytest.mark.asyncio
async def test_bot_on_ready_event(caplog: pytest.LogCaptureFixture) -> None:
    """Test on_ready event handler."""
    bot = NightScoutBackupBot()

    # Mock the user property and guilds
    mock_user = MagicMock()
    mock_user.id = 123456789
    mock_user.__str__ = MagicMock(return_value="TestBot#1234")  # type: ignore[method-assign]

    mock_guilds = [MagicMock(), MagicMock()]

    with patch.object(type(bot), "user", new=mock_user), patch.object(type(bot), "guilds", new=mock_guilds):
        # Mock nightly backup task
        bot.nightly_backup = MagicMock()  # type: ignore[method-assign]
        bot.nightly_backup.is_running.return_value = False
        bot.nightly_backup.start = MagicMock()

        # Call on_ready
        await bot.on_ready()

        # Verify nightly backup was started if enabled
        if settings.enable_nightly_backup:
            bot.nightly_backup.start.assert_called_once()


@pytest.mark.asyncio
async def test_bot_slash_command_logging() -> None:
    """Test slash command event logging."""
    bot = NightScoutBackupBot()

    # Create mock interaction
    mock_inter = MagicMock()
    mock_inter.application_command.name = "test_command"
    mock_inter.author.id = 111111111
    mock_inter.author.__str__ = MagicMock(return_value="TestUser#1234")
    mock_inter.guild_id = 987654321

    # This should not raise an exception
    await bot.on_slash_command(mock_inter)  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_bot_slash_command_error_handling() -> None:
    """Test slash command error handler."""
    from disnake.ext.commands import CommandError

    bot = NightScoutBackupBot()

    # Create mock interaction and error
    mock_inter = MagicMock()
    mock_inter.application_command.name = "test_command"
    mock_inter.author.id = 111111111

    # Use CommandError instead of generic Exception
    error = CommandError("Test error")

    # This should not raise an exception (type ignore needed for mock interaction)
    await bot.on_slash_command_error(mock_inter, error)  # pyright: ignore


@pytest.mark.asyncio
async def test_bot_cog_loading() -> None:
    """Test that cogs are loaded correctly."""
    with patch("nightscout_backup_bot.bot.setup_logging"):
        bot = create_bot()

        # Check that cogs were loaded
        cog_names = [cog.qualified_name for cog in bot.cogs.values()]

        # We expect at least one cog to be loaded
        assert len(cog_names) > 0, "At least one cog should be loaded"


@pytest.mark.asyncio
async def test_nightly_backup_task_disabled() -> None:
    """Test that nightly backup task respects settings."""
    bot = NightScoutBackupBot()

    # If nightly backup is disabled in settings, task should not be running
    # This is handled in on_ready, so we test that behavior
    if not settings.enable_nightly_backup:
        bot.nightly_backup = MagicMock()
        bot.nightly_backup.is_running.return_value = False

        await bot.on_ready()

        # Should not call start if disabled
        bot.nightly_backup.start.assert_not_called()
