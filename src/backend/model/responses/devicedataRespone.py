from dataclasses import dataclass


@dataclass
class DevicedataResponse:
    """ Response for api when asking for device data contains boilder and domx data
    """
    boiler: str
    domx: str

