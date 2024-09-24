from enum import Enum
from typing import TypedDict


class Task(TypedDict, total=True):
    enabled: bool
    high_priority: bool
    logging_level: str
    options: dict[str, str]
    core: int


class Libraries(Enum):
    ASYNCIO = "asyncio"
