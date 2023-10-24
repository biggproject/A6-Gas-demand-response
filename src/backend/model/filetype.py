from enum import Enum


class FileType(Enum):
    """ The data type of the models used

    Args:
        Enum (_type_): the key contains the type and the value the type.
         in string form for creating a path
    """
    LOGS = 'logs/'
    MODEL = 'model/'
    DATA = 'data/'
