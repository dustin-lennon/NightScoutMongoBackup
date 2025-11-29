"""Unit tests for MongoService.

Note: This test file uses mocks which are inherently dynamically typed (Any).
This is acceptable in test files.
"""

# pyright: reportGeneralTypeIssues=false

import json
from typing import cast
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from nightscout_backup_bot.services.mongo_service import (
    CONNECTION_TIMEOUT_MS,
    MAX_RETRY_ATTEMPTS,
    RETRY_BASE_DELAY,
    SERVER_SELECTION_TIMEOUT_MS,
    MongoService,
)


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
        mock_mongo_client.admin.command.assert_called_once_with("ping")  # type: ignore[attr-defined, misc]


def test_connection_constants() -> None:
    """Test that connection timeout constants are set correctly."""
    assert CONNECTION_TIMEOUT_MS == 30000
    assert SERVER_SELECTION_TIMEOUT_MS == 30000
    assert MAX_RETRY_ATTEMPTS == 3
    assert RETRY_BASE_DELAY == 2


@pytest.mark.asyncio
async def test_connect_failure_all_retries_exhausted(mongo_service: MongoService) -> None:
    """Test MongoDB connection failure after all retries are exhausted."""
    with patch("asyncio.sleep", new_callable=AsyncMock):  # Mock sleep to avoid delays
        with patch(
            "nightscout_backup_bot.services.mongo_service.AsyncIOMotorClient",
            side_effect=Exception("Connection failed"),
        ):
            with pytest.raises(ConnectionError, match="Failed to connect to MongoDB Atlas after"):
                await mongo_service.connect()


@pytest.mark.asyncio
async def test_connect_failure_dns_error(mongo_service: MongoService) -> None:
    """Test MongoDB connection failure with DNS error detection."""
    dns_error = Exception("The resolution lifetime expired after 5.402 seconds: Server Do53")
    with patch("asyncio.sleep", new_callable=AsyncMock):  # Mock sleep to avoid delays
        with patch(
            "nightscout_backup_bot.services.mongo_service.AsyncIOMotorClient",
            side_effect=dns_error,
        ):
            with pytest.raises(ConnectionError, match="DNS resolution failed"):
                await mongo_service.connect()


@pytest.mark.asyncio
async def test_connect_success_after_retries(mongo_service: MongoService, mock_mongo_client: AsyncMock) -> None:
    """Test successful MongoDB connection after initial failures."""
    # First two attempts fail during client initialization, third succeeds
    call_count = 0

    def client_factory(*args: object, **kwargs: object) -> AsyncMock | Exception:
        nonlocal call_count
        call_count += 1
        if call_count <= 2:
            raise Exception("Temporary connection error")
        return mock_mongo_client

    with patch("asyncio.sleep", new_callable=AsyncMock):  # Mock sleep to avoid delays
        with patch("nightscout_backup_bot.services.mongo_service.AsyncIOMotorClient", side_effect=client_factory):
            await mongo_service.connect()
            assert mongo_service.client is not None
            assert mongo_service.db is not None
            mock_mongo_client.admin.command.assert_called_once_with("ping")  # type: ignore[attr-defined, misc]


@pytest.mark.asyncio
async def test_connect_retry_with_exponential_backoff(mongo_service: MongoService) -> None:
    """Test that retries use exponential backoff delays."""
    sleep_calls: list[float] = []

    async def mock_sleep(delay: float) -> None:
        sleep_calls.append(delay)

    with patch("asyncio.sleep", side_effect=mock_sleep):
        with patch(
            "nightscout_backup_bot.services.mongo_service.AsyncIOMotorClient",
            side_effect=Exception("Connection failed"),
        ):
            with pytest.raises(ConnectionError):
                await mongo_service.connect()

    # Should have slept 2 times (between attempts 1-2 and 2-3)
    # First delay: 2 * (2^0) = 2 seconds
    # Second delay: 2 * (2^1) = 4 seconds
    assert len(sleep_calls) == 2
    assert sleep_calls[0] == 2.0  # First retry delay (attempt 1 -> 2)
    assert sleep_calls[1] == 4.0  # Second retry delay (attempt 2 -> 3)


def test_is_dns_error(mongo_service: MongoService) -> None:
    """Test DNS error detection."""
    # Test various DNS error messages
    assert mongo_service._is_dns_error("The resolution lifetime expired after 5.402 seconds")
    assert mongo_service._is_dns_error("DNS operation timed out")
    assert mongo_service._is_dns_error("[Errno 65] No route to host")
    assert mongo_service._is_dns_error("Name resolution failed")
    assert mongo_service._is_dns_error("getaddrinfo failed")

    # Test case insensitivity
    assert mongo_service._is_dns_error("DNS OPERATION TIMED OUT")
    assert mongo_service._is_dns_error("dns operation timed out")

    # Test non-DNS errors
    assert not mongo_service._is_dns_error("Authentication failed")
    assert not mongo_service._is_dns_error("Connection timeout")
    assert not mongo_service._is_dns_error("Invalid credentials")


def test_format_connection_error(mongo_service: MongoService) -> None:
    """Test connection error formatting."""
    # Test DNS error formatting
    dns_error = Exception("The resolution lifetime expired")
    error_msg = mongo_service._format_connection_error(dns_error, attempt=1, max_attempts=3)
    assert "DNS resolution failed" in error_msg
    assert "attempt 1/3" in error_msg
    assert "Suggestions:" in error_msg
    assert "Check your network connection" in error_msg

    # Test non-DNS error formatting
    regular_error = Exception("Authentication failed")
    error_msg = mongo_service._format_connection_error(regular_error, attempt=2, max_attempts=3)
    assert "Failed to connect to MongoDB" in error_msg
    assert "attempt 2/3" in error_msg
    assert "Authentication failed" in error_msg


@pytest.mark.asyncio
async def test_disconnect(mongo_service: MongoService, mock_mongo_client: AsyncMock) -> None:
    """Test MongoDB disconnection."""
    mongo_service.client = mock_mongo_client
    mongo_service.disconnect()
    mock_mongo_client.close.assert_called_once()


@pytest.mark.asyncio
async def test_export_all_collections(
    mongo_service: MongoService, mock_mongo_database: AsyncMock, sample_mongo_data: dict[str, object]
) -> None:
    """Test exporting all collections."""
    mongo_service.db = mock_mongo_database

    from typing import cast

    async def mock_to_list(**_kwargs: object) -> list[dict[str, object]]:
        collections = cast(dict[str, object], sample_mongo_data["collections"])
        entries = cast(list[dict[str, object]], collections["entries"])
        return entries

    cursor = MagicMock()
    cursor.to_list = mock_to_list

    collection = MagicMock()
    collection.find.return_value = cursor  # type: ignore[attr-defined, misc]

    mock_mongo_database.__getitem__.return_value = collection  # type: ignore[attr-defined, misc]

    result = await mongo_service.export_collections()

    assert "metadata" in result
    assert "collections" in result
    assert result["metadata"]["collections_count"] == 3
    mock_mongo_database.list_collection_names.assert_called_once()


@pytest.mark.asyncio
async def test_export_specific_collections(mongo_service: MongoService, mock_mongo_database: AsyncMock) -> None:
    """Test exporting specific collections."""
    mongo_service.db = mock_mongo_database

    async def mock_to_list(**_kwargs: object) -> list[dict[str, object]]:
        return [{"_id": "1"}]

    cursor = MagicMock()
    cursor.to_list = mock_to_list

    collection = MagicMock()
    collection.find.return_value = cursor  # type: ignore[attr-defined, misc]

    mock_mongo_database.__getitem__.return_value = collection  # type: ignore[attr-defined, misc]

    result = await mongo_service.export_collections(["entries"])

    assert result["metadata"]["collections_count"] == 1
    assert "entries" in result["collections"]


@pytest.mark.asyncio
async def test_export_not_connected(mongo_service: MongoService) -> None:
    """Test export when not connected."""
    with pytest.raises(ValueError, match="Not connected to MongoDB"):
        _ = await mongo_service.export_collections()


def test_serialize_to_json(mongo_service: MongoService, sample_mongo_data: dict[str, object]) -> None:
    """Test JSON serialization."""
    json_str = mongo_service.serialize_to_json(sample_mongo_data)
    assert isinstance(json_str, str)
    parsed = cast(dict[str, dict[str, object]], json.loads(json_str))
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
    mock_mongo_database.command.assert_called_once_with("dbStats")  # type: ignore[attr-defined, misc]


@pytest.mark.asyncio
async def test_get_database_stats_not_connected(mongo_service: MongoService) -> None:
    """Test stats when not connected."""
    with pytest.raises(ValueError, match="Not connected to MongoDB"):
        _ = await mongo_service.get_database_stats()


@pytest.mark.asyncio
async def test_simulate_delete_many() -> None:
    service = MongoService()
    service.db = MagicMock()
    service.client = MagicMock()
    mock_collection = MagicMock()
    service.db.__getitem__.return_value = mock_collection  # type: ignore[attr-defined, misc]

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
        _ = await service.simulate_delete_many("foo", {})
