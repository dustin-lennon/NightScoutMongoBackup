from collections.abc import Callable
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

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


class MockInteraction:
    def __init__(self) -> None:
        self.author = MagicMock()
        self.author.id = 123
        self.channel = MagicMock()
        self.channel.id = 456
        self.response = MockResponse()
        self.followup = MockFollowup()


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
    interaction = MockInteraction()
    with (
        patch.object(interaction.response, "send_message", new_callable=AsyncMock) as send_message_mock,
        patch.object(interaction.followup, "send", new_callable=AsyncMock) as followup_send_mock,
        patch.object(cog.mongo_service, "connect", new_callable=AsyncMock),
        patch.object(cog.mongo_service, "disconnect", new_callable=AsyncMock),
        patch.object(cog.mongo_service, "simulate_delete_many", new_callable=AsyncMock, return_value=10),
    ):
        cog.mongo_service.db = MagicMock()
        mock_collection = MagicMock()
        cog.mongo_service.db.__getitem__.return_value = mock_collection
        mock_collection.delete_many = AsyncMock(return_value=MagicMock(deleted_count=10))
        with (
            patch("nightscout_backup_bot.cogs.admin.purge.validate_yyyy_mm_dd", return_value="2022-01-01"),
            patch("disnake.ui.View.wait", AsyncMock()),
        ):
            view = MagicMock()
            view.value = True
            orig_followup_send = followup_send_mock
            from typing import cast

            def fake_followup_send(*args: object, **kwargs: object) -> object:
                if "embed" in kwargs and "view" in kwargs:
                    view = cast(MagicMock, kwargs["view"])
                    view.value = True
                return orig_followup_send(*args, **kwargs)

            followup_send_mock.side_effect = fake_followup_send
            await cog._purge_collection_impl(interaction)  # type: ignore
    send_message_mock.assert_called()
    followup_send_mock.assert_any_call("Deleted 10 documents from the test_collection collection.", ephemeral=False)


@pytest.mark.asyncio
async def test_purge_collection_cancel() -> None:
    bot = DummyBot()
    cog = PurgeCog(bot)
    interaction = MockInteraction()
    with (
        patch.object(interaction.response, "send_message", new_callable=AsyncMock),
        patch.object(interaction.followup, "send", new_callable=AsyncMock) as followup_send_mock,
        patch.object(cog.mongo_service, "connect", new_callable=AsyncMock),
        patch.object(cog.mongo_service, "disconnect", new_callable=AsyncMock),
        patch.object(cog.mongo_service, "simulate_delete_many", new_callable=AsyncMock, return_value=10),
    ):
        cog.mongo_service.db = MagicMock()
        mock_collection = MagicMock()
        cog.mongo_service.db.__getitem__.return_value = mock_collection
        with (
            patch("nightscout_backup_bot.cogs.admin.purge.validate_yyyy_mm_dd", return_value="2022-01-01"),
            patch("disnake.ui.View.wait", AsyncMock()),
        ):
            view = MagicMock()
            view.value = False
            orig_followup_send = followup_send_mock
            from typing import cast

            def fake_followup_send(*args: object, **kwargs: object) -> object:
                if "embed" in kwargs and "view" in kwargs:
                    view = cast(MagicMock, kwargs["view"])
                    view.value = False
                return orig_followup_send(*args, **kwargs)

            followup_send_mock.side_effect = fake_followup_send
            await cog._purge_collection_impl(interaction)  # type: ignore
        followup_send_mock.assert_any_call("Deletion cancelled.", ephemeral=False)


@pytest.mark.asyncio
async def test_purge_collection_timeout() -> None:
    bot = DummyBot()
    cog = PurgeCog(bot)
    interaction = MockInteraction()
    with (
        patch.object(interaction.response, "send_message", new_callable=AsyncMock),
        patch.object(interaction.followup, "send", new_callable=AsyncMock) as followup_send_mock,
        patch.object(cog.mongo_service, "connect", new_callable=AsyncMock),
        patch.object(cog.mongo_service, "disconnect", new_callable=AsyncMock),
    ):
        with patch.object(bot, "wait_for", AsyncMock(side_effect=TimeoutError())):
            await cog._purge_collection_impl(interaction)  # type: ignore
        followup_send_mock.assert_any_call("Timed out waiting for collection name.", ephemeral=True)


@pytest.mark.asyncio
async def test_purge_collection_date_error() -> None:
    bot = DummyBot()
    cog = PurgeCog(bot)
    interaction = MockInteraction()
    with (
        patch.object(interaction.response, "send_message", new_callable=AsyncMock),
        patch.object(interaction.followup, "send", new_callable=AsyncMock) as followup_send_mock,
        patch.object(cog.mongo_service, "connect", new_callable=AsyncMock),
        patch.object(cog.mongo_service, "disconnect", new_callable=AsyncMock),
    ):
        from nightscout_backup_bot.utils.date_utils import DateValidationError

        with patch.object(
            bot,
            "wait_for",
            AsyncMock(side_effect=[MagicMock(content="test_collection"), MagicMock(content="bad-date")]),
        ):
            with patch(
                "nightscout_backup_bot.cogs.admin.purge.validate_yyyy_mm_dd",
                side_effect=DateValidationError("bad date"),
            ):
                await cog._purge_collection_impl(interaction)  # type: ignore
            followup_send_mock.assert_any_call("❌ bad date", ephemeral=False)


@pytest.mark.asyncio
async def test_purge_collection_mongo_error() -> None:
    bot = DummyBot()
    cog = PurgeCog(bot)
    interaction = MockInteraction()
    with (
        patch.object(interaction.response, "send_message", new_callable=AsyncMock),
        patch.object(interaction.followup, "send", new_callable=AsyncMock) as followup_send_mock,
        patch.object(cog.mongo_service, "connect", new_callable=AsyncMock, side_effect=Exception("mongo fail")),
        patch.object(cog.mongo_service, "disconnect", new_callable=AsyncMock),
    ):
        with patch.object(
            bot,
            "wait_for",
            AsyncMock(side_effect=[MagicMock(content="test_collection"), MagicMock(content="2022-01-01")]),
        ):
            with patch("nightscout_backup_bot.cogs.admin.purge.validate_yyyy_mm_dd", return_value="2022-01-01"):
                await cog._purge_collection_impl(interaction)  # type: ignore
        followup_send_mock.assert_any_call("❌ Error: mongo fail", ephemeral=True)
