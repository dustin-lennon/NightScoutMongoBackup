"""Discord thread service for progress updates."""

from typing import Any

import disnake

from ..logging_config import StructuredLogger

logger = StructuredLogger("services.discord_thread")


class DiscordThreadService:
    """Service for managing Discord threads for backup progress."""

    def __init__(self, channel: disnake.TextChannel) -> None:
        """
        Initialize Discord thread service.

        Args:
            channel: Discord channel where threads will be created.
        """
        self.channel = channel

    async def create_backup_thread(self, backup_date: str) -> disnake.Thread:
        """
        Create or reuse a thread for backup progress tracking for a given date.

        Args:
            backup_date: Date string for the backup (YYYY-MM-DD).

        Returns:
            Thread object for the backup.
        """
        thread_name = f"MongoDB Backup - {backup_date}"

        # Try to find an existing thread for this date
        existing_threads = [t for t in self.channel.threads if t.name == thread_name]
        if existing_threads:
            logger.info("Reusing existing backup thread", thread_id=existing_threads[0].id, name=thread_name)
            return existing_threads[0]
        try:
            thread = await self.channel.create_thread(
                name=thread_name,
                type=disnake.ChannelType.private_thread,
                auto_archive_duration=10080,  # 1 week
                invitable=False,
                reason=f"Backup Messages Generated for {backup_date}",
            )
            logger.info("Created backup thread", thread_id=thread.id, name=thread.name)
            return thread
        except Exception as e:
            logger.error("Failed to create backup thread", error=str(e))
            raise

    @staticmethod
    async def send_progress(thread: disnake.Thread, message: str, **context: Any) -> disnake.Message:
        """
        Send progress update to thread.

        Args:
            thread: Thread to send message to.
            message: Progress message.
            **context: Additional context for logging.

        Returns:
            Sent message object.
        """
        try:
            sent_message = await thread.send(message)
            logger.debug("Sent progress update", thread_id=thread.id, **context)
            return sent_message
        except Exception as e:
            logger.error("Failed to send progress update", thread_id=thread.id, error=str(e))
            raise

    @staticmethod
    async def send_error(thread: disnake.Thread, error_message: str) -> disnake.Message:
        """
        Send error message to thread.

        Args:
            thread: Thread to send message to.
            error_message: Error message.

        Returns:
            Sent message object.
        """
        formatted_message = f"❌ **Error:** {error_message}"
        try:
            sent_message = await thread.send(formatted_message)
            logger.info("Sent error message", thread_id=thread.id)
            return sent_message
        except Exception as e:
            logger.error("Failed to send error message", thread_id=thread.id, error=str(e))
            raise

    @staticmethod
    async def send_completion(
        thread: disnake.Thread,
        download_url: str,
        stats: dict[str, Any],
    ) -> disnake.Message:
        """
        Send backup completion message with download link.

        Args:
            thread: Thread to send message to.
            download_url: Public URL for backup download.
            stats: Dictionary with backup statistics.

        Returns:
            Sent message object.
        """
        try:
            embed = disnake.Embed(
                title="✅ Backup Complete",
                description="Your NightScout backup has been successfully created and uploaded.",
                color=disnake.Color.green(),
            )

            embed.add_field(name="Collections", value=str(stats.get("collections", "N/A")), inline=True)
            embed.add_field(name="Documents", value=str(stats.get("documents", "N/A")), inline=True)
            embed.add_field(name="Original Size", value=stats.get("original_size", "N/A"), inline=True)
            embed.add_field(name="Compressed Size", value=stats.get("compressed_size", "N/A"), inline=True)
            embed.add_field(name="Compression", value=stats.get("compression_ratio", "N/A"), inline=True)
            embed.add_field(name="Method", value=stats.get("compression_method", "N/A"), inline=True)

            embed.add_field(
                name="Download Link",
                value=f"[Click here to download]({download_url})",
                inline=False,
            )

            embed.set_footer(text="⚠️ Link expires in 7 days per S3 lifecycle policy")

            sent_message = await thread.send(embed=embed)
            logger.info("Sent completion message", thread_id=thread.id)
            return sent_message
        except Exception as e:
            logger.error("Failed to send completion message", thread_id=thread.id, error=str(e))
            raise
