"""Cog for handling the backup command."""

import disnake
from disnake.ext import commands

from nightscout_backup_bot.bot import NightScoutBackupBot
from nightscout_backup_bot.logging_config import StructuredLogger
from nightscout_backup_bot.services.backup_service import BackupService
from nightscout_backup_bot.utils.checks import is_owner

BACKUP_COMMAND_NAME = "backup"

logger = StructuredLogger(__name__)


class BackupCog(commands.Cog):
    """A cog for handling the backup command."""

    def __init__(self, bot: NightScoutBackupBot):
        """Initialize the BackupCog."""
        self.bot = bot
        self.backup_service = BackupService()

    @commands.slash_command(
        name=BACKUP_COMMAND_NAME,
        description="Creates a backup of the Nightscout database.",
    )
    @commands.cooldown(1, 300, type=commands.BucketType.user)
    @is_owner()
    async def backup(self, inter: disnake.ApplicationCommandInteraction[NightScoutBackupBot]) -> None:
        """
        Create a backup of the Nightscout database.

        This command is rate-limited to one use per user every 5 minutes.
        It can only be used in the designated backup channel.
        """
        await inter.response.defer(ephemeral=False)

        if not isinstance(inter.channel, disnake.TextChannel):
            await inter.followup.send(
                "This command can only be used in a server text channel.",
                ephemeral=True,
            )
            return

        # Immediately clear 'thinking' state and guide user to thread
        await inter.followup.send(
            "Backup started! Progress and download link will be posted in the thread.", ephemeral=False
        )

        try:
            result = await self.backup_service.execute_backup(inter.channel)
            if not result.get("success"):
                await inter.followup.send("❌ Backup failed. Please check logs or try again.", ephemeral=False)
            else:
                await inter.followup.send(
                    "✅ Backup completed successfully!",
                    ephemeral=False,
                )
        except Exception as e:
            await inter.followup.send(f"❌ Backup failed: {str(e)}", ephemeral=False)


def setup(bot: NightScoutBackupBot) -> None:
    """Load the BackupCog."""
    bot.add_cog(BackupCog(bot))
