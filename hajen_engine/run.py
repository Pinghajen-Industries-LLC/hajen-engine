import asyncio
import datetime
import json
import logging
import uvloop
import sys

# import cProfile
# import pstats

from logging.handlers import RotatingFileHandler
from asyncio_task_logger import task_logger
from hajen_engine.core.core import Core
from hajen_engine.types.shared import EnvData

global __version__
__version__ = "engine-0.0.2b1"


# with open("data/environment.json", "r") as file:
    # env_data: EnvData = json.load(file)

def handle_exception(exc_type, exc_value, exc_traceback):
    logger = logging.getLogger(__name__)
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return

    logger.error("Uncaught exception", exc_info=(exc_type, exc_value, exc_traceback))


def setup_logging(env_data):
    logging.basicConfig(
        level=getattr(logging, env_data["root"]['logging_level']),
        handlers=[
            RotatingFileHandler(
                f'logs/log-{datetime.datetime.now().strftime("%Y-%m-%d-%H:%M:%S")}.txt',
                maxBytes=2000000000,
                backupCount=5,
            ),
            logging.StreamHandler(stream=sys.stdout),
        ],
        format="%(levelname)s:%(name)s:%(lineno)s:%(message)s",
    )
    logger = logging.getLogger(__name__)
    logging.raiseExceptions = True
    for module in env_data["library_logging_levels"].keys():
        module_logger = logging.getLogger(module)
        module_logger.setLevel(getattr(logging, env_data["library_logging_levels"][module]))


async def async_run():

    with open("data/environment.json", "r") as file:
        env_data: EnvData = json.load(file)

    setup_logging(env_data)
    sys.excepthook = handle_exception
    logger = logging.getLogger()
    logger.info(
        f"Engine running on version: {__version__}"
    )

    core: Core = Core()

    # catches for a keyboard interrupt, will want to add more ways
    # to cancel in the future.
    result = task_logger.create_task(
            core.main(),
            logger=logger,
            message="Task raised an exception"
            )


def run() -> None:
    """
    Main entry point for the engine.
    """
    try:
        asyncio.get_running_loop()
        asyncio.create_task(async_run())
    except RuntimeError:
        asyncio.run(async_run())

# if __name__ == "__main__":
    # try:
        # result = asyncio.run(main(), debug=env_data['debug'])
    # except KeyboardInterrupt:
        # logging.info("Stopping")
        # quit()
