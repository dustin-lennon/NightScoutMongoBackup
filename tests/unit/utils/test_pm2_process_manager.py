"""Tests for PM2 process manager utilities.

Note: This test file intentionally tests private functions (_execute_action) to verify
internal implementation details. This is acceptable in test files.
"""

# pyright: reportPrivateUsage=false

from unittest.mock import AsyncMock, patch

import pytest

from nightscout_backup_bot.utils import pm2_process_manager


@pytest.mark.asyncio
async def test_stop_action_with_success_indicator_in_stdout() -> None:
    """Test that stop action succeeds when stdout contains success indicator despite non-zero exit code."""
    # Mock the _run_for_target to return non-zero exit code but with success message
    with patch(
        "nightscout_backup_bot.utils.pm2_process_manager._run_for_target",
        AsyncMock(
            return_value=(
                1,  # Non-zero exit code
                "[PM2] Applying action stopProcessId on app [nightscout-backup-bot](ids: [ 0 ])",
                "",
            )
        ),
    ):
        result = await pm2_process_manager._execute_action("bot", "stop")

        assert result.ok is True
        assert result.status == "stopped"
        assert "[PM2] Applying action stopProcessId" in result.stdout


@pytest.mark.asyncio
async def test_restart_action_with_success_indicator_in_stdout() -> None:
    """Test that restart action succeeds when stdout contains success indicator despite non-zero exit code."""
    # Mock the _run_for_target to return non-zero exit code but with success message
    with patch(
        "nightscout_backup_bot.utils.pm2_process_manager._run_for_target",
        AsyncMock(
            return_value=(
                1,  # Non-zero exit code
                "[PM2] Applying action restartProcessId on app [nightscout-backup-bot](ids: [ 0 ])",
                "",
            )
        ),
    ):
        result = await pm2_process_manager._execute_action("bot", "restart")

        assert result.ok is True
        assert result.status == "restarted"
        assert "[PM2] Applying action restartProcessId" in result.stdout


@pytest.mark.asyncio
async def test_stop_action_with_zero_exit_code() -> None:
    """Test that stop action succeeds with zero exit code."""
    with patch(
        "nightscout_backup_bot.utils.pm2_process_manager._run_for_target",
        AsyncMock(return_value=(0, "[PM2] Process stopped", "")),
    ):
        result = await pm2_process_manager._execute_action("bot", "stop")

        assert result.ok is True
        assert result.status == "stopped"


@pytest.mark.asyncio
async def test_stop_action_with_process_not_found() -> None:
    """Test that stop action fails when process is not found."""
    with patch(
        "nightscout_backup_bot.utils.pm2_process_manager._run_for_target",
        AsyncMock(return_value=(1, "", "process or namespace not found")),
    ):
        result = await pm2_process_manager._execute_action("bot", "stop")

        assert result.ok is False
        assert result.status == "not_found"


@pytest.mark.asyncio
async def test_stop_action_with_genuine_error() -> None:
    """Test that stop action fails with genuine error (no success indicators)."""
    with patch(
        "nightscout_backup_bot.utils.pm2_process_manager._run_for_target",
        AsyncMock(return_value=(1, "Unknown error occurred", "Error: something went wrong")),
    ):
        result = await pm2_process_manager._execute_action("bot", "stop")

        assert result.ok is False
        assert result.status == "error"


@pytest.mark.asyncio
async def test_start_action_does_not_use_success_indicator_fallback() -> None:
    """Test that start action does not use the success indicator fallback logic."""
    # Start action should only succeed with exit code 0
    with patch(
        "nightscout_backup_bot.utils.pm2_process_manager._run_for_target",
        AsyncMock(return_value=(1, "[PM2] Process started", "")),
    ):
        result = await pm2_process_manager._execute_action("bot", "start")

        # Should fail because exit code is non-zero and start doesn't have success indicator logic
        assert result.ok is False
        assert result.status == "error"
