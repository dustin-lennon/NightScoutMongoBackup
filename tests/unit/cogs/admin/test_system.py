import random
from unittest.mock import AsyncMock, MagicMock

import pytest

from nightscout_backup_bot.bot import NightScoutBackupBot
from nightscout_backup_bot.cogs.admin.system import SystemCog, logger


@pytest.mark.asyncio
async def test_restart_command_sends_message(monkeypatch: pytest.MonkeyPatch) -> None:
    bot = NightScoutBackupBot()
    cog = SystemCog(bot)
    inter = MagicMock()
    inter.response.send_message = AsyncMock()
    inter.author.id = 123456

    # Patch logger.info to avoid side effects
    monkeypatch.setattr(logger, "info", lambda *a, **kw: None)  # type: ignore
    # Patch random.choice to return a known message
    monkeypatch.setattr(random, "choice", lambda x: x[0])  # type: ignore
    # Patch bot.close to avoid closing test runner
    monkeypatch.setattr(bot, "close", AsyncMock())

    await cog._restart_impl(inter)  # type: ignore
    inter.response.send_message.assert_awaited_once()
    sent_msg = inter.response.send_message.call_args[0][0]
    assert sent_msg in [
        "Changing the infusion set... I'll be right back!",
        "Bolusing for a restart... this might take a moment.",
        "My blood sugar is low... rebooting to get some glucose.",
        "Recalibrating the sensors... I'll be back online shortly.",
    ]


@pytest.mark.asyncio
async def test_kill_command_sends_message_and_pm2(monkeypatch: pytest.MonkeyPatch) -> None:
    bot = NightScoutBackupBot()
    cog = SystemCog(bot)
    inter = MagicMock()
    inter.response.send_message = AsyncMock()
    inter.author.id = 123456
    inter.followup.send = AsyncMock()

    # Patch logger.info and logger.error to avoid side effects
    monkeypatch.setattr(logger, "info", lambda *a, **kw: None)  # type: ignore
    monkeypatch.setattr(logger, "error", lambda *a, **kw: None)  # type: ignore
    # Patch random.choice to return a known message
    monkeypatch.setattr(random, "choice", lambda x: x[0])  # type: ignore
    # Patch bot.close to avoid closing test runner
    monkeypatch.setattr(bot, "close", AsyncMock())

    # Patch pm2_stop to simulate success
    mock_pm2_result = MagicMock()
    mock_pm2_result.ok = True
    monkeypatch.setattr(
        "nightscout_backup_bot.utils.pm2_process_manager.pm2_stop", AsyncMock(return_value=mock_pm2_result)
    )

    await cog._kill_impl(inter)  # type: ignore
    inter.response.send_message.assert_awaited_once()
    sent_msg = inter.response.send_message.call_args[0][0]
    assert sent_msg in [
        "Rage bolusing... shutting down.",
        "I've had enough carbs for today. Goodbye.",
        "My pump is out of insulin. See you later.",
        "Looks like my CGM sensor expired. Shutting down.",
    ]
