"""Unit tests for dbstats command in general cog.

This module tests the DBStatsCog class which contains the /dbstats command.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import disnake
import pytest

from nightscout_backup_bot.cogs.general.dbstats import (
    DBStatsCog,
    format_bytes,
    parse_size_with_unit,
)

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_bot() -> MagicMock:
    """Create mock bot instance."""
    bot = MagicMock()
    return bot


@pytest.fixture
def mock_settings() -> MagicMock:
    """Create mock settings instance."""
    settings = MagicMock()
    settings.mongo_connection_string = "mongodb+srv://user:pass@host/db"
    settings.mongo_db = "test_db"
    settings.mongo_db_max_size = 512  # 512 MB
    return settings


@pytest.fixture
def dbstats_cog(mock_bot: MagicMock, mock_settings: MagicMock) -> DBStatsCog:
    """Create DBStatsCog instance with mock bot and settings."""
    with patch("nightscout_backup_bot.cogs.general.dbstats.get_settings", return_value=mock_settings):
        cog = DBStatsCog(mock_bot)
        # Ensure the cog has the mocked settings stored
        cog.settings = mock_settings
        return cog


@pytest.fixture
def mock_interaction() -> MagicMock:
    """Create mock Discord interaction for slash commands."""
    interaction = MagicMock(spec=disnake.ApplicationCommandInteraction)
    interaction.author.id = 123456789
    interaction.author.name = "TestUser"
    interaction.response.defer = AsyncMock()
    interaction.followup.send = AsyncMock()
    return interaction


@pytest.fixture
def mock_mongo_stats() -> dict[str, int | str]:
    """Create mock MongoDB stats response."""
    return {
        "db": "nightscout",
        "collections": 15,
        "dataSize": 104857600,  # 100 MB
        "storageSize": 157286400,  # 150 MB
        "indexSize": 52428800,  # 50 MB
        "indexes": 23,
    }


@pytest.fixture
def mock_mongo_client(mock_mongo_stats: dict[str, int | str]) -> MagicMock:
    """Create mock MongoDB client with proper structure."""
    mock_client = MagicMock()
    mock_db = MagicMock()
    mock_db.command = AsyncMock(return_value=mock_mongo_stats)
    mock_client.__getitem__.return_value = mock_db
    mock_client.close = MagicMock()  # Ensure close is a proper mock
    return mock_client


# ============================================================================
# Utility Function Tests
# ============================================================================


class TestFormatBytes:
    """Test suite for format_bytes utility function."""

    def test_format_zero_bytes(self) -> None:
        """Test formatting zero bytes."""
        result = format_bytes(0)
        assert result == "0 B"

    def test_format_bytes_only(self) -> None:
        """Test formatting less than 1 KiB."""
        result = format_bytes(512)
        assert result == "512.00 B"

    def test_format_kilobytes_binary(self) -> None:
        """Test formatting kilobytes in binary (1024)."""
        result = format_bytes(2048, binary=True)
        assert result == "2.00 KiB"

    def test_format_megabytes_binary(self) -> None:
        """Test formatting megabytes in binary."""
        result = format_bytes(104857600, binary=True)  # 100 MB
        assert result == "100.00 MiB"

    def test_format_gigabytes_binary(self) -> None:
        """Test formatting gigabytes in binary."""
        result = format_bytes(1073741824, binary=True)  # 1 GB
        assert result == "1.00 GiB"

    def test_format_bytes_decimal(self) -> None:
        """Test formatting bytes in decimal (1000)."""
        result = format_bytes(1000000, binary=False)
        assert result == "1.00 MB"

    def test_format_negative_bytes(self) -> None:
        """Test formatting negative bytes returns 0 B."""
        result = format_bytes(-1024)
        assert result == "0 B"

    def test_format_large_bytes(self) -> None:
        """Test formatting very large byte values."""
        result = format_bytes(1125899906842624, binary=True)  # 1 PiB
        assert result == "1.00 PiB"


class TestParseSizeWithUnit:
    """Test suite for parse_size_with_unit utility function."""

    def test_parse_bytes(self) -> None:
        """Test parsing bytes."""
        value, unit, exponent = parse_size_with_unit("512.00 B")
        assert value == 512.00
        assert unit == "B"
        assert exponent == 0

    def test_parse_kilobytes(self) -> None:
        """Test parsing kilobytes."""
        value, unit, exponent = parse_size_with_unit("2.00 KiB")
        assert value == 2.00
        assert unit == "KiB"
        assert exponent == 1

    def test_parse_megabytes(self) -> None:
        """Test parsing megabytes."""
        value, unit, exponent = parse_size_with_unit("100.00 MiB")
        assert value == 100.00
        assert unit == "MiB"
        assert exponent == 2

    def test_parse_gigabytes(self) -> None:
        """Test parsing gigabytes."""
        value, unit, exponent = parse_size_with_unit("1.50 GiB")
        assert value == 1.50
        assert unit == "GiB"
        assert exponent == 3

    def test_parse_invalid_format(self) -> None:
        """Test parsing invalid format returns defaults."""
        value, unit, exponent = parse_size_with_unit("invalid")
        assert value == 0.0
        assert unit == "B"
        assert exponent == 0


# ============================================================================
# DBStatsCog Initialization Tests
# ============================================================================


class TestDBStatsCogInitialization:
    """Test suite for DBStatsCog initialization and setup."""

    def test_cog_initialization(self, mock_bot: MagicMock, mock_settings: MagicMock) -> None:
        """Test DBStatsCog initializes with correct bot reference."""
        with patch("nightscout_backup_bot.cogs.general.dbstats.get_settings", return_value=mock_settings):
            cog = DBStatsCog(mock_bot)

        assert cog.bot is mock_bot, "Bot should be stored in cog"
        assert hasattr(cog, "dbstats"), "dbstats command should exist"
        assert cog.settings is mock_settings, "Settings should be stored in cog"

    def test_cog_setup_function(self) -> None:
        """Test setup function adds DBStatsCog to bot."""
        from nightscout_backup_bot.cogs.general.dbstats import DBStatsCog as StatsDBCog
        from nightscout_backup_bot.cogs.general.dbstats import setup

        mock_bot = MagicMock()
        with patch("nightscout_backup_bot.cogs.general.dbstats.get_settings"):
            setup(mock_bot)

        # Verify add_cog was called with DBStatsCog instance
        mock_bot.add_cog.assert_called_once()
        call_args = mock_bot.add_cog.call_args
        added_cog = call_args[0][0]
        assert isinstance(added_cog, StatsDBCog), "Should add DBStatsCog instance"


# ============================================================================
# DBStats Command Tests
# ============================================================================


class TestDBStatsCommand:
    """Test suite for the /dbstats slash command."""

    @pytest.mark.asyncio
    async def test_dbstats_returns_success_embed(
        self,
        dbstats_cog: DBStatsCog,
        mock_interaction: MagicMock,
        mock_mongo_client: MagicMock,
    ) -> None:
        """Test /dbstats command returns properly formatted success embed."""
        with patch("nightscout_backup_bot.cogs.general.dbstats.AsyncIOMotorClient", return_value=mock_mongo_client):
            # Execute dbstats command
            await dbstats_cog.dbstats.callback(dbstats_cog, mock_interaction)

        # Verify defer was called
        mock_interaction.response.defer.assert_called_once()

        # Verify followup was sent
        mock_interaction.followup.send.assert_called_once()

        # Get the embed that was sent
        call_args = mock_interaction.followup.send.call_args
        embed = call_args.kwargs.get("embed")

        # Verify embed properties
        assert embed is not None, "Embed should be sent"
        assert isinstance(embed, disnake.Embed), "Should send a Disnake Embed"
        assert embed.title == "Database: nightscout"
        assert embed.description == "Current statistics for this database"

    @pytest.mark.asyncio
    async def test_dbstats_calculates_aggregate_size(
        self,
        dbstats_cog: DBStatsCog,
        mock_interaction: MagicMock,
        mock_mongo_client: MagicMock,
    ) -> None:
        """Test /dbstats calculates aggregate size correctly."""
        with patch("nightscout_backup_bot.cogs.general.dbstats.AsyncIOMotorClient", return_value=mock_mongo_client):
            await dbstats_cog.dbstats.callback(dbstats_cog, mock_interaction)

        call_args = mock_interaction.followup.send.call_args
        embed = call_args.kwargs.get("embed")

        # Find the aggregate size field
        aggregate_field = next((f for f in embed.fields if "Aggregate Size" in f.name), None)
        assert aggregate_field is not None, "Should have aggregate size field"
        # Storage (150 MB) + Index (50 MB) = 200 MB
        assert "200.00 MiB" in aggregate_field.value

    @pytest.mark.asyncio
    async def test_dbstats_shows_percentage_when_max_size_configured(
        self,
        dbstats_cog: DBStatsCog,
        mock_interaction: MagicMock,
        mock_mongo_client: MagicMock,
    ) -> None:
        """Test /dbstats shows percentage used when max size is configured."""
        dbstats_cog.settings.mongo_db_max_size = 512  # 512 MB

        with patch("nightscout_backup_bot.cogs.general.dbstats.AsyncIOMotorClient", return_value=mock_mongo_client):
            await dbstats_cog.dbstats.callback(dbstats_cog, mock_interaction)

        call_args = mock_interaction.followup.send.call_args
        embed = call_args.kwargs.get("embed")

        # Find the percentage field
        percentage_field = next((f for f in embed.fields if "Percent of DB Used" in f.name), None)
        assert percentage_field is not None, "Should have percentage field"
        # Aggregate: 200 MB, Max: 512 MB = ~39% (200 MB / 512 MB * 100)
        assert "39%" in percentage_field.value

    @pytest.mark.asyncio
    async def test_dbstats_shows_warning_when_near_capacity(
        self,
        dbstats_cog: DBStatsCog,
        mock_interaction: MagicMock,
    ) -> None:
        """Test /dbstats shows warning when database is near capacity."""
        dbstats_cog.settings.mongo_db_max_size = 256  # 256 MB

        # Create stats that show ~85% usage
        high_usage_stats: dict[str, int | str] = {
            "db": "nightscout",
            "collections": 15,
            "dataSize": 104857600,  # 100 MB
            "storageSize": 157286400,  # 150 MB
            "indexSize": 62914560,  # 60 MB (total: 210 MB)
            "indexes": 23,
        }

        mock_mongo_client = MagicMock()
        mock_db = MagicMock()
        mock_db.command = AsyncMock(return_value=high_usage_stats)
        mock_mongo_client.__getitem__.return_value = mock_db
        mock_mongo_client.close = MagicMock()

        with patch("nightscout_backup_bot.cogs.general.dbstats.AsyncIOMotorClient", return_value=mock_mongo_client):
            await dbstats_cog.dbstats.callback(dbstats_cog, mock_interaction)

        call_args = mock_interaction.followup.send.call_args
        embed = call_args.kwargs.get("embed")

        # Should show yellow/warning color
        assert embed.color == disnake.Color.yellow()

        # Should have recommendation field
        recommendation_field = next((f for f in embed.fields if "Recommendation" in f.name), None)
        assert recommendation_field is not None, "Should have recommendation field"
        assert "close to being full" in recommendation_field.value.lower()

    @pytest.mark.asyncio
    async def test_dbstats_no_warning_when_below_threshold(
        self,
        dbstats_cog: DBStatsCog,
        mock_interaction: MagicMock,
        mock_mongo_stats: dict[str, int | str],
    ) -> None:
        """Test /dbstats does not show warning when database is below threshold."""
        dbstats_cog.settings.mongo_db_max_size = 1024  # 1024 MB (plenty of space)

        mock_mongo_client = MagicMock()
        mock_db = MagicMock()
        mock_db.command = AsyncMock(return_value=mock_mongo_stats)
        mock_mongo_client.__getitem__.return_value = mock_db

        with patch("nightscout_backup_bot.cogs.general.dbstats.AsyncIOMotorClient", return_value=mock_mongo_client):
            await dbstats_cog.dbstats.callback(dbstats_cog, mock_interaction)

        call_args = mock_interaction.followup.send.call_args
        embed = call_args.kwargs.get("embed")

        # Should show green color
        assert embed.color == disnake.Color.green()

        # Should not have recommendation field
        recommendation_field = next((f for f in embed.fields if "Recommendation" in f.name), None)
        assert recommendation_field is None, "Should not have recommendation field"

    @pytest.mark.asyncio
    async def test_dbstats_no_percentage_when_max_size_not_configured(
        self,
        dbstats_cog: DBStatsCog,
        mock_interaction: MagicMock,
        mock_mongo_client: MagicMock,
    ) -> None:
        """Test /dbstats does not show percentage when max size is not configured."""
        dbstats_cog.settings.mongo_db_max_size = None

        with patch("nightscout_backup_bot.cogs.general.dbstats.AsyncIOMotorClient", return_value=mock_mongo_client):
            await dbstats_cog.dbstats.callback(dbstats_cog, mock_interaction)

        call_args = mock_interaction.followup.send.call_args
        embed = call_args.kwargs.get("embed")

        # Should not have percentage field
        percentage_field = next((f for f in embed.fields if "Percent of DB Used" in f.name), None)
        assert percentage_field is None, "Should not have percentage field when max size not configured"

    @pytest.mark.asyncio
    async def test_dbstats_handles_mongo_connection_error(
        self,
        dbstats_cog: DBStatsCog,
        mock_interaction: MagicMock,
    ) -> None:
        """Test /dbstats handles MongoDB connection errors gracefully."""
        with patch(
            "nightscout_backup_bot.cogs.general.dbstats.AsyncIOMotorClient",
            side_effect=Exception("Connection failed"),
        ):
            await dbstats_cog.dbstats.callback(dbstats_cog, mock_interaction)

        # Verify defer was called
        mock_interaction.response.defer.assert_called_once()

        # Verify error message was sent
        call_args = mock_interaction.followup.send.call_args
        embed = call_args.kwargs.get("embed")

        assert embed is not None, "Error embed should be sent"
        assert "❌ Error" in embed.title
        assert "Failed to retrieve database statistics" in embed.description
        assert call_args.kwargs.get("ephemeral") is True, "Error should be ephemeral"

    @pytest.mark.asyncio
    async def test_dbstats_closes_mongo_connection(
        self,
        dbstats_cog: DBStatsCog,
        mock_interaction: MagicMock,
        mock_mongo_client: MagicMock,
    ) -> None:
        """Test /dbstats properly closes MongoDB connection."""
        with patch("nightscout_backup_bot.cogs.general.dbstats.AsyncIOMotorClient", return_value=mock_mongo_client):
            await dbstats_cog.dbstats.callback(dbstats_cog, mock_interaction)

        # Verify connection was closed
        mock_mongo_client.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_dbstats_closes_connection_on_error(
        self,
        dbstats_cog: DBStatsCog,
        mock_interaction: MagicMock,
    ) -> None:
        """Test /dbstats closes connection even when error occurs."""
        mock_mongo_client = MagicMock()
        mock_db = MagicMock()
        mock_db.command = AsyncMock(side_effect=Exception("Command failed"))
        mock_mongo_client.__getitem__.return_value = mock_db
        mock_mongo_client.close = MagicMock()

        with patch("nightscout_backup_bot.cogs.general.dbstats.AsyncIOMotorClient", return_value=mock_mongo_client):
            await dbstats_cog.dbstats.callback(dbstats_cog, mock_interaction)

        # Verify connection was closed despite error
        mock_mongo_client.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_dbstats_embed_has_all_required_fields(
        self,
        dbstats_cog: DBStatsCog,
        mock_interaction: MagicMock,
        mock_mongo_stats: dict[str, int | str],
    ) -> None:
        """Test /dbstats embed contains all required database statistics fields."""
        mock_mongo_client = MagicMock()
        mock_db = MagicMock()
        mock_db.command = AsyncMock(return_value=mock_mongo_stats)
        mock_mongo_client.__getitem__.return_value = mock_db

        with patch("nightscout_backup_bot.cogs.general.dbstats.AsyncIOMotorClient", return_value=mock_mongo_client):
            await dbstats_cog.dbstats.callback(dbstats_cog, mock_interaction)

        call_args = mock_interaction.followup.send.call_args
        embed = call_args.kwargs.get("embed")

        # Get all field names
        field_names = [f.name for f in embed.fields]

        # Verify required fields are present
        assert "Collections" in field_names
        assert "Indexes" in field_names
        assert "Data Size" in field_names
        assert "Storage Size" in field_names
        assert "Index Size" in field_names
        assert "Aggregate Size (Storage + Index)" in field_names
