import asyncio

from typing import Optional, TypedDict

class Task(TypedDict, total=True):
    running: bool
    last_run: float
    cooldown: float
    task: Optional[asyncio.Task] | None

RunningTasks = dict[str, Task]
