"""Unit tests for CompressionService."""

import gzip
from pathlib import Path

import pytest

from nightscout_backup_bot.services.compression_service import CompressionService


class TestCompressionService:
    """Tests for CompressionService."""

    @pytest.fixture
    def test_content(self) -> str:
        """Create test content for compression."""
        # JSON-like content that compresses well
        return '{"test": "data", "repeated": "value"}' * 1000

    @pytest.mark.asyncio
    async def test_compress_gzip(self, tmp_path: Path, test_content: str) -> None:
        """Test gzip compression."""
        input_path = tmp_path / "test.json"
        output_path = tmp_path / "test.json.gz"

        input_path.write_text(test_content)

        compressed_size = await CompressionService.compress_gzip(input_path, output_path)

        assert output_path.exists()
        assert compressed_size > 0
        assert compressed_size < len(test_content)  # Should be smaller

        # Verify can decompress
        with gzip.open(output_path, "rt") as f:
            decompressed = f.read()
        assert decompressed == test_content

    @pytest.mark.asyncio
    async def test_compress_brotli(self, tmp_path: Path, test_content: str) -> None:
        """Test Brotli compression."""
        import brotli

        input_path = tmp_path / "test.json"
        output_path = tmp_path / "test.json.br"

        input_path.write_text(test_content)

        compressed_size = await CompressionService.compress_brotli(input_path, output_path)

        assert output_path.exists()
        assert compressed_size > 0
        assert compressed_size < len(test_content)  # Should be smaller

        # Verify can decompress
        with open(output_path, "rb") as f:
            decompressed = brotli.decompress(f.read()).decode()
        assert decompressed == test_content

    @pytest.mark.asyncio
    async def test_gzip_vs_brotli(self, tmp_path: Path, test_content: str) -> None:
        """Test that Brotli typically has better compression than gzip."""
        input_path = tmp_path / "test.json"
        gzip_path = tmp_path / "test.json.gz"
        brotli_path = tmp_path / "test.json.br"

        input_path.write_text(test_content)

        gzip_size = await CompressionService.compress_gzip(input_path, gzip_path)

        # Need to recreate input file as it might be consumed
        input_path.write_text(test_content)
        brotli_size = await CompressionService.compress_brotli(input_path, brotli_path)

        # Brotli should typically be smaller or similar
        assert brotli_size <= gzip_size * 1.1  # Allow 10% margin

    def test_format_size_bytes(self) -> None:
        """Test formatting bytes."""
        assert CompressionService.format_size(500) == "500.0B"

    def test_format_size_kilobytes(self) -> None:
        """Test formatting kilobytes."""
        assert CompressionService.format_size(1536) == "1.5KB"

    def test_format_size_megabytes(self) -> None:
        """Test formatting megabytes."""
        assert CompressionService.format_size(1572864) == "1.5MB"

    def test_format_size_gigabytes(self) -> None:
        """Test formatting gigabytes."""
        assert CompressionService.format_size(1610612736) == "1.5GB"
