"""List backups command for viewing S3 backup files."""

from datetime import UTC, datetime
from typing import Any

import disnake
from disnake.ext import commands

from ...config import settings
from ...logging_config import StructuredLogger
from ...services.s3_service import S3Service

logger = StructuredLogger("cogs.general.listbackups")


def is_owner() -> Any:
    """Check if user is a bot owner."""

    async def predicate(inter: disnake.ApplicationCommandInteraction) -> bool:  # type: ignore
        if str(inter.author.id) not in settings.owner_id_list:
            await inter.response.send_message(
                "❌ This command is restricted to bot owners only.",
                ephemeral=True,
            )
            return False
        return True

    return commands.check(predicate)  # type: ignore


def format_file_size(size_bytes: int) -> str:
    """
    Format file size in human-readable format.

    Args:
        size_bytes: File size in bytes.

    Returns:
        Formatted string (e.g., "1.5 MB").
    """
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.2f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.2f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"


def format_datetime(dt: datetime) -> str:
    """
    Format datetime in the specified format: MMM DD, YYYY @ hh:mm a ZZ.

    Args:
        dt: Datetime object (timezone-aware).

    Returns:
        Formatted datetime string.
    """
    # Convert to UTC if not already
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    else:
        dt = dt.astimezone(UTC)

    # Format: MMM DD, YYYY @ hh:mm a ZZ
    return dt.strftime("%b %d, %Y @ %I:%M %p UTC")


class BackupPaginatorView(disnake.ui.View):
    """Paginated view for backup listings."""

    def __init__(self, backups: list[dict[str, Any]], s3_service: S3Service) -> None:
        """
        Initialize paginator view.

        Args:
            backups: List of backup objects from S3.
            s3_service: S3Service instance for generating URLs.
        """
        super().__init__(timeout=300)  # 5 minute timeout
        self.backups = backups
        self.s3_service = s3_service
        self.current_page = 0
        self.total_pages = len(backups)

        # Disable buttons if only one page
        if self.total_pages <= 1:
            # Buttons are added to self.children in order of definition
            for item in self.children:
                if isinstance(item, disnake.ui.Button):
                    item.disabled = True

    def create_embed(self) -> disnake.Embed:
        """
        Create embed for current page.

        Returns:
            Discord embed object.
        """
        backup = self.backups[self.current_page]

        embed = disnake.Embed(
            title="📦 Backup Files",
            description="File and download information for backups made",
            color=disnake.Color.gold(),
        )

        # Extract filename from key (remove "backups/" prefix and UUID)
        key = backup["key"]
        filename = key.split("/")[-1]

        # Add fields
        embed.add_field(name="File Name", value=f"`{filename}`", inline=False)
        embed.add_field(
            name="File Size",
            value=format_file_size(backup["size"]),
            inline=True,
        )
        embed.add_field(
            name="Uploaded (Last Modified)",
            value=format_datetime(backup["last_modified"]),
            inline=True,
        )

        # Generate download URL
        download_url = self.s3_service.generate_public_url(key)
        embed.add_field(
            name="Download",
            value=f"[Click here to download]({download_url})",
            inline=False,
        )

        # Footer with page information
        embed.set_footer(text=f"Page {self.current_page + 1} of {self.total_pages}")

        return embed

    @disnake.ui.button(label="◀ Previous", style=disnake.ButtonStyle.secondary)  # type: ignore
    async def previous_button(
        self,
        button: disnake.ui.Button[Any],
        inter: disnake.MessageInteraction,  # type: ignore
    ) -> None:
        """Handle previous button click."""
        self.current_page = max(0, self.current_page - 1)

        # Update button states
        self.previous_button.disabled = self.current_page == 0  # type: ignore
        self.next_button.disabled = False  # type: ignore

        await inter.response.edit_message(embed=self.create_embed(), view=self)

    @disnake.ui.button(label="Next ▶", style=disnake.ButtonStyle.secondary)  # type: ignore
    async def next_button(self, button: disnake.ui.Button, inter: disnake.MessageInteraction) -> None:  # type: ignore
        """Handle next button click."""
        self.current_page = min(self.total_pages - 1, self.current_page + 1)

        # Update button states
        self.previous_button.disabled = False  # type: ignore
        self.next_button.disabled = self.current_page == self.total_pages - 1  # type: ignore

        await inter.response.edit_message(embed=self.create_embed(), view=self)

    async def on_timeout(self) -> None:
        """Disable all buttons when view times out."""
        for item in self.children:
            if isinstance(item, disnake.ui.Button):
                item.disabled = True


class ListBackupsCog(commands.Cog):
    """Command for listing available backup files."""

    def __init__(self, bot: commands.Bot) -> None:
        """Initialize list backups cog."""
        self.bot = bot
        self.s3_service = S3Service()

    @commands.slash_command(
        name="listbackups",
        description="List all available backup files in S3 (Admin only)",
    )
    @is_owner()
    async def listbackups(self, inter: disnake.ApplicationCommandInteraction) -> None:  # type: ignore
        """
        List all available backup files with pagination.

        Args:
            inter: The interaction object.
        """
        # Defer response since S3 call may take time
        await inter.response.defer(ephemeral=True)

        try:
            logger.info(
                "List backups command initiated",
                user_id=inter.author.id,
                user=str(inter.author),
            )

            # Fetch backups from S3
            backups = await self.s3_service.list_backups()

            # Sort by last modified (newest first)
            backups.sort(key=lambda x: x["last_modified"], reverse=True)

            # Check if no backups available
            if not backups:
                embed = disnake.Embed(
                    title="📦 Backup Files",
                    description="No backups are currently available.",
                    color=disnake.Color.orange(),
                )
                await inter.followup.send(embed=embed, ephemeral=True)
                logger.info("No backups found", user_id=inter.author.id)
                return

            # Create paginated view
            view = BackupPaginatorView(backups, self.s3_service)
            embed = view.create_embed()

            await inter.followup.send(embed=embed, view=view, ephemeral=True)

            logger.info(
                "Listed backups successfully",
                user_id=inter.author.id,
                backup_count=len(backups),
            )

        except Exception as e:
            logger.error(
                "Failed to list backups",
                user_id=inter.author.id,
                error=str(e),
                error_type=type(e).__name__,
            )

            error_embed = disnake.Embed(
                title="❌ Error",
                description="Failed to retrieve backup list from S3. Please try again later.",
                color=disnake.Color.red(),
            )
            error_embed.add_field(
                name="Error Details",
                value=f"`{type(e).__name__}: {str(e)}`",
                inline=False,
            )

            await inter.followup.send(embed=error_embed, ephemeral=True)


def setup(bot: commands.Bot) -> None:
    """Setup function to add cog to bot."""
    bot.add_cog(ListBackupsCog(bot))
