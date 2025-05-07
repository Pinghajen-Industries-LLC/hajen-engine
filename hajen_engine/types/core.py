from enum import Enum
from typing import List, TypedDict


class Task(TypedDict, total=True):
    enabled: bool
    high_priority: bool
    logging_level: str
    options: dict[str, str]
    core: int

class UsedCore(TypedDict):
    high_priority: bool
    tasks: List[str]

class Libraries(Enum):
    ASYNCIO = "asyncio"
