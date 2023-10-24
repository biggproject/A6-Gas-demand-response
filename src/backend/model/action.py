from dataclasses import dataclass


@dataclass
class Action:
    boiler_id: str
    boiler_set_point: float
