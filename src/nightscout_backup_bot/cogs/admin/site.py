"""Admin commands cog for site management."""

import disnake
from disnake.ext import commands

from nightscout_backup_bot.bot import NightScoutBackupBot
from nightscout_backup_bot.logging_config import StructuredLogger
from nightscout_backup_bot.utils.checks import is_owner
from nightscout_backup_bot.utils.pm2_process_manager import (
    PM2Result,
    pm2_restart,
    pm2_start,
    pm2_stop,
)

logger = StructuredLogger(__name__)


class SiteCog(commands.Cog):
    """Admin commands for the NightScout site managed by PM2."""

    def __init__(self, bot: NightScoutBackupBot) -> None:
        """Initialize site cog."""
        self.bot = bot

    async def _handle_pm2_command(
        self,
        inter: disnake.ApplicationCommandInteraction[NightScoutBackupBot],
        result: PM2Result,
        action_verb: str,
    ) -> None:
        """Generic handler for sending command feedback to Discord."""
        target_name = "NightScout site"
        if result.ok:
            await inter.followup.send(f"✅ **{target_name}** {result.status} successfully!", ephemeral=True)
        elif result.status == "not_found":
            await inter.followup.send(
                f"⚠️ **{target_name}** does not appear to be running or managed by PM2.",
                ephemeral=True,
            )
        else:
            await inter.followup.send(
                f"❌ Failed to {action_verb} **{target_name}**.\n" f"```\n{result.stderr or result.stdout}\n```",
                ephemeral=True,
            )

    @commands.slash_command(
        name="site",
        description="Manage the NightScout application via PM2",
    )
    @is_owner()
    async def site(self, inter: disnake.ApplicationCommandInteraction[NightScoutBackupBot]) -> None:
        """Base command for site management."""
        pass

    @site.sub_command(name="start", description="Start the NightScout application")  # type: ignore[misc]
    async def start(self, inter: disnake.ApplicationCommandInteraction[NightScoutBackupBot]) -> None:
        """Start the NightScout application via PM2."""
        await inter.response.defer(ephemeral=True)
        logger.info("Site start command initiated", user_id=inter.author.id, user=str(inter.author))
        result = await pm2_start("nightscout")
        await self._handle_pm2_command(inter, result, "start")

    @site.sub_command(name="stop", description="Stop the NightScout application")  # type: ignore[misc]
    async def stop(self, inter: disnake.ApplicationCommandInteraction[NightScoutBackupBot]) -> None:
        """Stop the NightScout application via PM2."""
        await inter.response.defer(ephemeral=True)
        logger.info("Site stop command initiated", user_id=inter.author.id, user=str(inter.author))
        result = await pm2_stop("nightscout")
        await self._handle_pm2_command(inter, result, "stop")

    @site.sub_command(name="restart", description="Restart the NightScout application")  # type: ignore[misc]
    async def restart(self, inter: disnake.ApplicationCommandInteraction[NightScoutBackupBot]) -> None:
        """Restart the NightScout application via PM2."""
        await inter.response.defer(ephemeral=True)
        logger.info("Site restart command initiated", user_id=inter.author.id, user=str(inter.author))
        result = await pm2_restart("nightscout")
        await self._handle_pm2_command(inter, result, "restart")

    @site.sub_command(name="status", description="Show NightScout application status")  # type: ignore[misc]
    async def status(self, inter: disnake.ApplicationCommandInteraction[NightScoutBackupBot]) -> None:
        """Show the NightScout application's PM2 status."""
        await inter.response.defer(ephemeral=True)
        logger.info("Site status command initiated", user_id=inter.author.id, user=str(inter.author))
        import datetime
        import json
        import re

        from nightscout_backup_bot.utils.pm2_process_manager import PROCESS_TARGETS, pm2_status

        # Use 'nightscout' if available, else fallback to 'dexcom'
        target_key = "nightscout" if "nightscout" in PROCESS_TARGETS else "dexcom"
        result = await pm2_status(target_key)
        if result.ok and result.stdout:
            name = status = uptime = restarts = None
            # Improved PM2 table parsing: match keys with spaces and allow empty values
            # Match lines like: │ key            │ value             │
            for line in result.stdout.splitlines():
                m = re.search(r"[│|]\s*([^│|]+?)\s*[│|]\s*([^│|]+?)\s*[│|]", line)
                if m:
                    key = m.group(1).strip().lower().replace(" ", "")
                    value = m.group(2).strip()
                    match key:
                        case "name":
                            name = value
                        case "status":
                            status = value
                        case "uptime":
                            uptime = value
                        case "restarts":
                            restarts = value
                        case _:
                            pass
            # Fallback: try to find fields in JSON-like output
            if not name or not status or not uptime or not restarts:
                try:
                    json_match = re.search(r"({.*})", result.stdout, re.DOTALL)
                    if json_match:
                        proc = json.loads(json_match.group(1))
                        name = name or proc.get("name")
                        status = status or proc.get("pm2_env", {}).get("status")
                        uptime = uptime or proc.get("pm2_env", {}).get("pm_uptime")
                        restarts = restarts or proc.get("pm2_env", {}).get("restart_time")
                except Exception:
                    pass
            # Format uptime if it's a timestamp
            if uptime and uptime.isdigit():
                try:
                    dt = datetime.datetime.fromtimestamp(int(uptime) / 1000)
                    uptime = str(datetime.datetime.now() - dt).split(".")[0]
                except Exception:
                    pass
            # Status dot: treat 'started', 'running', or 'online' as online
            online_statuses = {"online", "started", "running"}
            dot = "🟢" if (status and status.lower() in online_statuses) else "🔴"
            embed = disnake.Embed(
                title=f"NightScout Site Status {dot}",
                color=disnake.Color.green() if dot == "🟢" else disnake.Color.red(),
            )
            embed.add_field(name="Name", value=name or "N/A", inline=True)
            embed.add_field(name="Status", value=status or "N/A", inline=True)
            embed.add_field(name="Uptime", value=uptime or "N/A", inline=True)
            embed.add_field(name="Restarts", value=restarts or "N/A", inline=True)
            await inter.followup.send(embed=embed, ephemeral=True)
        elif result.status == "not_found":
            await inter.followup.send("⚠️ NightScout is not running or not managed by PM2.", ephemeral=True)
        else:
            await inter.followup.send(
                f"❌ Failed to get status.\n```\n{result.stderr or result.stdout}\n```", ephemeral=True
            )


def setup(bot: NightScoutBackupBot) -> None:
    """Setup function to add cog to bot."""
    bot.add_cog(SiteCog(bot))
