"""Tests for DiscordThreadService."""

from unittest.mock import AsyncMock, MagicMock

import disnake
import pytest

from nightscout_backup_bot.services.discord_thread_service import DiscordThreadService


@pytest.fixture
def mock_channel() -> MagicMock:
    """Create a mock Discord text channel."""
    channel = MagicMock(spec=disnake.TextChannel)
    channel.threads = []
    return channel


@pytest.fixture
def mock_thread() -> MagicMock:
    """Create a mock Discord thread."""
    thread = MagicMock(spec=disnake.Thread)
    thread.id = 123456789
    thread.name = "MongoDB Backup - 2024-01-15"
    thread.send = AsyncMock()
    return thread


class TestDiscordThreadService:
    """Test cases for DiscordThreadService."""

    def test_init(self, mock_channel: MagicMock) -> None:
        """Test DiscordThreadService initialization."""
        service = DiscordThreadService(mock_channel)
        assert service.channel == mock_channel

    @pytest.mark.asyncio
    async def test_create_backup_thread_new(self, mock_channel: MagicMock, mock_thread: MagicMock) -> None:
        """Test creating a new backup thread."""
        mock_channel.threads = []
        mock_channel.create_thread = AsyncMock(return_value=mock_thread)

        service = DiscordThreadService(mock_channel)
        result = await service.create_backup_thread("2024-01-15")

        assert result == mock_thread
        mock_channel.create_thread.assert_called_once()
        call_kwargs = mock_channel.create_thread.call_args[1]
        assert call_kwargs["name"] == "MongoDB Backup - 2024-01-15"
        assert call_kwargs["type"] == disnake.ChannelType.private_thread
        assert call_kwargs["auto_archive_duration"] == 10080
        assert call_kwargs["invitable"] is False

    @pytest.mark.asyncio
    async def test_create_backup_thread_reuse_existing(self, mock_channel: MagicMock, mock_thread: MagicMock) -> None:
        """Test reusing an existing backup thread."""
        mock_channel.threads = [mock_thread]

        service = DiscordThreadService(mock_channel)
        result = await service.create_backup_thread("2024-01-15")

        assert result == mock_thread
        mock_channel.create_thread.assert_not_called()

    @pytest.mark.asyncio
    async def test_create_backup_thread_error(self, mock_channel: MagicMock) -> None:
        """Test error handling when creating thread fails."""
        mock_channel.threads = []
        mock_channel.create_thread = AsyncMock(side_effect=Exception("Discord API error"))

        service = DiscordThreadService(mock_channel)

        with pytest.raises(Exception, match="Discord API error"):
            await service.create_backup_thread("2024-01-15")

    @pytest.mark.asyncio
    async def test_send_progress_success(self, mock_thread: MagicMock) -> None:
        """Test sending progress message successfully."""
        mock_message = MagicMock()
        mock_thread.send = AsyncMock(return_value=mock_message)

        result = await DiscordThreadService.send_progress(mock_thread, "Backup in progress...", step="dumping")

        assert result == mock_message
        mock_thread.send.assert_called_once_with("Backup in progress...")

    @pytest.mark.asyncio
    async def test_send_progress_error(self, mock_thread: MagicMock) -> None:
        """Test error handling when sending progress fails."""
        mock_thread.send = AsyncMock(side_effect=Exception("Send failed"))

        with pytest.raises(Exception, match="Send failed"):
            await DiscordThreadService.send_progress(mock_thread, "Backup in progress...")

    @pytest.mark.asyncio
    async def test_send_error_success(self, mock_thread: MagicMock) -> None:
        """Test sending error message successfully."""
        mock_message = MagicMock()
        mock_thread.send = AsyncMock(return_value=mock_message)

        result = await DiscordThreadService.send_error(mock_thread, "Backup failed")

        assert result == mock_message
        mock_thread.send.assert_called_once()
        call_args = mock_thread.send.call_args[0][0]
        assert "❌ **Error:** Backup failed" in call_args

    @pytest.mark.asyncio
    async def test_send_error_failure(self, mock_thread: MagicMock) -> None:
        """Test error handling when sending error message fails."""
        mock_thread.send = AsyncMock(side_effect=Exception("Send failed"))

        with pytest.raises(Exception, match="Send failed"):
            await DiscordThreadService.send_error(mock_thread, "Backup failed")

    @pytest.mark.asyncio
    async def test_send_completion_success(self, mock_thread: MagicMock) -> None:
        """Test sending completion message successfully."""
        mock_message = MagicMock()
        mock_thread.send = AsyncMock(return_value=mock_message)

        stats = {
            "collections": 5,
            "documents": 1000,
            "original_size": "10MB",
            "compressed_size": "2MB",
            "compression_ratio": "80%",
            "compression_method": "gzip",
        }

        result = await DiscordThreadService.send_completion(mock_thread, "https://example.com/backup.tar.gz", stats)

        assert result == mock_message
        mock_thread.send.assert_called_once()
        call_args = mock_thread.send.call_args
        assert "embed" in call_args.kwargs
        embed = call_args.kwargs["embed"]
        assert isinstance(embed, disnake.Embed)
        assert embed.title == "✅ Backup Complete"
        assert embed.color == disnake.Color.green()

    @pytest.mark.asyncio
    async def test_send_completion_with_missing_stats(self, mock_thread: MagicMock) -> None:
        """Test sending completion message with missing stats fields."""
        mock_message = MagicMock()
        mock_thread.send = AsyncMock(return_value=mock_message)

        stats = {
            "collections": 5,
            # Missing other fields
        }

        result = await DiscordThreadService.send_completion(mock_thread, "https://example.com/backup.tar.gz", stats)

        assert result == mock_message
        mock_thread.send.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_completion_error(self, mock_thread: MagicMock) -> None:
        """Test error handling when sending completion message fails."""
        mock_thread.send = AsyncMock(side_effect=Exception("Send failed"))

        stats = {
            "collections": 5,
            "documents": 1000,
            "original_size": "10MB",
            "compressed_size": "2MB",
            "compression_ratio": "80%",
            "compression_method": "gzip",
        }

        with pytest.raises(Exception, match="Send failed"):
            await DiscordThreadService.send_completion(mock_thread, "https://example.com/backup.tar.gz", stats)
