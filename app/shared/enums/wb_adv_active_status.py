from enum import StrEnum


class WBAdvActiveStatus(StrEnum):
    STARTED = "started"
    PAUSE = "pause"
    DONE = "done"
    READY_FOR_START = "ready_for_start"
