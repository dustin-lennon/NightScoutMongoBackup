"""S3 service for uploading backups to AWS S3."""

from pathlib import Path
from typing import Any
from uuid import uuid4

import aioboto3  # type: ignore
from botocore.exceptions import ClientError

from ..config import settings
from ..logging_config import StructuredLogger

logger = StructuredLogger("services.s3")


class S3Service:
    """Service for AWS S3 operations."""

    def __init__(self) -> None:
        """Initialize S3 service."""
        self.session = aioboto3.Session(
            aws_access_key_id=settings.aws_access_key_id,
            aws_secret_access_key=settings.aws_secret_access_key,
            region_name=settings.aws_region,
        )
        self.bucket_name = settings.s3_backup_bucket

    async def upload_file(
        self,
        file_path: Path,
        object_key: str | None = None,
        progress_callback: Any = None,
    ) -> str:
        """
        Upload file to S3 bucket.

        Args:
            file_path: Path to file to upload.
            object_key: S3 object key. If None, uses filename with UUID.
            progress_callback: Optional callback for upload progress.

        Returns:
            Public URL of uploaded file.
        """
        try:
            if object_key is None:
                # Add UUID to make filename unguessable but keep original name
                unique_id = str(uuid4())[:8]
                object_key = f"backups/{unique_id}-{file_path.name}"

            logger.info(
                "Uploading to S3",
                file=str(file_path),
                bucket=self.bucket_name,
                key=object_key,
            )

            async with self.session.client("s3") as s3_client:  # type: ignore
                # Upload with public-read ACL
                with open(file_path, "rb") as f:
                    await s3_client.upload_fileobj(  # type: ignore
                        f,
                        self.bucket_name,
                        object_key,
                        ExtraArgs={"ACL": "public-read"},
                        Callback=progress_callback,
                    )

            # Generate public URL
            url = self.generate_public_url(object_key)

            logger.info("S3 upload complete", url=url)
            return url

        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")  # type: ignore
            logger.error("S3 upload failed", error=str(e), error_code=error_code)
            raise
        except Exception as e:
            logger.error("S3 upload failed", error=str(e))
            raise

    async def test_connection(self) -> bool:
        """
        Test S3 connection and bucket access.

        Returns:
            True if connection successful, False otherwise.
        """
        try:
            async with self.session.client("s3") as s3_client:  # type: ignore
                # Try to list objects (limit 1 to minimize data transfer)
                await s3_client.list_objects_v2(Bucket=self.bucket_name, MaxKeys=1)  # type: ignore

            logger.info("S3 connection test successful", bucket=self.bucket_name)
            return True
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")  # type: ignore
            logger.error(
                "S3 connection test failed",
                bucket=self.bucket_name,
                error=str(e),
                error_code=error_code,
            )
            return False
        except Exception as e:
            logger.error("S3 connection test failed", error=str(e))
            return False

    async def delete_file(self, object_key: str) -> None:
        """
        Delete file from S3 bucket.

        Args:
            object_key: S3 object key to delete.
        """
        try:
            async with self.session.client("s3") as s3_client:  # type: ignore
                await s3_client.delete_object(Bucket=self.bucket_name, Key=object_key)  # type: ignore

            logger.info("Deleted S3 object", key=object_key)
        except ClientError as e:
            logger.error("S3 delete failed", key=object_key, error=str(e))
            raise
        except Exception as e:
            logger.error("S3 delete failed", error=str(e))
            raise

    async def list_backups(self, prefix: str = "backups/") -> list[dict[str, Any]]:
        """
        List backup files in S3 bucket.

        Args:
            prefix: S3 key prefix to filter by.

        Returns:
            List of dictionaries with backup file metadata.
        """
        try:
            async with self.session.client("s3") as s3_client:  # type: ignore
                response = await s3_client.list_objects_v2(Bucket=self.bucket_name, Prefix=prefix)  # type: ignore

                objects: list[dict[str, Any]] = []
                if "Contents" in response:
                    for obj in response["Contents"]:  # type: ignore
                        objects.append(
                            {
                                "key": obj["Key"],  # type: ignore
                                "size": obj["Size"],  # type: ignore
                                "last_modified": obj["LastModified"],  # type: ignore
                            }
                        )

                logger.debug("Listed S3 backups", count=len(objects))
                return objects
        except ClientError as e:
            logger.error("Failed to list S3 backups", error=str(e))
            raise
        except Exception as e:
            logger.error("Failed to list S3 backups", error=str(e))
            raise

    def generate_public_url(self, object_key: str) -> str:
        """
        Generate public URL for S3 object.

        Args:
            object_key: S3 object key.

        Returns:
            Public URL string.
        """
        # Standard S3 public URL format
        return f"https://{self.bucket_name}.s3.{settings.aws_region}.amazonaws.com/{object_key}"
