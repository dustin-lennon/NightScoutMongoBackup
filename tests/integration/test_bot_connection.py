"""Integration test for Discord bot connection.

This test verifies that the bot can:
1. Initialize properly
2. Connect to Discord
3. Load all cogs
4. Access configured channels
5. Register slash commands

Run with: poetry run pytest tests/integration/test_bot_connection.py -v

Note: This requires valid Discord credentials in .env file.
Set SKIP_DISCORD_TESTS=1 to skip this test.
"""

import os

import pytest

from nightscout_backup_bot.bot import create_bot
from nightscout_backup_bot.config import settings
from nightscout_backup_bot.logging_config import StructuredLogger

logger = StructuredLogger("test.bot_connection")

# Skip if Discord tests should be skipped
pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(os.getenv("SKIP_DISCORD_TESTS") == "1", reason="Discord integration tests disabled"),
]


@pytest.mark.asyncio
async def test_bot_creation() -> None:
    """Test that bot can be created with valid configuration."""
    # Verify settings are loaded
    assert settings.discord_token, "Discord token not set"
    assert settings.discord_client_id, "Discord client ID not set"
    assert settings.backup_channel_id, "Backup channel ID not set"

    logger.info("Creating bot instance...")
    bot = create_bot()

    assert bot is not None, "Bot should be created"
    assert bot.backup_service is not None, "Backup service should be initialized"
    logger.info("✅ Bot created successfully")


@pytest.mark.asyncio
async def test_bot_cogs_loaded() -> None:
    """Test that all cogs are loaded properly."""
    bot = create_bot()

    # Check that cogs are loaded
    cog_names = [cog.qualified_name for cog in bot.cogs.values()]
    logger.info("Loaded cogs", cogs=cog_names)

    # We expect at least GeneralCog and AdminCog (if implemented)
    assert len(cog_names) > 0, "At least one cog should be loaded"
    logger.info("✅ Cogs loaded successfully")


@pytest.mark.asyncio
@pytest.mark.slow
async def test_bot_discord_connection() -> None:
    """Test that bot can connect to Discord.

    WARNING: This is a real connection test that will:
    - Connect the bot to Discord
    - Verify guild access
    - Check channel accessibility
    - Automatically disconnect after checks

    This test is marked as 'slow' - run with: pytest -m slow
    """
    logger.info("Starting Discord connection test...")

    bot = create_bot()
    connection_verified = False

    @bot.event  # type: ignore[misc]
    async def on_ready() -> None:  # pyright: ignore[reportUnusedFunction]
        """Verify connection when bot is ready."""
        nonlocal connection_verified

        logger.info(
            "Bot connected to Discord",
            bot_user=str(bot.user),
            bot_id=bot.user.id if bot.user else None,
            guilds=len(bot.guilds),
        )

        # Verify we're in at least one guild
        assert len(bot.guilds) > 0, "Bot should be in at least one guild"

        guild_names = [guild.name for guild in bot.guilds]
        logger.info("Connected to guilds", guilds=guild_names)

        # Check if we can access the backup channel
        channel = bot.get_channel(int(settings.backup_channel_id))
        if channel:
            logger.info(
                "✅ Backup channel accessible", channel_name=getattr(channel, "name", "unknown"), channel_id=channel.id
            )
        else:
            logger.warning("⚠️ Backup channel not accessible", channel_id=settings.backup_channel_id)

        # Check registered slash commands
        command_names = [cmd.name for cmd in bot.slash_commands]
        logger.info("Registered slash commands", commands=command_names)
        assert len(command_names) > 0, "At least one slash command should be registered"

        connection_verified = True

        # Close the connection
        logger.info("Connection test complete, closing bot...")
        await bot.close()

    try:
        # Start the bot (will run until on_ready closes it)
        logger.info("Connecting to Discord...")
        await bot.start(settings.discord_token)
    except Exception as e:
        logger.error("Failed to connect", error=str(e))
        raise
    finally:
        if not bot.is_closed():
            await bot.close()

    assert connection_verified, "Connection should be verified in on_ready"
    logger.info("✅ Discord connection test passed")


@pytest.mark.asyncio
async def test_bot_slash_commands_registered() -> None:
    """Test that slash commands are properly registered."""
    bot = create_bot()

    # Check for expected slash commands
    command_names = [cmd.name for cmd in bot.slash_commands]
    logger.info("Slash commands", commands=command_names)

    # At minimum we should have 'ping'
    assert "ping" in command_names, "Ping command should be registered"

    logger.info("✅ Slash commands registered")
