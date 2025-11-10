"""File service for local backup file management."""

import shutil
from datetime import UTC, datetime
from pathlib import Path

from ..logging_config import StructuredLogger

logger = StructuredLogger("services.file")


class FileService:
    """Service for managing local backup files."""

    def __init__(self, backup_dir: Path | None = None) -> None:
        """
        Initialize file service.

        Args:
            backup_dir: Directory for storing backups. Defaults to ./backups/
        """
        self.backup_dir = backup_dir or Path("backups")
        self._ensure_backup_directory()

    def _ensure_backup_directory(self) -> None:
        """Ensure backup directory exists."""
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        logger.debug("Backup directory ready", path=str(self.backup_dir))

    def generate_filename(self, extension: str = "json") -> str:
        """
        Generate timestamped backup filename.

        Args:
            extension: File extension (without dot).

        Returns:
            Filename string.
        """
        timestamp = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S UTC")
        filename = f"nightscout-backup-{timestamp}.{extension}"
        logger.debug("Generated filename", filename=filename)
        return filename

    def get_backup_path(self, filename: str) -> Path:
        """
        Get full path for backup file.

        Args:
            filename: Backup filename.

        Returns:
            Full path to backup file.
        """
        return self.backup_dir / filename

    async def write_file(self, filepath: Path, content: str) -> int:
        """
        Write content to file.

        Args:
            filepath: Path to file.
            content: Content to write.

        Returns:
            Size of written file in bytes.
        """
        try:
            filepath.write_text(content, encoding="utf-8")
            size = filepath.stat().st_size
            logger.info("Wrote file", path=str(filepath), size_bytes=size)
            return size
        except Exception as e:
            logger.error("Failed to write file", path=str(filepath), error=str(e))
            raise

    async def delete_file(self, filepath: Path | str) -> None:
        """
        Delete file if it exists.

        Args:
            filepath: Path to file to delete.
        """
        try:
            # Ensure filepath is a Path object
            if isinstance(filepath, str):
                filepath = Path(filepath)
            if filepath.exists():
                filepath.unlink()
                logger.info("Deleted file", path=str(filepath))
            else:
                logger.debug("File does not exist, skipping delete", path=str(filepath))
        except Exception as e:
            logger.error("Failed to delete file", path=str(filepath), error=str(e))
            raise

    async def cleanup_old_backups(self, keep_latest: int = 5) -> int:
        """
        Clean up old backup files, keeping only the latest N files.

        Args:
            keep_latest: Number of recent backups to keep.

        Returns:
            Number of files deleted.
        """
        try:
            # Get all backup files sorted by modification time (newest first)
            backup_files = sorted(
                self.backup_dir.glob("nightscout-backup-*"),
                key=lambda p: p.stat().st_mtime,
                reverse=True,
            )

            if len(backup_files) <= keep_latest:
                logger.debug("No old backups to clean up", total=len(backup_files), keep=keep_latest)
                return 0

            # Delete old files
            files_to_delete = backup_files[keep_latest:]
            deleted_count = 0

            for filepath in files_to_delete:
                await self.delete_file(filepath)
                deleted_count += 1

            logger.info("Cleaned up old backups", deleted=deleted_count, kept=keep_latest)
            return deleted_count

        except Exception as e:
            logger.error("Failed to cleanup old backups", error=str(e))
            raise

    def get_disk_usage(self) -> dict[str, int]:
        """
        Get disk usage information for backup directory.

        Returns:
            Dictionary with total, used, and free space in bytes.
        """
        try:
            usage = shutil.disk_usage(self.backup_dir)
            return {
                "total": usage.total,
                "used": usage.used,
                "free": usage.free,
            }
        except Exception as e:
            logger.error("Failed to get disk usage", error=str(e))
            raise
