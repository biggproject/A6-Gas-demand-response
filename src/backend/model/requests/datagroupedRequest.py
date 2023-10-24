from dataclasses import dataclass


@dataclass
class DataGrouped:
    """ the format to request data from obelisk through an API call
    """
    metrics_domx: list[str]
    metrics_boiler: list[str]
    start: int
    end: int
    house_id: str
    user_id_obelisk : str = 'NjNiNTM5YjE0MTQ4NWYzNDUxNjVkYmZkOjJjNjVjNWYyLTE5ZGEtNDEwMC04MTVkLWIyNDA3OWRkOGRiNg==' # default value ms 