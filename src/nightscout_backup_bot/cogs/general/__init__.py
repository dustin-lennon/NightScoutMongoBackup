"""General cogs package."""

from .dbstats import DBStatsCog
from .listbackups import ListBackupsCog
from .ping import GeneralCog
from .querydb import QueryDBCog

__all__ = ["GeneralCog", "QueryDBCog", "DBStatsCog", "ListBackupsCog"]


def setup(bot):  # type: ignore
    """Setup function to add all general cogs to bot."""
    from .dbstats import setup as setup_dbstats
    from .listbackups import setup as setup_listbackups
    from .ping import setup as setup_ping
    from .querydb import setup as setup_querydb

    setup_ping(bot)  # type: ignore
    setup_querydb(bot)  # type: ignore
    setup_dbstats(bot)  # type: ignore
    setup_listbackups(bot)  # type: ignore
