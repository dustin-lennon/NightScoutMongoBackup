from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from nightscout_backup_bot.services.mongo_service import MongoService


@pytest.mark.asyncio
async def test_connect_success() -> None:
    service = MongoService()
    mock_client = AsyncMock()
    mock_db = MagicMock()
    with patch("nightscout_backup_bot.services.mongo_service.AsyncIOMotorClient", return_value=mock_client):
        mock_client.__getitem__.return_value = mock_db
        mock_client.admin.command = AsyncMock(return_value={"ok": 1})
        await service.connect()
        assert service.client is mock_client
        assert service.db is mock_db


@pytest.mark.asyncio
async def test_connect_failure() -> None:
    service = MongoService()
    with patch("nightscout_backup_bot.services.mongo_service.AsyncIOMotorClient", side_effect=RuntimeError("fail")):
        with pytest.raises(RuntimeError):
            await service.connect()


@pytest.mark.asyncio
async def test_export_collections() -> None:
    service = MongoService()
    service.db = MagicMock()
    service.db.list_collection_names = AsyncMock(return_value=["foo"])
    mock_collection = MagicMock()
    mock_collection.find.return_value.to_list = AsyncMock(return_value=[{"_id": 1}])
    service.db.__getitem__.return_value = mock_collection
    result = await service.export_collections()
    assert "collections" in result
    assert "foo" in result["collections"]
    assert result["metadata"]["collections_count"] == 1


@pytest.mark.asyncio
async def test_export_collections_not_connected() -> None:
    service = MongoService()
    service.db = None
    with pytest.raises(ValueError):
        await service.export_collections()


@pytest.mark.asyncio
async def test_serialize_to_json() -> None:
    service = MongoService()
    data = {"foo": "bar"}
    result = service.serialize_to_json(data)
    assert "foo" in result
    assert isinstance(result, str)


@pytest.mark.asyncio
async def test_get_database_stats() -> None:
    service = MongoService()
    service.db = MagicMock()
    service.db.command = AsyncMock(return_value={"dbStats": True})
    result = await service.get_database_stats()
    assert result["dbStats"] is True


@pytest.mark.asyncio
async def test_get_database_stats_not_connected() -> None:
    service = MongoService()
    service.db = None
    with pytest.raises(ValueError):
        await service.get_database_stats()


@pytest.mark.asyncio
async def test_simulate_delete_many() -> None:
    service = MongoService()
    service.db = MagicMock()
    service.client = MagicMock()
    mock_collection = MagicMock()
    service.db.__getitem__.return_value = mock_collection

    # Setup async context manager for session
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


@pytest.mark.asyncio
async def test_disconnect() -> None:
    service = MongoService()
    service.client = MagicMock()
    await service.disconnect()
    # Should not raise
