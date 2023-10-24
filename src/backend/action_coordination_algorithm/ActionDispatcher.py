import os
from datetime import datetime
from os import path
from src.backend.action_coordination_algorithm.helper import load_config
from src.backend.service.housesservice import HouseService
from src.misc.codelist.origin import Origin
from src.misc.logger import log, log_warn, log_debug, log_info, log_error
import time


class ActionDispatcher:
    """
    In the action dispatcher, a few steps are done before we actually send out actions to the devices:
        1. We map the internal id to the id specified in the config.
        2. A backup mechanism is introduced that prevents overheating or under-cooling of the house
        3. Actions are mapped to temperature set-points (t_set) for each device
    """

    def __init__(self):
        config = load_config()
        self.houses_service = HouseService()
        self.id_mappings = config['house_id_mappings']
        self.action_mappings = config['action_mappings']
        self.temperature_band = config['action_dispatcher']['temperature_band']
        self.enable_backup_controller = bool(config['action_dispatcher']['enable_backup_controller'])
        self.enable_dispatch_actions = bool(config['action_dispatcher']['enable_dispatch_actions'])
        if not self.enable_dispatch_actions:
            log_warn("Dispatcher disabled by config. It works in dummy mode.", Origin.DISPATCHER)
        # If any action mapping exists for a household, check if the full action space is covered
        self.action_space = config['agent']['action_space']
        for house_id, action_mapping in self.action_mappings.items():
            for action in self.action_space:
                if action not in action_mapping:
                    raise Exception(f"Action {action} is not mapped for house {house_id}")

    def dispatch(self, actions: dict[str, float], current_t_r_dict: dict[str, float],
                 current_t_r_set_dict: dict[str, float]):
        # Keep dict to store the actions that are actually dispatched
        time_str = datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d_%H_%M_%S')
        dispatched_actions_logs = {}
        # For every key in actions
        for house_id, action in actions.items():
            if house_id in self.id_mappings:
                real_house_id = self.id_mappings[house_id]  # Map the house id to the id specified in the config
            else:
                real_house_id = house_id  # If no mapping exists, use the house id as is

            current_t_r = current_t_r_dict[house_id]  # Get the current temperature of the house
            current_t_r_set = current_t_r_set_dict[house_id]  # Get the current set-point of the house

            # %% Backup controller: prevent over-heating or under-cooling
            backup_action = False
            if self.enable_backup_controller:
                if current_t_r > current_t_r_set + self.temperature_band:
                    backup_action = True
                    action = min(self.action_space)
                    log_warn(
                        f"House {house_id} is overheating! (t_r_set={current_t_r_set}; t_r={current_t_r}) Sending action '{action}'",
                        Origin.BACKUP_CONTROLLER)
                elif current_t_r < current_t_r_set - self.temperature_band:
                    backup_action = True
                    action = max(self.action_space)
                    log_warn(
                        f"House {house_id} is under-cooling! (t_r_set={current_t_r_set}; t_r={current_t_r}) Sending action '{action}'",
                        Origin.BACKUP_CONTROLLER)

            # Map the action to a temperature set-point
            if house_id in self.action_mappings:
                t_set = self.action_mappings[house_id][action]
            else:
                log_warn(f"House {house_id} has no action mapping, using default '{action}' as t_set",
                         Origin.DISPATCHER)
                t_set = self.action_mappings['default'][action]

            # %% Dispatch actions
            if self.enable_dispatch_actions and 'test' not in real_house_id:
                dispatch_successful = self.houses_service.put_t_set_house(real_house_id, t_set)
                if not dispatch_successful:
                    log_error(f"Dispatching action '{action}' to house '{house_id}' failed", Origin.DISPATCHER)
            else:
                # Do nothing
                log_debug(f"Dispatching is disabled for house {house_id}", Origin.DISPATCHER)
                pass

            # Log the action
            log_info(f"House '{house_id}' gets action '{action}', which maps to a t_set of {t_set}°C | t_r = {current_t_r}, t_r_set = {current_t_r_set}", Origin.DISPATCHER)
            dispatched_actions_logs[house_id] = (current_t_r, current_t_r_set, action, t_set, backup_action)

        self._export_csv(dispatched_actions_logs, f'dispatched_actions_{time_str}.csv')

    def _export_csv(self, dispatched_actions_logs: dict[str, tuple[float, float, float, float, bool]], filename: str):
        root = path.join(os.path.dirname(__file__), "..", "..", "..")
        logs_dir = path.join(root, 'data', 'action-coord', 'action_dispatcher')
        if not os.path.exists(logs_dir):
            os.makedirs(logs_dir)

        filepath = path.join(logs_dir, filename)
        with open(filepath, 'w') as f:
            f.write('house_id,t_r,t_r_set,action,t_set,backup_action\n')
            for house_id, (
            current_t_r, current_t_r_set, action, t_set, backup_action) in dispatched_actions_logs.items():
                f.write(f'{house_id},{current_t_r},{current_t_r_set},{action},{t_set},{backup_action}\n')
            f.close()
