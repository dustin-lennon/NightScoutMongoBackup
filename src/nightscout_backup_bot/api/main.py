"""Entry point for running the FastAPI server."""

import uvicorn

from ..config import settings
from ..logging_config import StructuredLogger, setup_logging
from .server import app

logger = StructuredLogger("api.main")


def main() -> None:
    """Run the FastAPI server."""
    setup_logging()

    host = "0.0.0.0"
    port = 8000

    logger.info("Starting NightScout Backup API server", host=host, port=port, environment=settings.node_env)

    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level="info",
    )


if __name__ == "__main__":
    main()
