from os import path
import yaml


def load_config() -> dict:
    """ Load the config file
    """
    root = path.join(path.dirname(__file__), "..", "..", "..")

    path_config = path.join(root, 'config.yml')
    assert path.isfile(path_config), 'Config file not found'
    with open(path_config, 'r') as f_open:
        config = yaml.safe_load(f_open)
    return config
