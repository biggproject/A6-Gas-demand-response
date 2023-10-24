from dataclasses import dataclass
from datetime import datetime


@dataclass
class DevicedataRequest:
    """ When making a request for data from a specific ID the variables from the class need to be given
    """
    device_id: str
    time_from: datetime
    time_to: datetime
