from dataclasses import dataclass
from typing import Any


@dataclass
class ObeliskResponse:
    """ the parameters of each item received from the obelisk database
    """
    # eg. 1671706025814
    timestamp: int
    #  eg. domx.ch_lb::number
    metric: str
    # eg. 45.0
    value: Any
    # domx_ot_a8:03:2a:d5:81:3c
    source: str
