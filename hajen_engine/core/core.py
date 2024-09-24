import logging
import multiprocessing
import platform

from json import load
from hajen_engine.types.communication import Packet
from hajen_engine.types.shared import EnvData
from hajen_engine.libs.core import TaskManager


logger = logging.getLogger(__name__)


class Core:
    def __init__(self) -> None:
        super().__init__()

        # Dictionaries holding the human readable names, futures, and any
        # other userful information for the different components
        self.tasks: dict[str, dict] = {}

        with open("data/environment.json", "r") as json_file:
            self.env_data: EnvData = load(json_file)

        # Added it to self so other processes could have access if needed
        # Should eventually be moved over to a non-blocking file read but the
        # file is small enough to not matter for now
        self.receive_queue: multiprocessing.Queue[
                Packet
                 ] = multiprocessing.Queue()

        self.root_manager: TaskManager = TaskManager()

        self.core_count = multiprocessing.cpu_count()
        # Gives the OS, distro, version, and architecture
        # Added it to self so other processes could have easier access if
        # needed
        self.uname = platform.uname()
        logger.info(
            "hajen core initialized on {} {} {}".format(
                self.uname[0], self.uname[3], self.uname[4]
            )
        )

    async def main(self) -> None:
        """
        Main loop for the core
        """
        while True:
            await self.root_manager.manager()
