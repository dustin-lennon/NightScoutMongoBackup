"""Tests for QueryDB command."""

from datetime import datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import disnake
import pytest

from nightscout_backup_bot.cogs.admin.querydb import QueryDBCog


@pytest.fixture
def mock_bot() -> MagicMock:
    """Create a mock bot instance."""
    bot = MagicMock()
    bot.latency = 0.045  # 45ms latency
    return bot


@pytest.fixture
def querydb_cog(mock_bot: MagicMock) -> QueryDBCog:
    """Create QueryDBCog instance with mocked dependencies."""
    return QueryDBCog(mock_bot)


@pytest.fixture
def mock_interaction() -> MagicMock:
    """Create a mock interaction."""
    inter = MagicMock(spec=disnake.ApplicationCommandInteraction)
    inter.author = MagicMock()
    inter.author.id = 123456789
    inter.response = MagicMock()
    inter.response.defer = AsyncMock()
    inter.followup = MagicMock()
    inter.followup.send = AsyncMock()
    return inter


class TestQueryDBCog:  # type: ignore[misc]
    """Test cases for QueryDBCog."""

    def test_init(self, mock_bot: Any) -> None:
        """Test QueryDBCog initialization."""
        cog = QueryDBCog(mock_bot)
        assert cog.bot == mock_bot
        assert cog.mongo_service is not None

    def test_flatten_document_to_fields_simple(self, querydb_cog: Any) -> None:
        """Test flattening a simple document."""
        doc: dict[str, Any] = {"_id": "123", "date": 1234567890, "sgv": 120}

        fields = querydb_cog._flatten_document_to_fields(doc)

        assert len(fields) == 3
        assert fields[0] == {"name": "_id", "value": "123", "inline": True}
        assert fields[1] == {"name": "date", "value": "1234567890", "inline": True}
        assert fields[2] == {"name": "sgv", "value": "120", "inline": True}

    def test_flatten_document_to_fields_with_uploader(self, querydb_cog: Any) -> None:
        """Test flattening a document with uploader field."""
        doc: dict[str, Any] = {
            "_id": "123",
            "sgv": 120,
            "uploader": {"name": "TestDevice", "battery": 85},
        }

        fields = querydb_cog._flatten_document_to_fields(doc)

        # Should have _id, sgv, uploader separator, and 2 uploader sub-fields
        assert len(fields) == 5
        assert fields[0] == {"name": "_id", "value": "123", "inline": True}
        assert fields[1] == {"name": "sgv", "value": "120", "inline": True}
        assert fields[2] == {"name": "uploader", "value": "\u200b", "inline": False}
        assert fields[3] == {"name": "name", "value": "TestDevice", "inline": True}
        assert fields[4] == {"name": "battery", "value": "85", "inline": True}

    def test_format_number(self, querydb_cog: Any) -> None:
        """Test number formatting."""
        assert querydb_cog._format_number(1000) == "1,000"
        assert querydb_cog._format_number(1000000) == "1,000,000"
        assert querydb_cog._format_number(123) == "123"

    def test_format_date(self, querydb_cog: Any) -> None:
        """Test date formatting."""
        assert querydb_cog._format_date("2024-01-15") == "Jan 15, 2024"
        assert querydb_cog._format_date("2024-12-31") == "Dec 31, 2024"

    def test_format_date_invalid(self, querydb_cog: Any) -> None:
        """Test date formatting with invalid date."""
        invalid_date = "invalid-date"
        assert querydb_cog._format_date(invalid_date) == invalid_date

    def test_parse_date_to_millis_valid(self, querydb_cog: Any) -> None:
        """Test parsing valid date to milliseconds."""
        date_str = "2024-01-15"
        millis = querydb_cog._parse_date_to_millis(date_str)

        # Verify it's a valid timestamp
        assert isinstance(millis, int)
        assert millis > 0

        # Verify it converts back correctly
        dt = datetime.fromtimestamp(millis / 1000)
        assert dt.year == 2024
        assert dt.month == 1
        assert dt.day == 15

    def test_parse_date_to_millis_invalid(self, querydb_cog: Any) -> None:
        """Test parsing invalid date to milliseconds."""
        with pytest.raises(ValueError, match="Invalid date format"):
            querydb_cog._parse_date_to_millis("invalid-date")

    def test_parse_date_to_iso_valid(self, querydb_cog: Any) -> None:
        """Test parsing valid date to ISO format."""
        date_str = "2024-01-15"
        iso_str = querydb_cog._parse_date_to_iso(date_str)

        assert iso_str.startswith("2024-01-15T")
        assert iso_str.endswith("Z")

    def test_parse_date_to_iso_invalid(self, querydb_cog: Any) -> None:
        """Test parsing invalid date to ISO format."""
        with pytest.raises(ValueError, match="Invalid date format"):
            querydb_cog._parse_date_to_iso("invalid-date")

    def test_build_embed(self, querydb_cog: Any) -> None:
        """Test building embed."""
        fields: list[dict[str, Any]] = [
            {"name": "_id", "value": "123", "inline": True},
            {"name": "sgv", "value": "120", "inline": True},
        ]

        embed = querydb_cog._build_embed("entries", 1000, "2024-01-15", fields)

        assert isinstance(embed, disnake.Embed)
        assert embed.title == "Oldest entry for Entries collection"
        assert embed.color.value == 0xFFFF00  # type: ignore[union-attr]  # Yellow
        assert len(embed.fields) == 2
        assert embed.footer.text == "The Entries collection has 1,000 entries since Jan 15, 2024"

    def test_build_embed_device_status(self, querydb_cog: Any) -> None:
        """Test building embed for device status."""
        fields: list[dict[str, Any]] = [{"name": "battery", "value": "85", "inline": True}]

        embed = querydb_cog._build_embed("devicestatus", 500, "2024-01-15", fields)

        assert embed.title == "Oldest entry for Device Status collection"
        assert "Device Status collection has 500 entries" in embed.footer.text

    def test_build_embed_treatments(self, querydb_cog: Any) -> None:
        """Test building embed for treatments."""
        fields: list[dict[str, Any]] = [{"name": "insulin", "value": "5.0", "inline": True}]

        embed = querydb_cog._build_embed("treatments", 250, "2024-01-15", fields)

        assert embed.title == "Oldest entry for Treatments collection"
        assert "Treatments collection has 250 entries" in embed.footer.text

    def test_build_embed_limits_fields(self, querydb_cog: Any) -> None:
        """Test that embed limits fields to 25."""
        # Create 30 fields
        fields: list[dict[str, Any]] = [{"name": f"field{i}", "value": f"value{i}", "inline": True} for i in range(30)]

        embed = querydb_cog._build_embed("entries", 1000, "2024-01-15", fields)

        # Discord limits embeds to 25 fields
        assert len(embed.fields) == 25

    def test_build_error_embed(self, querydb_cog: Any) -> None:
        """Test building error embed."""
        error_msg = "Connection timeout"

        embed = querydb_cog._build_error_embed("entries", error_msg)

        assert isinstance(embed, disnake.Embed)
        assert embed.title == "Error querying Entries collection"
        assert error_msg in str(embed.description)  # type: ignore[operator]
        assert "❌" in str(embed.description)  # type: ignore[operator]
        assert embed.color.value == 0xFF0000  # type: ignore[union-attr]  # Red

    @pytest.mark.asyncio
    async def test_handle_entries_success(self, querydb_cog: Any, mock_interaction: Any) -> None:
        """Test successful entries query."""
        # Mock MongoDB service
        mock_collection = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.to_list = AsyncMock(return_value=[{"_id": "123", "date": 1234567890, "sgv": 120}])
        mock_collection.find = MagicMock(return_value=mock_cursor)
        mock_cursor.sort = MagicMock(return_value=mock_cursor)
        mock_cursor.limit = MagicMock(return_value=mock_cursor)
        mock_collection.count_documents = AsyncMock(return_value=1000)

        querydb_cog.mongo_service.connect = AsyncMock()
        querydb_cog.mongo_service.disconnect = MagicMock()
        mock_db = MagicMock()
        mock_db.__getitem__ = MagicMock(return_value=mock_collection)
        querydb_cog.mongo_service.db = mock_db

        await querydb_cog._handle_entries(mock_interaction, "2024-01-15")

        # Verify MongoDB operations
        querydb_cog.mongo_service.connect.assert_called_once()
        querydb_cog.mongo_service.disconnect.assert_called_once()
        mock_collection.find.assert_called_once()
        mock_collection.count_documents.assert_called_once()

        # Verify response sent
        mock_interaction.followup.send.assert_called_once()
        call_args = mock_interaction.followup.send.call_args
        assert "embed" in call_args.kwargs

    @pytest.mark.asyncio
    async def test_handle_entries_db_none(self, querydb_cog: Any, mock_interaction: Any) -> None:
        """Test entries query when db is None."""
        querydb_cog.mongo_service.connect = AsyncMock()
        querydb_cog.mongo_service.disconnect = MagicMock()
        querydb_cog.mongo_service.db = None

        await querydb_cog._handle_entries(mock_interaction, "2024-01-15")

        # Verify error message sent
        mock_interaction.followup.send.assert_called_once()
        call_args = mock_interaction.followup.send.call_args
        assert "❌" in str(call_args)

    @pytest.mark.asyncio
    async def test_handle_entries_no_results(self, querydb_cog: Any, mock_interaction: Any) -> None:
        """Test entries query with no results."""
        # Mock MongoDB service
        mock_collection = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.to_list = AsyncMock(return_value=[])
        mock_collection.find = MagicMock(return_value=mock_cursor)
        mock_cursor.sort = MagicMock(return_value=mock_cursor)
        mock_cursor.limit = MagicMock(return_value=mock_cursor)

        querydb_cog.mongo_service.connect = AsyncMock()
        querydb_cog.mongo_service.disconnect = MagicMock()
        mock_db = MagicMock()
        mock_db.__getitem__ = MagicMock(return_value=mock_collection)
        querydb_cog.mongo_service.db = mock_db

        await querydb_cog._handle_entries(mock_interaction, "2024-01-15")

        # Verify "No entries found" message sent
        mock_interaction.followup.send.assert_called_once()
        call_args = mock_interaction.followup.send.call_args
        assert "No entries found" in str(call_args)

    @pytest.mark.asyncio
    async def test_handle_entries_invalid_date(self, querydb_cog: Any, mock_interaction: Any) -> None:
        """Test entries query with invalid date."""
        querydb_cog.mongo_service.connect = AsyncMock()
        querydb_cog.mongo_service.disconnect = MagicMock()

        await querydb_cog._handle_entries(mock_interaction, "invalid-date")

        # Verify error message sent
        mock_interaction.followup.send.assert_called_once()
        call_args = mock_interaction.followup.send.call_args
        assert "❌" in str(call_args)

    @pytest.mark.asyncio
    async def test_handle_entries_connection_error(self, querydb_cog: Any, mock_interaction: Any) -> None:
        """Test entries query with connection error."""
        querydb_cog.mongo_service.connect = AsyncMock(side_effect=Exception("Connection failed"))
        querydb_cog.mongo_service.disconnect = MagicMock()

        await querydb_cog._handle_entries(mock_interaction, "2024-01-15")

        # Verify error embed sent
        mock_interaction.followup.send.assert_called_once()
        call_args = mock_interaction.followup.send.call_args
        assert "embed" in call_args.kwargs

    @pytest.mark.asyncio
    async def test_handle_device_status_success(self, querydb_cog: Any, mock_interaction: Any) -> None:
        """Test successful device status query."""
        # Mock MongoDB service
        mock_collection = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.to_list = AsyncMock(
            return_value=[{"_id": "123", "created_at": "2024-01-15T00:00:00.000Z", "battery": 85}]
        )
        mock_collection.find = MagicMock(return_value=mock_cursor)
        mock_cursor.sort = MagicMock(return_value=mock_cursor)
        mock_cursor.limit = MagicMock(return_value=mock_cursor)
        mock_collection.count_documents = AsyncMock(return_value=500)

        querydb_cog.mongo_service.connect = AsyncMock()
        querydb_cog.mongo_service.disconnect = MagicMock()
        mock_db = MagicMock()
        mock_db.__getitem__ = MagicMock(return_value=mock_collection)
        querydb_cog.mongo_service.db = mock_db

        await querydb_cog._handle_device_status(mock_interaction, "2024-01-15")

        # Verify MongoDB operations
        querydb_cog.mongo_service.connect.assert_called_once()
        querydb_cog.mongo_service.disconnect.assert_called_once()

        # Verify response sent
        mock_interaction.followup.send.assert_called_once()
        # Verify count_documents was called
        mock_collection.count_documents.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_device_status_db_none(self, querydb_cog: Any, mock_interaction: Any) -> None:
        """Test device status query when db is None."""
        querydb_cog.mongo_service.connect = AsyncMock()
        querydb_cog.mongo_service.disconnect = MagicMock()
        querydb_cog.mongo_service.db = None

        await querydb_cog._handle_device_status(mock_interaction, "2024-01-15")

        # Verify error message sent
        mock_interaction.followup.send.assert_called_once()
        call_args = mock_interaction.followup.send.call_args
        assert "❌" in str(call_args)

    @pytest.mark.asyncio
    async def test_handle_treatments_success(self, querydb_cog: Any, mock_interaction: Any) -> None:
        """Test successful treatments query."""
        # Mock MongoDB service
        mock_collection = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.to_list = AsyncMock(return_value=[{"_id": "123", "timestamp": 1234567890, "insulin": 5.0}])
        mock_collection.find = MagicMock(return_value=mock_cursor)
        mock_cursor.sort = MagicMock(return_value=mock_cursor)
        mock_cursor.limit = MagicMock(return_value=mock_cursor)
        mock_collection.count_documents = AsyncMock(return_value=250)

        querydb_cog.mongo_service.connect = AsyncMock()
        querydb_cog.mongo_service.disconnect = MagicMock()
        mock_db = MagicMock()
        mock_db.__getitem__ = MagicMock(return_value=mock_collection)
        querydb_cog.mongo_service.db = mock_db

        await querydb_cog._handle_treatments(mock_interaction, "2024-01-15")

        # Verify MongoDB operations
        querydb_cog.mongo_service.connect.assert_called_once()
        querydb_cog.mongo_service.disconnect.assert_called_once()

        # Verify response sent
        mock_interaction.followup.send.assert_called_once()
        # Verify count_documents was called
        mock_collection.count_documents.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_treatments_db_none(self, querydb_cog: Any, mock_interaction: Any) -> None:
        """Test treatments query when db is None."""
        querydb_cog.mongo_service.connect = AsyncMock()
        querydb_cog.mongo_service.disconnect = MagicMock()
        querydb_cog.mongo_service.db = None

        await querydb_cog._handle_treatments(mock_interaction, "2024-01-15")

        # Verify error message sent
        mock_interaction.followup.send.assert_called_once()
        call_args = mock_interaction.followup.send.call_args
        assert "❌" in str(call_args)

    @pytest.mark.asyncio
    async def test_querydb_command_entries(self, querydb_cog: Any, mock_interaction: Any) -> None:
        """Test querydb command with Entries collection."""
        querydb_cog._handle_entries = AsyncMock()

        # Call the callback directly to bypass decorator wrapping
        await querydb_cog.querydb.callback(querydb_cog, mock_interaction, "Entries", "2024-01-15")

        # Verify defer was called
        mock_interaction.response.defer.assert_called_once()

        # Verify correct handler was called
        querydb_cog._handle_entries.assert_called_once_with(mock_interaction, "2024-01-15")

    @pytest.mark.asyncio
    async def test_querydb_command_device_status(self, querydb_cog: Any, mock_interaction: Any) -> None:
        """Test querydb command with Device Status collection."""
        querydb_cog._handle_device_status = AsyncMock()

        # Call the callback directly to bypass decorator wrapping
        await querydb_cog.querydb.callback(querydb_cog, mock_interaction, "Device Status", "2024-01-15")

        # Verify correct handler was called
        querydb_cog._handle_device_status.assert_called_once_with(mock_interaction, "2024-01-15")

    @pytest.mark.asyncio
    async def test_querydb_command_treatments(self, querydb_cog: Any, mock_interaction: Any) -> None:
        """Test querydb command with Treatments collection."""
        querydb_cog._handle_treatments = AsyncMock()

        # Call the callback directly to bypass decorator wrapping
        await querydb_cog.querydb.callback(querydb_cog, mock_interaction, "Treatments", "2024-01-15")

        # Verify correct handler was called
        querydb_cog._handle_treatments.assert_called_once_with(mock_interaction, "2024-01-15")

    @pytest.mark.asyncio
    async def test_handle_device_status_invalid_date(self, querydb_cog: Any, mock_interaction: Any) -> None:
        """Test device status query with invalid date."""
        querydb_cog.mongo_service.connect = AsyncMock()
        querydb_cog.mongo_service.disconnect = MagicMock()

        await querydb_cog._handle_device_status(mock_interaction, "invalid-date")

        mock_interaction.followup.send.assert_called_once()
        call_args = mock_interaction.followup.send.call_args
        assert "❌" in str(call_args)

    @pytest.mark.asyncio
    async def test_handle_device_status_connection_error(self, querydb_cog: Any, mock_interaction: Any) -> None:
        """Test device status query with connection error."""
        querydb_cog.mongo_service.connect = AsyncMock(side_effect=Exception("Connection failed"))
        querydb_cog.mongo_service.disconnect = MagicMock()

        await querydb_cog._handle_device_status(mock_interaction, "2024-01-15")

        mock_interaction.followup.send.assert_called_once()
        call_args = mock_interaction.followup.send.call_args
        assert "embed" in call_args.kwargs

    @pytest.mark.asyncio
    async def test_handle_device_status_query_error(self, querydb_cog: Any, mock_interaction: Any) -> None:
        """Test device status query with query error."""
        mock_collection = MagicMock()
        mock_collection.find = MagicMock(side_effect=Exception("Query failed"))
        querydb_cog.mongo_service.connect = AsyncMock()
        querydb_cog.mongo_service.disconnect = MagicMock()
        mock_db = MagicMock()
        mock_db.__getitem__ = MagicMock(return_value=mock_collection)
        querydb_cog.mongo_service.db = mock_db

        await querydb_cog._handle_device_status(mock_interaction, "2024-01-15")

        mock_interaction.followup.send.assert_called_once()
        call_args = mock_interaction.followup.send.call_args
        assert "embed" in call_args.kwargs

    @pytest.mark.asyncio
    async def test_handle_device_status_no_results(self, querydb_cog: Any, mock_interaction: Any) -> None:
        """Test device status query with no results."""
        mock_collection = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.to_list = AsyncMock(return_value=[])
        mock_collection.find = MagicMock(return_value=mock_cursor)
        mock_cursor.sort = MagicMock(return_value=mock_cursor)
        mock_cursor.limit = MagicMock(return_value=mock_cursor)

        querydb_cog.mongo_service.connect = AsyncMock()
        querydb_cog.mongo_service.disconnect = MagicMock()
        mock_db = MagicMock()
        mock_db.__getitem__ = MagicMock(return_value=mock_collection)
        querydb_cog.mongo_service.db = mock_db

        await querydb_cog._handle_device_status(mock_interaction, "2024-01-15")

        mock_interaction.followup.send.assert_called_once()
        call_args = mock_interaction.followup.send.call_args
        assert "No device status found" in str(call_args)

    @pytest.mark.asyncio
    async def test_handle_treatments_invalid_date(self, querydb_cog: Any, mock_interaction: Any) -> None:
        """Test treatments query with invalid date."""
        querydb_cog.mongo_service.connect = AsyncMock()
        querydb_cog.mongo_service.disconnect = MagicMock()

        await querydb_cog._handle_treatments(mock_interaction, "invalid-date")

        mock_interaction.followup.send.assert_called_once()
        call_args = mock_interaction.followup.send.call_args
        assert "❌" in str(call_args)

    @pytest.mark.asyncio
    async def test_handle_treatments_connection_error(self, querydb_cog: Any, mock_interaction: Any) -> None:
        """Test treatments query with connection error."""
        querydb_cog.mongo_service.connect = AsyncMock(side_effect=Exception("Connection failed"))
        querydb_cog.mongo_service.disconnect = MagicMock()

        await querydb_cog._handle_treatments(mock_interaction, "2024-01-15")

        mock_interaction.followup.send.assert_called_once()
        call_args = mock_interaction.followup.send.call_args
        assert "embed" in call_args.kwargs

    @pytest.mark.asyncio
    async def test_handle_treatments_query_error(self, querydb_cog: Any, mock_interaction: Any) -> None:
        """Test treatments query with query error."""
        mock_collection = MagicMock()
        mock_collection.find = MagicMock(side_effect=Exception("Query failed"))
        querydb_cog.mongo_service.connect = AsyncMock()
        querydb_cog.mongo_service.disconnect = MagicMock()
        mock_db = MagicMock()
        mock_db.__getitem__ = MagicMock(return_value=mock_collection)
        querydb_cog.mongo_service.db = mock_db

        await querydb_cog._handle_treatments(mock_interaction, "2024-01-15")

        mock_interaction.followup.send.assert_called_once()
        call_args = mock_interaction.followup.send.call_args
        assert "embed" in call_args.kwargs

    @pytest.mark.asyncio
    async def test_handle_treatments_no_results(self, querydb_cog: Any, mock_interaction: Any) -> None:
        """Test treatments query with no results."""
        mock_collection = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.to_list = AsyncMock(return_value=[])
        mock_collection.find = MagicMock(return_value=mock_cursor)
        mock_cursor.sort = MagicMock(return_value=mock_cursor)
        mock_cursor.limit = MagicMock(return_value=mock_cursor)

        querydb_cog.mongo_service.connect = AsyncMock()
        querydb_cog.mongo_service.disconnect = MagicMock()
        mock_db = MagicMock()
        mock_db.__getitem__ = MagicMock(return_value=mock_collection)
        querydb_cog.mongo_service.db = mock_db

        await querydb_cog._handle_treatments(mock_interaction, "2024-01-15")

        mock_interaction.followup.send.assert_called_once()
        call_args = mock_interaction.followup.send.call_args
        assert "No treatments found" in str(call_args)
