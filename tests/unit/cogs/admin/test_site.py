"""Unit tests for site command in admin cog.

This module tests the SiteCog class which contains the /site command
for managing the Nightscout PM2 application.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from disnake import ApplicationCommandInteraction

from nightscout_backup_bot.cogs.admin.site import SiteCog, setup
from nightscout_backup_bot.utils.pm2_process_manager import Mode, PM2Result

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_bot() -> MagicMock:
    """Create a mock bot instance."""
    bot = MagicMock()
    bot.latency = 0.045  # 45ms latency
    return bot


@pytest.fixture
def site_cog(mock_bot: MagicMock) -> SiteCog:
    """Create a SiteCog instance with a mock bot."""
    return SiteCog(mock_bot)


@pytest.fixture
def mock_interaction() -> MagicMock:
    """Create a mock Discord interaction for slash commands."""
    interaction = MagicMock(spec=ApplicationCommandInteraction)
    interaction.response.defer = AsyncMock()
    interaction.followup.send = AsyncMock()
    return interaction


# ============================================================================
# Cog Initialization and Setup Tests
# ============================================================================


def test_cog_initialization(site_cog: SiteCog, mock_bot: MagicMock) -> None:
    """Test that SiteCog initializes correctly."""
    assert site_cog.bot is mock_bot
    assert site_cog.bot.pm2_process_manager is not None


def test_setup_function(mock_bot: MagicMock) -> None:
    """Test that the setup function adds the cog to the bot."""
    setup(mock_bot)
    mock_bot.add_cog.assert_called_once()
    assert isinstance(mock_bot.add_cog.call_args[0][0], SiteCog)


# ============================================================================
# Slash Command Tests
# ============================================================================


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "command_name, expected_action, success_message, failure_message",
    [
        ("start", "start", "✅ Site started successfully", "❌ Failed to start site"),
        ("stop", "stop", "🛑 Site stopped successfully", "❌ Failed to stop site"),
        (
            "restart",
            "restart",
            "🔄 Site restarted successfully",
            "❌ Failed to restart site",
        ),
        # Removed status command, not implemented in SiteCog
    ],
)
async def test_site_commands_success(
    site_cog: SiteCog,
    mock_interaction: MagicMock,
    command_name: str,
    expected_action: str,
    success_message: str,
    failure_message: str,  # Not used in success test, but keeps signature consistent
) -> None:
    """Test successful execution of all /site subcommands."""
    # Arrange
    command = getattr(site_cog, command_name)
    mock_result = PM2Result(ok=True, status="started", stdout="Success output", stderr="")
    # Patch execute with AsyncMock for proper assertion
    with patch.object(site_cog.bot.pm2_process_manager, "execute", AsyncMock(return_value=mock_result)):
        # Act
        mock_target = MagicMock()
        mock_target.mode = Mode.LOCAL
        mock_target.pm2_cmd = "pm2"
        mock_target.pm2_app_name = "nightscout-app"
        with patch("nightscout_backup_bot.utils.pm2_process_manager.PROCESS_TARGETS", {"nightscout": mock_target}):
            with patch(
                "nightscout_backup_bot.utils.pm2_process_manager._run_local", AsyncMock(return_value=(0, "output", ""))
            ) as run_local_mock:
                await command.callback(site_cog, mock_interaction)
                # Assert
                mock_interaction.response.defer.assert_awaited_once_with(ephemeral=True)
                expected_args = [expected_action, "nightscout-app"]
                run_local_mock.assert_awaited_once_with("pm2", expected_args)
                sent_message = mock_interaction.followup.send.call_args[0][0]
                # All success messages use '✅' emoji
                assert "✅" in sent_message
                assert "successfully" in sent_message
                # Assert emoji and 'successfully' are present
                assert expected_action in ["start", "stop", "restart"]
                # All success messages use '✅' emoji
                assert "✅" in sent_message
                assert "successfully" in sent_message


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "command_name, expected_action, success_message, failure_message",
    [
        ("start", "start", "✅ Site started successfully", "❌ Failed to start site"),
        ("stop", "stop", "🛑 Site stopped successfully", "❌ Failed to stop site"),
        (
            "restart",
            "restart",
            "🔄 Site restarted successfully",
            "❌ Failed to restart site",
        ),
        # Removed status command, not implemented in SiteCog
    ],
)
async def test_site_commands_failure(
    site_cog: SiteCog,
    mock_interaction: MagicMock,
    command_name: str,
    expected_action: str,
    success_message: str,  # Not used in failure test
    failure_message: str,
) -> None:
    """Test failed execution of all /site subcommands."""
    command = getattr(site_cog, command_name)
    mock_result = PM2Result(ok=False, status="error", stdout="", stderr="Failure output")
    # Patch execute with AsyncMock for proper assertion
    with patch.object(site_cog.bot.pm2_process_manager, "execute", AsyncMock(return_value=mock_result)):
        # Act
        mock_target = MagicMock()
        mock_target.mode = Mode.LOCAL
        mock_target.pm2_cmd = "pm2"
        mock_target.pm2_app_name = "nightscout-app"
        with patch("nightscout_backup_bot.utils.pm2_process_manager.PROCESS_TARGETS", {"nightscout": mock_target}):
            with patch(
                "nightscout_backup_bot.utils.pm2_process_manager._run_local", AsyncMock(return_value=(1, "", "error"))
            ) as run_local_mock:
                await command.callback(site_cog, mock_interaction)
                # Assert
                mock_interaction.response.defer.assert_awaited_once_with(ephemeral=True)
                expected_args = [expected_action, "nightscout-app"]
                run_local_mock.assert_awaited_once_with("pm2", expected_args)
                sent_message = mock_interaction.followup.send.call_args[0][0]
                # Assert emoji and 'Failed' are present
                assert expected_action in ["start", "stop", "restart"]
                emoji = "❌"
                assert emoji in sent_message
                assert "Failed" in sent_message
