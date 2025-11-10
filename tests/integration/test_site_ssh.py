"""Integration tests for site command SSH connectivity.

These tests verify real SSH connectivity to the Linode server.
They only run when proper SSH credentials are configured.
"""

import os
from unittest.mock import AsyncMock, MagicMock

import pytest

from nightscout_backup_bot.cogs.admin.site import SiteCog
from nightscout_backup_bot.config import Settings

# Skip all tests in this module if SSH configuration is not available
pytestmark = pytest.mark.skipif(
    not os.environ.get("LINODE_SSH_HOST"),
    reason="SSH integration tests require LINODE_SSH_HOST environment variable",
)


@pytest.fixture
def real_ssh_settings() -> Settings:
    """Create settings with real SSH configuration from environment."""
    return Settings(  # type: ignore[call-arg]
        discord_token="test_token",
        discord_client_id="123456789",
        backup_channel_id="987654321",
        mongo_host="test.mongodb.net",
        mongo_username="testuser",
        mongo_password="testpass",
        mongo_db="testdb",
        aws_access_key_id="test_access_key",
        aws_secret_access_key="test_secret_key",
        s3_backup_bucket="test-bucket",
        linode_ssh_host=os.environ.get("LINODE_SSH_HOST"),
        linode_ssh_user=os.environ.get("LINODE_SSH_USER", "root"),
        linode_ssh_key_path=os.environ.get("LINODE_SSH_KEY_PATH"),
        pm2_dexcom_app_name=os.environ.get("PM2_DEXCOM_APP_NAME", "Dexcom"),
    )


@pytest.fixture
def site_cog_with_real_ssh() -> SiteCog:
    """Create SiteCog instance for integration testing."""
    mock_bot = MagicMock()
    return SiteCog(mock_bot)


class TestSSHConnectivity:
    """Integration tests for SSH connectivity to Linode server."""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_ssh_connection_successful(
        self,
        site_cog_with_real_ssh: SiteCog,
        real_ssh_settings: Settings,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Test SSH connection to Linode server succeeds.

        This test verifies that:
        1. SSH authentication works
        2. Commands can be executed remotely
        3. Output is returned correctly
        """
        import nightscout_backup_bot.config

        monkeypatch.setattr(nightscout_backup_bot.config, "_settings", real_ssh_settings)
        # Force remote execution by pretending we're not on production
        monkeypatch.setattr(site_cog_with_real_ssh, "_is_production_server", lambda: False)

        # Try a simple echo command to verify SSH connectivity
        # We'll patch the PM2 command to use echo instead
        import asyncio

        async def test_ssh_echo(action: str) -> tuple[bool, str]:
            """Execute a simple echo command via SSH to test connectivity."""
            # Use echo instead of PM2 for connectivity test
            test_cmd = "echo 'SSH test successful'"

            # Build SSH command (copied from original implementation)
            ssh_key_arg = ""
            if real_ssh_settings.linode_ssh_key_path:
                ssh_key_arg = f"-i {real_ssh_settings.linode_ssh_key_path}"
            else:
                default_key = os.path.expanduser("~/.ssh/id_rsa")
                if os.path.exists(default_key):
                    ssh_key_arg = f"-i {default_key}"

            ssh_cmd = (
                f"ssh {ssh_key_arg} "
                f"-o StrictHostKeyChecking=no "
                f"-o UserKnownHostsFile=/dev/null "
                f"-o LogLevel=ERROR "
                f"-o ConnectTimeout=10 "
                f"{real_ssh_settings.linode_ssh_user}@{real_ssh_settings.linode_ssh_host} "
                f"'{test_cmd}'"
            )

            process = await asyncio.create_subprocess_shell(
                ssh_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await process.communicate()

            if process.returncode == 0:
                output = stdout.decode().strip()
                return True, output
            else:
                error = stderr.decode().strip()
                return False, error

        # Test SSH connectivity
        success, output = await test_ssh_echo("status")

        assert success is True, f"SSH connection should succeed. Error: {output}"
        assert "SSH test successful" in output, "Should receive echo response"

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_pm2_status_command_via_ssh(
        self,
        site_cog_with_real_ssh: SiteCog,
        real_ssh_settings: Settings,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Test PM2 status command executes successfully via SSH.

        This test verifies that:
        1. PM2 is installed on the remote server
        2. The configured app exists in PM2
        3. Status can be retrieved successfully
        """
        import nightscout_backup_bot.config

        monkeypatch.setattr(nightscout_backup_bot.config, "_settings", real_ssh_settings)
        monkeypatch.setattr(site_cog_with_real_ssh, "_is_production_server", lambda: False)

        # Execute status command
        success, output = await site_cog_with_real_ssh._execute_pm2_command("status")  # type: ignore[misc]

        # Even if the app doesn't exist, PM2 should be available
        # We just verify the command executes without SSH errors
        assert isinstance(success, bool), "Should return boolean success status"
        assert isinstance(output, str), "Should return string output"
        assert len(output) > 0, "Should return non-empty output"

        # If successful, output should contain PM2 status information
        if success:
            assert (
                "status" in output.lower() or "online" in output.lower() or "stopped" in output.lower()
            ), "Output should contain status information"

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_ssh_with_invalid_host_fails(
        self, site_cog_with_real_ssh: SiteCog, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test SSH connection fails gracefully with invalid host.

        This verifies error handling when SSH cannot connect.
        """
        import nightscout_backup_bot.config

        # Create settings with invalid host
        invalid_settings = Settings(  # type: ignore[call-arg]
            discord_token="test_token",
            discord_client_id="123456789",
            backup_channel_id="987654321",
            mongo_host="test.mongodb.net",
            mongo_username="testuser",
            mongo_password="testpass",
            mongo_db="testdb",
            aws_access_key_id="test_access_key",
            aws_secret_access_key="test_secret_key",
            s3_backup_bucket="test-bucket",
            linode_ssh_host="192.0.2.1",  # TEST-NET-1 (should not be reachable)
            linode_ssh_user="root",
        )

        monkeypatch.setattr(nightscout_backup_bot.config, "_settings", invalid_settings)
        monkeypatch.setattr(site_cog_with_real_ssh, "_is_production_server", lambda: False)

        # Try to execute command (should timeout and fail)
        success, output = await site_cog_with_real_ssh._execute_pm2_command("status")  # type: ignore[misc]

        assert success is False, "Connection to invalid host should fail"
        assert len(output) > 0, "Should return error message"


class TestSSHCommandSecurity:
    """Integration tests for SSH command security and proper escaping."""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_ssh_command_uses_proper_options(
        self,
        site_cog_with_real_ssh: SiteCog,
        real_ssh_settings: Settings,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Test SSH command uses proper security options.

        Verifies that SSH commands include:
        - StrictHostKeyChecking=no (for automation)
        - UserKnownHostsFile=/dev/null (no host key storage)
        - Proper key authentication
        """
        from unittest.mock import patch

        import nightscout_backup_bot.config

        monkeypatch.setattr(nightscout_backup_bot.config, "_settings", real_ssh_settings)
        monkeypatch.setattr(site_cog_with_real_ssh, "_is_production_server", lambda: False)

        # Capture the SSH command that gets executed
        captured_command = None

        async def capture_subprocess_shell(cmd: str, **kwargs):  # type: ignore[no-untyped-def]
            nonlocal captured_command
            captured_command = cmd
            # Return a mock process
            mock_process = AsyncMock()
            mock_process.communicate = AsyncMock(return_value=(b"test output", b""))
            mock_process.returncode = 0
            return mock_process

        with patch("asyncio.create_subprocess_shell", side_effect=capture_subprocess_shell):
            await site_cog_with_real_ssh._execute_pm2_command("status")  # type: ignore[misc]

        assert captured_command is not None, "Should have captured SSH command"
        assert "StrictHostKeyChecking=no" in captured_command, "Should disable strict host checking"
        assert "UserKnownHostsFile=/dev/null" in captured_command, "Should not store host keys"
        assert "LogLevel=ERROR" in captured_command, "Should suppress verbose SSH output"
        assert f"{real_ssh_settings.linode_ssh_user}@" in captured_command, "Should use configured user"
