"""Unit tests for ping command in general cog.

This module tests the GeneralCog class which contains the /ping command.
"""

from unittest.mock import AsyncMock, MagicMock

import disnake
import pytest

from nightscout_backup_bot.cogs.general.ping import GeneralCog

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_bot() -> MagicMock:
    """Create mock bot instance with default latency."""
    bot = MagicMock()
    bot.latency = 0.045  # 45ms latency
    return bot


@pytest.fixture
def general_cog(mock_bot: MagicMock) -> GeneralCog:
    """Create GeneralCog instance with mock bot."""
    return GeneralCog(mock_bot)


@pytest.fixture
def mock_interaction() -> MagicMock:
    """Create mock Discord interaction for slash commands."""
    interaction = MagicMock(spec=disnake.ApplicationCommandInteraction)
    interaction.author.id = 123456789
    interaction.author.name = "TestUser"
    interaction.response.send_message = AsyncMock()
    return interaction


# ============================================================================
# GeneralCog Initialization Tests
# ============================================================================


class TestGeneralCogInitialization:
    """Test suite for GeneralCog initialization and setup."""

    def test_cog_initialization(self, mock_bot: MagicMock) -> None:
        """Test GeneralCog initializes with correct bot reference."""
        cog = GeneralCog(mock_bot)

        assert cog.bot is mock_bot, "Bot should be stored in cog"
        assert hasattr(cog, "ping"), "Ping command should exist"

    def test_cog_setup_function(self) -> None:
        """Test setup function adds GeneralCog to bot."""
        from nightscout_backup_bot.cogs.general.ping import GeneralCog as PingGeneralCog
        from nightscout_backup_bot.cogs.general.ping import setup

        mock_bot = MagicMock()
        setup(mock_bot)

        # Verify add_cog was called with GeneralCog instance
        mock_bot.add_cog.assert_called_once()
        call_args = mock_bot.add_cog.call_args
        added_cog = call_args[0][0]
        assert isinstance(added_cog, PingGeneralCog), "Should add GeneralCog instance"


# ============================================================================
# Ping Command Tests
# ============================================================================


class TestPingCommand:
    """Test suite for the /ping slash command."""

    @pytest.mark.asyncio
    async def test_ping_returns_success_embed(
        self,
        general_cog: GeneralCog,
        mock_interaction: MagicMock,
        mock_bot: MagicMock,
    ) -> None:
        """Test /ping command returns properly formatted success embed."""
        # Execute ping command - call the callback directly
        await general_cog.ping.callback(general_cog, mock_interaction)

        # Verify response was sent
        mock_interaction.response.send_message.assert_called_once()

        # Get the embed that was sent
        call_args = mock_interaction.response.send_message.call_args
        embed = call_args.kwargs.get("embed")

        # Verify embed properties
        assert embed is not None, "Embed should be sent"
        assert isinstance(embed, disnake.Embed), "Should send a Disnake Embed"
        assert embed.title == "🏓 Pong!", "Embed title should be '🏓 Pong!'"
        assert embed.description is not None
        assert "Bot is online and responsive" in embed.description
        assert embed.color == disnake.Color.green(), "Embed should be green"

    @pytest.mark.asyncio
    async def test_ping_embed_contains_latency_field(
        self,
        general_cog: GeneralCog,
        mock_interaction: MagicMock,
    ) -> None:
        """Test /ping embed includes latency field with correct formatting."""
        await general_cog.ping.callback(general_cog, mock_interaction)

        call_args = mock_interaction.response.send_message.call_args
        embed = call_args.kwargs.get("embed")

        # Verify embed has correct number of fields
        assert len(embed.fields) == 2, "Should have 2 fields"

        # Check latency field
        latency_field = embed.fields[0]
        assert latency_field.name == "Latency"
        assert latency_field.value is not None
        assert "45ms" in latency_field.value
        assert latency_field.inline is True

    @pytest.mark.asyncio
    async def test_ping_embed_contains_status_field(
        self,
        general_cog: GeneralCog,
        mock_interaction: MagicMock,
    ) -> None:
        """Test /ping embed includes operational status field."""
        await general_cog.ping.callback(general_cog, mock_interaction)

        call_args = mock_interaction.response.send_message.call_args
        embed = call_args.kwargs.get("embed")

        # Check status field
        status_field = embed.fields[1]
        assert status_field.name == "Status"
        assert status_field.value is not None
        assert "✅ Operational" in status_field.value
        assert status_field.inline is True

    @pytest.mark.asyncio
    async def test_ping_uses_correct_interaction_response_method(
        self,
        general_cog: GeneralCog,
        mock_interaction: MagicMock,
    ) -> None:
        """Test /ping uses response.send_message (not followup or edit)."""
        await general_cog.ping.callback(general_cog, mock_interaction)

        # Verify it uses response.send_message (not followup or edit)
        mock_interaction.response.send_message.assert_called_once()
        assert not mock_interaction.followup.send.called, "Should use response.send_message, not followup"

    @pytest.mark.asyncio
    async def test_ping_logs_execution_with_metadata(
        self,
        general_cog: GeneralCog,
        mock_interaction: MagicMock,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Test /ping logs command execution with user and latency metadata."""
        import logging

        caplog.set_level(logging.INFO)
        await general_cog.ping.callback(general_cog, mock_interaction)

        # Verify log was captured
        assert len(caplog.records) > 0

        # Check that "Ping command executed" was logged
        log_messages = [record.message for record in caplog.records]
        assert any("Ping command executed" in msg for msg in log_messages)


# ============================================================================
# Ping Command - Latency Calculation Tests
# ============================================================================


class TestPingCommandLatencyCalculation:
    """Test suite for /ping command latency calculation accuracy."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "bot_latency,expected_display",
        [
            (0.001, "1ms"),  # 1ms
            (0.025, "25ms"),  # 25ms
            (0.123, "123ms"),  # 123ms
            (1.500, "1500ms"),  # 1500ms
        ],
        ids=["1ms", "25ms", "123ms", "1500ms"],
    )
    async def test_ping_calculates_latency_correctly(
        self,
        bot_latency: float,
        expected_display: str,
        mock_interaction: MagicMock,
    ) -> None:
        """Test /ping accurately calculates and displays various latency values."""
        mock_bot = MagicMock()
        mock_bot.latency = bot_latency
        cog = GeneralCog(mock_bot)

        await cog.ping.callback(cog, mock_interaction)

        # Get the embed and verify latency display
        call_args = mock_interaction.response.send_message.call_args
        embed = call_args.kwargs.get("embed")
        latency_field = embed.fields[0]

        assert latency_field.value is not None
        assert expected_display in latency_field.value, f"Expected {expected_display} for latency {bot_latency}"

    @pytest.mark.asyncio
    async def test_ping_handles_zero_latency(
        self,
        mock_interaction: MagicMock,
    ) -> None:
        """Test /ping handles zero latency edge case without errors."""
        mock_bot = MagicMock()
        mock_bot.latency = 0.0
        cog = GeneralCog(mock_bot)

        await cog.ping.callback(cog, mock_interaction)

        # Should not raise error and should show 0ms
        call_args = mock_interaction.response.send_message.call_args
        embed = call_args.kwargs.get("embed")
        latency_field = embed.fields[0]

        assert latency_field.value is not None
        assert "0ms" in latency_field.value

    @pytest.mark.asyncio
    async def test_ping_handles_very_high_latency(
        self,
        mock_interaction: MagicMock,
    ) -> None:
        """Test /ping handles extremely high latency gracefully."""
        mock_bot = MagicMock()
        mock_bot.latency = 5.0  # 5000ms - very high latency
        cog = GeneralCog(mock_bot)

        await cog.ping.callback(cog, mock_interaction)

        # Should handle high latency gracefully
        call_args = mock_interaction.response.send_message.call_args
        embed = call_args.kwargs.get("embed")
        latency_field = embed.fields[0]

        assert latency_field.value is not None
        assert "5000ms" in latency_field.value
