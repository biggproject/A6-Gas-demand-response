from dataclasses import dataclass


@dataclass
class ActionCoordVar:
    """ Parameters and their values for the action coordinator
    """
    # List of possible actions
    action_space = [0, 1]
    # The time interval in seconds between two control steps
    control_interval_s: float = 10
    # List of Device IDs
    participants = ['house1', 'house2', 'house3']
