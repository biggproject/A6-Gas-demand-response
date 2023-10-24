from enum import Enum


class Level(Enum):
    NOTSET=0
    DEBUG=10
    INFO=20
    WARN=30
    ERROR=40
    CRITICAL=50