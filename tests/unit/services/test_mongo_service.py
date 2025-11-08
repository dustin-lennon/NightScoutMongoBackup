"""Unit tests for MongoService."""

import json
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from nightscout_backup_bot.services.mongo_service import MongoService


class TestMongoService:
    """Tests for MongoService."""

    @pytest.fixture
    def mongo_service(self) -> MongoService:
        """Create MongoService instance."""
        return MongoService()

    @pytest.mark.asyncio
    async def test_connect_success(
        self,
        mongo_service: MongoService,
        mock_mongo_client: AsyncMock,
    ) -> None:
        """Test successful MongoDB connection."""
        with patch("nightscout_backup_bot.services.mongo_service.AsyncIOMotorClient", return_value=mock_mongo_client):
            await mongo_service.connect()
            assert mongo_service.client is not None
            assert mongo_service.db is not None
            mock_mongo_client.admin.command.assert_called_once_with("ping")

    @pytest.mark.asyncio
    async def test_connect_failure(self, mongo_service: MongoService) -> None:
        """Test MongoDB connection failure."""
        with patch(
            "nightscout_backup_bot.services.mongo_service.AsyncIOMotorClient",
            side_effect=Exception("Connection failed"),
        ):
            with pytest.raises(Exception, match="Connection failed"):
                await mongo_service.connect()

    @pytest.mark.asyncio
    async def test_disconnect(
        self,
        mongo_service: MongoService,
        mock_mongo_client: AsyncMock,
    ) -> None:
        """Test MongoDB disconnection."""
        mongo_service.client = mock_mongo_client
        await mongo_service.disconnect()
        mock_mongo_client.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_export_all_collections(
        self,
        mongo_service: MongoService,
        mock_mongo_database: AsyncMock,
        sample_mongo_data: dict[str, Any],
    ) -> None:
        """Test exporting all collections."""
        mongo_service.db = mock_mongo_database

        # Mock collection data - find() returns a cursor (not async)
        # but to_list() is async
        async def mock_to_list(length: int | None = None) -> list[dict[str, Any]]:
            return sample_mongo_data["collections"]["entries"]  # type: ignore[no-any-return]

        cursor = MagicMock()
        cursor.to_list = mock_to_list

        collection = MagicMock()
        collection.find.return_value = cursor

        def mock_getitem(self: Any, name: str) -> Any:  # noqa: ANN401
            return collection

        mock_mongo_database.__getitem__ = mock_getitem

        result = await mongo_service.export_collections()

        assert "metadata" in result
        assert "collections" in result
        assert result["metadata"]["collections_count"] == 3
        mock_mongo_database.list_collection_names.assert_called_once()

    @pytest.mark.asyncio
    async def test_export_specific_collections(
        self,
        mongo_service: MongoService,
        mock_mongo_database: AsyncMock,
    ) -> None:
        """Test exporting specific collections."""
        mongo_service.db = mock_mongo_database

        # Mock collection with proper async chain
        # find() returns cursor (sync), to_list() is async
        async def mock_to_list(length: int | None = None) -> list[dict[str, Any]]:
            return [{"_id": "1"}]

        cursor = MagicMock()
        cursor.to_list = mock_to_list

        collection = MagicMock()
        collection.find.return_value = cursor

        mock_mongo_database.__getitem__ = lambda self, name: collection  # type: ignore

        result = await mongo_service.export_collections(["entries"])

        assert result["metadata"]["collections_count"] == 1
        assert "entries" in result["collections"]

    @pytest.mark.asyncio
    async def test_export_not_connected(self, mongo_service: MongoService) -> None:
        """Test export when not connected."""
        with pytest.raises(ValueError, match="Not connected to MongoDB"):
            await mongo_service.export_collections()

    def test_serialize_to_json(
        self,
        mongo_service: MongoService,
        sample_mongo_data: dict[str, Any],
    ) -> None:
        """Test JSON serialization."""
        json_str = mongo_service.serialize_to_json(sample_mongo_data)
        assert isinstance(json_str, str)

        # Verify it's valid JSON
        parsed = json.loads(json_str)
        assert parsed["metadata"]["database"] == "testdb"

    @pytest.mark.asyncio
    async def test_get_database_stats(
        self,
        mongo_service: MongoService,
        mock_mongo_database: AsyncMock,
    ) -> None:
        """Test getting database statistics."""
        mongo_service.db = mock_mongo_database
        mock_mongo_database.command = AsyncMock(
            return_value={
                "db": "testdb",
                "collections": 3,
                "objects": 150,
                "dataSize": 1024000,
            }
        )

        stats = await mongo_service.get_database_stats()

        assert stats["db"] == "testdb"
        assert stats["collections"] == 3
        mock_mongo_database.command.assert_called_once_with("dbStats")

    @pytest.mark.asyncio
    async def test_get_database_stats_not_connected(self, mongo_service: MongoService) -> None:
        """Test stats when not connected."""
        with pytest.raises(ValueError, match="Not connected to MongoDB"):
            await mongo_service.get_database_stats()
