from enum import Enum


class LogType(Enum):
    TEST = 'test'
    BASELINE_ACTIONS = 'baseline_actions'
    BASELINE_CONSUMPTIONS = 'baseline_consumptions'
    RANKING_TABLE_UPWARDS = 'ranking_table_upwards'
    RANKING_TABLE_DOWNWARDS = 'ranking_table_downwards'
    ACTION_RESPONSE_LVL_DICT = 'action_response_lvl'
    RESPONSE_LVL = 'response_lvl'
    OBSERVED_POWER = 'observed_power'
    DR_PROGRESS = 'dr_progress'
    DR_PARAM_SECONDS = 'second_param'
    DR_PARAM_ENERGY = 'energy_param'
    TIMESTAMP = 'timestamp'