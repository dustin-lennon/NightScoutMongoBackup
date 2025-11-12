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
    async def purge_collection(self, inter: disnake.ApplicationCommandInteraction[NightScoutBackupBot]) -> None:
        """
        Purge documents from a MongoDB collection after confirmation.
        """
        await inter.response.send_message("Which collection do you want to purge?", ephemeral=False)

        def check_collection(msg: disnake.Message) -> bool:
            return bool(msg.author.id == inter.author.id and msg.channel.id == inter.channel.id)

        try:
            collection_msg = await self.bot.wait_for("message", check=check_collection, timeout=60)
            collection_name = collection_msg.content.strip()
        except TimeoutError:
            await inter.followup.send("Timed out waiting for collection name.", ephemeral=True)
            return

        await inter.followup.send("From what date (YYYY-MM-DD) do you want to delete records?", ephemeral=False)

        def check_date(msg: disnake.Message) -> bool:
            return bool(msg.author.id == inter.author.id and msg.channel.id == inter.channel.id)

        try:
            date_msg = await self.bot.wait_for("message", check=check_date, timeout=60)
            date_str = date_msg.content.strip()
            try:
                purge_date = validate_yyyy_mm_dd(date_str)
            except DateValidationError as err:
                await inter.followup.send(f"❌ {err}", ephemeral=False)
                return
        except TimeoutError:
            await inter.followup.send("Timed out waiting for date input.", ephemeral=False)
            return

        try:
            await self.mongo_service.connect()
            if self.mongo_service.db is None:
                raise ValueError("Failed to connect to MongoDB")

            collection = self.mongo_service.db[collection_name]
            filter_query = {"date": {"$gte": purge_date}}
            count = await self.mongo_service.simulate_delete_many(collection_name, filter_query)

            embed = disnake.Embed(
                title="Confirm Purge",
                description=f"{count} documents from the `{collection_name}` will be deleted. Continue?",
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
            await inter.followup.send(embed=embed, view=view, ephemeral=False)
            await view.wait()

            if not view.value:
                await inter.followup.send("Deletion cancelled.", ephemeral=False)
                return

            result = await collection.delete_many(filter_query)
            deleted_count = getattr(result, "deleted_count", 0)
            await inter.followup.send(
                f"Deleted {deleted_count} documents from the {collection_name} collection.", ephemeral=False
            )
        except Exception as e:
            logger.error("Error in purge_collection command", error=str(e))
            await inter.followup.send(f"❌ Error: {e}", ephemeral=True)
        finally:
            await self.mongo_service.disconnect()
