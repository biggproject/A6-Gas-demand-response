from typing import Tuple, Any

import numpy as np
import yaml

from src.backend.action_coordination_algorithm.helper import load_config
from src.backend.action_coordination_algorithm.model.State import State
from rltraining.rl_agents.offline_fqi import OfflineAgent
import os
from os import path


class A_Function:
    def __init__(self, agent: OfflineAgent, baseline_u: float, state: State):
        self.agent = agent
        self.Q_fn = agent.meanQ
        config = load_config()
        self.action_space = config['agent']['action_space']
        assert baseline_u in self.action_space, \
            f'Baseline u is not in action space, expected action in {self.action_space} but got {baseline_u}'
        u_pos = self.action_space.index(baseline_u)
        state_baseline = state.transform(agent)
        q_values = self.Q_fn(state_baseline)
        assert len(q_values) == 1, 'Q-values should be a list of length 1'
        assert len(q_values[0]) == len(self.action_space), 'Q-values do not match action space'
        self.q_value_baseline = self.Q_fn(state_baseline)[0][u_pos]

    def __call__(self, state: State) -> tuple[np.array, float]:
        state = state.transform(self.agent)
        q_values = self.Q_fn(state)[0]
        a_values = q_values - self.q_value_baseline
        u = self.action_space[np.argmin(a_values)]
        return a_values, u

