"""Type stubs for dotenv_vault package."""

from os import PathLike
from typing import IO

def load_dotenv(
    dotenv_path: str | PathLike[str] | None = None,
    stream: IO[str] | None = None,
    verbose: bool = False,
    override: bool = True,
    interpolate: bool = True,
    encoding: str | None = "utf-8",
) -> bool: ...
