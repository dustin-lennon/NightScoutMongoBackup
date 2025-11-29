"""Tests for FastAPI server endpoints."""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from nightscout_backup_bot.api.server import app

client = TestClient(app)


def test_health_check() -> None:
    """Test health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_create_backup_success() -> None:
    """Test backup endpoint with successful backup."""
    with patch("nightscout_backup_bot.api.server.backup_service") as mock_service:
        mock_service.execute_backup_api = AsyncMock(
            return_value={
                "success": True,
                "url": "https://s3-backup-url",
                "stats": {
                    "collections": "5",
                    "compression_method": "GZIP",
                    "original_size": "10MB",
                    "compressed_size": "2MB",
                },
            }
        )

        response = client.post("/backup")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["url"] == "https://s3-backup-url"
        assert data["stats"]["collections"] == "5"
        mock_service.execute_backup_api.assert_called_once()


@pytest.mark.asyncio
async def test_create_backup_failure() -> None:
    """Test backup endpoint with failure."""
    with patch("nightscout_backup_bot.api.server.backup_service") as mock_service:
        mock_service.execute_backup_api = AsyncMock(side_effect=Exception("Backup failed"))

        response = client.post("/backup")
        assert response.status_code == 500
        assert "Backup failed" in response.json()["detail"]
        mock_service.execute_backup_api.assert_called_once()


@pytest.mark.asyncio
async def test_test_connections_success() -> None:
    """Test connections endpoint with successful tests."""
    with patch("nightscout_backup_bot.api.server.backup_service") as mock_service:
        mock_service.test_connections = AsyncMock(return_value={"mongodb": True, "s3": True})

        response = client.get("/test-connections")
        assert response.status_code == 200
        data = response.json()
        assert data["mongodb"] is True
        assert data["s3"] is True
        mock_service.test_connections.assert_called_once()


@pytest.mark.asyncio
async def test_test_connections_failure() -> None:
    """Test connections endpoint with failure."""
    with patch("nightscout_backup_bot.api.server.backup_service") as mock_service:
        mock_service.test_connections = AsyncMock(side_effect=Exception("Connection test failed"))

        response = client.get("/test-connections")
        assert response.status_code == 500
        assert "Connection test failed" in response.json()["detail"]
        mock_service.test_connections.assert_called_once()
