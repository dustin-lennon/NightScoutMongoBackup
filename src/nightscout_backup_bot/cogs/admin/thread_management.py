"""Admin command for thread management: archive and delete backup threads."""

from __future__ import annotations

import datetime
from typing import TYPE_CHECKING, cast

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

    async def _fetch_archived_threads(self, channel: disnake.TextChannel) -> list[disnake.Thread]:
        """Fetch archived private threads from Discord API with pagination."""
        archived_threads: list[disnake.Thread] = []

        if not channel.guild or not hasattr(self.bot, "http") or not self.bot.http:
            return archived_threads

        try:
            before: str | None = None
            while True:
                before = await self._fetch_archived_threads_page(channel, archived_threads, before)
                if before is None:
                    break

            return archived_threads
        except ImportError:
            logger.debug("disnake.http.Route not available, archived threads will not be fetched")
            return archived_threads
        except Exception as e:
            logger.warning("Failed to fetch archived threads", error=str(e), channel_id=channel.id)
            return archived_threads

    async def _fetch_archived_threads_page(
        self, channel: disnake.TextChannel, archived_threads: list[disnake.Thread], before: str | None
    ) -> str | None:
        """Fetch a single page of archived threads and return the next 'before' value."""
        from disnake.http import Route

        url = f"/channels/{channel.id}/threads/archived/private"
        params: dict[str, int | str] = {"limit": 100}
        if before:
            params["before"] = before

        route = Route("GET", url)
        data: dict[str, object] = await self.bot.http.request(route, params=params)  # type: ignore[arg-type, assignment]

        threads_data_raw = data.get("threads", [])  # type: ignore[assignment]
        if not isinstance(threads_data_raw, list):
            return None

        threads_list = cast(list[object], threads_data_raw)
        for thread_data_item in threads_list:  # type: ignore[assignment]
            thread = await self._parse_thread_from_data(thread_data_item, channel)
            if thread and thread.type == disnake.ChannelType.private_thread:
                archived_threads.append(thread)

        has_more_raw = data.get("has_more", False)  # type: ignore[assignment]
        has_more = bool(has_more_raw) if isinstance(has_more_raw, bool) else False
        if not has_more:
            return None

        return self._extract_next_before_value(threads_list)

    async def _parse_thread_from_data(
        self, thread_data_item: object, channel: disnake.TextChannel
    ) -> disnake.Thread | None:
        """Parse a thread object from Discord API response data."""
        if not isinstance(thread_data_item, dict) or "id" not in thread_data_item:
            return None

        thread_data_raw = cast(dict[str, object], thread_data_item)
        thread_id_str = str(thread_data_raw["id"])

        try:
            thread_id = int(thread_id_str)
        except (ValueError, TypeError):
            return None

        try:
            thread = channel.guild.get_thread(thread_id) if channel.guild else None
            if thread is None and channel.guild:
                fetched_channel = await channel.guild.fetch_channel(thread_id)
                if not isinstance(fetched_channel, disnake.Thread):
                    return None
                thread = fetched_channel
            return thread
        except Exception:
            logger.debug("Could not fetch archived thread", thread_id=thread_id)
            return None

    def _extract_next_before_value(self, threads_list: list[object]) -> str | None:
        """Extract the 'before' timestamp value for pagination from the last thread."""
        if not threads_list:
            return None

        last_thread_item = threads_list[-1]
        if not isinstance(last_thread_item, dict):
            return None

        last_thread_raw = cast(dict[str, object], last_thread_item)
        thread_metadata = last_thread_raw.get("thread_metadata")

        if not isinstance(thread_metadata, dict):
            logger.warning(
                "Thread missing thread_metadata, cannot paginate further",
                thread_id=last_thread_raw.get("id"),
            )
            return None

        thread_metadata_dict = cast(dict[str, object], thread_metadata)
        archive_timestamp = thread_metadata_dict.get("archive_timestamp")

        if isinstance(archive_timestamp, str):
            return archive_timestamp

        logger.warning(
            "archive_timestamp is not a string, cannot paginate further",
            thread_id=last_thread_raw.get("id"),
        )
        return None

    def _combine_and_deduplicate_threads(
        self, active_threads: list[disnake.Thread], archived_threads: list[disnake.Thread]
    ) -> list[disnake.Thread]:
        """Combine active and archived threads, deduplicating by thread ID."""
        seen_thread_ids: set[int] = set()
        all_threads: list[disnake.Thread] = []

        for thread in active_threads:
            if thread.id not in seen_thread_ids:
                seen_thread_ids.add(thread.id)
                all_threads.append(thread)

        for thread in archived_threads:
            if thread.id not in seen_thread_ids:
                seen_thread_ids.add(thread.id)
                all_threads.append(thread)

        return all_threads

    async def _process_threads(self, threads: list[disnake.Thread], now: datetime.datetime) -> tuple[int, int]:
        """Process threads: delete old ones (8+ days) and archive others (1+ days)."""
        archived_count = 0
        deleted_count = 0

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

    async def manage_threads_impl(self, channel: disnake.TextChannel) -> tuple[int, int]:
        """Main implementation for managing threads: fetch, combine, and process."""
        now = datetime.datetime.now(datetime.UTC)

        # Get active (non-archived) threads
        active_threads = list(channel.threads)

        # Fetch archived threads separately - channel.threads only returns active threads
        # We need to fetch archived threads to ensure we can delete old archived threads (8+ days)
        archived_threads = await self._fetch_archived_threads(channel)

        # Combine active and archived threads, deduplicating by thread ID
        all_threads = self._combine_and_deduplicate_threads(active_threads, archived_threads)

        # Process threads: delete old ones and archive others
        return await self._process_threads(all_threads, now)


def setup(bot: NightScoutBackupBot) -> None:
    bot.add_cog(ThreadManagement(bot))
