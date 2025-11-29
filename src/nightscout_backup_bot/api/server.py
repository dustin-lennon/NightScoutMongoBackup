"""FastAPI server for backup operations."""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from ..config import settings
from ..logging_config import StructuredLogger
from ..services.backup_service import BackupService

logger = StructuredLogger("api.server")

app = FastAPI(
    title="NightScout Backup API",
    description="HTTP API for triggering MongoDB backups",
    version="1.0.0",
)

# Configure CORS - allow origins from settings
cors_origins = [origin.strip() for origin in settings.backup_api_cors_origins.split(",") if origin.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

backup_service = BackupService()


@app.get("/health")
async def health_check() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "ok"}


@app.post("/backup")
async def create_backup() -> dict[str, object]:
    """
    Trigger a MongoDB backup.

    Returns:
        Dictionary with backup results including success status, S3 URL, and statistics.
    """
    try:
        logger.info("Backup request received via API")
        result = await backup_service.execute_backup_api()
        return result
    except Exception as e:
        error_msg = str(e)
        logger.error("Backup API request failed", error=error_msg)
        raise HTTPException(status_code=500, detail=error_msg) from e


@app.get("/test-connections")
async def test_connections() -> dict[str, bool]:
    """
    Test connections to MongoDB and S3.

    Returns:
        Dictionary with connection test results.
    """
    try:
        results = await backup_service.test_connections()
        return results
    except Exception as e:
        error_msg = str(e)
        logger.error("Connection test failed", error=error_msg)
        raise HTTPException(status_code=500, detail=error_msg) from e
