import asyncio
import functools
import json
import logging
import struct

from multiprocessing import shared_memory
from typing import Coroutine, Optional

logger = logging.getLogger(__name__)

async def get_env_data():
    """
    Gets env_data from shared_memory and should be properly handling the memory reading
    """
    shm = shared_memory.SharedMemory(name='env_data')
    try:
        size = struct.unpack('Q', shm.buf[:8])[0]
        return json.loads(bytes(shm.buf[8:8 + size]).decode('utf-8'))
    finally:
        shm.close()

def create_task(
        coroutine: Coroutine,
        name: str,
        loop: Optional[asyncio.AbstractEventLoop] = None,
    ) -> asyncio.Task:
    """
    This function adds a callback to the asyncio.create_task() to handle when a
    task raises an exception
    """
    if loop is None:
        loop = asyncio.get_running_loop()
    task = loop.create_task(coroutine, name=name)
    task.add_done_callback(
        functools.partial(
            _handle_task_result,
        )
    )
    return task

def _handle_task_result(
        task: asyncio.Task,
    ) -> None:
    """
    Checks `task.result()` for a result, if the result is
    `asyncio.CancelledError` then pass and don't raise anything.
    `asyncio.CancelledError` is raised when the task ends. All other errors
    should be logged
    """
    try:
        task.result()
    except asyncio.CancelledError:
        pass
    except Exception:
        logger.exception("Task raised an exception")
