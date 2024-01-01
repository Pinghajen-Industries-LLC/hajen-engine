import asyncio
import logging

from src.classes.classes import DriverClass

from src.custom_types.communication import PacketWithHeaders

logger = logging.getLogger(__name__)


class Main(DriverClass):
    def __init__(self, env_data) -> None:
        super().__init__()

        self.env_data = env_data

        self.source = "processes.template"

        # Sets logger level based on environment.json
        logger.setLevel(
            getattr(
                logging,
                self.env_data["tasks"][self.source.split(".")[0]][self.source.split(".")[1]]['logging_level'],
                )
        )

        logger.info("Template Driver Started!")

    async def run(self) -> None:
        while True:
            if not self.receive_queue.empty():
                logger.info("Running self._process_queue()")
                await self._process_queue()

            if self.get_tasks(running=False) != {}:
                logger.info("Running self.start_process()")
                await self.start_process()

            await asyncio.sleep(0)

    async def _process_queue(self) -> dict:
        """
        """
        logger.info("Reading queue")
        queue: list[PacketWithHeaders] = await self._read_queue()

        logger.info("Iterating over queue")
        for index, result in enumerate(queue):
            json_data = result[2]
            logger.debug("{}\n{}\n{}".format(index, result, json_data))
            match json_data["job_id"]:
                case "":
                    """
                    """
                    pass

            await asyncio.sleep(0)
        return {"result": 0}

    async def start_process(self):
        """
        """
        logger.info("Running start_process()")

        return {"result": 0}
