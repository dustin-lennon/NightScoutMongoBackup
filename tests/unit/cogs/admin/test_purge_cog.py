from collections.abc import Callable
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import disnake
import pytest

from nightscout_backup_bot.bot import NightScoutBackupBot
from nightscout_backup_bot.cogs.admin.purge import PurgeCog


# Custom mock classes for mypy compliance
class MockResponse:
    async def send_message(self, *args, **kwargs) -> None:  # type: ignore
        pass


class MockFollowup:
    async def send(self, *args, **kwargs) -> None:  # type: ignore
        pass


def make_interaction() -> MagicMock:
    inter = MagicMock(spec=disnake.ApplicationCommandInteraction)
    inter.author = MagicMock()
    inter.author.id = 123
    inter.channel = MagicMock()
    inter.channel.id = 456
    inter.send = AsyncMock()
    inter.response = AsyncMock()
    return inter


class MockView:
    def __init__(self, value: bool):
        self.value = value

    async def wait(self) -> None:
        return None

    def stop(self) -> None:
        pass


class DummyBot(NightScoutBackupBot):
    async def wait_for(
        self, event: str | Any, *, check: Callable[[Any], bool] | None = None, timeout: float | None = None
    ) -> MagicMock:
        if event == "message":
            msg = MagicMock()
            msg.author.id = 123
            msg.channel.id = 456
            msg.content = "test_collection" if not hasattr(self, "date_asked") else "2022-01-01"
            self.date_asked = True
            return msg
        return MagicMock()  # Always return MagicMock for mypy compliance


@pytest.mark.asyncio
async def test_purge_collection_success() -> None:
    bot = DummyBot()
    cog = PurgeCog(bot)
    interaction = make_interaction()
    with (
        patch.object(cog.mongo_service, "connect", new_callable=AsyncMock),
        patch.object(cog.mongo_service, "disconnect", new_callable=AsyncMock),
        patch.object(cog.mongo_service, "simulate_delete_many", new_callable=AsyncMock, return_value=10),
        patch("nightscout_backup_bot.cogs.admin.purge.validate_yyyy_mm_dd", return_value="2022-01-01"),
        patch("disnake.ui.View.wait", AsyncMock()),
    ):
        cog.mongo_service.db = MagicMock()
        cog.mongo_service.client = MagicMock()
        mock_collection = MagicMock()
        cog.mongo_service.db.__getitem__.return_value = mock_collection
        mock_collection.delete_many = AsyncMock(return_value=MagicMock(deleted_count=10))
        with patch("disnake.ui.View.__new__", side_effect=lambda *args, **kwargs: MockView(True)):  # type: ignore
            await cog.purge_collection.callback(cog, interaction, "test_collection", "2022-01-01")
    # No assertion for mock_send_message; MockView does not call it
    interaction.send.assert_any_call("Deleted 10 documents from the `test_collection` collection.", ephemeral=False)


@pytest.mark.asyncio
async def test_purge_collection_cancel() -> None:
    bot = DummyBot()
    cog = PurgeCog(bot)
    interaction = make_interaction()
    with (
        patch.object(cog.mongo_service, "connect", new_callable=AsyncMock),
        patch.object(cog.mongo_service, "disconnect", new_callable=AsyncMock),
        patch.object(cog.mongo_service, "simulate_delete_many", new_callable=AsyncMock, return_value=10),
        patch("nightscout_backup_bot.cogs.admin.purge.validate_yyyy_mm_dd", return_value="2022-01-01"),
        patch("disnake.ui.View.wait", AsyncMock()),
    ):
        cog.mongo_service.db = MagicMock()
        cog.mongo_service.client = MagicMock()
        mock_collection = MagicMock()
        cog.mongo_service.db.__getitem__.return_value = mock_collection
        mock_collection.delete_many = AsyncMock(return_value=MagicMock(deleted_count=10))
        with patch("disnake.ui.View.__new__", side_effect=lambda *args, **kwargs: MockView(False)):  # type: ignore
            await cog.purge_collection.callback(cog, interaction, "test_collection", "2022-01-01")
    # No assertion for mock_send_message; MockView does not call it
    interaction.send.assert_any_call("Deletion cancelled.", ephemeral=False)


@pytest.mark.asyncio
async def test_purge_collection_date_error() -> None:
    bot = DummyBot()
    cog = PurgeCog(bot)
    interaction = make_interaction()
    from nightscout_backup_bot.utils.date_utils import DateValidationError

    with (
        patch.object(cog.mongo_service, "connect", new_callable=AsyncMock),
        patch.object(cog.mongo_service, "disconnect", new_callable=AsyncMock),
        patch(
            "nightscout_backup_bot.cogs.admin.purge.validate_yyyy_mm_dd", side_effect=DateValidationError("bad date")
        ),
    ):
        cog.mongo_service.db = MagicMock()
        cog.mongo_service.client = MagicMock()
        await cog.purge_collection.callback(cog, interaction, "test_collection", "bad-date")
    print("SEND CALLS:", interaction.send.call_args_list)
    # Accept either error message (date validation or generic error)
    calls = [call[0][0] for call in interaction.send.call_args_list]
    assert any(msg.startswith("❌ Invalid date format") or msg.startswith("❌ Error:") for msg in calls)


@pytest.mark.asyncio
async def test_purge_collection_mongo_error() -> None:
    bot = DummyBot()
    cog = PurgeCog(bot)
    interaction = make_interaction()
    with (
        patch.object(cog.mongo_service, "connect", new_callable=AsyncMock, side_effect=Exception("mongo fail")),
        patch.object(cog.mongo_service, "disconnect", new_callable=AsyncMock),
        patch("nightscout_backup_bot.cogs.admin.purge.validate_yyyy_mm_dd", return_value="2022-01-01"),
    ):
        cog.mongo_service.db = MagicMock()
        cog.mongo_service.client = MagicMock()
        await cog.purge_collection.callback(cog, interaction, "test_collection", "2022-01-01")
    interaction.send.assert_any_call("❌ Error: mongo fail", ephemeral=True)
