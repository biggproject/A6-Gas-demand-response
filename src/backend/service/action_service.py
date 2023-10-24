import os
from os import path
from threading import Event
import yaml
from src.misc.codelist.origin import Origin
from src.misc.logger import log_error, log_info
from src.backend.action_coordination_algorithm.action_coordinator import ActionCoordinator
from src.backend.model.DR_Event import DrEvent
from requests import get

class ActionService:
    """ Service that will execute certain action that are received 
    from a frontend website
    """
    config = None
    ac_c: ActionCoordinator

    def __init__(self):
        # Load configuation file
        root = path.join(os.path.dirname(__file__), '..', '..', '..')
        path_config = path.join(root, 'config.yml')
        assert path.isfile(path_config), 'Config file not found'
        with open(path_config, 'r') as f_open:
            self.config = yaml.safe_load(f_open)

    def post_dr_event(self, seconds: int, energy: float, dr_event_signal: Event) -> bool:
        """ Submitting a DR Event, this event will go to the 
            action_coordination_Algorithm

        Args:
            seconds (int): the seconds needed for the event
            energy (float): the energy value needed for the event

        Returns:
            bool: returns true if the action could be executed
        """
        # sent the message to the action coordinator logic
        log_info(f'Received a POST request for DR Event: [seconds = {seconds}, energy = { energy }]', Origin.ACTION_SERVICE)
        drevent: DrEvent = DrEvent(seconds, energy)
        participants = self.config['dr_event']['participants']
        control_interval_s = self.config['dr_event']['control_interval_s']
        action_space = self.config['agent']['action_space']
        
        # Action coordinator
        self.ac_c: ActionCoordinator = ActionCoordinator(drevent, action_space, control_interval_s, participants, dr_event_signal)
        self.ac_c.start()
        log_info("Action Coordinator started by POST call", Origin.ACTION_SERVICE)

        return True

    def stop_updating(self):
        try:
            r = get("<private>")
        except:
            log_error("Grafana update did not stop")