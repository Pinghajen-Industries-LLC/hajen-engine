import asyncio
import datetime
import importlib
import logging
import multiprocessing
import platform
import time

from json import load
from multiprocessing import Queue, Manager
from hajen_engine.custom_types.communication import Packet
from hajen_engine.custom_types.core import EnvData

from asyncio_task_logger import task_logger
from typing import Any, Literal
from logging.handlers import RotatingFileHandler



logger = logging.getLogger(__name__)


class Core:
    def __init__(self, env_data) -> None:
        super().__init__()

        # Dictionaries holding the human readable names, futures, and any
        # other userful information for the different components
        self.tasks: dict[str, dict[str, Any]] = {
                                        "drivers": {},
                                        "processes": {},
                                        "core": {},
                                        }

        with open("data/environment.json", "r") as json_file:
            self.env = load(json_file)

        # Added it to self so other processes could have access if needed
        # Should eventually be moved over to a non-blocking file read but the
        # file is small enough to not matter for now
        self.env_data: EnvData = env_data

        self.logger: multiprocessing.Queue[tuple[str, str]] = multiprocessing.Queue()
        self.low_priority_setup_queue: multiprocessing.Queue[tuple[Literal['SETUP'], tuple[str, str]]] = multiprocessing.Queue()

        self.low_priority_receive_queue: multiprocessing.Queue[Packet] = multiprocessing.Queue()
        self.low_priority_send_queue: multiprocessing.Queue[Packet] = multiprocessing.Queue()
        self.core_count = multiprocessing.cpu_count()
        self.last_cpu_affinity = 1
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
        result = task_logger.create_task(
                self.handle_log(),
                logger=logger,
                message="Task raised an exception"
                )

        # Must wait for these tasks to complete before continuing
        # Will want to make it so these can constantly run to dynamically
        # enable and disable processes and drivers
        # await driver_manager_future
        # await process_manager_future
        low_priority_manager = multiprocessing.Process(
                target=self.run_low_priority_manager,
                kwargs={
                    "logger": logger,
                    "receive_queue": self.low_priority_receive_queue,
                    "send_queue": self.low_priority_send_queue,
                    "low_priority_setup_queue": self.low_priority_setup_queue,
                    }
                )
        low_priority_manager.start()
        self.manager = multiprocessing.Manager()
        for task_type in self.env_data["tasks"]:
            logger.debug(f"{task_type}")
            for task in self.env_data["tasks"][task_type]:
                logger.debug(f"{task}")
                # Checks if the task isenabled and not already initialized
                if (
                        self.env_data["tasks"][task_type][task]['enabled']
                        and task not in self.tasks[task_type].keys()
                    ):
                    if self.env_data['tasks'][task_type][task]['high_priority']:
                        temp_object, receive_queue, send_queue = self.setup_object(
                                manager_type=task_type,
                                object_name=task,
                                )
                        logger.info("Setting up high priority tasks")
                        try:
                            temp_process = multiprocessing.Process(target=temp_object.main, name=task)
                            temp_process.start()
                            self.tasks[task_type][task] = {
                                "send_queue": send_queue,
                                "receive_queue": receive_queue,
                                "object": temp_object,
                                "enabled": True,
                                "process": temp_process,
                            }
                        except Exception as e:
                            logger.debug(e)
                    else:
                        logger.info("Setting up low priority tasks")
                        self.tasks[task_type][task] = {
                                "send_queue": self.low_priority_send_queue,
                                "receive_queue": self.low_priority_receive_queue,
                                "object": None,
                                "enabled": True,
                                "process": low_priority_manager,
                                }
                        packet: tuple[Literal['SETUP'], tuple[str, str]] = ("SETUP", (task_type, task))
                        self.low_priority_setup_queue.put(packet)
                # Marking as NotImplemented for now until this functionality gets fixed as it hasn't really worked properly or was really used
                elif (
                    self.env_data["tasks"][task_type][task]
                    and task in self.tasks[task_type].keys()
                    and not self.tasks[task_type][task]["enabled"]
                ):
                    raise NotImplemented
                # temp_future = Worker(target=temp_object.main())
                    logger.info("Starting {}.{}".format(task_type, task))
                    self.tasks[task_type][task]["enabled"] = True
                    temp_future = task_logger.create_task(
                        temp_object.main(),
                        logger=logger,
                        message="Task raised an exception",
                    )
                # Marking as NotImplemented for now until this functionality gets fixed as it hasn't really worked properly or was rarely used
                elif not self.env_data["tasks"][task_type][task] and task in self.tasks[task_type].keys():
                    raise NotImplemented
                    logger.info("Canceling {}.{}".format(task_type, task))
                    self.tasks[task_type][task]["enabled"] = False
                    self.tasks[task_type][task]["future"].cancel()
        logger.info("Managers finished running")

        await self._read_queue()

    def setup_object(
            self,
            manager_type,
            object_name,
            ):
        logger.info(f"Setting up and starting {manager_type}.{object_name}")
        temp_module = importlib.import_module(
            f"src.{manager_type}.{object_name}.main"
        )
        # This backwards looking naming is intentional since it's named is based on the perpective of the process
        temp_object = temp_module.Main(self.env_data)
        receive_queue, send_queue = temp_object.get_queues()
        temp_object.logger_queue = self.logger
        return temp_object, receive_queue, send_queue

    def run_low_priority_manager(
            self,
            logger: logging.Logger,
            receive_queue: multiprocessing.Queue,
            send_queue: multiprocessing.Queue,
            low_priority_setup_queue: multiprocessing.Queue,
            ) -> None:
        logger.info("Starting run_low_priority_manager")
        asyncio.run(
            self.async_run(
                logger,
                receive_queue=receive_queue,
                send_queue=send_queue,
                low_priority_setup_queue=low_priority_setup_queue,
                )
            )

    async def async_run(
            self,
            logger: logging.Logger,
            receive_queue: multiprocessing.Queue,
            send_queue: multiprocessing.Queue,
            low_priority_setup_queue: multiprocessing.Queue,
            ):
        task_logger.create_task(
            self.low_priority_manager(
                logger=logger,
                receive_queue=receive_queue,
                send_queue=send_queue,
                low_priority_setup_queue=low_priority_setup_queue,
                ),
            logger=logger,
            message="Task raised an exception",
            )

    async def low_priority_manager(
            self,
            logger: logging.Logger,
            receive_queue: multiprocessing.Queue,
            send_queue: multiprocessing.Queue,
            low_priority_setup_queue: multiprocessing.Queue,
            ) -> None:
        logger.debug("Starting now!")
        logger.info("Starting low_priority_manager()")
        local_tasks: dict[str, dict[str, Any]] = {
                "drivers": {},
                "processes": {},
                }
        while True:
            if not low_priority_setup_queue.empty():
                process = low_priority_setup_queue.get()[1]
                temp_object, receive_queue, send_queue = self.setup_object(
                        process[0],
                        process[1],
                    )
                temp_future = task_logger.create_task(
                        temp_object.run(),
                        logger=logger,
                        message="Task raised an exception",
                        )
                local_tasks[process[0]][process[1]] = {
                        "send_queue": send_queue,
                        "receive_queue": receive_queue,
                        "object": temp_object,
                        "enabled": True,
                        "process": temp_future,
                        }

            enabled_tasks = [
                (t, i)
                for t in local_tasks.keys()
                for i in local_tasks[t]
                if local_tasks[t][i]["enabled"]
                ]
            for i in enabled_tasks:
                current = local_tasks[i[0]][i[1]]
                while not current["receive_queue"].empty():
                    packet = current["receive_queue"].get()
                    destination = packet[1].split(".")
                    send_queue.put(
                        (packet[0], packet[1], packet[2])
                    )

            await asyncio.sleep(0)

    # Need to clean this up to be more readable
    # Need to also document and comment it better
    async def handle_log(self) -> None:
        while True:
            for log in self.logger.get():
                match log[0].lower():
                    case 'debug':
                        logger.debug('{}'.format(log[1]))
                    case 'info':
                        logger.info('{}'.format(log[1]))
                    case 'warning':
                        logger.warning('{}'.format(log[1]))
                    case 'error':
                        logger.error('{}'.format(log[1]))
                    case 'critical':
                        logger.critical('{}'.format(log[1]))
                    case _:
                        logger.debug('{}'.format(log[1]))
            await asyncio.sleep(1)

    async def _read_queue(self) -> None:
        while True:
            enabled_tasks = [
                (t, i)
                for t in self.tasks.keys()
                for i in self.tasks[t]
                if self.tasks[t][i]["enabled"]
            ]

            if not enabled_tasks:
                await asyncio.sleep(0.1)
                continue

            for task_type, task_name in enabled_tasks:
                current = self.tasks[task_type][task_name]
                if current["receive_queue"].empty():
                    continue
                logger.debug("Getting out of queue")
                packet = current["receive_queue"].get()
                logger.debug(packet)
                logger.debug("Getting destination")
                destination = packet["destination"].split(".")
                logger.debug("Putting into queue")
                # TODO: add a check for if a task is disabled
                self.tasks[destination[0]][destination[1]]["send_queue"].put(
                    packet
                )
                logger.debug("Done?")


    """The methods driver_manager() and process_manager() are very similar
    they both dynamically import drivers and processes respectively. SoonTM.
    The difference between a driver and a process is what they
    interact with. A driver interacts with external sources and
    translates the data between an external format and the internal format.
    A process only directly interacts with the core itself as the core handles
    inter-driver/process communication and coordination"""

    async def driver_manager(self):
        await self._manager_template("drivers")

    async def process_manager(self):
        await self._manager_template("processes")

    async def _manager_template(self, manager_type: str):
        """ """
        for i in self.env_data["tasks"][manager_type]:
            if self.env_data["tasks"][manager_type][i] == True:
                temp_module = importlib.import_module(
                    "{manager_type}.{i}.main".format(manager_type=manager_type, i=i)
                )
                temp_object = temp_module.Main(self.env_data)
                (
                    send,
                    receive,
                ) = await temp_object.get_queues()
                self.tasks[manager_type][str(i)] = {
                    "send_queue": send,
                    "receive_queue": receive,
                    "object": temp_object,
                    "enabled": True,
                }
            elif (
                self.env_data["tasks"][manager_type][i] == False
                and i in self.tasks[manager_type]
            ):
                await self.tasks[manager_type][str(i)]["object"].shutdown()
                self.tasks[manager_type][str(i)]["enabled"] = False
