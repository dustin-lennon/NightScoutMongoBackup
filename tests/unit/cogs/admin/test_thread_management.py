import datetime
from typing import cast
from unittest.mock import AsyncMock, MagicMock

import disnake
import pytest

from nightscout_backup_bot.bot import NightScoutBackupBot
from nightscout_backup_bot.cogs.admin.thread_management import ThreadManagement


class DummyThread:
    created_at: datetime.datetime
    archived: bool
    type: disnake.ChannelType
    id: int
    edit: AsyncMock
    delete: AsyncMock

    def __init__(
        self,
        created_at: datetime.datetime,
        archived: bool = False,
        thread_type: disnake.ChannelType = disnake.ChannelType.public_thread,
        thread_id: int | None = None,
    ):
        self.created_at = created_at
        self.archived = archived
        self.type = thread_type
        self.id = thread_id if thread_id is not None else id(self)  # Use object id as fallback
        self.edit = AsyncMock()
        self.delete = AsyncMock()


class DummyChannel:
    threads: list[DummyThread]
    id: int
    guild: None

    def __init__(self, threads: list[DummyThread], channel_id: int = 123):
        self.threads = threads
        self.id = channel_id
        self.guild = None  # None to skip archived thread fetching in tests


@pytest.mark.asyncio
async def test_archive_threads(monkeypatch: pytest.MonkeyPatch) -> None:
    now = datetime.datetime.now(datetime.UTC)

    # Thread 1: private, older than 1 day, not archived
    t1 = DummyThread(
        created_at=now - datetime.timedelta(days=2), archived=False, thread_type=disnake.ChannelType.private_thread
    )

    # Thread 2: private, less than 1 day, not archived
    t2 = DummyThread(
        created_at=now - datetime.timedelta(hours=12), archived=False, thread_type=disnake.ChannelType.private_thread
    )

    # Thread 3: private, older than 1 day, already archived
    t3 = DummyThread(
        created_at=now - datetime.timedelta(days=3), archived=True, thread_type=disnake.ChannelType.private_thread
    )

    channel = DummyChannel([t1, t2, t3])

    bot = MagicMock(spec=NightScoutBackupBot)
    cog = ThreadManagement(bot)

    bot.get_channel.return_value = channel  # type: ignore

    # Patch settings.backup_channel_id
    monkeypatch.setattr("nightscout_backup_bot.config.settings.backup_channel_id", "123")

    archived_count, deleted_count = await cog.manage_threads_impl(cast(disnake.TextChannel, cast(object, channel)))

    t1.edit.assert_awaited_once_with(archived=True, reason="Archiving backup thread after open 1 day or longer...")  # type: ignore[attr-defined]
    t2.edit.assert_not_awaited()  # type: ignore[attr-defined]
    t3.edit.assert_not_awaited()  # type: ignore[attr-defined]

    assert archived_count == 1
    assert deleted_count == 0


@pytest.mark.asyncio
async def test_delete_threads(monkeypatch: pytest.MonkeyPatch) -> None:
    now = datetime.datetime.now(datetime.UTC)
    # Thread 1: private, older than 8 days
    t1 = DummyThread(created_at=now - datetime.timedelta(days=9), thread_type=disnake.ChannelType.private_thread)

    # Thread 2: private, less than 8 days
    t2 = DummyThread(created_at=now - datetime.timedelta(days=5), thread_type=disnake.ChannelType.private_thread)

    # Ensure mocks are reset before assertions
    t1.edit.reset_mock()  # type: ignore[attr-defined]
    t1.delete.reset_mock()  # type: ignore[attr-defined]
    t2.edit.reset_mock()  # type: ignore[attr-defined]
    t2.delete.reset_mock()  # type: ignore[attr-defined]

    channel = DummyChannel([t1, t2])

    bot = MagicMock(spec=NightScoutBackupBot)
    cog = ThreadManagement(bot)

    bot.get_channel.return_value = channel  # type: ignore

    monkeypatch.setattr("nightscout_backup_bot.config.settings.backup_channel_id", "123")

    archived_count, deleted_count = await cog.manage_threads_impl(cast(disnake.TextChannel, cast(object, channel)))

    # t1: 9 days old, should only be deleted
    t1.edit.assert_not_awaited()  # type: ignore[attr-defined]
    t1.delete.assert_awaited_once_with(reason="Download link no longer exists.. removing thread")  # type: ignore[attr-defined]

    # t2: 5 days old, should only be archived
    t2.edit.assert_awaited_once_with(archived=True, reason="Archiving backup thread after open 1 day or longer...")  # type: ignore[attr-defined]
    t2.delete.assert_not_awaited()  # type: ignore[attr-defined]

    assert archived_count == 1
    assert deleted_count == 1


@pytest.mark.asyncio
async def test_manage_threads_command_success(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test the manage_threads slash command."""
    now = datetime.datetime.now(datetime.UTC)
    t1 = DummyThread(
        created_at=now - datetime.timedelta(days=2), archived=False, thread_type=disnake.ChannelType.private_thread
    )

    # Make channel a proper TextChannel instance
    mock_text_channel = MagicMock(spec=disnake.TextChannel)
    mock_text_channel.threads = [t1]
    mock_text_channel.id = 123

    bot = MagicMock(spec=NightScoutBackupBot)
    cog = ThreadManagement(bot)
    inter = MagicMock(spec=disnake.ApplicationCommandInteraction)

    inter.response = MagicMock()  # type: ignore[assignment]
    inter.response.defer = AsyncMock()  # type: ignore
    inter.followup = MagicMock()  # type: ignore[assignment]
    inter.followup.send = AsyncMock()  # type: ignore
    bot.get_channel.return_value = mock_text_channel  # type: ignore[attr-defined]

    monkeypatch.setattr("nightscout_backup_bot.config.settings.backup_channel_id", "123")

    # Call via callback to properly invoke the slash command
    await cog.manage_threads.callback(cog, inter)  # type: ignore

    inter.response.defer.assert_called_once()  # type: ignore[attr-defined]
    inter.followup.send.assert_called_once()  # type: ignore[attr-defined]
    call_args = inter.followup.send.call_args[0][0]  # type: ignore[attr-defined]

    assert "Thread management complete" in call_args
    assert "Archived threads: 1" in call_args
    assert "Deleted threads: 0" in call_args


@pytest.mark.asyncio
async def test_manage_threads_channel_not_found(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test manage_threads when channel is not found."""
    bot = MagicMock(spec=NightScoutBackupBot)
    cog = ThreadManagement(bot)

    inter = MagicMock(spec=disnake.ApplicationCommandInteraction)
    inter.response = MagicMock()  # type: ignore[assignment]
    inter.response.defer = AsyncMock()  # type: ignore
    inter.followup = MagicMock()  # type: ignore[assignment]
    inter.followup.send = AsyncMock()  # type: ignore
    bot.get_channel.return_value = None  # type: ignore[attr-defined]

    monkeypatch.setattr("nightscout_backup_bot.config.settings.backup_channel_id", "123")

    # Call via callback to properly invoke the slash command
    await cog.manage_threads.callback(cog, inter)  # type: ignore

    inter.followup.send.assert_called_once()  # type: ignore[attr-defined]
    call_args = inter.followup.send.call_args[0][0]  # type: ignore[attr-defined]
    assert "Backup channel not found" in call_args


@pytest.mark.asyncio
async def test_manage_threads_not_text_channel(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test manage_threads when channel is not a text channel."""
    bot = MagicMock(spec=NightScoutBackupBot)
    cog = ThreadManagement(bot)
    inter = MagicMock(spec=disnake.ApplicationCommandInteraction)

    inter.response = MagicMock()  # type: ignore[assignment]
    inter.response.defer = AsyncMock()  # type: ignore
    inter.followup = MagicMock()  # type: ignore[assignment]
    inter.followup.send = AsyncMock()  # type: ignore

    # Return a non-text channel (e.g., voice channel)
    mock_voice_channel = MagicMock()
    bot.get_channel.return_value = mock_voice_channel  # type: ignore[attr-defined]

    monkeypatch.setattr("nightscout_backup_bot.config.settings.backup_channel_id", "123")

    # Call via callback to properly invoke the slash command
    await cog.manage_threads.callback(cog, inter)  # type: ignore

    inter.followup.send.assert_called_once()  # type: ignore[attr-defined]
    call_args = inter.followup.send.call_args[0][0]  # type: ignore[attr-defined]

    assert "not a text channel" in call_args


@pytest.mark.asyncio
async def test_manage_threads_skips_public_threads(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that public threads are skipped."""
    now = datetime.datetime.now(datetime.UTC)

    # Public thread older than 1 day - should be skipped
    t1 = DummyThread(
        created_at=now - datetime.timedelta(days=2), archived=False, thread_type=disnake.ChannelType.public_thread
    )

    channel = DummyChannel([t1])
    bot = MagicMock(spec=NightScoutBackupBot)
    cog = ThreadManagement(bot)

    monkeypatch.setattr("nightscout_backup_bot.config.settings.backup_channel_id", "123")

    archived_count, deleted_count = await cog.manage_threads_impl(cast(disnake.TextChannel, cast(object, channel)))

    t1.edit.assert_not_awaited()  # type: ignore[attr-defined]
    t1.delete.assert_not_awaited()  # type: ignore[attr-defined]

    assert archived_count == 0
    assert deleted_count == 0


@pytest.mark.asyncio
async def test_manage_threads_deduplicates_threads(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that duplicate threads are deduplicated."""
    now = datetime.datetime.now(datetime.UTC)

    t1 = DummyThread(
        created_at=now - datetime.timedelta(days=2),
        archived=False,
        thread_type=disnake.ChannelType.private_thread,
        thread_id=123,
    )

    # Same thread in both active and archived lists
    channel = DummyChannel([t1])
    bot = MagicMock(spec=NightScoutBackupBot)
    cog = ThreadManagement(bot)

    monkeypatch.setattr("nightscout_backup_bot.config.settings.backup_channel_id", "123")

    archived_count, deleted_count = await cog.manage_threads_impl(cast(disnake.TextChannel, cast(object, channel)))

    # Should only archive once, not twice
    t1.edit.assert_called_once()  # type: ignore[attr-defined]

    assert archived_count == 1
    assert deleted_count == 0


@pytest.mark.asyncio
async def test_manage_threads_exactly_one_day(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test threads exactly one day old are archived."""
    now = datetime.datetime.now(datetime.UTC)

    # Thread exactly 1 day old
    t1 = DummyThread(
        created_at=now - datetime.timedelta(days=1), archived=False, thread_type=disnake.ChannelType.private_thread
    )

    channel = DummyChannel([t1])
    bot = MagicMock(spec=NightScoutBackupBot)
    cog = ThreadManagement(bot)

    monkeypatch.setattr("nightscout_backup_bot.config.settings.backup_channel_id", "123")

    archived_count, deleted_count = await cog.manage_threads_impl(cast(disnake.TextChannel, cast(object, channel)))

    t1.edit.assert_awaited_once_with(archived=True, reason="Archiving backup thread after open 1 day or longer...")  # type: ignore[attr-defined]

    assert archived_count == 1
    assert deleted_count == 0


@pytest.mark.asyncio
async def test_manage_threads_exactly_eight_days(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test threads exactly 8 days old are deleted."""
    now = datetime.datetime.now(datetime.UTC)

    # Thread exactly 8 days old
    t1 = DummyThread(
        created_at=now - datetime.timedelta(days=8), archived=False, thread_type=disnake.ChannelType.private_thread
    )

    channel = DummyChannel([t1])
    bot = MagicMock(spec=NightScoutBackupBot)
    cog = ThreadManagement(bot)

    monkeypatch.setattr("nightscout_backup_bot.config.settings.backup_channel_id", "123")

    archived_count, deleted_count = await cog.manage_threads_impl(cast(disnake.TextChannel, cast(object, channel)))

    t1.delete.assert_awaited_once_with(reason="Download link no longer exists.. removing thread")  # type: ignore[attr-defined]
    t1.edit.assert_not_awaited()  # type: ignore[attr-defined]

    assert archived_count == 0
    assert deleted_count == 1


@pytest.mark.asyncio
async def test_delete_archived_thread_unarchives_first(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that archived threads are unarchived before deletion."""
    now = datetime.datetime.now(datetime.UTC)

    # Thread 9 days old and already archived
    t1 = DummyThread(
        created_at=now - datetime.timedelta(days=9),
        archived=True,
        thread_type=disnake.ChannelType.private_thread,
    )

    channel = DummyChannel([t1])
    bot = MagicMock(spec=NightScoutBackupBot)
    cog = ThreadManagement(bot)

    monkeypatch.setattr("nightscout_backup_bot.config.settings.backup_channel_id", "123")

    archived_count, deleted_count = await cog.manage_threads_impl(cast(disnake.TextChannel, cast(object, channel)))

    # Should unarchive first, then delete
    t1.edit.assert_awaited_once_with(archived=False, reason="Unarchiving thread before deletion...")  # type: ignore[attr-defined]
    t1.delete.assert_awaited_once_with(reason="Download link no longer exists.. removing thread")  # type: ignore[attr-defined]

    assert archived_count == 0
    assert deleted_count == 1
