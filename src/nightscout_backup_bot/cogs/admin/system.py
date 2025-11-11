"""Admin commands cog for bot system management."""

import asyncio
import random

import disnake
from disnake.ext import commands

from nightscout_backup_bot.bot import NightScoutBackupBot
from nightscout_backup_bot.logging_config import StructuredLogger
from nightscout_backup_bot.utils.checks import is_owner
from nightscout_backup_bot.utils.pm2_process_manager import pm2_stop

logger = StructuredLogger(__name__)


class SystemCog(commands.Cog):
    """System commands for the bot."""

    def __init__(self, bot: NightScoutBackupBot) -> None:
        """Initializes the System cog."""
        self.bot = bot

    @commands.slash_command(
        name="restart",
        description="Restarts the bot.",
    )
    @is_owner()
    async def restart(self, inter: disnake.ApplicationCommandInteraction[NightScoutBackupBot]) -> None:
        """Restarts the bot using PM2's auto-restart feature."""
        await self._restart_impl(inter)

    async def _restart_impl(self, inter: disnake.ApplicationCommandInteraction[NightScoutBackupBot]) -> None:
        restart_messages = [
            "Changing the infusion set... I'll be right back!",
            "Bolusing for a restart... this might take a moment.",
            "My blood sugar is low... rebooting to get some glucose.",
            "Recalibrating the sensors... I'll be back online shortly.",
        ]
        await inter.response.send_message(random.choice(restart_messages), ephemeral=False)
        logger.info("Bot restart initiated by owner", user_id=inter.author.id)
        await asyncio.sleep(1)
        await self.bot.close()

    @commands.slash_command(
        name="kill",
        description="Stops the bot process via PM2.",
    )
    @is_owner()
    async def kill(self, inter: disnake.ApplicationCommandInteraction[NightScoutBackupBot]) -> None:
        """Stops the bot process using PM2."""
        await self._kill_impl(inter)

    async def _kill_impl(self, inter: disnake.ApplicationCommandInteraction[NightScoutBackupBot]) -> None:
        kill_messages = [
            "Rage bolusing... shutting down.",
            "I've had enough carbs for today. Goodbye.",
            "My pump is out of insulin. See you later.",
            "Looks like my CGM sensor expired. Shutting down.",
        ]
        await inter.response.send_message(random.choice(kill_messages), ephemeral=False)

        logger.info("Bot kill command initiated by owner", user_id=inter.author.id)

        result = await pm2_stop("bot")

        if not result.ok:
            logger.error(
                "Failed to stop bot PM2 process",
                stdout=result.stdout,
                stderr=result.stderr,
            )
            await inter.followup.send("⚠️ Failed to stop the bot process via PM2.", ephemeral=True)
            return

        logger.info("Bot process stopped successfully via PM2.")
        await asyncio.sleep(1)
        await self.bot.close()


def setup(bot: NightScoutBackupBot) -> None:
    """Load the System cog."""
    bot.add_cog(SystemCog(bot))
