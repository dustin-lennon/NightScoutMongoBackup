"""Unit tests for FileService."""

from pathlib import Path

import pytest

from nightscout_backup_bot.services.file_service import FileService


class TestFileService:
    """Tests for FileService."""

    @pytest.fixture
    def file_service(self, temp_backup_dir: Path) -> FileService:
        """Create FileService instance with temp directory."""
        return FileService(backup_dir=temp_backup_dir)

    def test_backup_directory_creation(self, file_service: FileService, temp_backup_dir: Path) -> None:
        """Test backup directory is created."""
        assert temp_backup_dir.exists()
        assert temp_backup_dir.is_dir()

    def test_generate_filename(self, file_service: FileService) -> None:
        """Test filename generation."""
        filename = file_service.generate_filename("json")
        assert filename.startswith("nightscout-backup-")
        assert filename.endswith(".json")

    def test_get_backup_path(self, file_service: FileService, temp_backup_dir: Path) -> None:
        """Test getting backup path."""
        filename = "test-backup.json"
        path = file_service.get_backup_path(filename)
        assert path == temp_backup_dir / filename

    @pytest.mark.asyncio
    async def test_write_file(self, file_service: FileService, temp_backup_dir: Path) -> None:
        """Test writing file."""
        test_content = "test content"
        filepath = temp_backup_dir / "test.txt"

        size = await file_service.write_file(filepath, test_content)

        assert filepath.exists()
        assert filepath.read_text() == test_content
        assert size == len(test_content)

    @pytest.mark.asyncio
    async def test_delete_file(self, file_service: FileService, temp_backup_dir: Path) -> None:
        """Test deleting file."""
        filepath = temp_backup_dir / "test.txt"
        filepath.write_text("test")

        assert filepath.exists()
        await file_service.delete_file(filepath)
        assert not filepath.exists()

    @pytest.mark.asyncio
    async def test_delete_nonexistent_file(self, file_service: FileService, temp_backup_dir: Path) -> None:
        """Test deleting non-existent file doesn't raise error."""
        filepath = temp_backup_dir / "nonexistent.txt"
        await file_service.delete_file(filepath)  # Should not raise

    @pytest.mark.asyncio
    async def test_cleanup_old_backups(self, file_service: FileService, temp_backup_dir: Path) -> None:
        """Test cleaning up old backups."""
        # Create 10 backup files
        for i in range(10):
            filepath = temp_backup_dir / f"nightscout-backup-{i}.json"
            filepath.write_text(f"backup {i}")

        # Keep only 5 latest
        deleted_count = await file_service.cleanup_old_backups(keep_latest=5)

        assert deleted_count == 5
        remaining = list(temp_backup_dir.glob("nightscout-backup-*"))
        assert len(remaining) == 5

    @pytest.mark.asyncio
    async def test_cleanup_with_fewer_files(self, file_service: FileService, temp_backup_dir: Path) -> None:
        """Test cleanup when fewer files than keep_latest."""
        # Create 3 backup files
        for i in range(3):
            filepath = temp_backup_dir / f"nightscout-backup-{i}.json"
            filepath.write_text(f"backup {i}")

        deleted_count = await file_service.cleanup_old_backups(keep_latest=5)

        assert deleted_count == 0
        remaining = list(temp_backup_dir.glob("nightscout-backup-*"))
        assert len(remaining) == 3

    def test_get_disk_usage(self, file_service: FileService) -> None:
        """Test getting disk usage."""
        usage = file_service.get_disk_usage()

        assert "total" in usage
        assert "used" in usage
        assert "free" in usage
        assert usage["total"] > 0
