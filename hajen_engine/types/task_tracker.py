import asyncio

from typing import Optional, TypedDict

class Job(TypedDict, total=True):
    running: bool
    last_run: float
    cooldown: float
    task: Optional[asyncio.Task] | None

JobList = dict[str, Job]
