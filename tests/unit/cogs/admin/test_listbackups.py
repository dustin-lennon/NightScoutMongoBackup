from typing import Any
from unittest.mock import MagicMock

import disnake
import pytest

from nightscout_backup_bot.cogs.general.listbackups import ListBackupsCog


@pytest.fixture
def mock_bot() -> MagicMock:
    """Create a mock bot instance."""
    bot = MagicMock()
    bot.latency = 0.045  # 45ms latency
    return bot


@pytest.mark.asyncio
def test_listbackups_command_success(mock_bot: MagicMock) -> None:
    mock_inter = MagicMock()
    from unittest.mock import AsyncMock

    mock_inter.response.defer = AsyncMock()

    class DummyFollowup:
        pass

    mock_inter.followup = DummyFollowup()
    mock_inter.followup.send = AsyncMock()
    mock_inter.author.id = 123
    mock_inter.author.__str__.return_value = "TestUser"
    backups: list[dict[str, Any]] = [
        {
            "key": "backups/uuid-backup1.tar.gz",
            "size": 2048000,
            "last_modified": disnake.utils.utcnow(),
        },
        {
            "key": "backups/uuid-backup2.tar.gz",
            "size": 1024000,
            "last_modified": disnake.utils.utcnow(),
        },
    ]
    cog: ListBackupsCog = ListBackupsCog(mock_bot)  # type: ignore[arg-type]
    from unittest.mock import patch

    with (
        patch.object(cog.s3_service, "list_backups", new=AsyncMock(return_value=backups)),
        patch.object(cog.s3_service, "generate_public_url", new=MagicMock(return_value="https://s3-url")),
    ):
        import asyncio

        asyncio.run(cog.listbackups.callback(cog, mock_inter))
        assert mock_inter.followup.send.called
        _, kwargs = mock_inter.followup.send.call_args
        assert "embed" in kwargs
        assert "view" in kwargs
        assert kwargs["embed"].title == "📦 Backup Files"


@pytest.mark.asyncio
def test_listbackups_command_empty(mock_bot: MagicMock) -> None:
    mock_inter = MagicMock()
    from unittest.mock import AsyncMock

    mock_inter.response.defer = AsyncMock()

    class DummyFollowup:
        pass

    mock_inter.followup = DummyFollowup()
    mock_inter.followup.send = AsyncMock()
    mock_inter.author.id = 123
    mock_inter.author.__str__.return_value = "TestUser"
    cog: ListBackupsCog = ListBackupsCog(mock_bot)  # type: ignore[arg-type]
    from unittest.mock import patch

    with patch.object(cog.s3_service, "list_backups", new=AsyncMock(return_value=[])):
        import asyncio

        asyncio.run(cog.listbackups.callback(cog, mock_inter))
        assert mock_inter.followup.send.called
        _, kwargs = mock_inter.followup.send.call_args
        assert "embed" in kwargs
        assert kwargs["embed"].title == "📦 Backup Files"
        assert kwargs["embed"].description == "No backups are currently available."
