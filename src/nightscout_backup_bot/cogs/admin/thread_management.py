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

    async def manage_threads_impl(self, channel: disnake.TextChannel) -> tuple[int, int]:
        now = datetime.datetime.now(datetime.UTC)
        archived_count = 0
        deleted_count = 0

        # Get active (non-archived) threads
        active_threads = list(channel.threads)

        # Fetch archived threads separately - channel.threads only returns active threads
        # We need to fetch archived threads to ensure we can delete old archived threads (8+ days)
        # Discord API: GET /channels/{channel.id}/threads/archived/private
        archived_threads: list[disnake.Thread] = []
        if channel.guild and hasattr(self.bot, "http") and self.bot.http:
            try:
                # Use HTTP client to fetch archived private threads directly from Discord API
                from disnake.http import Route

                # Make direct API request to Discord's archived threads endpoint
                # Discord API expects ISO8601 timestamp string for 'before' parameter, not thread ID
                before: str | None = None
                while True:
                    # Build the API endpoint URL
                    url = f"/channels/{channel.id}/threads/archived/private"
                    params: dict[str, int | str] = {"limit": 100}
                    if before:
                        params["before"] = before

                    # Make the HTTP request
                    route = Route("GET", url)
                    # Type ignore needed as HTTP client types are not fully typed
                    data: dict[str, object] = await self.bot.http.request(route, params=params)  # type: ignore[arg-type, assignment]

                    # Extract threads from response
                    threads_data_raw = data.get("threads", [])  # type: ignore[assignment]
                    if not isinstance(threads_data_raw, list):
                        break

                    # Process each archived thread
                    # Type ignore needed as HTTP response types are not fully typed
                    # Cast list to help type checker understand element types
                    threads_list = cast(list[object], threads_data_raw)
                    for thread_data_item in threads_list:  # type: ignore[assignment]
                        # Type check to ensure it's a dict before processing
                        # Cast to help type checker understand the type after isinstance check
                        if not isinstance(thread_data_item, dict) or "id" not in thread_data_item:
                            continue
                        thread_data_raw = cast(dict[str, object], thread_data_item)

                        thread_id_str = str(thread_data_raw["id"])
                        try:
                            thread_id = int(thread_id_str)
                        except (ValueError, TypeError):
                            continue

                        try:
                            # Try to get thread from cache first
                            thread = channel.guild.get_thread(thread_id)
                            if thread is None:
                                # Fetch the thread if not in cache
                                fetched_channel = await channel.guild.fetch_channel(thread_id)
                                if not isinstance(fetched_channel, disnake.Thread):
                                    continue
                                thread = fetched_channel

                            if thread.type == disnake.ChannelType.private_thread:
                                archived_threads.append(thread)
                        except Exception:
                            # Thread might have been deleted, skip it
                            logger.debug("Could not fetch archived thread", thread_id=thread_id)
                            continue

                    # Check if there are more threads to fetch
                    has_more_raw = data.get("has_more", False)  # type: ignore[assignment]
                    has_more = bool(has_more_raw) if isinstance(has_more_raw, bool) else False
                    if not has_more:
                        break

                    # Set before to the oldest thread's archive_timestamp (ISO8601) for next iteration
                    # Discord API requires ISO8601 timestamp string, not thread ID
                    if threads_list:
                        last_thread_item = threads_list[-1]
                        # Cast to help type checker understand the type after isinstance check
                        if isinstance(last_thread_item, dict):
                            last_thread_raw = cast(dict[str, object], last_thread_item)
                            # Extract archive_timestamp from thread_metadata
                            thread_metadata = last_thread_raw.get("thread_metadata")
                            if isinstance(thread_metadata, dict):
                                thread_metadata_dict = cast(dict[str, object], thread_metadata)
                                archive_timestamp = thread_metadata_dict.get("archive_timestamp")
                                if isinstance(archive_timestamp, str):
                                    before = archive_timestamp
                                else:
                                    # If archive_timestamp is not a string, we can't paginate
                                    logger.warning(
                                        "archive_timestamp is not a string, cannot paginate further",
                                        thread_id=last_thread_raw.get("id"),
                                    )
                                    break
                            else:
                                # No thread_metadata means we can't get the timestamp
                                logger.warning(
                                    "Thread missing thread_metadata, cannot paginate further",
                                    thread_id=last_thread_raw.get("id"),
                                )
                                break
                        else:
                            break
                    else:
                        break
            except ImportError:
                # Route not available - this is expected if disnake version doesn't support it
                logger.debug("disnake.http.Route not available, archived threads will not be fetched")
            except Exception as e:
                logger.warning("Failed to fetch archived threads", error=str(e), channel_id=channel.id)

        # Combine active and archived threads, using a set to deduplicate by thread ID
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

        for thread in all_threads:
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
