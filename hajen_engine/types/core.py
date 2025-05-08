from enum import Enum
from multiprocessing import Process
from typing import List, Optional, TypedDict

from hajen_engine.libs.communication import QueueWrapper

class Task(TypedDict, total=True):
    name: str
    send_queue: Optional[QueueWrapper]
    receive_queue: QueueWrapper
    core: int
    high_priority: bool
    enabled: bool
    process: Optional[Process]
    logging_level: str
    options: Optional[dict[str, str]]

class UsedCore(TypedDict):
    high_priority: bool
    tasks: List[str]

class Libraries(Enum):
    ASYNCIO = "asyncio"
