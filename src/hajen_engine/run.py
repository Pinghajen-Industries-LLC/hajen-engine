import asyncio
import datetime
import json
import logging
import uvloop
import sys

# import cProfile
# import pstats

from logging.handlers import RotatingFileHandler
from hajen_engine.core.core import Core
from hajen_engine.custom_types.core import EnvData

global __version__
__version__ = "engine-0.0.1b"


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
    logging.raiseExceptions = True
    for module in env_data["logging"]["modules"]:
        botocore_log = logging.getLogger(module)
        botocore_log.setLevel(getattr(logging, env_data["library_logging_levels"][module]))


async def async_run():

    with open("data/environment.json", "r") as file:
        env_data: EnvData = json.load(file)

    setup_logging(env_data)
    sys.excepthook = handle_exception
    logger = logging.getLogger()
    logger.info(
        f"Engine running on version: {__version__}"
    )

    core: Core = Core(env_data)

    # catches for a keyboard interrupt, will want to add more ways
    # to cancel in the future.
    await core.main()

def run():
    """
    Main entry point for the engine.
    """
    if asyncio.get_running_loop() is not None:
        asyncio.create_task(async_run())
    else:
        asyncio.run(async_run())
        raise Exception("Engine is already running")

# if __name__ == "__main__":
    # try:
        # result = asyncio.run(main(), debug=env_data['debug'])
    # except KeyboardInterrupt:
        # logging.info("Stopping")
        # quit()
