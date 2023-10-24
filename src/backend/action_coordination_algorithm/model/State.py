from datetime import datetime

import numpy as np
from src.backend.action_coordination_algorithm.helper import load_config
from rltraining.rl_agents.offline_fqi import OfflineAgent


class State:

    def __init__(self,
                 time: int,
                 t_out: float,
                 t_r_set: float,
                 t_r_trajectory: np.array,
                 b_m_trajectory: np.array,
                 t_r: float
                 ):
        config = load_config()

        n = config['agent']['trajectory_length']
        n_t_r = len(t_r_trajectory)
        n_b_m = len(b_m_trajectory)
        assert n_t_r == n, f'The length of the t_r trajectory is not correct, expected {n} but got {n_t_r}'
        assert n_b_m == n, f'The length of the b_m trajectory is not correct, expected {n} but got {n_b_m}'
        self.time = time
        self.t_out = t_out
        self.t_r_set = t_r_set
        self.t_r_trajectory = t_r_trajectory
        self.b_m_trajectory = b_m_trajectory
        self.t_r = t_r

    def transform(self, agent: OfflineAgent) -> np.array:
        trans = agent.transformation_obj

        # Transform trajectory data
        t_r_trajectory_transformed = trans.transform_temp(self.t_r_trajectory)
        b_m_trajectory_transformed = trans.transform_boiler_modulation(self.b_m_trajectory)

        state = np.array([trans.transform_time(self._convert_time()),
                          trans.transform_outside_temp(self.t_out),
                          trans.transform_temp(self.t_r_set),
                          *t_r_trajectory_transformed,
                          *b_m_trajectory_transformed,
                          trans.transform_temp(self.t_r),
                          ])
        return state

    def _convert_time(self) -> int:
        # Transform current time to the number of minutes since the last midnight
        time_int = int(self.time)
        today_at_midnight = datetime.today().replace(hour=0, minute=0, second=0, microsecond=0)
        today_at_midnight = int(today_at_midnight.timestamp() * 1000)
        time_milliseconds_since_midnight = time_int - today_at_midnight
        time_minutes_since_midnight = int(time_milliseconds_since_midnight / 1000 / 60)
        return time_minutes_since_midnight
