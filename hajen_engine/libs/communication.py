from typing import Dict, Optional
from queue import Empty
import multiprocessing

from hajen_engine.types.communication import Packet


class QueueWrapper:
    def __init__(self):
        self.queue: multiprocessing.Queue[Packet] = multiprocessing.Queue()

    def put(self, item):
        self.queue.put(item)

    def get(self) -> Optional[Packet]:
        try:
            return self.queue.get(block=False)
        except Empty:
            return None

    def empty(self):
        return self.queue.empty()
