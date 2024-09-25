from enum import Enum, unique

@unique
class StreamState(Enum):
    ERROR = -1
    INIT = 0
    RUNNING = 1
    COMPLETED = 3

