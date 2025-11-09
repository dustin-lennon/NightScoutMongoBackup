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


def setup(bot: NightScoutBackupBot) -> None:
    """Setup function to add cog to bot."""
    bot.add_cog(SiteCog(bot))
