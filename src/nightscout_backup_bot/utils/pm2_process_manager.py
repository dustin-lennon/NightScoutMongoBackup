"""
Manages PM2 processes based on a per-process configuration.

This module defines different targets (e.g., the bot itself, a website)
and how to interact with them via PM2, whether they are running locally
or on a remote server via SSH.
"""

import asyncio
import shlex
from dataclasses import dataclass
from enum import Enum
from typing import Literal

from ..config import settings
from ..logging_config import StructuredLogger

logger = StructuredLogger(__name__)


class Mode(str, Enum):
    """Execution mode for PM2 commands."""

    LOCAL = "local"
    SSH = "ssh"


@dataclass
class ProcessTarget:
    """Configuration for a specific PM2-managed process."""

    pm2_app_name: str
    mode: Mode
    pm2_cmd: str
    ssh_user: str | None = None
    ssh_host: str | None = None
    ssh_key_path: str | None = None

    @property
    def ssh_connection_str(self) -> str | None:
        """Constructs the user@host string for SSH."""
        if self.ssh_user and self.ssh_host:
            return f"{self.ssh_user}@{self.ssh_host}"
        return None


# Define all managed processes
PROCESS_TARGETS: dict[str, ProcessTarget] = {
    "dexcom": ProcessTarget(
        pm2_app_name=settings.nightscout_pm2_app_name,
        # In production, run locally. In dev, use SSH.
        mode=Mode.LOCAL if settings.app_env == "production" else Mode.SSH,
        ssh_user=settings.nightscout_pm2_ssh_user,
        ssh_host=settings.nightscout_pm2_ssh_host,
        ssh_key_path=settings.nightscout_pm2_ssh_key_path,
        pm2_cmd=settings.nightscout_pm2_cmd,
    ),
    "bot": ProcessTarget(
        pm2_app_name=settings.bot_pm2_app_name,
        mode=Mode(settings.bot_pm2_mode),  # 'local' for dev, can be 'ssh' for prod
        ssh_user=settings.bot_pm2_ssh_user,
        ssh_host=settings.bot_pm2_ssh_host,
        ssh_key_path=settings.bot_pm2_ssh_key_path,
        pm2_cmd=settings.bot_pm2_cmd,
    ),
}


@dataclass
class PM2Result:
    """Standardized result from a PM2 command execution."""

    ok: bool
    status: Literal["started", "stopped", "restarted", "not_found", "error"]
    stdout: str
    stderr: str


async def _run(cmd: str) -> tuple[int, str, str]:
    """Asynchronously run a shell command."""
    process = await asyncio.create_subprocess_shell(
        cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await process.communicate()
    return process.returncode or 0, stdout.decode().strip(), stderr.decode().strip()


async def _run_local(pm2_cmd: str, args: list[str]) -> tuple[int, str, str]:
    """Run a PM2 command on the local machine."""
    # If pm2_cmd is npx, ensure 'pm2' is the first argument
    if pm2_cmd.endswith("npx"):
        cmd_list = [pm2_cmd, "pm2", *args]
    else:
        cmd_list = [pm2_cmd, *args]
    cmd_str = " ".join(shlex.quote(part) for part in cmd_list)
    logger.info("Executing local PM2 command", command=cmd_str)
    return await _run(cmd_str)


async def _run_ssh(target: ProcessTarget, args: list[str]) -> tuple[int, str, str]:
    """Run a PM2 command on a remote machine via SSH."""
    if not target.ssh_connection_str:
        raise ValueError("SSH target is missing user or host.")

    remote_cmd = target.pm2_cmd + " " + " ".join(shlex.quote(a) for a in args)
    ssh_cmd_list = [
        "ssh",
        "-o",
        "StrictHostKeyChecking=no",
        "-o",
        "UserKnownHostsFile=/dev/null",
        "-o",
        "LogLevel=ERROR",
    ]
    if target.ssh_key_path:
        ssh_cmd_list.extend(["-i", target.ssh_key_path])

    ssh_cmd_list.extend([target.ssh_connection_str, f"'bash -lc \"{remote_cmd}\"'"])
    ssh_cmd_str = " ".join(ssh_cmd_list)

    logger.info("Executing remote PM2 command via SSH", command=ssh_cmd_str)
    return await _run(ssh_cmd_str)


async def _run_for_target(target_key: str, args: list[str]) -> tuple[int, str, str]:
    """Run a command for a specific process target, handling local vs. SSH."""
    try:
        target = PROCESS_TARGETS[target_key]
    except KeyError as e:
        raise ValueError(f"Unknown process target key: {target_key}") from e

    if target.mode == Mode.LOCAL:
        return await _run_local(target.pm2_cmd, args)

    if target.mode == Mode.SSH:
        return await _run_ssh(target, args)

    raise NotImplementedError(f"Mode {target.mode} is not implemented.")


async def _execute_action(target_key: str, action: Literal["start", "stop", "restart", "status"]) -> PM2Result:
    """A generic executor for start, stop, and restart actions."""
    target = PROCESS_TARGETS[target_key]

    if action == "status":
        code, out, err = await _run_for_target(target_key, ["describe", target.pm2_app_name])
        if code == 0:
            return PM2Result(ok=True, status="started", stdout=out, stderr=err)
        return PM2Result(ok=False, status="error", stdout=out, stderr=err)

    code, out, err = await _run_for_target(target_key, [action, target.pm2_app_name])

    status_map: dict[
        Literal["start", "stop", "restart"],
        Literal["started", "stopped", "restarted"],
    ] = {"start": "started", "stop": "stopped", "restart": "restarted"}

    if code == 0:
        return PM2Result(ok=True, status=status_map[action], stdout=out, stderr=err)

    msg = (err or out or "").lower()
    if "process or namespace not found" in msg or "script not found" in msg:
        return PM2Result(ok=False, status="not_found", stdout=out, stderr=err)

    return PM2Result(ok=False, status="error", stdout=out, stderr=err)


async def pm2_start(target_key: str) -> PM2Result:
    """Starts a PM2 process."""
    return await _execute_action(target_key, "start")


async def pm2_stop(target_key: str) -> PM2Result:
    """Stops a PM2 process."""
    return await _execute_action(target_key, "stop")


async def pm2_restart(target_key: str) -> PM2Result:
    """Restarts a PM2 process."""
    return await _execute_action(target_key, "restart")


async def pm2_status(target_key: str) -> PM2Result:
    """Gets the status of a PM2 process."""
    return await _execute_action(target_key, "status")


class PM2ProcessManager:
    """A class to manage PM2 processes."""

    async def execute(self, target: str, action: Literal["start", "stop", "restart", "status"]) -> PM2Result:
        """
        Execute a PM2 command on a target process.

        Args:
            target: The key for the process target (e.g., 'dexcom', 'bot').
            action: The PM2 action to perform.

        Returns:
            A PM2Result object with the outcome.
        """
        return await _execute_action(target, action)
