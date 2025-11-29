"""Backup service that orchestrates the full backup workflow."""

from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import cast

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

    mongo_service: MongoService
    s3_service: S3Service
    file_service: FileService
    compression_service: CompressionService

    def __init__(self) -> None:
        """Initialize backup service with all sub-services."""
        self.mongo_service = MongoService()
        self.s3_service = S3Service()
        self.file_service = FileService()
        self.compression_service = CompressionService()

    async def _execute_backup_core(
        self, on_progress: Callable[[str], Awaitable[None]] | None = None
    ) -> tuple[str, dict[str, str | int | float]]:
        """
        Core backup workflow with optional progress callbacks.

        Args:
            on_progress: Optional async callback function that receives progress messages.

        Returns:
            Tuple of (download_url, stats_dict).
        """
        try:
            if on_progress:
                await on_progress("🔄 Starting backup process...")
            logger.info("Starting backup process")

            if on_progress:
                await on_progress("🔄 Connecting to MongoDB Atlas...")
            await self.mongo_service.connect()  # type: ignore[attr-defined]
            if on_progress:
                await on_progress("✅ Connected to MongoDB Atlas")
            logger.info("Connected to MongoDB Atlas")

            # Dump database
            if on_progress:
                await on_progress("🔄 Dumping MongoDB database...")
            logger.info("Dumping MongoDB database")
            backup_dir = "backups"
            dump_stats = await self.mongo_service.dump_database(backup_dir)
            if on_progress:
                await on_progress(
                    f"✅ Database dumped ({dump_stats['original_size']} uncompressed, {dump_stats['compressed_size']} compressed)"
                )
            logger.info(
                "Database dumped",
                original_size=dump_stats.get("original_size"),
                compressed_size=dump_stats.get("compressed_size"),
            )

            # Upload to S3
            if on_progress:
                await on_progress("🔄 Uploading to AWS S3...")
            logger.info("Uploading to AWS S3")
            archive_path_str = cast(str, dump_stats["archive_path"])
            download_url = await self.s3_service.upload_file(Path(archive_path_str))
            if on_progress:
                await on_progress("✅ Uploaded to S3")
            logger.info("Uploaded to S3", url=download_url)

            # Cleanup local files
            if on_progress:
                await on_progress("🔄 Cleaning up local files...")
            logger.info("Cleaning up local files")
            await self.file_service.delete_file(archive_path_str)
            if on_progress:
                await on_progress("✅ Local files cleaned up")
            logger.info("Local files cleaned up")

            # Calculate stats
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

            logger.info(
                "Backup completed successfully",
                collections=cast(str, stats["collections"]),
                url=download_url,
            )

            return download_url, stats

        finally:
            self.mongo_service.disconnect()  # type: ignore[attr-defined]

    async def execute_backup(
        self,
        channel: disnake.TextChannel,
        _collections: list[str] | None = None,
    ) -> dict[str, object]:
        """
        Execute full backup workflow with Discord progress updates (mongodump-based).

        Args:
            channel: Discord channel for creating progress thread.
            _collections: (Unused) for compatibility.

        Returns:
            Dictionary with backup results and statistics.
        """
        thread_service = DiscordThreadService(channel)
        timestamp = datetime.now(UTC).strftime("%m.%d.%Y")
        thread = await thread_service.create_backup_thread(timestamp)

        try:
            # Create progress callback that sends messages to Discord thread
            async def on_progress(message: str) -> None:
                _ = await thread_service.send_progress(thread, message)

            download_url, stats = await self._execute_backup_core(on_progress=on_progress)
            _ = await thread_service.send_completion(thread, download_url, cast(dict[str, object], stats))

            return {
                "success": True,
                "url": download_url,
                "stats": stats,
                "thread_id": thread.id,
            }

        except Exception as e:
            error_msg = str(e)
            logger.error("Backup failed", error=error_msg)
            _ = await thread_service.send_error(thread, error_msg)
            raise

    async def execute_backup_api(self) -> dict[str, object]:
        """
        Execute full backup workflow without Discord (for API usage).

        Returns:
            Dictionary with backup results and statistics.
        """
        try:
            download_url, stats = await self._execute_backup_core()
            return {
                "success": True,
                "url": download_url,
                "stats": stats,
            }
        except Exception as e:
            error_msg = str(e)
            logger.error("Backup failed", error=error_msg)
            raise

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
