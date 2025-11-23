import datetime
from unittest.mock import AsyncMock, MagicMock

import disnake
import pytest

from nightscout_backup_bot.cogs.admin.thread_management import ThreadManagement


class DummyThread:
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

    bot = MagicMock()
    cog = ThreadManagement(bot)
    inter = MagicMock()
    inter.response.defer = AsyncMock()
    inter.followup.send = AsyncMock()
    bot.get_channel.return_value = channel

    # Patch settings.backup_channel_id
    monkeypatch.setattr("nightscout_backup_bot.config.settings.backup_channel_id", "123")

    archived_count, deleted_count = await cog.manage_threads_impl(channel)  # type: ignore
    t1.edit.assert_awaited_once_with(archived=True, reason="Archiving backup thread after open 1 day or longer...")
    t2.edit.assert_not_awaited()
    t3.edit.assert_not_awaited()

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
    t1.edit.reset_mock()
    t1.delete.reset_mock()
    t2.edit.reset_mock()
    t2.delete.reset_mock()

    channel = DummyChannel([t1, t2])

    bot = MagicMock()
    cog = ThreadManagement(bot)
    inter = MagicMock()
    inter.response.defer = AsyncMock()
    inter.followup.send = AsyncMock()
    bot.get_channel.return_value = channel

    monkeypatch.setattr("nightscout_backup_bot.config.settings.backup_channel_id", "123")

    archived_count, deleted_count = await cog.manage_threads_impl(channel)  # type: ignore

    # t1: 9 days old, should only be deleted
    t1.edit.assert_not_awaited()
    t1.delete.assert_awaited_once_with(reason="Download link no longer exists.. removing thread")

    # t2: 5 days old, should only be archived
    t2.edit.assert_awaited_once_with(archived=True, reason="Archiving backup thread after open 1 day or longer...")
    t2.delete.assert_not_awaited()

    assert archived_count == 1
    assert deleted_count == 1
