"""Tests for backup service API methods."""

from typing import cast
from unittest.mock import AsyncMock

import pytest

from nightscout_backup_bot.services.backup_service import BackupService


@pytest.mark.asyncio
async def test_execute_backup_api_success() -> None:
    """Test execute_backup_api with successful backup."""
    backup_service = BackupService()
    backup_service.mongo_service = AsyncMock()
    backup_service.s3_service = AsyncMock()
    backup_service.file_service = AsyncMock()
    backup_service.compression_service = AsyncMock()

    # Mock mongo dump
    backup_service.mongo_service.connect.return_value = None
    backup_service.mongo_service.dump_database.return_value = {
        "collections": 5,
        "original_size": "10MB",
        "compressed_size": "2MB",
        "archive_path": "backups/dexcom_20251109.tar.gz",
        "compression_method": "gzip",
    }
    backup_service.s3_service.upload_file.return_value = "https://s3-url"
    backup_service.file_service.delete_file.return_value = None
    backup_service.mongo_service.disconnect.return_value = None

    result = await backup_service.execute_backup_api()
    assert result["success"] is True
    assert result["url"] == "https://s3-url"
    # Type ignore needed because result["stats"] is typed as object in the return type
    stats = cast(dict[str, str | int | float], result["stats"])  # type: ignore[arg-type]
    assert stats["collections"] == "5"
    assert stats["compression_method"] == "GZIP"
    assert "thread_id" not in result  # API version doesn't include thread_id


@pytest.mark.asyncio
async def test_execute_backup_api_failure() -> None:
    """Test execute_backup_api with failure."""
    backup_service = BackupService()
    backup_service.mongo_service = AsyncMock()
    backup_service.mongo_service.connect.side_effect = Exception("Mongo error")
    backup_service.mongo_service.disconnect.return_value = None

    with pytest.raises(Exception, match="Mongo error"):  # noqa: B017
        _ = await backup_service.execute_backup_api()


@pytest.mark.asyncio
async def test_execute_backup_core_without_callback() -> None:
    """Test _execute_backup_core without progress callback."""
    backup_service = BackupService()
    backup_service.mongo_service = AsyncMock()
    backup_service.s3_service = AsyncMock()
    backup_service.file_service = AsyncMock()

    backup_service.mongo_service.connect.return_value = None
    backup_service.mongo_service.dump_database.return_value = {
        "collections": 3,
        "original_size": "5MB",
        "compressed_size": "1MB",
        "archive_path": "backups/test.tar.gz",
        "compression_method": "brotli",
    }
    backup_service.s3_service.upload_file.return_value = "https://s3-test-url"
    backup_service.file_service.delete_file.return_value = None
    backup_service.mongo_service.disconnect.return_value = None

    download_url, stats = await backup_service._execute_backup_core()  # type: ignore[attr-defined]  # noqa: SLF001

    assert download_url == "https://s3-test-url"
    assert stats["collections"] == "3"
    assert stats["compression_method"] == "BROTLI"
    assert stats["original_size"] == "5MB"
    assert stats["compressed_size"] == "1MB"


@pytest.mark.asyncio
async def test_execute_backup_core_with_callback() -> None:
    """Test _execute_backup_core with progress callback."""
    backup_service = BackupService()
    backup_service.mongo_service = AsyncMock()
    backup_service.s3_service = AsyncMock()
    backup_service.file_service = AsyncMock()

    backup_service.mongo_service.connect.return_value = None
    backup_service.mongo_service.dump_database.return_value = {
        "collections": 2,
        "original_size": "3MB",
        "compressed_size": "0.5MB",
        "archive_path": "backups/test2.tar.gz",
        "compression_method": "gzip",
    }
    backup_service.s3_service.upload_file.return_value = "https://s3-callback-url"
    backup_service.file_service.delete_file.return_value = None
    backup_service.mongo_service.disconnect.return_value = None

    progress_messages: list[str] = []

    async def on_progress(message: str) -> None:
        progress_messages.append(message)

    download_url, _stats = await backup_service._execute_backup_core(on_progress=on_progress)  # type: ignore[attr-defined]  # noqa: SLF001

    assert download_url == "https://s3-callback-url"
    assert len(progress_messages) > 0
    assert "🔄 Starting backup process..." in progress_messages
    assert "✅ Connected to MongoDB Atlas" in progress_messages
    assert "🔄 Dumping MongoDB database..." in progress_messages
    assert "✅ Uploaded to S3" in progress_messages
    assert "✅ Local files cleaned up" in progress_messages


@pytest.mark.asyncio
async def test_test_connections_both_success() -> None:
    """Test test_connections with both MongoDB and S3 succeeding."""
    backup_service = BackupService()
    backup_service.mongo_service = AsyncMock()
    backup_service.s3_service = AsyncMock()

    backup_service.mongo_service.connect.return_value = None
    backup_service.mongo_service.disconnect.return_value = None
    backup_service.s3_service.test_connection.return_value = True

    results = await backup_service.test_connections()

    assert results["mongodb"] is True
    assert results["s3"] is True
    backup_service.mongo_service.connect.assert_called_once()
    backup_service.mongo_service.disconnect.assert_called_once()
    backup_service.s3_service.test_connection.assert_called_once()


@pytest.mark.asyncio
async def test_test_connections_mongodb_fails() -> None:
    """Test test_connections with MongoDB connection failure."""
    backup_service = BackupService()
    backup_service.mongo_service = AsyncMock()
    backup_service.s3_service = AsyncMock()

    backup_service.mongo_service.connect.side_effect = Exception("MongoDB connection error")
    backup_service.mongo_service.disconnect.return_value = None
    backup_service.s3_service.test_connection.return_value = True

    results = await backup_service.test_connections()

    assert results["mongodb"] is False
    assert results["s3"] is True
    backup_service.mongo_service.connect.assert_called_once()
    backup_service.s3_service.test_connection.assert_called_once()


@pytest.mark.asyncio
async def test_test_connections_s3_fails() -> None:
    """Test test_connections with S3 connection failure."""
    backup_service = BackupService()
    backup_service.mongo_service = AsyncMock()
    backup_service.s3_service = AsyncMock()

    backup_service.mongo_service.connect.return_value = None
    backup_service.mongo_service.disconnect.return_value = None
    backup_service.s3_service.test_connection.side_effect = Exception("S3 connection error")

    results = await backup_service.test_connections()

    assert results["mongodb"] is True
    assert results["s3"] is False
    backup_service.mongo_service.connect.assert_called_once()
    backup_service.mongo_service.disconnect.assert_called_once()
    backup_service.s3_service.test_connection.assert_called_once()


@pytest.mark.asyncio
async def test_test_connections_both_fail() -> None:
    """Test test_connections with both MongoDB and S3 failing."""
    backup_service = BackupService()
    backup_service.mongo_service = AsyncMock()
    backup_service.s3_service = AsyncMock()

    backup_service.mongo_service.connect.side_effect = Exception("MongoDB connection error")
    backup_service.mongo_service.disconnect.return_value = None
    backup_service.s3_service.test_connection.side_effect = Exception("S3 connection error")

    results = await backup_service.test_connections()

    assert results["mongodb"] is False
    assert results["s3"] is False
    backup_service.mongo_service.connect.assert_called_once()
    backup_service.s3_service.test_connection.assert_called_once()


@pytest.mark.asyncio
async def test_test_connections_s3_returns_false() -> None:
    """Test test_connections when S3 test_connection returns False (not an exception)."""
    backup_service = BackupService()
    backup_service.mongo_service = AsyncMock()
    backup_service.s3_service = AsyncMock()

    backup_service.mongo_service.connect.return_value = None
    backup_service.mongo_service.disconnect.return_value = None
    backup_service.s3_service.test_connection.return_value = False

    results = await backup_service.test_connections()

    assert results["mongodb"] is True
    assert results["s3"] is False
    backup_service.mongo_service.connect.assert_called_once()
    backup_service.mongo_service.disconnect.assert_called_once()
    backup_service.s3_service.test_connection.assert_called_once()
