"""Shared utility functions for command checks."""

from collections.abc import Callable
from typing import TypeVar, cast

import disnake
from disnake.ext import commands

from ..config import settings

T = TypeVar("T", bound=Callable[..., object])


def is_owner() -> Callable[[T], T]:
    """Check if the user is a bot owner."""

    async def predicate(inter: disnake.ApplicationCommandInteraction[disnake.Client]) -> bool:
        """Predicate check for bot ownership."""
        if str(inter.author.id) not in settings.owner_id_list:
            await inter.response.send_message(
                "❌ This command is restricted to bot owners only.",
                ephemeral=True,
            )
            return False
        return True

    # commands.check works with slash command predicates at runtime despite type mismatch
    # The type mismatch is a known limitation of disnake's type stubs for slash commands
    result = commands.check(predicate)  # type: ignore[arg-type, call-overload]
    return cast(Callable[[T], T], result)
