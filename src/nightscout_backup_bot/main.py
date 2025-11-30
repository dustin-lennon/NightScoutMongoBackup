"""Main entry point for NightScout Backup Bot."""

import asyncio
import sys
import threading

import uvicorn

from .bot import create_bot
from .config import settings
from .logging_config import StructuredLogger, setup_logging

logger = StructuredLogger("main")


def _run_api_server() -> None:
    """Run the FastAPI server in a background thread with its own event loop."""
    import asyncio

    try:
        # Setup logging for this thread
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
                logger.info("Sentry initialized in API server thread", environment=settings.node_env)
            except Exception as e:
                logger.warning("Failed to initialize Sentry in API server thread", error=str(e))

        from .api.server import app

        # Create a new event loop for this thread
        # This ensures it doesn't interfere with the main thread's event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        logger.info("Starting NightScout Backup API server in background thread", port=8000)

        # Use uvicorn's Server class to have more control over the event loop
        config = uvicorn.Config(app, host="0.0.0.0", port=8000, log_level="info")
        server = uvicorn.Server(config)
        loop.run_until_complete(server.serve())
    except Exception as e:
        logger.error("API server failed to start", error=str(e))


def main() -> None:
    """Main entry point for the bot."""
    setup_logging()

    logger.info("Starting NightScout Backup Bot", version="2.0.0", environment=settings.node_env)

    # Start API server in background thread if enabled
    # The API server thread will create its own event loop, so we start it first
    if settings.enable_api_in_bot:
        api_thread = threading.Thread(target=_run_api_server, daemon=True)
        api_thread.start()
        logger.info("API server started in background thread")

    try:
        # Ensure an event loop exists for Python 3.10+ compatibility
        # Do this after starting the API thread to avoid conflicts
        try:
            _ = asyncio.get_event_loop()
        except RuntimeError:
            # No event loop exists - create one
            # bot.run() will manage its own loop, but this prevents the error
            asyncio.set_event_loop(asyncio.new_event_loop())

        # Create and run bot
        bot = create_bot()
        bot.run(settings.discord_token)

    except KeyboardInterrupt:
        logger.info("Bot shutdown requested by user")
        sys.exit(0)
    except Exception as e:
        logger.critical("Fatal error during bot startup", error=str(e))
        sys.exit(1)


if __name__ == "__main__":
    main()
