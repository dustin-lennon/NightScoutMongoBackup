"""QueryDB command for querying NightScout MongoDB collections."""

from datetime import datetime
from typing import Any, Literal, cast

import disnake
from disnake.ext import commands

from nightscout_backup_bot.bot import NightScoutBackupBot
from nightscout_backup_bot.logging_config import StructuredLogger
from nightscout_backup_bot.services.mongo_service import MongoService
from nightscout_backup_bot.utils.checks import is_owner

logger = StructuredLogger(__name__)


class QueryDBCog(commands.Cog):
    """Database query commands for administrators."""

    def __init__(self, bot: NightScoutBackupBot) -> None:
        """Initialize QueryDB cog."""
        self.bot = bot
        self.mongo_service = MongoService()

    def _flatten_document_to_fields(self, doc: dict[str, Any]) -> list[dict[str, Any]]:
        """
        Flatten a MongoDB document into Discord embed fields.

        Args:
            doc: MongoDB document to flatten.

        Returns:
            List of embed field dictionaries.
        """
        fields: list[dict[str, Any]] = []

        for key, value in doc.items():
            if key != "uploader":
                fields.append({"name": key, "value": str(value), "inline": True})
            else:
                # Add separator for uploader section
                fields.append({"name": key, "value": "​", "inline": False})

                # Add uploader sub-fields if value is a dict
                if isinstance(value, dict):
                    typed_dict = cast(dict[str, Any], value)
                    for sub_key, sub_value in typed_dict.items():
                        fields.append(
                            {
                                "name": sub_key,
                                "value": str(sub_value),
                                "inline": True,
                            }
                        )

        return fields

    def _format_number(self, num: int) -> str:
        """
        Format number with commas.

        Args:
            num: Number to format.

        Returns:
            Formatted string.
        """
        return f"{num:,}"

    def _format_date(self, date_str: str) -> str:
        """
        Format date string to MMM DD, YYYY format.

        Args:
            date_str: Date string to format.

        Returns:
            Formatted date string.
        """
        try:
            date_obj = datetime.strptime(date_str, "%Y-%m-%d")
            return date_obj.strftime("%b %d, %Y")
        except ValueError:
            return date_str

    def _build_embed(
        self,
        collection_name: str,
        count: int,
        date_param: str,
        fields: list[dict[str, Any]],
    ) -> disnake.Embed:
        """
        Build Discord embed for query results.

        Args:
            collection_name: Name of the collection.
            count: Total document count.
            date_param: Date parameter used in query.
            fields: List of embed fields.

        Returns:
            Discord embed object.
        """
        # Map collection names to display names
        collection_display_names = {
            "entries": "Entries",
            "devicestatus": "Device Status",
            "treatments": "Treatments",
        }

        display_name = collection_display_names.get(collection_name.lower(), collection_name)

        embed = disnake.Embed(
            title=f"Oldest entry for {display_name} collection",
            color=0xFFFF00,  # Yellow
        )

        # Add fields (Discord limits to 25 fields per embed)
        for field in fields[:25]:
            embed.add_field(
                name=field["name"],
                value=field["value"],
                inline=field.get("inline", True),
            )

        # Add footer
        formatted_count = self._format_number(count)
        formatted_date = self._format_date(date_param)
        embed.set_footer(text=f"The {display_name} collection has {formatted_count} entries since {formatted_date}")

        return embed

    def _build_error_embed(self, collection_name: str, error: str) -> disnake.Embed:
        """
        Build error embed.

        Args:
            collection_name: Name of the collection.
            error: Error message.

        Returns:
            Discord embed object with error.
        """
        collection_display_names = {
            "entries": "Entries",
            "devicestatus": "Device Status",
            "treatments": "Treatments",
        }

        display_name = collection_display_names.get(collection_name.lower(), collection_name)

        embed = disnake.Embed(
            title=f"Error querying {display_name} collection",
            description=f"❌ An error occurred while querying the database: {error}",
            color=0xFF0000,  # Red
        )

        return embed

    def _parse_date_to_millis(self, date_str: str) -> int:
        """
        Parse date string to milliseconds timestamp.

        Args:
            date_str: Date string in YYYY-MM-DD format.

        Returns:
            Unix timestamp in milliseconds.

        Raises:
            ValueError: If date format is invalid.
        """
        try:
            date_obj = datetime.strptime(date_str, "%Y-%m-%d")
            return int(date_obj.timestamp() * 1000)
        except ValueError as e:
            raise ValueError(f"Invalid date format. Use YYYY-MM-DD. Error: {e}") from e

    def _parse_date_to_iso(self, date_str: str) -> str:
        """
        Parse date string to ISO 8601 format.

        Args:
            date_str: Date string in YYYY-MM-DD format.

        Returns:
            ISO 8601 formatted date string.

        Raises:
            ValueError: If date format is invalid.
        """
        try:
            date_obj = datetime.strptime(date_str, "%Y-%m-%d")
            return date_obj.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
        except ValueError as e:
            raise ValueError(f"Invalid date format. Use YYYY-MM-DD. Error: {e}") from e

    async def _handle_entries(
        self,
        inter: disnake.ApplicationCommandInteraction[NightScoutBackupBot],
        date_param: str,
    ) -> None:
        """
        Handle entries collection query.

        Args:
            inter: The interaction object.
            date_param: Date parameter for query.
        """
        try:
            # Parse date to milliseconds
            date_millis = self._parse_date_to_millis(date_param)

            # Connect to MongoDB
            await self.mongo_service.connect()

            if self.mongo_service.db is None:
                raise ValueError("Failed to connect to MongoDB")

            collection = self.mongo_service.db["entries"]

            # Query oldest entry
            query = {"date": {"$lte": date_millis}}
            cursor = collection.find(query).sort("date", 1).limit(1)
            result = await cursor.to_list(length=1)

            if not result:
                await inter.followup.send("No entries found.", ephemeral=True)
                return

            # Flatten document to fields
            fields = self._flatten_document_to_fields(result[0])

            # Get count
            count = await collection.count_documents(query)

            # Build embed
            embed = self._build_embed("entries", count, date_param, fields)

            await inter.followup.send(embed=embed)

        except ValueError as e:
            logger.error("Date validation error", error=str(e), user_id=inter.author.id)
            await inter.followup.send(f"❌ {str(e)}", ephemeral=True)

        except Exception as e:
            logger.error(
                "Error querying entries collection",
                error=str(e),
                user_id=inter.author.id,
            )
            embed = self._build_error_embed("entries", str(e))
            await inter.followup.send(embed=embed, ephemeral=True)

        finally:
            await self.mongo_service.disconnect()

    async def _handle_device_status(
        self,
        inter: disnake.ApplicationCommandInteraction[NightScoutBackupBot],
        date_param: str,
    ) -> None:
        """
        Handle device status collection query.

        Args:
            inter: The interaction object.
            date_param: Date parameter for query.
        """
        try:
            # Parse date to ISO format
            date_iso = self._parse_date_to_iso(date_param)

            # Connect to MongoDB
            await self.mongo_service.connect()

            if self.mongo_service.db is None:
                raise ValueError("Failed to connect to MongoDB")

            collection = self.mongo_service.db["devicestatus"]

            # Query oldest entry
            query = {"created_at": {"$lte": date_iso}}
            cursor = collection.find(query).sort("created_at", 1).limit(1)
            result = await cursor.to_list(length=1)

            if not result:
                await inter.followup.send("No device status found.", ephemeral=True)
                return

            # Flatten document to fields
            fields = self._flatten_document_to_fields(result[0])

            # Get count
            count = await collection.count_documents(query)

            # Build embed
            embed = self._build_embed("devicestatus", count, date_param, fields)

            await inter.followup.send(embed=embed)

        except ValueError as e:
            logger.error("Date validation error", error=str(e), user_id=inter.author.id)
            await inter.followup.send(f"❌ {str(e)}", ephemeral=True)

        except Exception as e:
            logger.error(
                "Error querying device status collection",
                error=str(e),
                user_id=inter.author.id,
            )
            embed = self._build_error_embed("devicestatus", str(e))
            await inter.followup.send(embed=embed, ephemeral=True)

        finally:
            await self.mongo_service.disconnect()

    async def _handle_treatments(
        self,
        inter: disnake.ApplicationCommandInteraction[NightScoutBackupBot],
        date_param: str,
    ) -> None:
        """
        Handle treatments collection query.

        Args:
            inter: The interaction object.
            date_param: Date parameter for query.
        """
        try:
            # Parse date to milliseconds
            date_millis = self._parse_date_to_millis(date_param)

            # Connect to MongoDB
            await self.mongo_service.connect()

            if self.mongo_service.db is None:
                raise ValueError("Failed to connect to MongoDB")

            collection = self.mongo_service.db["treatments"]

            # Query oldest entry
            query = {"timestamp": {"$lte": date_millis}}
            cursor = collection.find(query).sort("timestamp", 1).limit(1)
            result = await cursor.to_list(length=1)

            if not result:
                await inter.followup.send("No treatments found.", ephemeral=True)
                return

            # Flatten document to fields
            fields = self._flatten_document_to_fields(result[0])

            # Get count
            count = await collection.count_documents(query)

            # Build embed
            embed = self._build_embed("treatments", count, date_param, fields)

            await inter.followup.send(embed=embed)

        except ValueError as e:
            logger.error("Date validation error", error=str(e), user_id=inter.author.id)
            await inter.followup.send(f"❌ {str(e)}", ephemeral=True)

        except Exception as e:
            logger.error(
                "Error querying treatments collection",
                error=str(e),
                user_id=inter.author.id,
            )
            embed = self._build_error_embed("treatments", str(e))
            await inter.followup.send(embed=embed, ephemeral=True)

        finally:
            await self.mongo_service.disconnect()

    @commands.slash_command(
        name="querydb",
        description="Query NightScout database collections (Admin only)",
    )
    @is_owner()
    async def querydb(
        self,
        inter: disnake.ApplicationCommandInteraction[NightScoutBackupBot],
        collection: Literal["Entries", "Device Status", "Treatments"],
        date: str = commands.Param(  # type: ignore[assignment]
            description="Date to query (YYYY-MM-DD format, e.g., 2024-01-01)"
        ),
    ) -> None:
        """
        Query NightScout database collections.

        Args:
            inter: The interaction object.
            collection: Collection to query (Entries, Device Status, or Treatments).
            date: Date to query in YYYY-MM-DD format.
        """
        # Defer response since query takes time
        await inter.response.defer()

        logger.info(
            "QueryDB command executed",
            user_id=inter.author.id,
            collection=collection,
            date=date,
        )

        # Map collection display names to internal names
        collection_map = {
            "Entries": "entries",
            "Device Status": "devicestatus",
            "Treatments": "treatments",
        }

        internal_collection = collection_map.get(collection)

        if internal_collection == "entries":
            await self._handle_entries(inter, date)
        elif internal_collection == "devicestatus":
            await self._handle_device_status(inter, date)
        elif internal_collection == "treatments":
            await self._handle_treatments(inter, date)


def setup(bot: NightScoutBackupBot) -> None:
    """Setup function to add cog to bot."""
    bot.add_cog(QueryDBCog(bot))
