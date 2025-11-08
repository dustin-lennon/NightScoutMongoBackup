"""Database statistics command for the bot."""

import disnake
from disnake.ext import commands
from motor.motor_asyncio import AsyncIOMotorClient

from ...config import get_settings
from ...logging_config import StructuredLogger

logger = StructuredLogger("cogs.general.dbstats")


def format_bytes(bytes_value: int, binary: bool = True) -> str:
    """
    Format bytes into human-readable format.

    Args:
        bytes_value: Number of bytes to format
        binary: Use binary units (1024) if True, decimal (1000) if False

    Returns:
        Formatted string like "1.5 GiB" or "1.5 GB"
    """
    if bytes_value < 0:
        return "0 B"

    units = ["B", "KiB", "MiB", "GiB", "TiB", "PiB"] if binary else ["B", "KB", "MB", "GB", "TB", "PB"]
    base = 1024 if binary else 1000

    if bytes_value == 0:
        return f"0 {units[0]}"

    exponent = 0
    size = float(bytes_value)

    while size >= base and exponent < len(units) - 1:
        size /= base
        exponent += 1

    return f"{size:.2f} {units[exponent]}"


def parse_size_with_unit(size_str: str) -> tuple[float, str, int]:
    """
    Parse a size string like "1.5 GiB" into value, unit, and exponent.

    Args:
        size_str: Formatted size string

    Returns:
        Tuple of (value, unit, exponent)
    """
    parts = size_str.split()
    if len(parts) != 2:
        return 0.0, "B", 0

    value = float(parts[0])
    unit = parts[1]

    units = ["B", "KiB", "MiB", "GiB", "TiB", "PiB"]
    exponent = units.index(unit) if unit in units else 0

    return value, unit, exponent


class DBStatsCog(commands.Cog):
    """Database statistics commands."""

    def __init__(self, bot: commands.Bot) -> None:
        """Initialize DB stats cog."""
        self.bot = bot
        self.settings = get_settings()

    @commands.slash_command(
        name="dbstats",
        description="Display MongoDB statistics for Nightscout database",
    )
    async def dbstats(self, inter: disnake.ApplicationCommandInteraction) -> None:  # type: ignore
        """
        Get database statistics from MongoDB.

        Args:
            inter: The interaction object.
        """
        # Defer reply since this might take a moment
        await inter.response.defer()

        mongo_client: AsyncIOMotorClient[dict[str, str]] | None = None

        try:
            # Connect to MongoDB
            mongo_client = AsyncIOMotorClient(self.settings.mongo_connection_string)
            db = mongo_client[self.settings.mongo_db]

            # Get database statistics
            stats_result = await db.command({"dbStats": 1})

            # Calculate aggregate size (storage + index)
            aggregate_size = stats_result["storageSize"] + stats_result["indexSize"]
            aggregate_size_formatted = format_bytes(aggregate_size)

            # Parse the aggregate size to get value and unit
            agg_value, agg_unit, _ = parse_size_with_unit(aggregate_size_formatted)

            # Calculate percentage used if max size is configured
            max_size = self.settings.mongo_db_max_size
            percentage_used = None
            warning_level = False

            if max_size:
                # Convert max_size from MB to bytes for comparison
                max_size_bytes = max_size * 1024 * 1024
                percentage_used = int((aggregate_size * 100.0) / max_size_bytes)

                # Check if we're at 80% or higher (warning threshold)
                if percentage_used >= 80:
                    warning_level = True

            # Build embed
            embed_color = disnake.Color.yellow() if warning_level else disnake.Color.green()

            embed = disnake.Embed(
                title=f"Database: {stats_result['db']}",
                description="Current statistics for this database",
                color=embed_color,
            )

            # Add fields
            embed.add_field(name="Collections", value=str(stats_result["collections"]), inline=True)
            embed.add_field(name="Indexes", value=str(stats_result["indexes"]), inline=True)
            embed.add_field(name="\u200b", value="\u200b", inline=True)  # Spacer

            embed.add_field(name="Data Size", value=format_bytes(stats_result["dataSize"]), inline=True)
            embed.add_field(name="Storage Size", value=format_bytes(stats_result["storageSize"]), inline=True)
            embed.add_field(name="Index Size", value=format_bytes(stats_result["indexSize"]), inline=True)

            embed.add_field(name="Aggregate Size (Storage + Index)", value=aggregate_size_formatted, inline=True)

            # Add percentage if max size is configured
            if percentage_used is not None:
                embed.add_field(
                    name="Percent of DB Used", value=f"{percentage_used}% - {agg_value} {agg_unit}", inline=True
                )

            # Add warning/recommendation if database is getting full
            if warning_level:
                embed.add_field(
                    name="⚠️ Recommendation",
                    value="Your database is close to being full. Backup the database and clear some old entries "
                    "out to shrink the size.",
                    inline=False,
                )

            logger.info(
                "DB stats command executed",
                user_id=inter.author.id,
                database=stats_result["db"],
                collections=stats_result["collections"],
                aggregate_size=aggregate_size,
                percentage_used=percentage_used,
            )

            await inter.followup.send(embed=embed)

        except Exception as e:
            logger.error(
                "Failed to retrieve database statistics",
                error=str(e),
                user_id=inter.author.id,
                exc_info=True,
            )

            error_embed = disnake.Embed(
                title="❌ Error",
                description="Failed to retrieve database statistics. Please try again later.",
                color=disnake.Color.red(),
            )

            await inter.followup.send(embed=error_embed, ephemeral=True)

        finally:
            if mongo_client:
                mongo_client.close()


def setup(bot: commands.Bot) -> None:
    """Setup function to add cog to bot."""
    bot.add_cog(DBStatsCog(bot))
