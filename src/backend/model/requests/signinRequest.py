from dataclasses import dataclass


@dataclass
class SigninRequest:
    """ Data fields needed to sign in in the domx api
    """
    email: str
    password: str

