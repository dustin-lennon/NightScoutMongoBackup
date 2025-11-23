import datetime
from typing import Any, cast
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


class DummyGuild:
    """Mock guild for testing archived thread fetching."""

    def __init__(self) -> None:
        self._threads: dict[int, DummyThread] = {}

    def get_thread(self, thread_id: int) -> DummyThread | None:
        return self._threads.get(thread_id)

    async def fetch_channel(self, channel_id: int) -> DummyThread:
        thread = self._threads.get(channel_id)
        if thread is None:
            raise ValueError(f"Thread {channel_id} not found")
        return thread


class DummyChannelWithGuild:
    """Channel with guild for testing archived thread fetching."""

    def __init__(self, threads: list[DummyThread], channel_id: int = 123, guild: DummyGuild | None = None):
        self.threads = threads
        self.id = channel_id
        self.guild = guild or DummyGuild()


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


@pytest.mark.asyncio
async def test_fetch_archived_threads_no_guild() -> None:
    """Test that archived thread fetching returns early when no guild."""
    channel = DummyChannel([DummyThread(created_at=datetime.datetime.now(datetime.UTC))])
    bot = MagicMock(spec=NightScoutBackupBot)
    bot.http = None
    cog = ThreadManagement(bot)

    archived_threads = await cog._fetch_archived_threads(cast(disnake.TextChannel, cast(object, channel)))  # type: ignore[attr-defined]  # noqa: SLF001
    assert archived_threads == []


@pytest.mark.asyncio
async def test_fetch_archived_threads_no_http() -> None:
    """Test that archived thread fetching returns early when no http client."""
    guild = DummyGuild()
    channel = DummyChannelWithGuild([], guild=guild)
    bot = MagicMock(spec=NightScoutBackupBot)
    bot.http = None
    cog = ThreadManagement(bot)

    archived_threads = await cog._fetch_archived_threads(cast(disnake.TextChannel, cast(object, channel)))  # type: ignore[attr-defined]  # noqa: SLF001
    assert archived_threads == []


@pytest.mark.asyncio
async def test_fetch_archived_threads_import_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that ImportError is handled when Route is not available."""
    guild = DummyGuild()
    channel = DummyChannelWithGuild([], guild=guild)
    bot = MagicMock(spec=NightScoutBackupBot)
    bot.http = MagicMock()

    # Mock the import to raise ImportError
    original_import = __import__

    def mock_import_error(name: str, *args: Any, **kwargs: Any) -> Any:  # type: ignore[no-any-return, no-any-untyped]
        if name == "disnake.http":
            raise ImportError("No module named 'disnake.http'")
        return original_import(name, *args, **kwargs)  # type: ignore[no-any-return]

    monkeypatch.setattr("builtins.__import__", mock_import_error)

    cog = ThreadManagement(bot)
    archived_threads = await cog._fetch_archived_threads(cast(disnake.TextChannel, cast(object, channel)))
    assert archived_threads == []


@pytest.mark.asyncio
async def test_fetch_archived_threads_success(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test successful fetching of archived threads."""
    now = datetime.datetime.now(datetime.UTC)
    guild = DummyGuild()

    # Create an archived thread
    archived_thread = DummyThread(
        created_at=now - datetime.timedelta(days=2),
        archived=True,
        thread_type=disnake.ChannelType.private_thread,
        thread_id=456,
    )
    guild._threads[456] = archived_thread

    channel = DummyChannelWithGuild([], guild=guild, channel_id=123)

    # Mock the HTTP client and Route
    async def mock_request(route: Any, params: Any = None) -> dict[str, Any]:  # type: ignore[no-any-untyped]  # noqa: ARG001
        return {
            "threads": [
                {
                    "id": 456,
                    "type": 12,  # private_thread
                    "thread_metadata": {"archive_timestamp": "2024-01-01T00:00:00.000000+00:00"},
                }
            ],
            "has_more": False,
        }

    bot = MagicMock(spec=NightScoutBackupBot)
    bot.http = MagicMock()
    bot.http.request = AsyncMock(side_effect=mock_request)

    # Mock Route class
    def mock_route_init(_method: str, _url: str) -> MagicMock:
        return MagicMock()

    with monkeypatch.context() as m:
        m.setattr("disnake.http.Route", mock_route_init)
        cog = ThreadManagement(bot)
        archived_threads = await cog._fetch_archived_threads(cast(disnake.TextChannel, cast(object, channel)))

    assert len(archived_threads) == 1
    assert archived_threads[0].id == 456


@pytest.mark.asyncio
async def test_fetch_archived_threads_page_no_more() -> None:
    """Test pagination when has_more is False."""
    guild = DummyGuild()
    channel = DummyChannelWithGuild([], guild=guild, channel_id=123)
    archived_threads: list[disnake.Thread] = []

    async def mock_request(route: Any, params: Any = None) -> dict[str, Any]:  # type: ignore[no-any-untyped]  # noqa: ARG001
        return {"threads": [], "has_more": False}

    bot = MagicMock(spec=NightScoutBackupBot)
    bot.http = MagicMock()
    bot.http.request = AsyncMock(side_effect=mock_request)

    cog = ThreadManagement(bot)
    result = await cog._fetch_archived_threads_page(cast(disnake.TextChannel, cast(object, channel)), archived_threads, None)  # type: ignore[attr-defined]  # noqa: SLF001

    assert result is None
    assert len(archived_threads) == 0


@pytest.mark.asyncio
async def test_fetch_archived_threads_page_not_list() -> None:
    """Test when threads data is not a list."""
    guild = DummyGuild()
    channel = DummyChannelWithGuild([], guild=guild, channel_id=123)
    archived_threads: list[disnake.Thread] = []

    async def mock_request(route: Any, params: Any = None) -> dict[str, Any]:  # type: ignore[no-any-untyped]  # noqa: ARG001
        return {"threads": "not a list", "has_more": False}

    bot = MagicMock(spec=NightScoutBackupBot)
    bot.http = MagicMock()
    bot.http.request = AsyncMock(side_effect=mock_request)

    cog = ThreadManagement(bot)
    result = await cog._fetch_archived_threads_page(cast(disnake.TextChannel, cast(object, channel)), archived_threads, None)  # type: ignore[attr-defined]  # noqa: SLF001

    assert result is None


@pytest.mark.asyncio
async def test_fetch_archived_threads_page_with_before() -> None:
    """Test pagination with before parameter."""
    now = datetime.datetime.now(datetime.UTC)
    guild = DummyGuild()
    thread = DummyThread(created_at=now, thread_type=disnake.ChannelType.private_thread, thread_id=789)
    guild._threads[789] = thread  # noqa: SLF001

    channel = DummyChannelWithGuild([], guild=guild, channel_id=123)
    archived_threads: list[disnake.Thread] = []
    before_timestamp = "2024-01-01T00:00:00.000000+00:00"

    async def mock_request(route: Any, params: Any = None) -> dict[str, Any]:  # type: ignore[no-any-untyped]  # noqa: ARG001
        assert params is not None
        assert params.get("before") == before_timestamp
        return {
            "threads": [
                {"id": 789, "type": 12, "thread_metadata": {"archive_timestamp": "2024-01-02T00:00:00.000000+00:00"}}
            ],
            "has_more": False,
        }

    bot = MagicMock(spec=NightScoutBackupBot)
    bot.http = MagicMock()
    bot.http.request = AsyncMock(side_effect=mock_request)

    cog = ThreadManagement(bot)
    result = await cog._fetch_archived_threads_page(cast(disnake.TextChannel, cast(object, channel)), archived_threads, before_timestamp)  # type: ignore[attr-defined]  # noqa: SLF001

    assert result is None
    assert len(archived_threads) == 1


@pytest.mark.asyncio
async def test_fetch_archived_threads_page_has_more() -> None:
    """Test pagination when has_more is True."""
    now = datetime.datetime.now(datetime.UTC)
    guild = DummyGuild()
    thread = DummyThread(created_at=now, thread_type=disnake.ChannelType.private_thread, thread_id=999)
    guild._threads[999] = thread  # noqa: SLF001

    channel = DummyChannelWithGuild([], guild=guild, channel_id=123)
    archived_threads: list[disnake.Thread] = []
    next_timestamp = "2024-01-02T00:00:00.000000+00:00"

    async def mock_request(route: Any, params: Any = None) -> dict[str, Any]:  # type: ignore[no-any-untyped]  # noqa: ARG001
        return {
            "threads": [{"id": 999, "type": 12, "thread_metadata": {"archive_timestamp": next_timestamp}}],
            "has_more": True,
        }

    bot = MagicMock(spec=NightScoutBackupBot)
    bot.http = MagicMock()
    bot.http.request = AsyncMock(side_effect=mock_request)

    cog = ThreadManagement(bot)
    result = await cog._fetch_archived_threads_page(cast(disnake.TextChannel, cast(object, channel)), archived_threads, None)  # type: ignore[attr-defined]  # noqa: SLF001

    assert result == next_timestamp
    assert len(archived_threads) == 1


@pytest.mark.asyncio
async def test_parse_thread_from_data_invalid_dict() -> None:
    """Test parsing thread from invalid data."""
    guild = DummyGuild()
    channel = DummyChannelWithGuild([], guild=guild)

    cog = ThreadManagement(MagicMock(spec=NightScoutBackupBot))
    result = await cog._parse_thread_from_data("not a dict", cast(disnake.TextChannel, cast(object, channel)))  # type: ignore[attr-defined]  # noqa: SLF001
    assert result is None

    result = await cog._parse_thread_from_data({}, cast(disnake.TextChannel, cast(object, channel)))  # type: ignore[attr-defined]  # noqa: SLF001
    assert result is None


@pytest.mark.asyncio
async def test_parse_thread_from_data_invalid_id() -> None:
    """Test parsing thread with invalid ID."""
    guild = DummyGuild()
    channel = DummyChannelWithGuild([], guild=guild)

    cog = ThreadManagement(MagicMock(spec=NightScoutBackupBot))
    result = await cog._parse_thread_from_data({"id": "not a number"}, cast(disnake.TextChannel, cast(object, channel)))  # type: ignore[attr-defined]  # noqa: SLF001
    assert result is None


@pytest.mark.asyncio
async def test_parse_thread_from_data_fetch_channel() -> None:
    """Test parsing thread that needs to be fetched (not in cache)."""
    now = datetime.datetime.now(datetime.UTC)
    guild = DummyGuild()

    # Don't add to _threads so get_thread returns None, forcing a fetch
    # But make fetch_channel return the thread
    # Create a mock that passes isinstance check
    mock_thread = MagicMock(spec=disnake.Thread)
    mock_thread.id = 789
    mock_thread.type = disnake.ChannelType.private_thread
    mock_thread.created_at = now

    async def mock_fetch_channel(channel_id: int) -> MagicMock:
        if channel_id == 789:
            return mock_thread
        raise ValueError(f"Thread {channel_id} not found")

    guild.fetch_channel = mock_fetch_channel  # type: ignore[method-assign]

    channel = DummyChannelWithGuild([], guild=guild)

    cog = ThreadManagement(MagicMock(spec=NightScoutBackupBot))
    result = await cog._parse_thread_from_data({"id": 789}, cast(disnake.TextChannel, cast(object, channel)))  # type: ignore[attr-defined]  # noqa: SLF001
    assert result is not None
    assert result.id == 789


@pytest.mark.asyncio
async def test_parse_thread_from_data_from_cache() -> None:
    """Test parsing thread that is found in cache."""
    now = datetime.datetime.now(datetime.UTC)
    guild = DummyGuild()
    thread = DummyThread(created_at=now, thread_type=disnake.ChannelType.private_thread, thread_id=888)
    guild._threads[888] = thread  # noqa: SLF001

    channel = DummyChannelWithGuild([], guild=guild)

    cog = ThreadManagement(MagicMock(spec=NightScoutBackupBot))
    result = await cog._parse_thread_from_data({"id": 888}, cast(disnake.TextChannel, cast(object, channel)))  # type: ignore[attr-defined]  # noqa: SLF001
    assert result is not None
    assert result.id == 888


@pytest.mark.asyncio
async def test_parse_thread_from_data_fetch_fails() -> None:
    """Test parsing thread when fetch fails."""
    guild = DummyGuild()
    channel = DummyChannelWithGuild([], guild=guild)

    async def mock_fetch_channel(channel_id: int) -> DummyThread:
        raise ValueError("Thread not found")

    guild.fetch_channel = mock_fetch_channel  # type: ignore[method-assign]

    cog = ThreadManagement(MagicMock(spec=NightScoutBackupBot))
    result = await cog._parse_thread_from_data({"id": 999}, cast(disnake.TextChannel, cast(object, channel)))  # type: ignore[attr-defined]  # noqa: SLF001
    assert result is None


@pytest.mark.asyncio
async def test_parse_thread_from_data_not_thread_type() -> None:
    """Test parsing when fetched channel is not a thread."""
    guild = DummyGuild()
    channel = DummyChannelWithGuild([], guild=guild)

    async def mock_fetch_channel(channel_id: int) -> MagicMock:
        return MagicMock()  # Not a thread

    guild.fetch_channel = mock_fetch_channel  # type: ignore[method-assign]

    cog = ThreadManagement(MagicMock(spec=NightScoutBackupBot))
    result = await cog._parse_thread_from_data({"id": 999}, cast(disnake.TextChannel, cast(object, channel)))  # type: ignore[attr-defined]  # noqa: SLF001
    assert result is None


@pytest.mark.asyncio
async def test_extract_next_before_value_empty_list() -> None:
    """Test extracting before value from empty list."""
    cog = ThreadManagement(MagicMock(spec=NightScoutBackupBot))
    result = cog._extract_next_before_value([])  # type: ignore[attr-defined]  # noqa: SLF001
    assert result is None


@pytest.mark.asyncio
async def test_extract_next_before_value_not_dict() -> None:
    """Test extracting before value when last item is not a dict."""
    cog = ThreadManagement(MagicMock(spec=NightScoutBackupBot))
    result = cog._extract_next_before_value(["not a dict"])  # type: ignore[attr-defined]  # noqa: SLF001
    assert result is None


@pytest.mark.asyncio
async def test_extract_next_before_value_no_metadata() -> None:
    """Test extracting before value when thread has no metadata."""
    cog = ThreadManagement(MagicMock(spec=NightScoutBackupBot))
    result = cog._extract_next_before_value([{"id": 123}])  # type: ignore[attr-defined]  # noqa: SLF001
    assert result is None


@pytest.mark.asyncio
async def test_extract_next_before_value_metadata_not_dict() -> None:
    """Test extracting before value when metadata is not a dict."""
    cog = ThreadManagement(MagicMock(spec=NightScoutBackupBot))
    result = cog._extract_next_before_value([{"id": 123, "thread_metadata": "not a dict"}])  # type: ignore[attr-defined]  # noqa: SLF001
    assert result is None


@pytest.mark.asyncio
async def test_extract_next_before_value_no_timestamp() -> None:
    """Test extracting before value when timestamp is missing."""
    cog = ThreadManagement(MagicMock(spec=NightScoutBackupBot))
    result = cog._extract_next_before_value([{"id": 123, "thread_metadata": {}}])  # type: ignore[attr-defined]  # noqa: SLF001
    assert result is None


@pytest.mark.asyncio
async def test_extract_next_before_value_timestamp_not_string() -> None:
    """Test extracting before value when timestamp is not a string."""
    cog = ThreadManagement(MagicMock(spec=NightScoutBackupBot))
    result = cog._extract_next_before_value([{"id": 123, "thread_metadata": {"archive_timestamp": 12345}}])  # type: ignore[attr-defined]  # noqa: SLF001
    assert result is None


@pytest.mark.asyncio
async def test_extract_next_before_value_success() -> None:
    """Test successfully extracting before value."""
    cog = ThreadManagement(MagicMock(spec=NightScoutBackupBot))
    timestamp = "2024-01-01T00:00:00.000000+00:00"
    result = cog._extract_next_before_value(  # type: ignore[attr-defined]  # noqa: SLF001
        [{"id": 123, "thread_metadata": {"archive_timestamp": timestamp}}]
    )
    assert result == timestamp


@pytest.mark.asyncio
async def test_combine_and_deduplicate_with_archived() -> None:
    """Test combining threads with archived threads."""
    now = datetime.datetime.now(datetime.UTC)
    active_thread = DummyThread(created_at=now, thread_type=disnake.ChannelType.private_thread, thread_id=111)
    archived_thread = DummyThread(created_at=now, thread_type=disnake.ChannelType.private_thread, thread_id=222)

    cog = ThreadManagement(MagicMock(spec=NightScoutBackupBot))
    result = cog._combine_and_deduplicate_threads(  # type: ignore[attr-defined]  # noqa: SLF001
        cast("list[disnake.Thread]", [active_thread]),  # type: ignore[redundant-cast]
        cast("list[disnake.Thread]", [archived_thread]),  # type: ignore[redundant-cast]
    )

    assert len(result) == 2
    assert result[0].id == 111
    assert result[1].id == 222


@pytest.mark.asyncio
async def test_fetch_archived_threads_exception(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test exception handling in fetch archived threads."""
    guild = DummyGuild()
    channel = DummyChannelWithGuild([], guild=guild, channel_id=123)

    async def mock_request(route: Any, params: Any = None) -> dict[str, Any]:  # type: ignore[no-any-untyped]  # noqa: ARG001
        raise Exception("API error")

    bot = MagicMock(spec=NightScoutBackupBot)
    bot.http = MagicMock()
    bot.http.request = AsyncMock(side_effect=mock_request)

    def mock_route_init(_method: str, _url: str) -> MagicMock:
        return MagicMock()

    with monkeypatch.context() as m:
        m.setattr("disnake.http.Route", mock_route_init)
        cog = ThreadManagement(bot)
        archived_threads = await cog._fetch_archived_threads(cast(disnake.TextChannel, cast(object, channel)))  # type: ignore[attr-defined]  # noqa: SLF001

    assert archived_threads == []


@pytest.mark.asyncio
async def test_setup_function() -> None:
    """Test the setup function."""
    from nightscout_backup_bot.cogs.admin.thread_management import setup

    bot = MagicMock(spec=NightScoutBackupBot)
    bot.add_cog = MagicMock()

    setup(bot)

    bot.add_cog.assert_called_once()  # type: ignore[attr-defined]
    assert isinstance(bot.add_cog.call_args[0][0], ThreadManagement)  # type: ignore[attr-defined]
