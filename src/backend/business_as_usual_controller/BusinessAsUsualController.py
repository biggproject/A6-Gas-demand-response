from threading import Thread, Event
from src.backend.action_coordination_algorithm.ActionDispatcher import ActionDispatcher
from src.backend.action_coordination_algorithm.helper import load_config
from src.backend.service.action_service import ActionService
from src.backend.service.housesservice import HouseService
from src.misc.codelist.origin import Origin
from src.misc.logger import log_info, log_warn
import time

TAG = Origin.BAU_CONTROLLER


class BusinessAsUsualController(Thread):
    def __init__(self, dr_event_signal: Event):
        Thread.__init__(self)
        config = load_config()
        self._house_service = HouseService()
        self._action_dispatcher = ActionDispatcher()
        self._dr_event_signal = dr_event_signal
        self._participants = config['dr_event']['participants']
        self._control_interval_s = config['bau_controller']['control_interval_s']
        self._action_space = config['agent']['action_space']
        self.stopped = True
        self._action_service = ActionService()

    def run(self):
        just_stopped = False

        while True:
            if not self._dr_event_signal.is_set():
                if self.stopped:
                    log_info("BaU controller started", TAG)
                    self._action_service.stop_updating()
                    self.stopped = False
                log_info("Getting t_set and t_r_set for each household", TAG)
                res = self._house_service.get_latest(self._participants)
                if res is not None:  # Data received successfully
                    _, t_r_dict, t_r_set_dict = res
                    # Check if there is no DR event being launched in the meantime
                    if self._dr_event_signal.is_set():
                        just_stopped = True
                        continue

                    action_dict = {}
                    for participant in self._participants:
                        action_dict[participant] = 1 if t_r_set_dict[participant] > t_r_dict[participant] else 0
                    log_info("Dispatching actions", TAG)
                    self._action_dispatcher.dispatch(action_dict, t_r_dict, t_r_set_dict)

                    # Check if there is no DR event being launched in the meantime
                    if self._dr_event_signal.is_set():
                        just_stopped = True
                        continue
                else:  # Failure: Just continue at the next control interval
                    log_warn(f"Failed to receive the latest measurement for this control interval.", TAG)

                # Now we wait until the next control interval or until a DR event is launched
                last_dispatch = time.time()
                time_text = time.strftime("%H:%M:%S", time.localtime(last_dispatch + self._control_interval_s))
                log_info(f"Waiting for next control interval (until {time_text})", TAG)
                while time.time() < last_dispatch + self._control_interval_s and not self._dr_event_signal.is_set():
                    time.sleep(0.1)
                if self._dr_event_signal.is_set():
                    just_stopped = True
            elif just_stopped:
                log_info("BaU controller stopped", TAG)
                just_stopped = False
                self.stopped = True
            else:
                # DR event is active, wait until it is over
                time.sleep(0.1)
