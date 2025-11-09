"""Shared utility functions for command checks."""

from typing import Any

import disnake
from disnake.ext import commands

from ..config import settings


def is_owner() -> Any:
    """Check if the user is a bot owner."""

    async def predicate(inter: disnake.ApplicationCommandInteraction) -> bool:  # type: ignore
        """Predicate check for bot ownership."""
        if str(inter.author.id) not in settings.owner_id_list:
            await inter.response.send_message(
                "❌ This command is restricted to bot owners only.",
                ephemeral=True,
            )
            return False
        return True

    return commands.check(predicate)  # type: ignore
