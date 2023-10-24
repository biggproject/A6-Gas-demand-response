from dataclasses import dataclass


@dataclass
class Environment:
    """ The environment of the running project
        these values are set in the assets folder
    """
    domain: str
    email: str
    password: str
    filelocation: str

