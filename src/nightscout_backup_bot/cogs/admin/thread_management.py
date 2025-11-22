"""Admin command for thread management: archive and delete backup threads."""

from __future__ import annotations

import datetime
from typing import TYPE_CHECKING

import disnake
from disnake.ext import commands

if TYPE_CHECKING:
    from nightscout_backup_bot.bot import NightScoutBackupBot

from nightscout_backup_bot.config import settings
from nightscout_backup_bot.logging_config import StructuredLogger

logger = StructuredLogger(__name__)


class ThreadManagement(commands.Cog):
    """Cog for managing backup threads: archiving and deleting."""

    def __init__(self, bot: NightScoutBackupBot):
        self.bot: NightScoutBackupBot = bot

    @commands.slash_command(
        name="manage_threads",
        description="Archive threads older than 1 day, delete threads older than 8 days (private).",
    )
    async def manage_threads(self, inter: disnake.ApplicationCommandInteraction[commands.Bot]) -> None:
        await inter.response.defer(ephemeral=True)
        channel = self.bot.get_channel(int(settings.backup_channel_id))
        if not isinstance(channel, disnake.TextChannel):
            await inter.followup.send("Backup channel not found or not a text channel.", ephemeral=True)
            return
        archived_count, deleted_count = await self.manage_threads_impl(channel)  # type: ignore
        await inter.followup.send(
            f"✅ Thread management complete.\nArchived threads: {archived_count}\nDeleted threads: {deleted_count}",
            ephemeral=True,
        )

    async def manage_threads_impl(self, channel: disnake.TextChannel) -> tuple[int, int]:
        now = datetime.datetime.now(datetime.UTC)
        archived_count = 0
        deleted_count = 0
        threads = channel.threads

        for thread in threads:
            if thread.type != disnake.ChannelType.private_thread:
                continue
            age = now - thread.created_at
            # Check for deletion first (8+ days), regardless of archived status
            if age.days >= 8:
                await thread.delete(reason="Download link no longer exists.. removing thread")
                deleted_count += 1
            # Then check for archiving (1+ days), but only if not already archived
            elif age.days >= 1 and not thread.archived:
                _ = await thread.edit(archived=True, reason="Archiving backup thread after open 1 day or longer...")
                archived_count += 1
        return archived_count, deleted_count


def setup(bot: NightScoutBackupBot) -> None:
    bot.add_cog(ThreadManagement(bot))
