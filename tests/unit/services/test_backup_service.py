from typing import cast
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from nightscout_backup_bot.services.backup_service import BackupService


@pytest.mark.asyncio
async def test_execute_backup_success() -> None:
    backup_service = BackupService()
    backup_service.mongo_service = AsyncMock()
    backup_service.s3_service = AsyncMock()
    backup_service.file_service = AsyncMock()
    backup_service.compression_service = AsyncMock()

    # Mock Discord channel and thread service
    mock_channel = MagicMock()
    mock_thread_service = AsyncMock()

    # Patch thread creation and progress
    with patch("nightscout_backup_bot.services.backup_service.DiscordThreadService", return_value=mock_thread_service):
        mock_thread = MagicMock()
        mock_thread_service.create_backup_thread.return_value = mock_thread
        mock_thread_service.send_progress = AsyncMock()
        mock_thread_service.send_completion = AsyncMock()
        mock_thread_service.send_error = AsyncMock()

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

        result = await backup_service.execute_backup(mock_channel)
        assert result["success"] is True
        assert "url" in result
        # Type ignore needed because result["stats"] is typed as object in the return type
        stats = cast(dict[str, str | int | float], result["stats"])  # type: ignore[arg-type]
        assert stats["collections"] == "5"
        assert stats["compression_method"] == "GZIP"


@pytest.mark.asyncio
async def test_execute_backup_failure() -> None:
    backup_service = BackupService()
    backup_service.mongo_service = AsyncMock()
    backup_service.s3_service = AsyncMock()
    backup_service.file_service = AsyncMock()
    backup_service.compression_service = AsyncMock()

    mock_channel = MagicMock()
    mock_thread_service = AsyncMock()

    with patch("nightscout_backup_bot.services.backup_service.DiscordThreadService", return_value=mock_thread_service):
        mock_thread = MagicMock()
        mock_thread_service.create_backup_thread.return_value = mock_thread
        mock_thread_service.send_progress = AsyncMock()
        mock_thread_service.send_error = AsyncMock()

        backup_service.mongo_service.connect.side_effect = Exception("Mongo error")
        backup_service.mongo_service.disconnect.return_value = None

        with pytest.raises(Exception):  # noqa: B017
            _ = await backup_service.execute_backup(mock_channel)
        mock_thread_service.send_error.assert_called()
