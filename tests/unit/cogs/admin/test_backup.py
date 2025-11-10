from unittest.mock import AsyncMock, MagicMock

import pytest
from disnake import TextChannel

from nightscout_backup_bot.bot import NightScoutBackupBot
from nightscout_backup_bot.cogs.admin.backup import BackupCog


@pytest.fixture
def bot_and_cog() -> tuple[MagicMock, BackupCog]:
    bot: MagicMock = MagicMock(spec=NightScoutBackupBot)
    cog: BackupCog = BackupCog(bot)
    cog.backup_service = AsyncMock()  # type: ignore[attr-defined]
    return bot, cog


@pytest.fixture
def mock_inter() -> MagicMock:
    inter: MagicMock = MagicMock()
    inter.channel = MagicMock(spec=TextChannel)
    inter.response.defer = AsyncMock()
    inter.followup.send = AsyncMock()
    return inter


@pytest.mark.asyncio
@pytest.mark.asyncio
async def test_backup_command_success(bot_and_cog: tuple[MagicMock, BackupCog], mock_inter: MagicMock) -> None:
    _, cog = bot_and_cog
    cog.backup_service.execute_backup.return_value = {"success": True, "url": "https://s3-url"}  # type: ignore[attr-defined]
    await cog.backup.callback(cog, mock_inter)
    mock_inter.response.defer.assert_called_once()
    calls = [call.args[0] for call in mock_inter.followup.send.call_args_list]
    assert "Backup started! Progress and download link will be posted in the thread." in calls
    assert "✅ Backup completed successfully!" in calls
    assert mock_inter.followup.send.call_count == 2


@pytest.mark.asyncio
@pytest.mark.asyncio
async def test_backup_command_failure(bot_and_cog: tuple[MagicMock, BackupCog], mock_inter: MagicMock) -> None:
    _, cog = bot_and_cog
    cog.backup_service.execute_backup.return_value = {"success": False}  # type: ignore[attr-defined]
    await cog.backup.callback(cog, mock_inter)
    mock_inter.followup.send.assert_any_call("❌ Backup failed. Please check logs or try again.", ephemeral=False)


@pytest.mark.asyncio
@pytest.mark.asyncio
async def test_backup_command_exception(bot_and_cog: tuple[MagicMock, BackupCog], mock_inter: MagicMock) -> None:
    _, cog = bot_and_cog
    cog.backup_service.execute_backup.side_effect = Exception("fail")  # type: ignore[attr-defined]
    await cog.backup.callback(cog, mock_inter)
    mock_inter.followup.send.assert_any_call("❌ Backup failed: fail", ephemeral=False)
