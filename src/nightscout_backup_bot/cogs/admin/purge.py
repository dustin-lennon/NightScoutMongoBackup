"""Admin command cog for purging MongoDB collections."""

import disnake
from disnake.ext import commands
from disnake.ui import button  # type: ignore

from nightscout_backup_bot.bot import NightScoutBackupBot
from nightscout_backup_bot.logging_config import StructuredLogger
from nightscout_backup_bot.services.mongo_service import MongoService
from nightscout_backup_bot.utils.checks import is_owner
from nightscout_backup_bot.utils.date_utils import DateValidationError, validate_yyyy_mm_dd

logger = StructuredLogger(__name__)


class PurgeCog(commands.Cog):
    """Cog for purging MongoDB collections."""

    def __init__(self, bot: NightScoutBackupBot) -> None:
        """Initializes the Purge cog."""
        self.bot = bot
        self.mongo_service = MongoService()

    @commands.slash_command(
        name="purge_collection",
        description="Purge documents from a MongoDB collection by date (admin only)",
    )
    @is_owner()
    async def purge_collection(
        self,
        inter: disnake.ApplicationCommandInteraction[NightScoutBackupBot],
        collection: str = commands.Param(  # type: ignore[assignment]
            description="Collection to purge (e.g., entries, devicestatus, treatments)"
        ),
        date: str = commands.Param(description="Date to purge from (YYYY-MM-DD)"),  # type: ignore[assignment]
    ) -> None:
        """
        Purge documents from a MongoDB collection by date, with confirmation.
        """
        await inter.response.defer()

        try:
            purge_date = validate_yyyy_mm_dd(date)
        except DateValidationError:
            await inter.send("❌ Invalid date format. Use YYYY-MM-DD.", ephemeral=True)
            return

        try:
            await self.mongo_service.connect()
            if self.mongo_service.db is None:
                raise ValueError("Failed to connect to MongoDB")

            collection_obj = self.mongo_service.db[collection]
            filter_query = {"date": {"$gte": purge_date}}
            count = await self.mongo_service.simulate_delete_many(collection, filter_query)

            embed = disnake.Embed(
                title="Confirm Purge",
                description=f"{count} documents from the `{collection}` collection will be deleted. Continue?",
                color=disnake.Color.red(),
            )

            class ConfirmView(disnake.ui.View):
                def __init__(self) -> None:
                    super().__init__(timeout=30)
                    self.value: bool | None = None

                @button(label="Yes", style=disnake.ButtonStyle.danger)
                async def yes(
                    self,
                    button: disnake.ui.Button,  # type: ignore
                    interaction: disnake.MessageInteraction[NightScoutBackupBot],
                ) -> None:
                    self.value = True
                    self.stop()
                    await interaction.response.send_message("Proceeding with deletion...", ephemeral=True)

                @button(label="No", style=disnake.ButtonStyle.secondary)
                async def no(
                    self,
                    button: disnake.ui.Button,  # type: ignore
                    interaction: disnake.MessageInteraction[NightScoutBackupBot],
                ) -> None:
                    self.value = False
                    self.stop()
                    await interaction.response.send_message("Deletion cancelled.", ephemeral=True)

            view = ConfirmView()
            await inter.send(embed=embed, view=view, ephemeral=False)
            await view.wait()

            if not view.value:
                await inter.send("Deletion cancelled.", ephemeral=False)
                return

            result = await collection_obj.delete_many(filter_query)
            deleted_count = getattr(result, "deleted_count", 0)
            await inter.send(f"Deleted {deleted_count} documents from the `{collection}` collection.", ephemeral=False)
        except Exception as e:
            logger.error("Error in purge_collection command", error=str(e))
            await inter.send(f"❌ Error: {e}", ephemeral=True)
        finally:
            await self.mongo_service.disconnect()


def setup(bot: NightScoutBackupBot) -> None:
    """Setup function to add cog to bot."""
    bot.add_cog(PurgeCog(bot))
