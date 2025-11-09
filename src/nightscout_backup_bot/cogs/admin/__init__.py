"""Admin cogs package."""

from .backup import AdminCog
from .backup import setup as setup_backup
from .site import SiteCog
from .site import setup as setup_site

__all__ = ["AdminCog", "SiteCog", "setup_backup", "setup_site"]
