from datetime import datetime
import os
import time
from os import path
from src.misc.codelist.level import Level
from src.misc.codelist.origin import Origin
from src.misc.codelist.type import LogType
import pandas as pd
# from src.misc.loki_logger import LokiLogger

root = path.join(os.path.dirname(__file__), "..", "..")
dr_related = [
    Origin.ACTION_SERVICE,
    Origin.BACKUP_CONTROLLER,
    Origin.COORDINATOR,
    Origin.DISPATCHER,
    Origin.DOMX_CONTROLLER
]

# loki = LokiLogger()

class Timestamps:
    timestamp = ''

times = Timestamps()


class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def setcurrentdrtiem(self, time):
    self.currentdrtime = time

def write_line_to_log_line(line):
    logs_dir = path.join(root, 'data', 'action-coord', 'console_output')
    if not os.path.exists(logs_dir):
        os.makedirs(logs_dir)
    # Get current hour
    now = datetime.now()
    current_hour = now.strftime("%H")
    # Get current date
    current_date = now.strftime("%Y-%m-%d")
    # Create file name
    file_name = f'{current_date}_{current_hour}h.log'
    # Check if log file exists
    if not os.path.exists(path.join(logs_dir, file_name)):
        # Create file
        with open(path.join(logs_dir, file_name), 'w') as f:
            f.write(line + '\n')
    else:
        # Append to file
        with open(path.join(logs_dir, file_name), 'a') as f:
            f.write(line + '\n')

    f.close()


def log(text, color=bcolors.ENDC):
    print(color + text + bcolors.ENDC, flush=True)
    write_line_to_log_line(text)


def log_debug(text, label : Origin = Origin.TEST):
    log(f"[DEBUG][{_get_current_timestamp()}][{label.value}]: {text}")
    # loki.log_loki(label.value, text, 'DEBUG')


def log_warn(text, label : Origin = Origin.TEST):
    log(f"[WARN][{_get_current_timestamp()}][{label.value}]: {text}", bcolors.WARNING)
    # loki.log_loki(label.value, text, 'WARN')

def log_error(text, label : Origin= Origin.TEST):
    log(f"[ERROR][{_get_current_timestamp()}][{label.value}]: {text}", bcolors.FAIL)
    # loki.log_loki(label.value, text, 'ERROR')


def log_info(text, label : Origin= Origin.TEST):
    log(f"[INFO][{_get_current_timestamp()}][{label.value}]: {text}", bcolors.OKBLUE)
    # loki.log_loki(label.value, text, 'INFO')


def log_test(text, label : Origin= Origin.TEST):
    log(f"[TEST][{_get_current_timestamp()}][{label}]: {text}", bcolors.OKGREEN)
    # loki.log_loki(label.value, text, 'TEST')

def _get_current_timestamp():
    now = time.localtime()
    return time.strftime("%Y-%m-%d %H:%M:%S", now)

def log_coordinator_actions(response_level, actions: dict[str, float]):
    # Get current date and timestamp with milliseconds
    now = time.localtime()
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S", now)
    line = f"{timestamp}; {response_level}; {actions}\n"
    filepath = path.join(root, 'data', 'action-coord', 'coordinator_actions.txt')

    # append to file
    with open(filepath, 'a') as file:
        file.write(f"{line}")
    file.close()

def _get_current_timestamp():
    now = time.localtime()
    return time.strftime("%Y-%m-%d %H:%M:%S", now)

def get_houses_log():
    filepath = path.join(root, 'data', 'action-coord', 'coordinator_actions.txt')
    file = open(filepath, 'r')
    lines = file.readlines()
    result = ''
    for line in lines:
        splitted = line.split(";")
        result = result + splitted[2]
    return result

def get_logs(type : str):
    filepath = path.join(root, 'data', 'action-coord', f'{type}.txt')
    try:
        file = open(filepath, 'r')
        lines = file.readlines()
        result = ''
        for line in lines:
            splitted = line.split(";")
            result=result+ line
        return result
    except FileNotFoundError:
        return None

def get_log_time(type : str, start : datetime):
    filepath = path.join(root, 'data', 'action-coord', f'{type}.txt')
    try:
        file = open(filepath, 'r')
        lines = file.readlines()
        result = ''
        for line in lines:
            splitted = line.split(";")
            date_time = datetime.strptime(splitted[0], '%Y-%m-%d %H:%M:%S')
            if date_time == start:
                result=splitted[3]
        return result
    except FileNotFoundError:
        return None

def get_last_logs(type : str):
    filepath = path.join(root, 'data', 'action-coord', f'{type}.txt')
    try:
        file = open(filepath, 'r')
        lines = file.readlines()
        result = ''
        for line in lines:
            splitted = line.split(";")
            result=splitted[2]
        return result
    except FileNotFoundError:
        return None

def get_times():
    filepath = path.join(root, 'data', 'action-coord', f'{LogType.TIMESTAMP.value}.txt')
    try:
        file = open(filepath, 'r')
        lines = file.readlines()
        result = ''
        for line in lines:
            splitted = line.split(";")
            result=result+ f"{splitted[0]}\n"
        return result
    except FileNotFoundError:
        return None

result = ''
def last_time():
    filepath = path.join(root, 'data', 'action-coord', f'{LogType.TIMESTAMP.value}.txt')
    try:
        with open(filepath, 'r') as f:
            result = f.readlines()[-1]
        return result.strip()
    except FileNotFoundError:
        return None

def log_dataframe( level: Level, type : LogType, dataFrame):
    """ Log dataframe with certain log leven and logtype to be able to query on grafana

    Args:
        level (Level): The level of the log used as Level.INFO
        type (LogType): The type of the log, each type is a different object,
                        used as LogType.TEST
        dataFrame (_type_): A pandas dataframe
    """
     # Get current date and timestamp with milliseconds
    now = time.localtime()
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S", now)
    line = f"{last_time()}; {timestamp}; {level.value}; {dataFrame.to_json(orient='table')}\n"
    filepath = path.join(root, 'data', 'action-coord', f'{type.value}.txt')

    # append to file
    with open(filepath, 'a') as file:
        file.write(f"{line}")
    file.close()

def log_variable(level: Level, type : LogType, variable):
    """ Log variable with certain log leven and logtype to be able to query on grafana

    Args:
        level (Level): The level of the log used as Level.INFO
        type (LogType): The type of the log, each type is a different object,
                        used as LogType.TEST
        variable (_type_): A variable
    """
     # Get current date and timestamp with milliseconds
    now = time.localtime()
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S", now)
    line = f"{last_time()}; {timestamp}; {level.value}; {variable}\n"
    filepath = path.join(root, 'data', 'action-coord', f'{type.value}.txt')

    # append to file
    with open(filepath, 'a') as file:
        file.write(f"{line}")

    file.close()

def log_timestamp(type : LogType, variable):
    """ Log variable with certain log leven and logtype to be able to query on grafana

    Args:
        level (Level): The level of the log used as Level.INFO
        type (LogType): The type of the log, each type is a different object,
                        used as LogType.TEST
        variable (_type_): A variable
    """
     # Get current date and timestamp with milliseconds
    now = time.localtime()
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S", now)
    times.timestamp = timestamp
    print(times.timestamp, flush=True)
    line = f"{timestamp}\n"
    filepath = path.join(root, 'data', 'action-coord', f'{type.value}.txt')

    # append to file
    with open(filepath, 'a') as file:
        file.write(f"{line}")

    file.close()