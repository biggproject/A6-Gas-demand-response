from src.backend.controller.domxController import DomxController
from src.backend.model.requests.devicedataRequest import DevicedataRequest
from src.backend.model.responses.devicedataRespone import DevicedataResponse

class DomxService:
    """_summary_

    Returns:
        _type_: _description_
    """
    __event_dispatcher = DomxController()

    def get_device_data(self, device_data: DevicedataRequest, metrics : list[str]) -> DevicedataResponse:
        """ Get data according to the device request 

        Args:
            device_data (DevicedataRequest): the parameters for the request

        Returns:
            json: list of data
        """

        r = DomxService.__event_dispatcher.get_devicedata(device_data, metrics)
        if r == None:
            return r
        else:
            try:
                return DevicedataResponse(r['boiler'],r['domx'])
            except Exception:
                print("Did not work ", flush=True)

    def get_last_device_data(self, device_id: str) -> DevicedataResponse:
        """ Get data according to the device request 

        Args:
            device_data (DevicedataRequest): the parameters for the request

        Returns:
            json: list of data
        """

        r = DomxService.__event_dispatcher.get_last_data(device_id)
        if r == None:
            return r
        else:
            try:
                return DevicedataResponse(r['boiler'],r['domx'])
            except Exception:
                print("Did not work ", flush=True)