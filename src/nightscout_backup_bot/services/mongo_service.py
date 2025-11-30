"""MongoDB service for NightScout data export."""

import asyncio
import json
from datetime import UTC, datetime
from typing import Any

from bson import json_util
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from ..config import settings
from ..logging_config import StructuredLogger

logger = StructuredLogger("services.mongo")


NOT_CONNECTED_ERROR = "Not connected to MongoDB. Call connect() first."

# Connection configuration
CONNECTION_TIMEOUT_MS = 30000  # 30 seconds for connection attempts
SERVER_SELECTION_TIMEOUT_MS = 30000  # 30 seconds for server selection (includes DNS resolution)
MAX_RETRY_ATTEMPTS = 3
RETRY_BASE_DELAY = 2  # Base delay in seconds for exponential backoff


class MongoService:
    def __init__(self) -> None:
        self.client: AsyncIOMotorClient[Any] | None = None
        self.db: AsyncIOMotorDatabase[Any] | None = None

    def _is_dns_error(self, error_msg: str) -> bool:
        """Check if error is related to DNS resolution."""
        dns_indicators = [
            "resolution lifetime expired",
            "DNS operation timed out",
            "No route to host",
            "Name resolution failed",
            "getaddrinfo failed",
        ]
        return any(indicator.lower() in error_msg.lower() for indicator in dns_indicators)

    def _format_connection_error(self, error: Exception, attempt: int, max_attempts: int) -> str:
        """Format a user-friendly error message."""
        error_msg = str(error)

        if self._is_dns_error(error_msg):
            base_msg = "DNS resolution failed when connecting to MongoDB Atlas"
            suggestions = [
                "Check your network connection",
                "Verify DNS servers are accessible",
                "Try using a different DNS server (e.g., 8.8.8.8 or 1.1.1.1)",
                "Check if MongoDB Atlas hostname is correct in your configuration",
                "Verify firewall/network settings allow DNS queries",
            ]
            suggestion_text = "; ".join(suggestions)
            return f"{base_msg} (attempt {attempt}/{max_attempts}): {error_msg}. Suggestions: {suggestion_text}"
        else:
            return f"Failed to connect to MongoDB (attempt {attempt}/{max_attempts}): {error_msg}"

    async def connect(self) -> None:
        """
        Establish connection to MongoDB Atlas with retry logic.

        Retries connection attempts up to MAX_RETRY_ATTEMPTS times with exponential backoff.
        Uses longer timeouts to accommodate DNS resolution delays.
        """
        last_error: Exception | None = None

        for attempt in range(1, MAX_RETRY_ATTEMPTS + 1):
            try:
                # Close existing client if any (from previous failed attempt)
                if self.client is not None:
                    try:
                        self.client.close()
                    except Exception:
                        pass  # Ignore errors when closing failed connection
                    self.client = None
                    self.db = None

                logger.info(
                    "Attempting MongoDB connection",
                    attempt=attempt,
                    max_attempts=MAX_RETRY_ATTEMPTS,
                    host=settings.mongo_host,
                )

                self.client = AsyncIOMotorClient(
                    settings.mongo_connection_string,
                    serverSelectionTimeoutMS=SERVER_SELECTION_TIMEOUT_MS,
                    connectTimeoutMS=CONNECTION_TIMEOUT_MS,
                    socketTimeoutMS=CONNECTION_TIMEOUT_MS,
                )
                self.db = self.client[settings.mongo_db]

                # Verify connection with ping
                await self.client.admin.command("ping")
                logger.info("Successfully connected to MongoDB Atlas", host=settings.mongo_host)
                return

            except Exception as e:
                last_error = e
                error_msg = self._format_connection_error(e, attempt, MAX_RETRY_ATTEMPTS)

                if attempt < MAX_RETRY_ATTEMPTS:
                    # Calculate exponential backoff delay
                    delay: float = RETRY_BASE_DELAY * (2 ** (attempt - 1))
                    logger.warning(
                        "MongoDB connection attempt failed, retrying",
                        attempt=attempt,
                        max_attempts=MAX_RETRY_ATTEMPTS,
                        delay_seconds=delay,
                        error=error_msg,
                    )
                    await asyncio.sleep(delay)
                else:
                    # Last attempt failed
                    logger.error("Failed to connect to MongoDB after all retry attempts", error=error_msg)

        # All attempts failed
        if last_error:
            last_error_msg = self._format_connection_error(last_error, MAX_RETRY_ATTEMPTS, MAX_RETRY_ATTEMPTS)
            full_error_msg = (
                f"Failed to connect to MongoDB Atlas after {MAX_RETRY_ATTEMPTS} attempts. "
                f"Last error: {last_error_msg}"
            )
            raise ConnectionError(full_error_msg) from last_error
        else:
            raise ConnectionError("Failed to connect to MongoDB Atlas: Unknown error")

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

    def disconnect(self) -> None:
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
