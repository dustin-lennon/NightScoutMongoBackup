"""Backup service that orchestrates the full backup workflow."""

from datetime import UTC, datetime
from typing import Any

import disnake

from ..config import settings
from ..logging_config import StructuredLogger
from .compression_service import CompressionService
from .discord_thread_service import DiscordThreadService
from .file_service import FileService
from .mongo_service import MongoService
from .s3_service import S3Service

logger = StructuredLogger("services.backup")


class BackupService:
    """Service that orchestrates the full backup workflow."""

    def __init__(self) -> None:
        """Initialize backup service with all sub-services."""
        self.mongo_service = MongoService()
        self.s3_service = S3Service()
        self.file_service = FileService()
        self.compression_service = CompressionService()

    async def execute_backup(
        self,
        channel: disnake.TextChannel,
        collections: list[str] | None = None,
    ) -> dict[str, Any]:
        """
        Execute full backup workflow with Discord progress updates.

        Args:
            channel: Discord channel for creating progress thread.
            collections: List of collections to backup. If None, backs up all.

        Returns:
            Dictionary with backup results and statistics.
        """
        # Create Discord thread for progress
        thread_service = DiscordThreadService(channel)
        timestamp = datetime.now(UTC).strftime("%m.%d.%Y")
        thread = await thread_service.create_backup_thread(timestamp)

        try:
            await thread_service.send_progress(thread, "🔄 Starting backup process...")

            # Step 1: Connect to MongoDB
            await thread_service.send_progress(thread, "🔄 Connecting to MongoDB Atlas...")
            await self.mongo_service.connect()
            await thread_service.send_progress(thread, "✅ Connected to MongoDB Atlas")

            # Step 2: Export data
            await thread_service.send_progress(thread, "🔄 Exporting data from MongoDB...")
            export_data = await self.mongo_service.export_collections(collections)

            collections_count = export_data["metadata"]["collections_count"]
            documents_count = export_data["metadata"]["total_documents"]
            await thread_service.send_progress(
                thread,
                f"✅ Exported {collections_count} collections ({documents_count:,} documents)",
            )

            # Step 3: Serialize to JSON
            await thread_service.send_progress(thread, "🔄 Serializing data to JSON...")
            json_data = self.mongo_service.serialize_to_json(export_data)
            original_size = len(json_data.encode("utf-8"))
            original_size_str = CompressionService.format_size(original_size)
            await thread_service.send_progress(thread, f"✅ Data serialized ({original_size_str})")

            # Step 4: Write to file
            json_filename = self.file_service.generate_filename("json")
            json_path = self.file_service.get_backup_path(json_filename)
            await self.file_service.write_file(json_path, json_data)

            # Step 5: Compress
            compression_method = settings.compression_method
            await thread_service.send_progress(
                thread,
                f"🔄 Compressing with {compression_method.upper()}...",
            )

            compressed_filename = f"{json_filename}.{compression_method.split()[0]}"
            compressed_path = self.file_service.get_backup_path(compressed_filename)

            if compression_method == "gzip":
                compressed_size = await self.compression_service.compress_gzip(json_path, compressed_path)
            else:  # brotli
                compressed_size = await self.compression_service.compress_brotli(json_path, compressed_path)

            compressed_size_str = CompressionService.format_size(compressed_size)
            reduction = ((original_size - compressed_size) / original_size) * 100
            await thread_service.send_progress(
                thread,
                f"✅ Compressed ({compressed_size_str} - {reduction:.1f}% reduction)",
            )

            # Step 6: Upload to S3
            await thread_service.send_progress(thread, "🔄 Uploading to AWS S3...")
            download_url = await self.s3_service.upload_file(compressed_path)
            await thread_service.send_progress(thread, "✅ Uploaded to S3")

            # Step 7: Cleanup local files
            await thread_service.send_progress(thread, "🔄 Cleaning up local files...")
            await self.file_service.delete_file(json_path)
            await self.file_service.delete_file(compressed_path)
            await thread_service.send_progress(thread, "✅ Local files cleaned up")

            # Step 8: Send completion message
            stats: dict[str, str] = {
                "collections": str(collections_count),
                "documents": f"{documents_count:,}",
                "original_size": original_size_str,
                "compressed_size": compressed_size_str,
                "compression_ratio": f"{reduction:.1f}%",
                "compression_method": compression_method.upper(),
            }
            await thread_service.send_completion(thread, download_url, stats)

            logger.info(
                "Backup completed successfully",
                collections=collections_count,
                documents=documents_count,
                url=download_url,
            )

            return {
                "success": True,
                "url": download_url,
                "stats": stats,
                "thread_id": thread.id,
            }

        except Exception as e:
            error_msg = str(e)
            logger.error("Backup failed", error=error_msg)
            await thread_service.send_error(thread, error_msg)
            raise

        finally:
            # Always disconnect from MongoDB
            await self.mongo_service.disconnect()

    async def test_connections(self) -> dict[str, bool]:
        """
        Test connections to external services.

        Returns:
            Dictionary with connection test results.
        """
        results: dict[str, bool] = {}

        # Test MongoDB
        try:
            await self.mongo_service.connect()
            await self.mongo_service.disconnect()
            results["mongodb"] = True
            logger.info("MongoDB connection test: PASS")
        except Exception as e:
            results["mongodb"] = False
            logger.error("MongoDB connection test: FAIL", error=str(e))

        # Test S3
        try:
            results["s3"] = await self.s3_service.test_connection()
            logger.info(f"S3 connection test: {'PASS' if results['s3'] else 'FAIL'}")
        except Exception as e:
            results["s3"] = False
            logger.error("S3 connection test: FAIL", error=str(e))

        return results
