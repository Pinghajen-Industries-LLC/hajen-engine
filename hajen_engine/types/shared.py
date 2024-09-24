from typing import TypedDict
from asyncio import Future
from multiprocessing import Process
from hajen_engine.types.core import Task
from hajen_engine.libs.communication import QueueWrapper


class RunningTasks(TypedDict, total=True):
    name: str
    send_queue: QueueWrapper
    receive_queue: QueueWrapper
    core: int
    enabled: bool
    process: Future | Process


class EnvData(TypedDict, total=True):
    debug: bool
    root: Task
    core: Task
    tasks: dict[str, Task]
    library_logging_levels: dict[str, str]
