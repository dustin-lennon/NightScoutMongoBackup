"""MongoDB service for NightScout data export."""

import json
from datetime import UTC, datetime
from typing import Any

from bson import json_util
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from ..config import settings
from ..logging_config import StructuredLogger

logger = StructuredLogger("services.mongo")


NOT_CONNECTED_ERROR = "Not connected to MongoDB. Call connect() first."


class MongoService:
    def __init__(self) -> None:
        self.client: AsyncIOMotorClient[Any] | None = None
        self.db: AsyncIOMotorDatabase[Any] | None = None

    async def connect(self) -> None:
        """
        Establish connection to MongoDB Atlas and set self.client and self.db.
        """
        try:
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

    async def dump_database(self, backups_dir: str) -> dict[str, Any]:
        """
        Perform a mongodump of the database and compress the output using CompressionService.

        Args:
            output_path: Path (without extension) for output archive.

        Returns:
            Dict with dump stats and archive path.
        """
        import asyncio
        import os
        import shutil
        import tarfile
        from datetime import datetime
        from pathlib import Path

        from .compression_service import CompressionService

        backup_date = datetime.now().strftime("%Y%m%d")
        backup_folder_name = f"dexcom_{backup_date}"
        backup_folder_path = os.path.join(backups_dir, backup_folder_name)
        os.makedirs(backup_folder_path, exist_ok=True)
        dump_cmd = [
            "mongodump",
            f"--uri={settings.mongo_connection_string}",
            f"--db={settings.mongo_db}",
            f"--out={backup_folder_path}",
        ]
        # Extract value from CompressionMethod enum for display
        compression_method_value = (
            settings.compression_method.value
            if hasattr(settings.compression_method, "value")
            else str(settings.compression_method)
        )
        stats: dict[str, Any] = {
            "collections": 0,  # int
            "documents": 0,  # int (not used here)
            "original_size": "N/A",
            "compressed_size": "N/A",
            "compression_method": compression_method_value,
        }
        try:
            proc = await asyncio.create_subprocess_exec(
                *dump_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            _stdout, stderr = await proc.communicate()
            if proc.returncode != 0:
                logger.error("mongodump failed", error=stderr.decode())
                raise RuntimeError(f"mongodump failed: {stderr.decode()}")

            # Count collections
            for _root, _dirs, files in os.walk(backup_folder_path):
                for file in files:
                    if file.endswith(".bson"):
                        stats["collections"] += 1

            # Compress the backup folder
            archive_base = os.path.join(backups_dir, backup_folder_name)
            if settings.compression_method == "brotli":
                archive_path = Path(archive_base + ".tar.br")
                tar_path = archive_base + ".tar"
                with tarfile.open(tar_path, "w") as tar:
                    tar.add(backup_folder_path, arcname=backup_folder_name)
                stats["original_size"] = CompressionService.format_size(os.path.getsize(tar_path))
                await CompressionService.compress_brotli(Path(tar_path), archive_path)
                stats["compressed_size"] = CompressionService.format_size(archive_path.stat().st_size)
                os.remove(tar_path)
            else:
                archive_path = Path(archive_base + ".tar.gz")
                tar_path = archive_base + ".tar"
                with tarfile.open(tar_path, "w") as tar:
                    tar.add(backup_folder_path, arcname=backup_folder_name)
                stats["original_size"] = CompressionService.format_size(os.path.getsize(tar_path))
                await CompressionService.compress_gzip(Path(tar_path), archive_path)
                stats["compressed_size"] = CompressionService.format_size(archive_path.stat().st_size)
                os.remove(tar_path)

            logger.info("Database dumped and compressed", archive_path=str(archive_path), stats=stats)

            # Clean up backup folder after upload
            shutil.rmtree(backup_folder_path)
            # Archive will be deleted by caller after S3 upload
            return {**stats, "archive_path": str(archive_path)}
            # Connection is now handled by connect()
        except Exception as e:
            logger.error("Failed to connect to MongoDB", error=str(e))
            raise

    async def disconnect(self) -> None:
        """Close MongoDB connection."""
        if self.client is not None:
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
            raise ValueError(NOT_CONNECTED_ERROR)

        try:
            # Get collection names if not specified
            if collection_names is None:
                collection_names = list(await self.db.list_collection_names())
            else:
                collection_names = list(collection_names)
            logger.info("Exporting collections", count=len(collection_names))

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
                collection = self.db[collection_name]  # type: ignore[index]
                documents = await collection.find().to_list(length=None)  # type: ignore[no-untyped-call]

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
            raise ValueError(NOT_CONNECTED_ERROR)

        try:
            stats: dict[str, Any] = await self.db.command("dbStats")
            logger.debug("Retrieved database stats", db=settings.mongo_db)
            return stats
        except Exception as e:
            logger.error("Failed to get database stats", error=str(e))
            raise

    async def simulate_delete_many(self, collection_name: str, filter_query: dict[str, Any]) -> int:
        """
        Simulate a delete_many operation in a transaction that is aborted.
        Returns the count of documents that would be deleted.
        """
        if self.db is None or self.client is None:
            raise ValueError(NOT_CONNECTED_ERROR)

        collection = self.db[collection_name]
        session = await self.client.start_session()

        try:
            async with session.start_transaction():
                result = await collection.delete_many(filter_query, session=session)
                await session.abort_transaction()
            await session.end_session()
            return int(result.deleted_count)
        except Exception as e:
            await session.end_session()
            logger.error("Failed to simulate delete_many", error=str(e))
            raise
