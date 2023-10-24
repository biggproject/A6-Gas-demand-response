import time
from datetime import datetime
from threading import Thread, Event
import numpy as np
import pandas as pd
import pytz
from matplotlib import pyplot as plt

from src.misc.codelist.level import Level
from src.misc.codelist.origin import Origin
from src.misc.codelist.type import LogType
from src.backend.action_coordination_algorithm.pi_controller import PIController
from src.backend.model.DR_Event import DrEvent
from src.misc.logger import log_info, log_warn, log_coordinator_actions, log_debug, log_dataframe, log_variable, \
    log_error
from src.backend.action_coordination_algorithm.ActionDispatcher import ActionDispatcher
from src.backend.action_coordination_algorithm.helper import load_config
from src.backend.action_coordination_algorithm.model.A_Function import A_Function
from src.backend.action_coordination_algorithm.model.State import State
from src.backend.controller.storageacces import Storage
from src.backend.service.housesservice import HouseService

TAG = Origin.COORDINATOR

class ActionCoordinator(Thread):
    dr_event: DrEvent  # The DR event to be executed
    action_space: list[int]  # List of possible actions
    control_interval_s: float  # The time interval in seconds between two control steps
    participants: list[str]  # List of Device IDs
    finished: bool = False

    # Data services
    _house_service: HouseService = None
    _storage: Storage = None

    # Dictionaries
    _advantage_functions: dict[str, A_Function] = None  # Function that takes an action and returns the advantage value
    _baseline_consumptions: dict[str, float] = None  # The power reference to which the DR-event is compared
    _baseline_actions: dict[str, float] = None  # The action that is executed when the DR-event is not active
    _ranking_table_up = pd.DataFrame(columns=['device_id', 'action', 'cost', 'rank'])
    _ranking_table_down = pd.DataFrame(columns=['device_id', 'action', 'cost', 'rank'])

    # Device state tracking
    _step_time = 0
    _states: list[dict[str: State]] = None
    _current_power_consumption: float = 0

    # DR response properties
    _target: float = None  # The target power consumption
    _response_level_range: tuple[int, int] = None
    _actions_by_response_level: dict[int, dict[str, float]] = None

    # Track the current Response Level and the actions
    _current_response_level: int = 0
    _pi_controller: PIController = None
    _stats: list[tuple[float, float, float]] = None  # List of tuples (time, summed observed power, response level)

    # Action dispatcher
    _action_dispatcher = ActionDispatcher()

    def __init__(self, dr_event: DrEvent, action_space: list[int], control_interval_s: float,
                 participants: list[str] = None, dr_event_signal: Event = None, kp: float = None, ki: float = None):
        Thread.__init__(self)
        config = load_config()
        self.dr_event = dr_event
        self.action_space = action_space
        self.control_interval_s = control_interval_s
        if participants is None:
            participants = config['dr_event']['participants']
        self.participants = participants
        if dr_event_signal is None:
            self.dr_event_signal = Event()
            self.dr_event_signal.set()
        else:
            self.dr_event_signal = dr_event_signal
        if (kp is None) or (ki is None):
            kp, ki = config['pi_controller']['kp'], config['pi_controller']['ki']
        self._pi_controller = PIController(kp, ki)
        self._baseline_states = dict[str, State]()
        self._actions_by_response_level = dict[int, dict[str, float]]()
        self._house_service = HouseService()
        self._storage = Storage()
        self._stats = list[tuple[float, float, float]]()
        self._datetime_dr_start = None

    def run(self):
        assert not self.finished, "DR event already finished. Cannot start again."
        # Load measurements
        measurement_tuple = self._parse_trajectory_measurements()
        if measurement_tuple is None:
            log_error("Aborting DR event.", TAG)
        self._baseline_states = measurement_tuple[0]
        self._baseline_consumptions = measurement_tuple[1]
        self._baseline_actions = measurement_tuple[2]
        self._current_power_consumption = measurement_tuple[3]

        # Load advantage functions
        self._load_advantage_functions()
        baseline_total = sum(self._baseline_consumptions.values())
        self._target = baseline_total + self.dr_event.power_alternation

        # Get ranking list of devices with their actions
        self._populate_ranking_table()
        self._calculate_actions_per_response_level()

        # Logging
        log_info(f"Starting DR event (power difference of {self.dr_event.power_alternation} over {baseline_total}) "
                 f"over {self.dr_event.duration_sec} seconds.", TAG)
        self._log_tables()
        self._stats.append((self._step_time, self._current_power_consumption, self._current_response_level))
        self._datetime_dr_start = time.time()
        self._log_progress_values()

        # Run PI controller to dispatch actions
        start_time_s, dr_dur = time.time(), self.dr_event.duration_sec
        cur_step, total_nr_steps = 0, int(self.dr_event.duration_sec / self.control_interval_s)
        while self._step_time < self.dr_event.duration_sec and self.dr_event_signal.is_set():
            now = time.time() - start_time_s
            log_info(f"Starting step {cur_step}/{total_nr_steps} at {round(now, 3)}s/{dr_dur}s", TAG)
            # Get latest observations
            res = self._house_service.get_latest(self.participants)
            if res is not None:
                self._current_power_consumption, t_r_dict, t_r_set_dict = res
                self._step(t_r_dict, t_r_set_dict)
                self._stats.append((self._step_time, self._current_power_consumption, self._current_response_level))
                self._log_progress_values()
                now = time.time() - start_time_s
                progress_str = f'Finished step {cur_step}/{total_nr_steps} at {round(now, 3)}s/{dr_dur}s'
                power_str = f'Power (b_m): {round(self._current_power_consumption, 3)}/{self._target}'
                response_str = f'Res lvl: {self._current_response_level}'
                log_info(f"{progress_str} => {power_str} | {response_str}\n", TAG)
            else:
                log_warn(f"Failed to receive the latest measurement. Skipping step {cur_step}.", TAG)

            # Wait for next control step
            start_time_next_step = self._step_time + self.control_interval_s  # The DR time at which the next step should start
            if now > start_time_next_step:
                log_warn(f"Control step {cur_step} took longer than {self.control_interval_s} seconds", TAG)
            while start_time_next_step > now:
                if not self.dr_event_signal.is_set():
                    continue
                time.sleep(0.01)
                now = time.time() - start_time_s
            new_step = int(now / self.control_interval_s)
            if new_step > cur_step + 1:
                log_warn(f"Skipped {new_step - cur_step - 1} control step(s). The coordinator cannot keep up!", TAG)
            cur_step = new_step
            self._step_time = cur_step * self.control_interval_s

        # Done
        self._finish_dr_event()

    def _step(self, current_t_r_dict: dict[str, float], current_t_set_dict: dict[str, float]):
        """
        Perform one step of the action coordinator.
        :return: the action to be executed on each device.
        """
        proposed_response_level = self._pi_controller.step(self._target, self._current_power_consumption)
        response_level_diff = proposed_response_level - self._current_response_level
        response_level_diff = int(response_level_diff + 0.5)  # Round to the nearest int

        # Change actions if necessary
        if response_level_diff > 0:
            self._increase_power_actions(nr_levels=response_level_diff)
        elif response_level_diff < 0:
            self._decrease_power_actions(nr_levels=abs(response_level_diff))

        # Create actions
        actions = self._actions_by_response_level[self._current_response_level]
        log_coordinator_actions(self._current_response_level, actions)

        # Dispatch actions
        self._action_dispatcher.dispatch(actions, current_t_r_dict, current_t_set_dict)

    # %% Private methods
    def _populate_ranking_table(self):
        for device_id in self.participants:
            baseline_action = self._baseline_actions[device_id]
            for action in self.action_space:
                if action == baseline_action:  # Skip baseline action: no need to rank it
                    continue  # Only consider actions that are higher than or equal to the baseline action
                # TODO: "Nice to have" Eliminate this for loop to speed up things
                baseline_state = self._baseline_states[device_id]
                advantage_values, _ = self._advantage_functions[device_id](baseline_state)
                assert len(advantage_values) == len(
                    self.action_space), "Action space does not match the advantage function"
                action_ix = self.action_space.index(action)
                cost = advantage_values[action_ix]

                if action > baseline_action:  # Action is to increase power
                    self._ranking_table_up = pd.concat([
                        self._ranking_table_up,
                        pd.DataFrame({'device_id': device_id, 'action': action, 'cost': cost}, index=[0])])
                else:  # Action is to decrease power`
                    self._ranking_table_down = pd.concat([
                        self._ranking_table_down,
                        pd.DataFrame({'device_id': device_id, 'action': action, 'cost': cost}, index=[0])])
        # Filter unreachable actions
        self._ranking_table_up = self._filter_unreachable_actions_upwards(self._ranking_table_up)
        self._ranking_table_down = self._filter_unreachable_actions_upwards(self._ranking_table_down)

        # Create rankings based on lowest cost
        self._ranking_table_up['rank'] = self._ranking_table_up['cost'].rank(method='dense', ascending=False)
        self._ranking_table_down['rank'] = self._ranking_table_down['cost'].rank(method='dense', ascending=False)

    def _filter_unreachable_actions_upwards(self, ranking_table: pd.DataFrame):
        """
        Filters actions from the ranking table that are not reachable by the controller.
        Example: One household with action space [0, 1, 2], with A-values [5, 20, 15]. Action 1 is not reachable, because
        the costs is higher than the cost of a 'more powerful' action 2. So we remove action 1 from the ranking table.
        :param ranking_table: The ranking table to be filtered.
        :return: The filtered ranking table.
        """
        if ranking_table.empty:
            return ranking_table

        # Sort ranking table by cost (ascending)
        ranking_table = ranking_table.sort_values(by='cost', ascending=True)

        new_raking_table = []
        for device_id in ranking_table['device_id'].unique():
            device_ranking_table = ranking_table[ranking_table['device_id'] == device_id]
            remaining_actions_mask = device_ranking_table['action'].diff().fillna(0) >= 0
            device_ranking_table = device_ranking_table[remaining_actions_mask]
            new_raking_table.append(device_ranking_table)

        return pd.concat(new_raking_table)

    def _filter_unreachable_actions_downwards(self, ranking_table: pd.DataFrame):
        """
        Filters actions from the ranking table that are not reachable by the controller.
        Example: One household with action space [0, 1, 2], with A-values [5, 10, 15]. Action 1 is not reachable, because
        the costs is higher than the cost of a 'more powerful' action 2. So we remove action 1 from the ranking table.
        :param ranking_table: The ranking table to be filtered.
        :return: The filtered ranking table.
        """
        if ranking_table.empty:
            return ranking_table

        # Sort ranking table by cost (ascending)
        ranking_table = ranking_table.sort_values(by='cost', ascending=True)

        new_raking_table = []
        for device_id in ranking_table['device_id'].unique():
            device_ranking_table = ranking_table[ranking_table['device_id'] == device_id]
            remaining_actions_mask = device_ranking_table['action'].diff().fillna(0) <= 0
            device_ranking_table = device_ranking_table[remaining_actions_mask]
            new_raking_table.append(device_ranking_table)

        return pd.concat(new_raking_table)

    def _increase_power_actions(self, nr_levels=1):
        """
        Get the next actions to be executed by the coordinator when the DR-target is not yet reached.
        It takes the action with the highest ranking from the ranking table. But it ensures that no device-action pairs
        are executed with the same device.
        :return:
        """
        proposed_response_level = self._current_response_level + nr_levels
        if proposed_response_level > self._response_level_range[1]:
            log_warn(f"Reached maximum response level elevation at dr time {self._step_time}s", TAG)
            proposed_response_level = self._response_level_range[1]
        else:
            log_info(f"Elevating response level from '{self._current_response_level}' to '{proposed_response_level}' "
                     f"at dr time {self._step_time}s")
        self._current_response_level = proposed_response_level

    def _decrease_power_actions(self, nr_levels=1):
        """
        Get the next actions to be executed by the coordinator when the DR-target is overshot.
        It takes the action with the highest ranking from the ranking table. But it ensures that no device-action pairs
        are executed with the same device.
        :return:
        """
        proposed_response_level = self._current_response_level - nr_levels
        if proposed_response_level < self._response_level_range[0]:
            log_warn(f"Reached maximum response level reduction at step time {self._step_time}", TAG)
            proposed_response_level = self._response_level_range[0]
        else:
            log_info(f"Reducing response level from '{self._current_response_level}' to '{proposed_response_level}' "
                     f"at step time {self._step_time}")
        self._current_response_level = proposed_response_level

    def _finish_dr_event(self):
        if self.dr_event_signal.is_set():
            log_info("DR-event finished!", TAG)
        else:
            log_info("DR-event is interrupted!", TAG)

        # Clear the DR-event signal to start the Business-as-Usual mode
        self.dr_event_signal.clear()
        self.finished = True

    def _calculate_actions_per_response_level(self):
        """
        Finds an optimal action set for each Response Level in the range
        The higher the Response Level, the more power we can deliver.
        The lower the Response Level, the more power we can save.
        A response level of 0 means that we only dispatch the baseline actions.
        The action set is a dictionary with device_id as key and action as value.
        """
        self._response_level_range = (-len(self._ranking_table_down), len(self._ranking_table_up))
        # Ensure that ranking tables are sorted by highest rank
        self._ranking_table_up = self._ranking_table_up.sort_values(by='rank', ascending=False)
        self._ranking_table_down = self._ranking_table_down.sort_values(by='rank', ascending=False)

        for response_level in range(-len(self._ranking_table_down), len(self._ranking_table_up) + 1):
            actions = self._baseline_actions.copy()  # Start with the baseline actions

            if response_level == 0:  # Response level 0 means that we only dispatch the baseline actions
                self._actions_by_response_level[0] = actions
                continue

            # Overwrite baseline actions with the actions from the upwards or downwards ranking table
            action_bucket = self._ranking_table_up if response_level > 0 else self._ranking_table_down
            nr_actions_to_take = abs(response_level)
            for i in range(nr_actions_to_take):
                device_id = action_bucket.iloc[i]['device_id']
                actions[device_id] = action_bucket.iloc[i]['action']

            # Store the all actions for this response level
            self._actions_by_response_level[response_level] = actions

    # %% Helper methods for file I/O
    def _parse_trajectory_measurements(self) -> tuple[
        dict[str, State], dict[str, float], dict[str, float], float | int]:
        config = load_config()
        action_space = config['agent']['action_space']
        measurements_dict = self._house_service.get_recent_houses_measurements(self.participants)
        if measurements_dict is None:  # failed to get measurements, return None
            return None

        states: dict[str, State] = {}
        power_observations: dict[str, float] = {}
        action_observations: dict[str, float] = {}

        for device in self.participants:
            assert device in measurements_dict, f"Device {device} not found in measurements_dict"
            # check if the time interval is the same as the one in the config
            # change datatype of time to float
            measurements_dict[device]['time'] = measurements_dict[device]['time'].astype(float)
            observed_intervals = measurements_dict[device]['time'].diff().dropna().unique()
            assert len(
                observed_intervals) == 1, f"Received inconsistent time interval for device {device}: {observed_intervals}"
            observed_interval_sec = int(observed_intervals[0] // 1000)
            expected = config['agent']['trajectory_interval_s']
            if observed_interval_sec != expected:
                if 'test' in device:
                    pass
                else:
                    log_error(f"Observed measurement time interval '{observed_interval_sec}' for {device} does not match the one in the config '{expected}'",
                         TAG)

            newest_measurement = measurements_dict[device].tail(1)
            states[device] = self._generate_state_from_measurements(measurements_dict[device])
            power_observations[device] = states[device].b_m_trajectory[-1]
            t_set = newest_measurement['t_set'].iloc[0]
            if len(action_space) == 2:  # Binary action space
                action_obs = 1 if t_set > 20 else 0
            else:
                raise NotImplementedError("Cannot map t_set to non-binary action space. It's not implemented yet.")
            action_observations[device] = action_obs

        return states, power_observations, action_observations, sum(power_observations.values())

    def _generate_state_from_measurements(self, measurements: pd.DataFrame) -> np.array:
        """
        Generates the state of the environment.
        :param measurement: The measurement of the current time step.
        :param action: The action of the current time step.
        :return: The state of the environment.
        """
        # Assert we have enough historical measurements to create a state
        config = load_config()
        trajectory_length = config['agent']['trajectory_length']
        log_debug(f"{len(measurements)} ", Origin.ACTION_SERVICE)
        assert len(measurements) >= trajectory_length, 'Not enough measurements to create a state'
        
        # Only get the last trajectory_length measurements
        measurements = measurements.tail(trajectory_length)
        latest_measurement = measurements.tail(1)

        # Collect the attributes from the measurements to create the state
        time = latest_measurement['time'].iloc[0]
        t_out = latest_measurement['t_out'].iloc[0]
        t_r_set = latest_measurement['t_r_set'].iloc[0]

        t_r_trajectory = measurements['t_r'].to_numpy()
        b_m_trajectory = measurements['blr_mod_lvl'].to_numpy()
        t_r = latest_measurement['t_r'].iloc[0]

        return State(time, t_out, t_r_set, t_r_trajectory, b_m_trajectory, t_r)

    def _load_advantage_functions(self):
        self._advantage_functions = {}
        for device in self.participants:
            # Load Q functions from file system
            agent = self._storage.load_agent(device)
            baseline_u = self._baseline_actions[device]
            baseline_state = self._baseline_states[device]
            self._advantage_functions[device] = A_Function(agent, baseline_u, baseline_state)

    def get_cur_time(self) -> float:
        return self._step_time

    # %% Visualisation methods
    def plot_dr_response(self):
        # Plot the response of the DR-event
        if not self.finished:
            log_warn("Cannot plot DR-response, DR-event is not yet finished.", TAG)
            return

        t = [stat[0] for stat in self._stats]
        p_observed = [stat[1] for stat in self._stats]
        response_level = [stat[2] for stat in self._stats]
        # Plot
        fix, ax = plt.subplots()
        ax.plot(t, p_observed, label='P Observed', color='blue')
        ax.plot(t, [self._target] * len(p_observed), '--', label='P Target', color='green', )
        ax.plot(t, [sum(self._baseline_consumptions.values())] * len(p_observed), '--', label='P Baseline',
                color='orange')
        # Plot line with dotted line
        ax2 = ax.twinx()
        ax2.plot(t, response_level, label='Response Level', color='red', marker='o')
        # Title
        ax.set_title(f"DR-response")
        # Labels
        ax.set_xlabel('Time [s]')
        ax.set_ylabel('Power [kW]')

        # Set y axis limits
        ax.set_ylim([0, max(p_observed) * 1.1])
        ax2.set_ylabel('Response Level')

        # Legend
        ax.legend(loc='upper left')
        ax2.legend(loc='upper right')

        # Plot
        plt.show()

    def _log_tables(self):
        df_baseline_actions = pd.DataFrame(self._baseline_actions, index=[1]).T
        df_baseline_actions.columns = ['baseline_action']
        log_dataframe(Level.INFO, LogType.BASELINE_ACTIONS, df_baseline_actions)

        df_baseline_consumptions = pd.DataFrame(self._baseline_consumptions, index=[1]).T
        df_baseline_consumptions.columns = ['baseline_consumption']
        log_dataframe(Level.INFO, LogType.BASELINE_CONSUMPTIONS, df_baseline_consumptions)

        log_dataframe(Level.INFO, LogType.RANKING_TABLE_UPWARDS, self._ranking_table_up)
        log_dataframe(Level.INFO, LogType.RANKING_TABLE_DOWNWARDS, self._ranking_table_down)
        log_dataframe(Level.INFO, LogType.ACTION_RESPONSE_LVL_DICT, pd.DataFrame(self._actions_by_response_level))

    def _log_progress_values(self):
        # Convert stats to dataframe
        p_target = [self._target] * len(self._stats)
        df_stats = pd.DataFrame(self._stats, columns=['time', 'p_observed', 'response_level'])
        # Include target power
        df_stats['p_target'] = p_target

        # Add start time to stats
        df_stats['time'] = df_stats['time'] + self._datetime_dr_start
        # Convert epoch time to datetime, in Greek timezone
        df_stats['time'] = df_stats['time'].apply(
            lambda x: datetime.fromtimestamp(x, tz=pytz.timezone('Europe/Athens')))
        # Set time as index
        df_stats.set_index('time', inplace=True)
        # Shuffle order of columns
        df_stats = df_stats[['p_target', 'p_observed', 'response_level']]
        # Rename columns
        df_stats.columns = ['P Target', 'P Observed', 'Response Level']

        # Dispatch info
        log_dataframe(Level.INFO, LogType.DR_PROGRESS, df_stats)
        log_variable(Level.INFO, LogType.RESPONSE_LVL, self._stats[-1][2])
        log_variable(Level.INFO, LogType.OBSERVED_POWER, self._stats[-1][1])
