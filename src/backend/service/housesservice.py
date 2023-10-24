import time
from datetime import datetime, timedelta
from os import path
import pandas as pd
from src.backend.action_coordination_algorithm.helper import load_config
from src.backend.controller.domxController import DomxController
from src.backend.mapper.boilerMapper import map_json_boiler
from src.backend.mapper.domxMapper import map_json_domx
from src.backend.model.requests.devicedataRequest import DevicedataRequest
from src.backend.model.responses.boiler import Boiler
from src.backend.model.responses.devicedataRespone import DevicedataResponse
from src.backend.model.responses.domx import Domx
from src.backend.service.domxService import DomxService
from src.backend.service.obelisk_customer import ObeliskConsumer
from src.misc.codelist.origin import Origin
from src.misc.logger import log_warn, log_debug


class HouseService:
    """ Get the models from the houses
    """
    controller = DomxController()

    def put_t_set_house(self, house: str, t_set_value : int) -> bool:
        """ Newly fetched data from the domx api will be stored in the storage

        Args:
            house (str): house id
        Returns:
            bool: succes or failed value for the action
        """
        # only one value will be set so this is a fairly easy implementation
        # if multiple would be set , change the unctions
        return self.controller.post_metric(house, 't_set', t_set_value)

    def get_recent_houses_measurements(self, house_ids: list[str]) -> dict[str, pd.DataFrame]:
        """
        Get all the measurements from the given houses from the last 12 hours

        Args:
            house_ids (list[str]): list of house ids ex. House_2

        Returns:
            dict[str, np.array]: dictionary containing the measurements, where key is the house id, and value the
            measurement matrix. The measurement matrix is in the following format:
            [
              [time, t_out, t_r_set, t_r, b_m, t_set],
              [...]                                  ,
              [time, t_out, t_r_set, t_r, b_m, t_set],
            ]

            met blr_mod_lvl = b_m

        """
        measurements: dict[str, pd.DataFrame] = {}
        config = load_config()

        # Filter out houses that have the word 'test' in it
        for house_id in house_ids:
            if 'test' in house_id:
                measurements[house_id] = self._get_test_measurements(house_id)
            else:
                # Load from domx
                domx = DomxService()
                trajectory_length = config['agent']['trajectory_length']
                trajectory_interval_s = config['agent']['trajectory_interval_s']
                start = datetime.now() - timedelta(seconds=trajectory_interval_s * (trajectory_length + 12) )
                end = datetime.now()
                metrics = ['t_out', 't_r_set', 't_r', 'blr_mod_lvl', 't_set']
                log_debug(f"Getting measurements from domX for period '{start}' - '{end}'")

                
                res = domx.get_device_data(DevicedataRequest(config['house_id_mappings'][house_id], start, end), metrics)
                if res == None:
                    return None

                df = pd.DataFrame(res.domx)
                df_b = pd.DataFrame(res.boiler)
                df2 = pd.concat([df, df_b])
                df2 = df2[['time', 't_out', 't_r_set', 't_r', 'blr_mod_lvl', 't_set']]
                df2.rename(columns={'time': "timestamp"}, inplace=True)
                print(df2)
                ob = ObeliskConsumer()

                results = ob.format_given(df2)
                df = pd.DataFrame.from_dict(results, orient='index')
                df = df.reset_index()
                df.rename(columns={'index': 'time'}, inplace=True)

                measurements[house_id] = df

        return measurements

    def get_latest(self, house_ids: list[str], parameters: list[str] = ['t_r', 't_r_set','']) -> tuple[float, dict[str, float], dict[str, float]]:
        """
        Get ONLY THE LATEST t_r and t_set values for the given houses; and the summed b_m values
        Args:
            house_ids: List of house ids
        Returns:
            tuple[float, dict[str, float], dict[str, float]]: The summed b_m value of all houses; and a tuple
            containing the latest t_r and t_set values for the given houses
        """
        b_m_summed: float = 0 # blr_mod_lvl
        t_r_dict  = {} # t_r
        t_r_set_dict = {} # t_set
        config = load_config()
        domx = DomxService()

        for house_id in house_ids:
            if 'test' in house_id:
                latest_measurement = self._get_test_measurements(house_id).tail(1)
                b_m_summed += latest_measurement['blr_mod_lvl'].iloc[0]
                t_r_dict[house_id] = latest_measurement['t_r'].iloc[0]
                t_r_set_dict[house_id] = latest_measurement['t_r_set'].iloc[0]
            else:
                res: DevicedataResponse = domx.get_last_device_data(config['house_id_mappings'][house_id])
                
                try:
                    b_m_summed += (float(res.boiler[0]['blr_mod_lvl']) if float(res.boiler[0]['blr_mod_lvl']) > 0  else 0.0)
                    t_r_dict[house_id]=float(res.domx[0]['t_r'])
                    t_r_set_dict[house_id]=float(res.domx[0]['t_r_set'])
                except Exception:
                    return None

        return b_m_summed, t_r_dict, t_r_set_dict

    def _get_test_measurements(self, device) -> pd.DataFrame:
        root = path.join(path.dirname(__file__), "..", "..", "..")
        date_str = '{dt.day}_{dt.month}_{dt.year}'.format(dt=datetime.now())
        folder_name = f'{device}_{date_str}'
        folder_path = path.join(root, 'data', 'training', folder_name)
        file_dir = path.join(folder_path, device + '_measurements.csv')
        # Check if file exists
        if not path.exists(file_dir):
            raise FileNotFoundError(f"File {file_dir} does not exist.")
        df = self._force_load_df(file_dir)

        df.sort_values(by='time', ascending=True, inplace=True)
        trajectory_length = load_config()['agent']['trajectory_length']
        df = df.tail(trajectory_length)  # Select only the needed measurements

        return df

    def _force_load_df(self, file_dir: str) -> pd.DataFrame:
        # Check if file exists
        if not path.exists(file_dir):
            raise FileNotFoundError(f"File {file_dir} does not exist.")
        df = None
        while df is None:
            try:
                df = pd.read_csv(file_dir)
            except pd.errors.EmptyDataError:
                log_warn(f"File {file_dir} is busy. Waiting for access...")
                time.sleep(0.01)
        return df
