"""Backup service that orchestrates the full backup workflow."""

from datetime import UTC, datetime
from typing import Any

import disnake

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
        Execute full backup workflow with Discord progress updates (mongodump-based).

        Args:
            channel: Discord channel for creating progress thread.
            collections: (Unused) for compatibility.

        Returns:
            Dictionary with backup results and statistics.
        """
        thread_service = DiscordThreadService(channel)
        timestamp = datetime.now(UTC).strftime("%m.%d.%Y")
        thread = await thread_service.create_backup_thread(timestamp)

        try:
            await thread_service.send_progress(thread, "🔄 Starting backup process...")
            await thread_service.send_progress(thread, "🔄 Connecting to MongoDB Atlas...")
            await self.mongo_service.connect()  # type: ignore[attr-defined]
            await thread_service.send_progress(thread, "✅ Connected to MongoDB Atlas")

            # Step 2: Dump database
            await thread_service.send_progress(thread, "🔄 Dumping MongoDB database...")
            backup_dir = "backups"
            dump_stats = await self.mongo_service.dump_database(backup_dir)

            await thread_service.send_progress(
                thread,
                f"✅ Database dumped ({dump_stats['original_size']} uncompressed, {dump_stats['compressed_size']} compressed)",
            )

            # Step 3: Upload to S3
            await thread_service.send_progress(thread, "🔄 Uploading to AWS S3...")
            download_url = await self.s3_service.upload_file(dump_stats["archive_path"])
            await thread_service.send_progress(thread, "✅ Uploaded to S3")

            # Step 4: Cleanup local files
            await thread_service.send_progress(thread, "🔄 Cleaning up local files...")
            await self.file_service.delete_file(dump_stats["archive_path"])
            await thread_service.send_progress(thread, "✅ Local files cleaned up")

            # Step 5: Send completion message
            def parse_size(size_str: str) -> float:
                # Parse size like "12.3MB" to bytes
                try:
                    if size_str.endswith("MB"):
                        return float(size_str[:-2]) * 1024 * 1024
                    elif size_str.endswith("KB"):
                        return float(size_str[:-2]) * 1024
                    elif size_str.endswith("GB"):
                        return float(size_str[:-2]) * 1024 * 1024 * 1024
                    elif size_str.endswith("B"):
                        return float(size_str[:-1])
                except Exception:
                    return 0.0
                return 0.0

            original_size_str = str(dump_stats.get("original_size", "N/A"))
            compressed_size_str = str(dump_stats.get("compressed_size", "N/A"))
            original_size_bytes = parse_size(original_size_str)
            compressed_size_bytes = parse_size(compressed_size_str)
            compression_ratio = (
                f"{(1 - compressed_size_bytes / original_size_bytes) * 100:.1f}%"
                if original_size_bytes > 0 and compressed_size_bytes > 0
                else "N/A"
            )
            compression_method = dump_stats.get("compression_method", None)
            if compression_method:
                compression_method = str(compression_method).upper()
            else:
                compression_method = "N/A"
            stats: dict[str, str | int | float] = {
                "collections": str(dump_stats.get("collections", "N/A")),
                "documents": "N/A",  # Not counted in mongodump
                "original_size": original_size_str,
                "compressed_size": compressed_size_str,
                "compression_ratio": compression_ratio,
                "compression_method": compression_method,
            }
            await thread_service.send_completion(thread, download_url, stats)

            logger.info(
                "Backup completed successfully",
                collections=stats["collections"],
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
            self.mongo_service.disconnect()  # type: ignore[attr-defined]

    async def test_connections(self) -> dict[str, bool]:
        """
        Test connections to external services.

        Returns:
            Dictionary with connection test results.
        """
        results: dict[str, bool] = {}

        # Test MongoDB
        try:
            await self.mongo_service.connect()  # type: ignore[attr-defined]
            self.mongo_service.disconnect()  # type: ignore[attr-defined]
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
