import multiprocessing
from copy import deepcopy
import psutil
import os
from typing import Dict, Optional, List, Tuple
from datetime import datetime, timezone
from json import load
import logging
from asyncio import Task

import asyncio
import importlib

from hajen_engine.libs.utils import create_task, get_env_data
from hajen_engine.types.shared import EnvData, RunningTasks
from hajen_engine.types.core import Task, UsedCore
from hajen_engine.types.task_tracker import JobList
from hajen_engine.types.communication import Packet
from hajen_engine.libs.communication import QueueWrapper

logger = logging.getLogger(__name__)


class TaskManager:
    def __init__(self, name: str):
        """
        This class manages each task in a uniform way.
        - self.env_data - From the `data/environment.json` file
        - self.receive_queue - Queue for this task to receive from
        - self.send_queue - Queue for this task to send on
        - self.used_cores - The currently used cores by this task
        - self.tasks - List of all running tasks from this TaskManager
        - self.last_process_number - Tracks the last process number used
        """
        # TODO: Make self.env_data get updated whenever env_data changes
        self.env_data: EnvData = get_env_data()
        self.name: str = name

        self.receive_queue: QueueWrapper = QueueWrapper()
        self.send_queue: QueueWrapper = QueueWrapper()
        self.setup_queue: multiprocessing.Queue = multiprocessing.Queue()
        self.used_cores: Dict[int, UsedCore] = {}
        # Need to update the Task type to be more relevant
        self.tasks: Dict[str, Task] = {}
        self.last_process_number: int = 0

        # This won't change unless there is a system restart, this could
        # possibly change
        if self.env_data['total_cores'] > multiprocessing.cpu_count():
            error = f"""Too many cores allocated
            ({self.env_data['total_cores']}), only
            {multiprocessing.cpu_count()} available."""
            logger.fatal(error)
            raise ValueError(error)
        elif (
                self.env_data['total_cores'] < multiprocessing.cpu_count()
                and self.env_data['total_cores'] > -1
            ):
            self.total_cores = self.env_data['total_cores']
        else:
            self.total_cores = multiprocessing.cpu_count()

        for core in range(0, self.total_cores):
            self.used_cores.update({
                core: {
                    'high_priority': False,
                    'tasks': [],
                    }
                })

    async def manager(self):
        """
        Starts and stops processes
        """
        logger.info(f"Starting the {self.name} manager")
        # self._update_used_cores(
                # name,
                # psutil.Process(
                        # os.getpid()
                    # ).cpu_num(),
                # multiprocessing.Queue()
                # )
        result = create_task(
                self.read_queue(),
                name=f"{self.name}_read_queue",
                )
        # TODO: Remove the while True and use a callback
        while True:
            # Starts a new task
            # TODO: Should handle shutting down tasks as well
            for task in self.env_data['tasks'].keys():
                logger.debug(task)
                logger.debug(self.tasks.keys())
                if task in self.tasks.keys():
                    continue
                if self.env_data['tasks'][task]['enabled']:
                    await self.start(task)
                elif not self.env_data['tasks'][task]['enabled']:
                    await self.stop(task)
            logger.info("Sleeping...")
            await asyncio.sleep(60)

    def _update_used_cores(self, task: Task, high_priority: bool, task_name: str, core=-1) -> int:
        """
        Updates self.used_cores and increments self.last_process_number
        This is supposed to keep track of the used cores by the root TaskTracker

        This should keep track of coores dedicated to high priority and cores
        that can be used for low priority
        """
        # Have a dictionary of all cores
        # this dictionary can never be larger in length than
        # the available cores on the machine
        # this can and should be able to be set to lower in env_data
        # should include a field for if it's high priority or not
        # and then not allow assigning 2 tasks if they are both trying to use
        # the same core
        existing_core = self.used_cores[task['core']]
        logger.debug(existing_core)
        if existing_core['high_priority'] and len(existing_core['tasks']) == 1:
            error = f"""{task_name} is assigned to core {task['core']} but core {task['core']}
                is running task {existing_core['tasks'][0]} which is set to
                high_priority and can not share it's core"""
            raise ValueError(error)
        elif existing_core['high_priority'] and len(existing_core['tasks']) > 1:
            error = f"""Core {task['core']} is set to high_priority but core {task['core']}
                has {len(existing_core['tasks'])} which is higher than the
                allowed max of 1"""
            raise ValueError(error)
        elif not existing_core['high_priority'] and not high_priority:
            existing_core['high_priority'] = high_priority
            existing_core['tasks'].append(task_name)
            self.used_cores.update({core: existing_core})
        elif len(existing_core['tasks']) == 0 and high_priority:
            existing_core['high_priority'] = high_priority
            existing_core['tasks'] = [task_name]
        elif len(existing_core['tasks']) > 0 and high_priority:
            error = f"""{task_name} is assigned to core {task['core']} but core {task['core']}
                is set to be low_priority with running tasks but {task_name}
                is set to high_priority"""
            raise ValueError(error)
        self.used_cores[task['core']] = existing_core

    async def start(self, task: str):
        """
        Starts a process regardless of if it's high priority or low priority
        """
        logger.info(f"Starting {task}")
        # Checks if it's marked as high priority and if it's already running
        # TODO: Change this to remove currently running tasks and where they are
        if self.env_data['tasks'][task]['high_priority']:
            logger.info(f"""Setting up {task} as a {'high' if
                                                  self.env_data['tasks'][task]['high_priority']
                                                  else 'low'} priority task""")
        # This needs to allow setting to a certain core
        # as this might require manual core assignment
            core: int = self._update_used_cores(self.env_data['tasks'][task],
                                           self.env_data['tasks'][task]['high_priority'],
                                           task,
                                           )
            temp_process = multiprocessing.Process(
                    target=self.run,
                    args=(task, ),
                    name=task,
                    )
            temp_process.start()
            self.tasks.update({
                task: {
                    'name': task,
                    "send_queue": None,
                    "receive_queue": self.receive_queue,
                    "core": core,
                    "high_priority": self.env_data['tasks'][task]['high_priority'],
                    "enabled": True,
                    "process": temp_process,
                    "logging_level": self.env_data['tasks'][task]['logging_level'],
                    "options": None,
                    }
                })
        else:
            if self.name == 'root':
                # This branch needs to start up a new process on the right core
                # or send a signal on the self.setup_queue queue to start a
                # certain task
                core: int = self._update_used_cores(self.env_data['tasks'][task],
                                               self.env_data['tasks'][task]['high_priority'],
                                               task,
                                               core=self.env_data['tasks'][task]['core'],
                                               )
                self.tasks.update({
                    task: {
                        'name': task,
                        "send_queue": None,
                        "receive_queue": self.receive_queue,
                        "core": core,
                        "high_priority": self.env_data['tasks'][task]['high_priority'],
                        "enabled": True,
                        "process": None,
                        "logging_level": self.env_data['tasks'][task]['logging_level'],
                        "options": None,
                        }
                    })
                temp_process = multiprocessing.Process(
                        target=self.run,
                        args=(task, ),
                        name=f"core{core}",
                        )
                temp_process.start()
                self.tasks[task]["process"] = temp_process
            else:
                # This branch should start the task as a new task on this core
                # self.used_cores should have a field for the set_queue for each core
                core = self._update_used_cores(self.env_data['tasks'][task],
                                           self.env_data['tasks'][task]['high_priority'],
                                           task,
                                           core=self.env_data['tasks'][task]['core'],
                                           )
                result = await create_task(
                        self.async_run(task),
                        name=f"task",
                        )
                self.tasks.update({
                    task: {
                        'name': task,
                        "send_queue": None,
                        "receive_queue": self.receive_queue,
                        "core": core,
                        "high_priority": self.env_data['tasks'][task]['high_priority'],
                        "enabled": True,
                        "process": None,
                        "logging_level": self.env_data['tasks'][task]['logging_level'],
                        "options": None,
                        }
                    })
            # This needs to signal to each core to start a task
        logger.debug(f"{self.used_cores}")
        return 0

    async def restart(self, task):
        """
        This should kill and start the process again, reevaluating the setup settings
        Should also have a force option and a graceful shutdown option
        """
        pass

    async def stop(self, task):
        """
        This should kill the process
        Should also have a force option and a graceful shutdown option
        """
        pass

    async def async_run(self, task: str):
        """
        Allows for using self.run() with create_task() which expects a coroutine
        """
        self.run(task)

    def run(self, task: str):
        """
        This should either create the task or start an event loop
        """
        temp_object, send_queue = self.setup_object(
                object_name=task,
                )
        self.tasks[task]["send_queue"] = send_queue
        logging.debug(self.tasks)
        try:
            asyncio.get_running_loop()
            asyncio.create_task(temp_object.run())
        except RuntimeError:
            asyncio.run(temp_object.run())

    async def get_send_queue(self):
        """
        Simply returns the send queue of this process' core
        """
        return self.send_queue

    async def read_queue(self):
        """
        Standard way to read from any supported queue and then send on any supported queue
        """
        logger.info(f"Starting read_queue()")
        while True:
            enabled_tasks = [
                i
                for i in self.tasks
                if self.tasks[i]['enabled']
            ]

            if not enabled_tasks:
                # TODO: this needs to be redone
                await asyncio.sleep(0.1)

            for task in enabled_tasks:
                if self.tasks[task]["receive_queue"].empty():
                    continue
                logger.debug("Getting out of queue")
                packet = self.tasks[task]["receive_queue"].get()
                if packet is None:
                    continue
                logger.debug(packet)
                logger.debug("Getting destination")
                destination = packet["destination"]
                logger.debug("Putting into queue")
                # TODO: add a check for if a task is disabled
                self.tasks[destination]['send_queue'].put(
                    packet
                )
                logger.debug("Done?")
            await asyncio.sleep(0.1)

    def setup_object(
            self,
            object_name: str,
            ):
        """
        Builds the object to be used, ideally this should be contained within the TaskClass
        TODO: Impliment this into the TaskClass
        """
        logger.info(f"Setting up and starting task.{object_name}")
        temp_module = importlib.import_module(
            f"src.{object_name}.main"
        )
        send_queue: QueueWrapper = QueueWrapper()
        # This backwards looking naming is intentional since it's named is based on the perpective of the process
        temp_object = temp_module.Main(self.env_data)
        temp_object.send_queue = self.receive_queue
        temp_object.receive_queue = send_queue
        return temp_object, send_queue


class TaskClass:
    def __init__(self) -> None:
        super().__init__()

        self.class_type = "base_class"

        self.source = ""

        self.uid: int = 0
        self.process_name: str = __name__

        # self.scheduled_tasks = dict()

        self.send_queue: QueueWrapper = QueueWrapper()
        self.receive_queue: QueueWrapper = QueueWrapper()

        self.logger_queue: multiprocessing.Queue = multiprocessing.Queue()

    async def _read_queue(self,
                          ) -> list[Packet]:
        queue: list[Packet] = []
        while not self.receive_queue.empty():
            queue_item = self.receive_queue.get()
            if queue_item is not None:
                queue.append(queue_item)
        return queue

    def get_queues(self,
                   ) -> tuple[QueueWrapper, QueueWrapper]:
        '''
        Returns the send and receive queues.

        This is intentionally backwards to how it is used
        in core.py because it is named from the perspective
        of the process using the queues.
        '''
        return (self.send_queue, self.receive_queue, )

    def logger(
            self,
            message: str,
            level: str = 'DEBUG',
            ) -> None:
        self.logger_queue.put((level.upper(), f'{self.source}:{message}'))

    async def _async_run(
            self,
            ) -> None:
        logger = logging.getLogger(__name__)
        result = create_task(
                self.run(),
                logger=logger,
                message="Task raised an exception"
                )

    def main(self) -> None:
        try:
            asyncio.get_running_loop()
            asyncio.create_task(self._async_run())
        except RuntimeError:
            # TODO: Add uvloop support
            # uvloop.install()
            asyncio.run(self._async_run()) # TODO: add debug parameter

    async def run(self) -> None:
        print("The task needs to impliment run()")

    async def get_request_id(
            self,
            process_name: str
            ) -> str:
        """
        returns class_type.process_name.uid.timestamp for use with the
        request_id field of communication dictionaries. This also increments
        self.uid for use as a unqiue indentifier for each request.

        `class_type` - The type of class, e.g. `ProccessClass` would be the
        class_type of a process
        `process_name` - The name of the class, e.g. `sql` would be the SQL
        driver, while this can be confusing as to if it only includes the
        'process' type in the core it includes anything that runs on top of the
        core.
        `uid` - A unique number that increments for each call to get_request_id
        for each instance.
        `timestamp` - UNIX Epoch time, using `now(tz=timezone.utc)``utcnow` converted to
        milliseconds to help with the uniqueness of the `get_request_id`.
        """
        self.uid += 1
        return "{class_type}.{process_name}.{uid}.{timestamp}".format(
            class_type=self.class_type,
            process_name=process_name,
            uid=self.uid,
            timestamp=int(datetime.now(tz=timezone.utc).timestamp() * 1000),
        )

    async def _send_packet_list(self
                                ,packet_list: list[Packet]
                                ) -> dict[str, str]:
        """
        Sends a list of Packet to self.send_queue.
        This keep _send_packet able to do only one packet at a time.

        `packet_list` - A list of packets to send to self.send_queue.
        Each packet is a dictionary with the following keys:
            - `priority` - The priority of the packet.
            - `source` - The source of the packet.
            - `job_id` - The job_id of the packet.
            - `data` - The data of the packet.
            - `destination` - The destination of the packet.
            - `result` - The result of the packet.
            - `datatype` - The datatype of the packet.
            - `requestid` - The requestid of the packet.
        """
        if not isinstance(packet_list, list):
            return {
                'result': '1',
                'error': 'Packet is not of type list[].',
            }
        if isinstance(packet_list, list) and len(packet_list) == 0:
            return {'result': '1', 'error': 'packet_list was empty'}
        for packet in packet_list:
            try:
                await self._send_packet(
                    source=packet['source'],
                    job_id=packet['job_id'],
                    data=packet['data'],
                    destination=packet['destination'],
                    result=packet['result'],
                    datatype=packet['datatype'],
                    requestid=packet['requestid'],
                )
            except (KeyError, IndexError, TypeError) as e:
                return {
                'result': '1',
                'message': 'Packet is not of type list[Packet].',
                'error': str(e),
                }
        return {'result': '0'}

    async def _send_packet(self
                           ,source: str
                           ,job_id: str
                           ,data: dict
                           ,destination: str
                           ,result: str
                           ,datatype: str
                           ,requestid: str
                           ) -> None:
        """
        Constructs and sends a packet to self.send_queue.

        :param priority: The priority of the packet.
        :param source: The source of the packet.
        :param job_id: The job_id of the packet.
        :param data: The data of the packet.
        :param destination: The destination of the packet.
        :param result: The result of the packet.
        :param datatype: The datatype of the packet.
        :param requestid: The requestid of the packet.
        """
        json_data = Packet(
            source=source,
            job_id=job_id,
            data=data,
            destination=destination,
            result=result,
            datatype=datatype,
            requestid=requestid,
        )
        self.send_queue.put(json_data)

    async def schedule_task(self, data_packet) -> dict:
        raise NotImplementedError
        self.scheduled_tasks.update({str(json.loads(data_packet[2]))["job_id"]})
        asyncio.create_task(self._run_scheduled_task(data_packet))
        return {"result": 0}

    async def shutdown(self) -> dict:
        raise NotImplementedError
        asyncio.current_task().cancel()
        return {"result": 0}


class JobTracker:
    def __init__(self) -> None:
        self.running_tasks: JobList = JobList()

    def stop_task(
            self,
            key: str,
            delete: bool = False,
            force: bool = False
            ) -> None:
        raise NotImplementedError

    def get_tasks(
            self,
            key: str = "",
            running: bool = False,
            all_tasks: bool = False
    ) -> JobList:
        if all_tasks is True:
            return self.running_tasks
        elif key != "":
            return {
                task: self.running_tasks[task]
                for task in self.running_tasks
                if self.running_tasks[task]["running"] == running
                and key == task
                and datetime.timestamp(datetime.now(tz=timezone.utc))
                - self.running_tasks[task]["last_run"]
                >= self.running_tasks[task]["cooldown"]
            }
        elif key == "":
            return {
                task: self.running_tasks[task]
                for task in self.running_tasks
                if self.running_tasks[task]["running"] == running
                and datetime.timestamp(datetime.now(tz=timezone.utc))
                - self.running_tasks[task]["last_run"]
                >= self.running_tasks[task]["cooldown"]
            }

    def set_task_callback(
        self,
        task: Task[dict[str, int]],
        key: str,
        running: bool,
    ) -> None:
        '''This function only exists to do a callback without having to add Task to `set_task_running`, this is a wrapper'''
        self.set_task_running(key=key, running=running)

    def set_task_running(
        self,
        key: str,
        running: bool = True,
        cooldown: float = 60.0,
        task: Optional[asyncio.Task] = None,
        update_last_run: bool = False,
        update_cooldown: bool = False,
        update_task: bool = False,
    ) -> None:
        """
        This needs to update the task or set it running if it's not already set
        """
        if key in self.running_tasks.keys():
            self.running_tasks[key].update(
                {
                    "running": running,
                    "last_run": datetime.timestamp(datetime.now(tz=timezone.utc))
                    if update_last_run
                    else self.running_tasks[key]["last_run"],
                    "cooldown": cooldown if update_cooldown
                    else self.running_tasks[key]["cooldown"],
                    "task": task if task is not None
                    else self.running_tasks[key]["task"],
                }
            )
            return None
        else:
            self.running_tasks[key] = {
                "running": running,
                "last_run": datetime.timestamp(datetime.now(tz=timezone.utc))
                if update_last_run
                else datetime.timestamp(
                    datetime.now(tz=timezone.utc)) - ((cooldown)),
                "cooldown": cooldown,
                "task": task if task is not None
                else None,
            }
            return None
