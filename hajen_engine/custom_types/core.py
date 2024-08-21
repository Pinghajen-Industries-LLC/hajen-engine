from typing import TypedDict

class TaskType(TypedDict, total=False):
    enabled: bool
    high_priority: bool
    logging_level: str
    options: dict[str, str]

class Tasks(TypedDict, total=True):
    drivers: dict[str, TaskType]
    processes: dict[str, TaskType]

class EnvData(TypedDict, total=True):
    debug: bool
    root: TaskType
    core: TaskType
    tasks: Tasks
    library_logging_levels: dict[str, str]

