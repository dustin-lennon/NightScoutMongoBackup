"""MongoDB service for NightScout data export."""

import json
from datetime import UTC, datetime
from typing import Any

from bson import json_util
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from ..config import settings
from ..logging_config import StructuredLogger

logger = StructuredLogger("services.mongo")


class MongoService:
    """Service for MongoDB Atlas operations."""

    def __init__(self) -> None:
        """Initialize MongoDB service."""
        self.client: AsyncIOMotorClient[dict[str, Any]] | None = None
        self.db: AsyncIOMotorDatabase[dict[str, Any]] | None = None

    async def connect(self) -> None:
        """Establish connection to MongoDB Atlas."""
        try:
            logger.info("Connecting to MongoDB Atlas", host=settings.mongo_host, database=settings.mongo_db)
            self.client = AsyncIOMotorClient(
                settings.mongo_connection_string,
                serverSelectionTimeoutMS=5000,
                connectTimeoutMS=5000,
            )
            self.db = self.client[settings.mongo_db]

            # Verify connection
            await self.client.admin.command("ping")
            logger.info("Successfully connected to MongoDB Atlas")
        except Exception as e:
            logger.error("Failed to connect to MongoDB", error=str(e))
            raise

    async def disconnect(self) -> None:
        """Close MongoDB connection."""
        if self.client:
            self.client.close()
            logger.info("Disconnected from MongoDB Atlas")

    async def export_collections(self, collection_names: list[str] | None = None) -> dict[str, Any]:
        """
        Export specified collections or all collections if none specified.

        Args:
            collection_names: List of collection names to export. If None, exports all.

        Returns:
            Dictionary with collection data and metadata.

        Raises:
            ValueError: If not connected to database.
        """
        if self.db is None:
            raise ValueError("Not connected to MongoDB. Call connect() first.")

        try:
            # Get collection names if not specified
            if collection_names is None:
                collection_names = await self.db.list_collection_names()
                logger.info("Exporting all collections", count=len(collection_names))
            else:
                logger.info("Exporting specified collections", collections=collection_names)

            export_data: dict[str, Any] = {
                "metadata": {
                    "database": settings.mongo_db,
                    "export_date": datetime.now(UTC).isoformat(),
                    "collections_count": len(collection_names),
                },
                "collections": {},
            }

            total_documents = 0

            for collection_name in collection_names:
                collection = self.db[collection_name]
                documents = await collection.find().to_list(length=None)

                export_data["collections"][collection_name] = documents
                total_documents += len(documents)

                logger.debug(
                    "Exported collection",
                    collection=collection_name,
                    documents=len(documents),
                )

            export_data["metadata"]["total_documents"] = total_documents

            logger.info(
                "Export completed",
                collections=len(collection_names),
                total_documents=total_documents,
            )

            return export_data

        except Exception as e:
            logger.error("Failed to export collections", error=str(e))
            raise

    def serialize_to_json(self, data: dict[str, Any]) -> str:
        """
        Serialize MongoDB data to JSON string.

        Args:
            data: Dictionary containing MongoDB data.

        Returns:
            JSON string with proper BSON type handling.
        """
        try:
            # Use json_util to handle BSON types (ObjectId, DateTime, etc.)
            json_str = json.dumps(data, default=json_util.default, indent=2)
            logger.debug("Serialized data to JSON", size_bytes=len(json_str))
            return json_str
        except Exception as e:
            logger.error("Failed to serialize data to JSON", error=str(e))
            raise

    async def get_database_stats(self) -> dict[str, Any]:
        """
        Get database statistics.

        Returns:
            Dictionary with database statistics.
        """
        if self.db is None:
            raise ValueError("Not connected to MongoDB. Call connect() first.")

        try:
            stats = await self.db.command("dbStats")
            logger.debug("Retrieved database stats", db=settings.mongo_db)
            return dict(stats)
        except Exception as e:
            logger.error("Failed to get database stats", error=str(e))
            raise
