from dataclasses import dataclass


@dataclass
class SigninResponse:
    """ Response from the sign in call has this dataclass as format, containing a token
    """
    token: str

