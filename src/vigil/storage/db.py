"""Database handle. One writer thread, any number of readers."""

from __future__ import annotations

from pathlib import Path
from typing import Union

from sqlalchemy.engine import Engine

from .schema import create_schema, make_engine


class Database:
    def __init__(self, path: Union[str, Path]) -> None:
        self.path = Path(path)
        self.engine: Engine = make_engine(self.path)

    def create(self) -> "Database":
        create_schema(self.engine)
        return self

    def close(self) -> None:
        self.engine.dispose()
