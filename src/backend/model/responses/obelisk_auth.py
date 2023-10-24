from dataclasses import dataclass


@dataclass
class ObeliskToken:
    """ Answer of obelisk authentication
    """
    # eg. bearer
    token_type: str
    # eg. 
    token: str
    # eg. XNQNtuEZDfarzeDN
    access_token: str
    # eg.  eyJraWQiOiI4MWQ5MjhjYi1hNjQ4LTQyMDktYjk4OC00NjE0NDY...
    id_token: str
    # eg. 3600
    max_idle_time: int
    # eg. 3600
    expires_in: int
    # eg. 86400
    max_valid_time: int
    # eg. false
    remember_me: bool
