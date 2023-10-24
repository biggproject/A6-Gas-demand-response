from dataclasses import dataclass


@dataclass
class ErrorMsg:
    """ Errormsg returned from the API 
    """
    error: str

