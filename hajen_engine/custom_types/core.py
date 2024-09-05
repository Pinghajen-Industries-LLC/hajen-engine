from typing import TypedDict

class Task(TypedDict, total=True):
    enabled: bool
    high_priority: bool
    logging_level: str
    options: dict[str, str]


class EnvData(TypedDict, total=True):
    debug: bool
    root: Task
    core: Task
    tasks: dict[str, Task]
    library_logging_levels: dict[str, str]

