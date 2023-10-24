from dataclasses import dataclass


@dataclass
class DrEvent:
    """ The variables of a dr-event, used to send an api request 
        handled in action_coorinator_algorithm
    """
    duration_sec: int
    power_alternation: float
