from dataclasses import dataclass


@dataclass
class Boiler:
    """ The response of the domx api contains boiler data, the data fields are included in this dataclass
    """
    # eg. 2022-12-16T09:30:30.568Z
    time: str
    # eg. 0 
    blr_mod_lvl: int = None
    # eg. 65
    blr_t: float = None
    # eg. 1
    ch_pres: int = None
    # eg. 0
    dhw_flow: int = None
    # eg. 0
    dhw_t: float = None
    # eg. 0 todo not in data description - NOT NEEDED
    # diag: int = None
    # eg. 0
    fault: bool = None
    # eg. 0
    flame: bool = None
    # eg. 0
    heat: bool = None
    # eg. 9caf649197fb todo not in data description - NOT NEEDED
    # host: str = None
    # eg. 99 todo not in data description
    max_t_s: int = None
    # eg. 60 todo not in data description
    t_dhw_set: int = None
    # eg. 29.19922
    t_ret: float = None 
    # eg. 33
    t_exhaust: int = None
    # eg. 11.875
    t_out: float = None
    # eg ...
    t_out2: float = None
    # eg. domx_ot_e8:31:cd:af:12:44/ot/boiler/status - NOT NEEDED
    # topic: str = None
    # eg. 0  todo not in data description
    water: int = None

