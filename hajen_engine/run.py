import asyncio
import datetime
import json
import logging
import uvloop
import struct
import sys


# import cProfile
# import pstats

from logging.handlers import RotatingFileHandler
# from watchdog.observers import Observer

from hajen_engine.core.core import Core
from hajen_engine.libs.utils import create_task, get_env_data
from hajen_engine.types.shared import EnvData

global __version__
__version__ = "engine-0.0.3b1"

global env_data
with open("data/environment.json", "r") as file:
    env_data: EnvData = json.load(file)

def update_env_data(event):
    with open("data/environment.json", "r") as file:
        env_data: EnvData = json.load(file)


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
                maxBytes=2_000_000_000,
                backupCount=5,
            ),
            logging.StreamHandler(stream=sys.stdout),
        ],
        format="%(levelname)s:%(name)s:%(lineno)s:%(message)s",
    )
    logging.raiseExceptions = True
    for module in env_data["library_logging_levels"].keys():
        module_logger = logging.getLogger(module)
        module_logger.setLevel(getattr(logging, env_data["library_logging_levels"][module]))


async def _async_run():
    env_data = get_env_data()

    setup_logging(env_data)
    sys.excepthook = handle_exception
    logger = logging.getLogger()
    logger.info(
        f"Engine running on version: {__version__}"
    )

    core: Core = Core()

    result = create_task(
            coroutine=core.main(),
            name='root',
            )
    await result


def run() -> None:
    """
    Main entry point for the engine.
    """
    try:
        try:
            asyncio.get_running_loop()
            asyncio.create_task(_async_run())
        except RuntimeError:
            # TODO: Add uvloop support
            # uvloop.install()
            asyncio.run(_async_run(), debug=env_data["debug"])
    # TODO: add better program quitting
    except KeyboardInterrupt:
        quit()

# if __name__ == "__main__":
    # try:
        # result = asyncio.run(main(), debug=env_data['debug'])
    # except KeyboardInterrupt:
        # logging.info("Stopping")
        # quit()
