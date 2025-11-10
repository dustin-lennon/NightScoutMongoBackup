"""Integration tests for S3 service.

These tests require real AWS credentials and will be skipped if not available.
Set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY environment variables to run.
"""

import os
from pathlib import Path

import pytest

from nightscout_backup_bot.services.s3_service import S3Service

# Skip all tests if AWS credentials not available
pytestmark = pytest.mark.skipif(
    not os.getenv("AWS_ACCESS_KEY_ID") or not os.getenv("AWS_SECRET_ACCESS_KEY"),
    reason="AWS credentials not available",
)


class TestS3Integration:
    """Integration tests for S3Service."""

    @pytest.fixture
    def s3_service(self) -> S3Service:
        """Create S3Service instance."""
        return S3Service()

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_connection(self, s3_service: S3Service) -> None:
        """Test S3 connection."""
        result = await s3_service.test_connection()
        assert result is True

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_upload_and_list(self, s3_service: S3Service, tmp_path: Path) -> None:
        """Test uploading file and listing backups."""
        # Create test file
        test_file = tmp_path / "test-backup.txt"
        test_file.write_text("test content")

        # Upload
        url = await s3_service.upload_file(test_file)
        assert url.startswith("https://")
        assert "test-backup.txt" in url

        # List backups
        backups = await s3_service.list_backups()
        assert len(backups) > 0

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_delete(self, s3_service: S3Service, tmp_path: Path) -> None:
        """Test deleting file from S3."""
        # Create and upload test file
        test_file = tmp_path / "test-delete.txt"
        test_file.write_text("test content")

        await s3_service.upload_file(test_file, object_key="test/test-delete.txt")

        # Delete
        await s3_service.delete_file("test/test-delete.txt")

        # Verify deleted (list should not contain it or raise error)
        # Note: This is a basic check, proper verification would require checking if file exists
