"""Entry point for running the FastAPI server."""

import uvicorn

from ..config import settings
from ..logging_config import StructuredLogger, setup_logging
from .server import app

logger = StructuredLogger("api.main")


def main() -> None:
    """Run the FastAPI server."""
    setup_logging()

    # Initialize Sentry if configured
    if settings.sentry_dsn:
        try:
            import sentry_sdk
            from sentry_sdk.integrations.fastapi import FastApiIntegration
            from sentry_sdk.integrations.uvicorn import UvicornIntegration  # type: ignore[import-not-found]

            sentry_sdk.init(
                dsn=settings.sentry_dsn,
                environment=settings.node_env,
                traces_sample_rate=1.0 if not settings.is_production else 0.1,
                integrations=[
                    FastApiIntegration(),
                    UvicornIntegration(),
                ],
            )
            logger.info("Sentry initialized", environment=settings.node_env)
        except Exception as e:
            logger.warning("Failed to initialize Sentry", error=str(e))

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
