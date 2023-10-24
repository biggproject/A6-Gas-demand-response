""" DomxController class """
import json
import os
from requests import post, get, put
from src.misc.codelist.origin import Origin

from src.misc.logger import log_debug, log_error, log_info
from src.backend.model.environment import Environment
from src.backend.model.requests.devicedataRequest import DevicedataRequest


class DomxController: 
    """ Class description: 
        The domx controller makes a connection to the API of domx and returns the raw value
    """

    __env: Environment
    __token: str

    def __init__(self) -> None:
        """Init function description
        Loads in the __environment variables
        """
        with open(os.getcwd() +'/src/assets/dev.json', 'r') as j:
            jsono = json.loads(j.read())
            self.__env = Environment(**jsono)
        self.sign_in()

    def sign_in(self) -> str | None:
        """ Will sign in on the API with the variables from the assets/dev file

        Returns:
            str | None: the results of the sign in on the API
        """

        request_url = f"{self.__env.domain}{'/api/v1/user/signin'}"
        log_info(f"GET {request_url}", Origin.DOMX_CONTROLLER )
        r = post(request_url, data={'email': self.__env.email, 'password': self.__env.password})

        if r.status_code == 200:
            log_debug("Successfully authenticated", Origin.DOMX_CONTROLLER )
            self.__token = r.json()['token']
            return self.__token
        else:
            log_error(f"Authentication failed! {r.status_code} | {r.text}", 'DomX  Controller')
            return None
    
    def get_devicedata(self, request: DevicedataRequest, metrics : list[str]):
        """ Get the device data from a household

        Args:
            request (DevicedataRequest): Object containing the device id and start and end time of the requested data

        Returns:
            str : Raw json data results
        """
        if self.__token:

        
            # map to api call
            from_epoch = int(request.time_from.timestamp() * 1000000000)
            to_epoch = int(request.time_to.timestamp() * 1000000000)

            metric_str = ''
            for metric in metrics:
                metric_str=metric_str+f"&metric[]={metric}"

            request_url = f"{self.__env.domain}/api/v1/devices/{request.device_id}/data/raw?time_from={from_epoch}&time_to={to_epoch}{metric_str}"
            log_info(f"GET {request_url}", Origin.DOMX_CONTROLLER )
            r = get(request_url, headers={'Authorization': f'Bearer {self.__token}'})

            if r.status_code == 200: 
                log_debug(f"GET {request_url} SUCCESS", Origin.DOMX_CONTROLLER )
                return r.json()
            elif r.status_code == 401:
                log_debug("__token expired, getting new __token", Origin.DOMX_CONTROLLER )
                self.sign_in()
                self.get_devicedata(request, metrics)
            else:
                log_error(f"Error {r.status_code}: {r.text}", Origin.DOMX_CONTROLLER )
                return None
        else: 
            self.sign_in()

    def get_last_data(self, device_id: str):
        """ TODO
        Args:
            request (DevicedataRequest): Object containing the device id and start and end time of the requested data

        Returns:
            str : Raw json data results
        """
        if self.__token:

            # map to api call
            request_url = f"{self.__env.domain}/api/v1/devices/{device_id}/data?last=true"
            log_info(f"GET {request_url}", Origin.DOMX_CONTROLLER )
            r = get(request_url, headers={'Authorization': f'Bearer {self.__token}'})

            if r.status_code == 200: 
                log_debug(f"GET {request_url} SUCCESS : {r.json()}", Origin.DOMX_CONTROLLER )
                return r.json()
            elif r.status_code == 401:
                log_debug("__token expired, getting new __token", Origin.DOMX_CONTROLLER )
                self.sign_in()
                self.get_last_data(device_id)
            else:
                log_error(f"Error {r.status_code}: {r.text}", Origin.DOMX_CONTROLLER )
                return None
        else:
            self.sign_in()

    def post_metric(self, device_id : str, action : str, action_value : int):
        # https://<domain>/api/v1/devices/<deviceId>/config
        if self.__token:

            # if device_id == 'domx_ot_e8:31:cd:af:12:44':
                put_url = f"{self.__env.domain}/api/v1/devices/{device_id}/config"
                log_info(f"PUT {put_url}", Origin.DOMX_CONTROLLER )
                r = put(put_url, headers={'Authorization': f'Bearer {self.__token}'}, json={'action': action, 'action_value': int(action_value)})
                if r.status_code == 204: 
                    log_debug(f"PUT {put_url} SUCCESS", Origin.DOMX_CONTROLLER )
                    return True
                elif r.status_code == 401:
                    log_debug("__token expired, getting new __token", Origin.DOMX_CONTROLLER )
                    self.sign_in()
                    self.get_last_data(device_id)
                else:
                    log_error(f"Error {r.status_code}: {r.text}", Origin.DOMX_CONTROLLER )
                    return None

            # else: 
                # log_error(f"Not allowed yet to sent actions to id : {device_id}", Origin.DOMX_CONTROLLER )
        else:
            self.sign_in()
