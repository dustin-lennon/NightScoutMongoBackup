"""Admin command cog for purging MongoDB collections."""

from typing import Literal, cast

import disnake
from disnake.ext import commands
from disnake.ui import button  # pyright: ignore[reportUnknownVariableType]

from nightscout_backup_bot.bot import NightScoutBackupBot
from nightscout_backup_bot.logging_config import StructuredLogger
from nightscout_backup_bot.services.mongo_service import MongoService
from nightscout_backup_bot.utils.checks import is_owner
from nightscout_backup_bot.utils.collection_name_helper import get_internal_collection_name
from nightscout_backup_bot.utils.date_utils import DateValidationError, validate_yyyy_mm_dd

logger = StructuredLogger(__name__)

# Collection choices for purge command
COLLECTION_CHOICES = ("Entries", "Device Status", "Treatments")


class PurgeCog(commands.Cog):
    """Cog for purging MongoDB collections."""

    bot: NightScoutBackupBot
    mongo_service: MongoService

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
        collection: Literal[
            "Entries", "Device Status", "Treatments"
        ] = commands.Param(  # pyright: ignore[reportUnknownMemberType, reportCallInDefaultInitializer]
            choices=COLLECTION_CHOICES,
            description="Collection to purge (Entries, Device Status, Treatments)",
        ),
        date: str = commands.Param(  # pyright: ignore[reportUnknownMemberType, reportCallInDefaultInitializer]
            description="Date to query (YYYY-MM-DD format, e.g., 2024-01-01)"
        ),
    ) -> None:
        """
        Purge documents from a MongoDB collection by date, with confirmation.
        """
        await inter.response.defer()

        try:
            purge_date_str = validate_yyyy_mm_dd(date)

            # Convert string to datetime object (validate_yyyy_mm_dd returns datetime)
            from datetime import datetime

            purge_date = datetime.strptime(purge_date_str, "%Y-%m-%d")
            date_to_millis = int(purge_date.timestamp() * 1000)

            logger.info("Parsed date for purge", date=date, millis=date_to_millis)
        except DateValidationError:
            await inter.send("❌ Invalid date format. Use YYYY-MM-DD.", ephemeral=True)
            return

        try:
            await self.mongo_service.connect()
            if self.mongo_service.db is None:
                raise ValueError("Failed to connect to MongoDB")

            collection_name = get_internal_collection_name(str(collection))
            collection_obj = self.mongo_service.db[collection_name]
            filter_query = {"date": {"$lte": date_to_millis}}
            count = await self.mongo_service.simulate_delete_many(
                collection_name, cast(dict[str, object], filter_query)
            )

            embed = disnake.Embed(
                title="Confirm Purge",
                description=f"{count} documents from the `{collection}` collection will be deleted. Continue?",
                color=disnake.Color.red(),
            )

            class ConfirmView(disnake.ui.View):
                def __init__(self) -> None:
                    super().__init__(timeout=30)
                    self.value: bool = False

                @button(label="Yes", style=disnake.ButtonStyle.danger)
                async def yes(
                    self,
                    _button: disnake.ui.Button["ConfirmView"],  # type: ignore
                    interaction: disnake.MessageInteraction[NightScoutBackupBot],  # type: ignore
                ) -> None:
                    self.value = True
                    self.stop()
                    await interaction.response.send_message("Proceeding with deletion...", ephemeral=False)

                @button(label="No", style=disnake.ButtonStyle.secondary)
                async def no(
                    self,
                    _button: disnake.ui.Button["ConfirmView"],  # type: ignore
                    interaction: disnake.MessageInteraction[NightScoutBackupBot],  # type: ignore
                ) -> None:
                    self.value = False
                    self.stop()
                    await interaction.response.send_message("Deletion cancelled.", ephemeral=False)

            view = ConfirmView()
            await inter.send(embed=embed, view=view, ephemeral=False)
            _ = await view.wait()

            if view.value:
                result = await collection_obj.delete_many(filter_query)
                deleted_count = getattr(result, "deleted_count", 0)
                await inter.send(
                    f"Deleted {deleted_count} documents from the `{collection}` collection.", ephemeral=False
                )
        except Exception as e:
            logger.error("Error in purge_collection command", error=str(e))
            await inter.send(f"❌ Error: {e}", ephemeral=True)
        finally:
            self.mongo_service.disconnect()


def setup(bot: NightScoutBackupBot) -> None:
    """Setup function to add cog to bot."""
    bot.add_cog(PurgeCog(bot))
