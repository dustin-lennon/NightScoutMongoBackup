"""Unit tests for configuration and settings."""

import os
from unittest.mock import patch

from nightscout_backup_bot.config import CompressionMethod, Settings


class TestMongoConnectionString:
    """Test MongoDB connection string generation."""

    def test_mongo_connection_string_basic(self) -> None:
        """Test basic connection string without special characters."""
        with patch.dict(
            os.environ,
            {
                "DISCORD_TOKEN": "test_token",
                "DISCORD_CLIENT_ID": "test_client_id",
                "BACKUP_CHANNEL_ID": "test_channel",
                "MONGO_HOST": "cluster.mongodb.net",
                "MONGO_USERNAME": "testuser",
                "MONGO_PASSWORD": "simplepass",
                "MONGO_DB": "testdb",
                "AWS_ACCESS_KEY_ID": "test_access",
                "AWS_SECRET_ACCESS_KEY": "test_secret",
                "S3_BACKUP_BUCKET": "test_bucket",
            },
        ):
            settings = Settings.model_validate({})
            connection_string = settings.mongo_connection_string

            # Should match MongoDB Atlas format (no database in path)
            assert "mongodb+srv://testuser:simplepass@cluster.mongodb.net/?" in connection_string
            assert "retryWrites=true" in connection_string
            assert "w=majority" in connection_string

    def test_mongo_connection_string_with_special_chars(self) -> None:
        """Test connection string properly URL-encodes passwords with special characters."""
        with patch.dict(
            os.environ,
            {
                "DISCORD_TOKEN": "test_token",
                "DISCORD_CLIENT_ID": "test_client_id",
                "BACKUP_CHANNEL_ID": "test_channel",
                "MONGO_HOST": "cluster.mongodb.net",
                "MONGO_USERNAME": "testuser",
                "MONGO_PASSWORD": "p@ss:w#rd/123$",  # Special chars: @ : # / $
                "MONGO_DB": "testdb",
                "AWS_ACCESS_KEY_ID": "test_access",
                "AWS_SECRET_ACCESS_KEY": "test_secret",
                "S3_BACKUP_BUCKET": "test_bucket",
            },
        ):
            settings = Settings.model_validate({})
            connection_string = settings.mongo_connection_string

            # Password should be URL-encoded
            # p@ss:w#rd/123$ becomes p%40ss%3Aw%23rd%2F123%24
            assert "p%40ss%3Aw%23rd%2F123%24" in connection_string
            # Original password should NOT appear in connection string
            assert "p@ss:w#rd/123$" not in connection_string

    def test_mongo_connection_string_with_username_special_chars(self) -> None:
        """Test connection string properly URL-encodes usernames with special characters."""
        with patch.dict(
            os.environ,
            {
                "DISCORD_TOKEN": "test_token",
                "DISCORD_CLIENT_ID": "test_client_id",
                "BACKUP_CHANNEL_ID": "test_channel",
                "MONGO_HOST": "cluster.mongodb.net",
                "MONGO_USERNAME": "user@domain.com",  # Email-style username
                "MONGO_PASSWORD": "simplepass",
                "MONGO_DB": "testdb",
                "AWS_ACCESS_KEY_ID": "test_access",
                "AWS_SECRET_ACCESS_KEY": "test_secret",
                "S3_BACKUP_BUCKET": "test_bucket",
            },
        ):
            settings = Settings.model_validate({})
            connection_string = settings.mongo_connection_string

            # Username should be URL-encoded
            # user@domain.com becomes user%40domain.com
            assert "user%40domain.com" in connection_string
            # Original username should NOT appear before the @ host separator
            assert "mongodb+srv://user@domain.com" not in connection_string

    def test_mongo_connection_string_with_spaces(self) -> None:
        """Test connection string handles passwords with spaces."""
        with patch.dict(
            os.environ,
            {
                "DISCORD_TOKEN": "test_token",
                "DISCORD_CLIENT_ID": "test_client_id",
                "BACKUP_CHANNEL_ID": "test_channel",
                "MONGO_HOST": "cluster.mongodb.net",
                "MONGO_USERNAME": "testuser",
                "MONGO_PASSWORD": "my password 123",  # Spaces in password
                "MONGO_DB": "testdb",
                "AWS_ACCESS_KEY_ID": "test_access",
                "AWS_SECRET_ACCESS_KEY": "test_secret",
                "S3_BACKUP_BUCKET": "test_bucket",
            },
        ):
            settings = Settings.model_validate({})
            connection_string = settings.mongo_connection_string

            # Spaces should be URL-encoded as %20
            assert "my%20password%20123" in connection_string

    def test_mongo_connection_string_with_percent_chars(self) -> None:
        """Test connection string handles passwords with percent signs."""
        with patch.dict(
            os.environ,
            {
                "DISCORD_TOKEN": "test_token",
                "DISCORD_CLIENT_ID": "test_client_id",
                "BACKUP_CHANNEL_ID": "test_channel",
                "MONGO_HOST": "cluster.mongodb.net",
                "MONGO_USERNAME": "testuser",
                "MONGO_PASSWORD": "pass%word",  # Percent sign in password
                "MONGO_DB": "testdb",
                "AWS_ACCESS_KEY_ID": "test_access",
                "AWS_SECRET_ACCESS_KEY": "test_secret",
                "S3_BACKUP_BUCKET": "test_bucket",
            },
        ):
            settings = Settings.model_validate({})
            connection_string = settings.mongo_connection_string

            # Percent should be double-encoded
            assert "pass%25word" in connection_string

    def test_mongo_connection_includes_database(self) -> None:
        """Test connection string follows MongoDB Atlas format (database not in path)."""
        with patch.dict(
            os.environ,
            {
                "DISCORD_TOKEN": "test_token",
                "DISCORD_CLIENT_ID": "test_client_id",
                "BACKUP_CHANNEL_ID": "test_channel",
                "MONGO_HOST": "cluster.mongodb.net",
                "MONGO_USERNAME": "testuser",
                "MONGO_PASSWORD": "testpass",
                "MONGO_DB": "mydatabase",
                "AWS_ACCESS_KEY_ID": "test_access",
                "AWS_SECRET_ACCESS_KEY": "test_secret",
                "S3_BACKUP_BUCKET": "test_bucket",
            },
        ):
            settings = Settings.model_validate({})
            connection_string = settings.mongo_connection_string

            # MongoDB Atlas format: no database in path, use /? for query params
            assert "/?retryWrites=true" in connection_string
            # Database should NOT be in the connection string path
            assert "/mydatabase?" not in connection_string

    def test_mongo_connection_includes_required_params(self) -> None:
        """Test connection string includes required MongoDB parameters."""
        with patch.dict(
            os.environ,
            {
                "DISCORD_TOKEN": "test_token",
                "DISCORD_CLIENT_ID": "test_client_id",
                "BACKUP_CHANNEL_ID": "test_channel",
                "MONGO_HOST": "cluster.mongodb.net",
                "MONGO_USERNAME": "testuser",
                "MONGO_PASSWORD": "testpass",
                "MONGO_DB": "testdb",
                "AWS_ACCESS_KEY_ID": "test_access",
                "AWS_SECRET_ACCESS_KEY": "test_secret",
                "S3_BACKUP_BUCKET": "test_bucket",
            },
        ):
            settings = Settings.model_validate({})
            connection_string = settings.mongo_connection_string

            assert "retryWrites=true" in connection_string
            assert "w=majority" in connection_string


class TestCompressionMethod:
    """Test CompressionMethod enum."""

    def test_compression_method_enum_values(self) -> None:
        """Test that CompressionMethod enum has expected values."""
        assert CompressionMethod.GZIP.value == "gzip"
        assert CompressionMethod.BROTLI.value == "brotli"

    def test_compression_method_default(self) -> None:
        """Test that default compression method is GZIP."""
        with patch.dict(
            os.environ,
            {
                "DISCORD_TOKEN": "test_token",
                "DISCORD_CLIENT_ID": "test_client_id",
                "BACKUP_CHANNEL_ID": "test_channel",
                "MONGO_HOST": "cluster.mongodb.net",
                "MONGO_USERNAME": "testuser",
                "MONGO_PASSWORD": "testpass",
                "MONGO_DB": "testdb",
                "AWS_ACCESS_KEY_ID": "test_access",
                "AWS_SECRET_ACCESS_KEY": "test_secret",
                "S3_BACKUP_BUCKET": "test_bucket",
            },
        ):
            settings = Settings.model_validate({})
            assert settings.compression_method == CompressionMethod.GZIP

    def test_compression_method_from_env_gzip(self) -> None:
        """Test that compression method can be set to gzip via environment variable."""
        with patch.dict(
            os.environ,
            {
                "DISCORD_TOKEN": "test_token",
                "DISCORD_CLIENT_ID": "test_client_id",
                "BACKUP_CHANNEL_ID": "test_channel",
                "MONGO_HOST": "cluster.mongodb.net",
                "MONGO_USERNAME": "testuser",
                "MONGO_PASSWORD": "testpass",
                "MONGO_DB": "testdb",
                "AWS_ACCESS_KEY_ID": "test_access",
                "AWS_SECRET_ACCESS_KEY": "test_secret",
                "S3_BACKUP_BUCKET": "test_bucket",
                "COMPRESSION_METHOD": "gzip",
            },
        ):
            settings = Settings.model_validate({})
            assert settings.compression_method == CompressionMethod.GZIP

    def test_compression_method_from_env_brotli(self) -> None:
        """Test that compression method can be set to brotli via environment variable."""
        with patch.dict(
            os.environ,
            {
                "DISCORD_TOKEN": "test_token",
                "DISCORD_CLIENT_ID": "test_client_id",
                "BACKUP_CHANNEL_ID": "test_channel",
                "MONGO_HOST": "cluster.mongodb.net",
                "MONGO_USERNAME": "testuser",
                "MONGO_PASSWORD": "testpass",
                "MONGO_DB": "testdb",
                "AWS_ACCESS_KEY_ID": "test_access",
                "AWS_SECRET_ACCESS_KEY": "test_secret",
                "S3_BACKUP_BUCKET": "test_bucket",
                "COMPRESSION_METHOD": "brotli",
            },
        ):
            settings = Settings.model_validate({})
            assert settings.compression_method == CompressionMethod.BROTLI

    def test_compression_method_enum_string_comparison(self) -> None:
        """Test that CompressionMethod enum can be compared with strings."""
        # This is important for backward compatibility
        assert CompressionMethod.GZIP.value == "gzip"
        assert CompressionMethod.BROTLI.value == "brotli"
