"""General commands cog for the bot."""

import disnake
from disnake.ext import commands

from nightscout_backup_bot.bot import NightScoutBackupBot
from nightscout_backup_bot.logging_config import StructuredLogger

logger = StructuredLogger(__name__)


class GeneralCog(commands.Cog):
    """General purpose commands available to all users."""

    def __init__(self, bot: NightScoutBackupBot) -> None:
        """Initialize general cog."""
        self.bot = bot

    @commands.slash_command(name="ping", description="Check if the bot is responsive")
    async def ping(self, inter: disnake.ApplicationCommandInteraction[NightScoutBackupBot]) -> None:
        """
        Ping command to check bot responsiveness.

        Args:
            inter: The interaction object.
        """
        latency_ms = round(self.bot.latency * 1000)

        embed = disnake.Embed(
            title="🏓 Pong!",
            description="Bot is online and responsive.",
            color=disnake.Color.green(),
        )
        embed.add_field(name="Latency", value=f"{latency_ms}ms", inline=True)
        embed.add_field(name="Status", value="✅ Operational", inline=True)

        logger.info("Ping command executed", user_id=inter.author.id, latency=latency_ms)
        await inter.response.send_message(embed=embed)


def setup(bot: NightScoutBackupBot) -> None:
    """Setup function to add cog to bot."""
    bot.add_cog(GeneralCog(bot))
