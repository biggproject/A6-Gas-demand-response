from dataclasses import dataclass


@dataclass
class Domx:
    """ Response data from the api containing domx data fields
    """
    # eg. 2022-12-16T09:30:30.569Z
    time: str
    # eg. 0   - NOT NEEDED
    # bst: int = None
    # eg. 1  - NOT NEEDED
    # bst_set: int = None
    # eg. 2
    bypass: int = None
    # eg. 36  - MAYBE NOT NEEDED 
    ch_lb: int = None
    # eg. 70  - MAYBE NOT NEEDED
    ch_ub: int = None
    # eg. 66 - MAYBE NOT NEEDED
    cloud_blr: int = None 
    # eg. 1 - NOT NEEDED
    # dal_num: int = None
    # eg. 0 - NOT NEEDED
    # dev_byp: int = None
    # eg. 1
    heat_ctl: int = None
    # eg. 1
    heat_set: int = None
    # eg. 9caf649197fb - NOT NEEDED
    # host: str = None
    # eg. 1 - NOT NEEDED
    # knob: int = None
    # eg. 0 - NOT NEEDED
    # low_status: int = None 
    # eg. 0
    max_mod: int = None
    # eg. 5.9
    otc_cur: float = None
    # eg. 63.467
    otc_maxt: float = None
    # eg. 0 
    pid: int = None
    # eg. 0 - NOT NEEDED
    # res_btn: int = None 
    # eg. 60
    t_dhw_set: int = None
    # eg. 8.5
    t_out: float = None
    # eg. 14 - M NOT NEEDED
    t_out_api: int = None
    # eg. 7 - M NOT NEEDED
    t_out_mask: int = None
    # eg. 0 - M NOT NEEDED
    t_out_rt: int = None
    # eg. 1 - M NOT NEEDED
    t_out_sel: int = None
    # eg. 20.5
    t_r: float = None
    # eg. 0 - M NOT NEEDED
    t_r_overr: int = None 
    # eg. 0 - M NOT NEEDED
    t_r_rt: int = None
    # eg. 20
    t_r_set: int = None
    # eg. 1
    t_r_set_ctl: int = None 
    # eg. 66
    t_set: int = None
    # eg. 0 
    therm_t_r: int = None
    # eg. domx_ot_e8:31:cd:af:12:44/ot/domx/status - NOT NEEDED
    # topic: str = None
    # eg. 0 - NOT NEEDED
    # tpi: int = None
    # eg. 1
    water_set: bool = None
