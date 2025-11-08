"""Main entry point for NightScout Backup Bot."""

import sys

from .bot import create_bot
from .config import settings
from .logging_config import StructuredLogger, setup_logging

logger = StructuredLogger("main")


def main() -> None:
    """Main entry point for the bot."""
    setup_logging()

    logger.info("Starting NightScout Backup Bot", version="2.0.0", environment=settings.node_env)

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


if __name__ == "__main__":
    main()
