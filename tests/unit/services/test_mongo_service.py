"""Unit tests for MongoService."""

import json
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from nightscout_backup_bot.services.mongo_service import MongoService


# Fixtures
@pytest.fixture
def mongo_service() -> MongoService:
    """Create MongoService instance."""
    return MongoService()


# Test functions
@pytest.mark.asyncio
async def test_connect_success(mongo_service: MongoService, mock_mongo_client: AsyncMock) -> None:
    """Test successful MongoDB connection."""
    with patch("nightscout_backup_bot.services.mongo_service.AsyncIOMotorClient", return_value=mock_mongo_client):
        await mongo_service.connect()
        assert mongo_service.client is not None
        assert mongo_service.db is not None
        mock_mongo_client.admin.command.assert_called_once_with("ping")


@pytest.mark.asyncio
async def test_connect_failure(mongo_service: MongoService) -> None:
    """Test MongoDB connection failure."""
    with patch(
        "nightscout_backup_bot.services.mongo_service.AsyncIOMotorClient",
        side_effect=Exception("Connection failed"),
    ):
        with pytest.raises(Exception, match="Connection failed"):
            await mongo_service.connect()


@pytest.mark.asyncio
async def test_disconnect(mongo_service: MongoService, mock_mongo_client: AsyncMock) -> None:
    """Test MongoDB disconnection."""
    mongo_service.client = mock_mongo_client
    await mongo_service.disconnect()
    mock_mongo_client.close.assert_called_once()


@pytest.mark.asyncio
async def test_export_all_collections(
    mongo_service: MongoService, mock_mongo_database: AsyncMock, sample_mongo_data: dict[str, Any]
) -> None:
    """Test exporting all collections."""
    mongo_service.db = mock_mongo_database

    from typing import cast

    async def mock_to_list(length: int | None = None) -> list[dict[str, Any]]:
        return cast(list[dict[str, Any]], sample_mongo_data["collections"]["entries"])

    cursor = MagicMock()
    cursor.to_list = mock_to_list

    collection = MagicMock()
    collection.find.return_value = cursor

    mock_mongo_database.__getitem__.return_value = collection

    result = await mongo_service.export_collections()

    assert "metadata" in result
    assert "collections" in result
    assert result["metadata"]["collections_count"] == 3
    mock_mongo_database.list_collection_names.assert_called_once()


@pytest.mark.asyncio
async def test_export_specific_collections(mongo_service: MongoService, mock_mongo_database: AsyncMock) -> None:
    """Test exporting specific collections."""
    mongo_service.db = mock_mongo_database

    async def mock_to_list(length: int | None = None) -> list[dict[str, Any]]:
        return [{"_id": "1"}]

    cursor = MagicMock()
    cursor.to_list = mock_to_list

    collection = MagicMock()
    collection.find.return_value = cursor

    mock_mongo_database.__getitem__.return_value = collection

    result = await mongo_service.export_collections(["entries"])

    assert result["metadata"]["collections_count"] == 1
    assert "entries" in result["collections"]


@pytest.mark.asyncio
async def test_export_not_connected(mongo_service: MongoService) -> None:
    """Test export when not connected."""
    with pytest.raises(ValueError, match="Not connected to MongoDB"):
        await mongo_service.export_collections()


def test_serialize_to_json(mongo_service: MongoService, sample_mongo_data: dict[str, Any]) -> None:
    """Test JSON serialization."""
    json_str = mongo_service.serialize_to_json(sample_mongo_data)
    assert isinstance(json_str, str)
    parsed = json.loads(json_str)
    assert parsed["metadata"]["database"] == "testdb"


@pytest.mark.asyncio
async def test_get_database_stats(mongo_service: MongoService, mock_mongo_database: AsyncMock) -> None:
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
async def test_get_database_stats_not_connected(mongo_service: MongoService) -> None:
    """Test stats when not connected."""
    with pytest.raises(ValueError, match="Not connected to MongoDB"):
        await mongo_service.get_database_stats()


@pytest.mark.asyncio
async def test_simulate_delete_many() -> None:
    service = MongoService()
    service.db = MagicMock()
    service.client = MagicMock()
    mock_collection = MagicMock()
    service.db.__getitem__.return_value = mock_collection

    class Transaction:
        async def __aenter__(self) -> "Transaction":
            return self

        async def __aexit__(self, exc_type: type | None, exc: Exception | None, tb: object | None) -> None:
            pass

    class MockSession:
        def start_transaction(self) -> Transaction:
            return Transaction()

        async def __aenter__(self) -> "MockSession":
            return self

        async def __aexit__(self, exc_type: type | None, exc: Exception | None, tb: object | None) -> None:
            pass

        async def abort_transaction(self) -> None:
            pass

        async def end_session(self) -> None:
            pass

    mock_session = MockSession()
    service.client.start_session = AsyncMock(return_value=mock_session)
    mock_collection.delete_many = AsyncMock(return_value=MagicMock(deleted_count=5))
    count = await service.simulate_delete_many("foo", {"bar": 1})
    assert count == 5


@pytest.mark.asyncio
async def test_simulate_delete_many_not_connected() -> None:
    service = MongoService()
    service.db = None
    service.client = None
    with pytest.raises(ValueError):
        await service.simulate_delete_many("foo", {})
