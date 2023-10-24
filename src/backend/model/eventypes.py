from enum import Enum


class ActionType(Enum):
    """ The action type, useful for logging events

    Args:
        Enum (_type_): the event type as key and the value is a string 
        representing the folder
    """
    DREVENT = 'dr-event/'
    NEWMODEL = 'new-model/'
