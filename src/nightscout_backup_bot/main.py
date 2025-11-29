"""Main entry point for NightScout Backup Bot."""

import sys
import threading
from typing import TYPE_CHECKING

from .bot import create_bot
from .config import settings
from .logging_config import StructuredLogger, setup_logging

if TYPE_CHECKING:
    import uvicorn

logger = StructuredLogger("main")


def _run_api_server() -> None:
    """Run the FastAPI server in a background thread."""
    try:
        from .api.server import app

        logger.info("Starting NightScout Backup API server in background thread", port=8000)
        uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
    except Exception as e:
        logger.error("API server failed to start", error=str(e))


def main() -> None:
    """Main entry point for the bot."""
    setup_logging()

    logger.info("Starting NightScout Backup Bot", version="2.0.0", environment=settings.node_env)

    # Start API server in background thread if enabled
    if settings.enable_api_in_bot:
        api_thread = threading.Thread(target=_run_api_server, daemon=True)
        api_thread.start()
        logger.info("API server started in background thread")

    try:
        # Create and run bot
        bot = create_bot()
        bot.run(settings.discord_token)

    except KeyboardInterrupt:
        logger.info("Bot shutdown requested by user")
        sys.exit(0)
    except Exception as e:
        logger.critical("Fatal error during bot startup", error=str(e))
        sys.exit(1)
