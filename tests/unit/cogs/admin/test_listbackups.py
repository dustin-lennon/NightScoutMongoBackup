from unittest.mock import MagicMock

import pytest


@pytest.fixture
def mock_bot() -> MagicMock:
    """Create a mock bot instance."""
    bot = MagicMock()
    bot.latency = 0.045  # 45ms latency
    return bot
