import asyncio

from typing import TypedDict

class Task(TypedDict, total=True):
    running: bool
    last_run: float
    cooldown: float
    task: asyncio.Task

RunningTasks = dict[str, Task]
