import multiprocessing
from typing import Dict, Optional
from datetime import datetime, timezone
from json import load
import logging
from asyncio import Task

import asyncio
import importlib
from asyncio_task_logger import task_logger
from hajen_engine.types.shared import EnvData, RunningTasks
from hajen_engine.types.task_tracker import JobList
from hajen_engine.types.communication import Packet
from hajen_engine.libs.communication import QueueWrapper

logger = logging.getLogger(__name__)


class TaskManager:
    def __init__(self):
        with open("data/environment.json", "r") as json_file:
            self.env_data: EnvData = load(json_file)

        self.receive_queue: QueueWrapper = QueueWrapper()
        self.tasks: Dict[str, RunningTasks] = {}

    async def manager(self):
        """
        Starts and stops processes
        """
        result = task_logger.create_task(
                self.read_queue(),
                logger=logger,
                message="Task raised an exception"
                )
        while True:
            with open("data/environment.json", "r") as json_file:
                self.env_data: EnvData = load(json_file)
            logger.debug("1234")

            for task in self.env_data['tasks'].keys():
                if task in self.tasks.keys():
                    continue
                elif self.env_data['tasks'][task]['enabled']:
                    await self.start(task)
            await asyncio.sleep(60)

    async def start(self, task):
        logger.debug(task)
        if self.env_data['tasks'][task]['high_priority']:
            temp_object, send_queue = self.setup_object(
                    object_name=task,
                    )
            logger.info("Setting up high priority tasks")
            temp_process = multiprocessing.Process(
                    target=temp_object.main,
                    name=task
                    )
            temp_process.start()
            self.tasks.update({
                task: {
                    'name': task,
                    "send_queue": send_queue,
                    "receive_queue": self.receive_queue,
                    'core': 1,
                    "enabled": True,
                    "process": temp_process,
                    }
                })
        if not self.env_data['tasks'][task]['high_priority']:
            pass

    async def restart(self, task):
        pass

    async def shutdown(self, task):
        pass

    async def read_queue(self):
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

    async def async_run(
            self,
            ) -> None:
        logger = logging.getLogger(__name__)
        result = task_logger.create_task(
                self.run(),
                logger=logger,
                message="Task raised an exception"
                )

    def main(self) -> None:
        asyncio.run(self.async_run(), debug=True)

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
        return self.running_tasks

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
        # task: asyncio.Task = asyncio.create_task(asyncio.sleep(0)),
        task: Optional[asyncio.Task] = None,
        update_last_run: bool = False,
        update_cooldown: bool = False,
        update_task: bool = False,
    ) -> None:
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

    async def _run_scheduled_task(
            self,
            data_packet
            ) -> None:
        raise DeprecationWarning
        while not asyncio.current_task().cancelled():
            self.receive_queue.put(data_packet)
            if not self.receive_event.is_set():
                self.receive_event.set()
            await asyncio.sleep(
                int(json.loads(data_packet[2]))["scheduled_task"]["interval"]
            )


