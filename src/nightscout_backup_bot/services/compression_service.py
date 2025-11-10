"""Compression service for backup files."""

import gzip
from pathlib import Path

import brotli  # type: ignore[import-untyped]

from ..logging_config import StructuredLogger

logger = StructuredLogger("services.compression")


class CompressionService:
    """Service for compressing backup files."""

    @staticmethod
    async def compress_gzip(input_path: Path, output_path: Path) -> int:
        """
        Compress file using gzip.

        Args:
            input_path: Path to input file.
            output_path: Path to output compressed file.

        Returns:
            Size of compressed file in bytes.
        """
        try:
            logger.info("Compressing with gzip", input=str(input_path))

            with open(input_path, "rb") as f_in:
                with gzip.open(output_path, "wb", compresslevel=9) as f_out:
                    f_out.write(f_in.read())

            compressed_size = output_path.stat().st_size
            original_size = input_path.stat().st_size
            reduction = ((original_size - compressed_size) / original_size) * 100

            logger.info(
                "Gzip compression complete",
                original_size=original_size,
                compressed_size=compressed_size,
                reduction_percent=f"{reduction:.1f}",
            )

            return compressed_size
        except Exception as e:
            logger.error("Gzip compression failed", error=str(e))
            raise

    @staticmethod
    async def compress_brotli(input_path: Path, output_path: Path) -> int:
        """
        Compress file using Brotli.

        Args:
            input_path: Path to input file.
            output_path: Path to output compressed file.

        Returns:
            Size of compressed file in bytes.
        """
        try:
            logger.info("Compressing with Brotli", input=str(input_path))

            with open(input_path, "rb") as f_in:
                data = f_in.read()
                compressed: bytes = brotli.compress(data, quality=11)  # type: ignore[no-untyped-call]

            with open(output_path, "wb") as f_out:
                f_out.write(compressed)  # type: ignore[arg-type]

            compressed_size = output_path.stat().st_size
            original_size = input_path.stat().st_size
            reduction = ((original_size - compressed_size) / original_size) * 100

            logger.info(
                "Brotli compression complete",
                original_size=original_size,
                compressed_size=compressed_size,
                reduction_percent=f"{reduction:.1f}",
            )

            return compressed_size
        except Exception as e:
            logger.error("Brotli compression failed", error=str(e))
            raise

    @staticmethod
    def format_size(size_bytes: int) -> str:
        """
        Format byte size to human-readable string.

        Args:
            size_bytes: Size in bytes.

        Returns:
            Formatted string (e.g., "1.2MB").
        """
        size: float = float(size_bytes)
        for unit in ["B", "KB", "MB", "GB"]:
            if size < 1024.0:
                return f"{size:.1f}{unit}"
            size /= 1024.0
        return f"{size:.1f}TB"
