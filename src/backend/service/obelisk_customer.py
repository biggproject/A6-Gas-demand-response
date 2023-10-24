from itertools import groupby
import json

from requests import post

from src.backend.action_coordination_algorithm.helper import load_config
from src.backend.codelist.domxObelisk import domx_list
from src.backend.codelist.boilerObelisk import boiler_list
from src.backend.model.requests.datagroupedRequest import DataGrouped
from src.backend.model.requests.obeliskRequest import ObeliskRequest
import requests
from src.backend.model.responses.obeliskResponse import ObeliskResponse
from src.backend.model.responses.obelisk_auth import ObeliskToken
import pandas as pd
from src.misc.codelist.origin import Origin

from src.misc.logger import log_info, log_warn


class ObeliskConsumer:
    """ The class that will access the obelisk database, only able to read the database

    """
    
    metrics: list[str] = []
    __token: str
    __house:str

    def __init__(self, token = '<private>') -> None:
        """ initialize the consumer
        """
        self.metrics = []
        self.authenticate(token)
        
    def authenticate(self, token):
        """ Authenticate on the obselisk database

        Returns:
            bool: validation 
        """
        values = '''{
            "grant_type": "client_credentials"
        }'''

        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Basic {token}'
        }  # TODO the value should be stored in a secret

        # cast responde as object 
        response = requests.post('https://obelisk.ilabt.imec.be/api/v3/auth/token', data=values, headers=headers, timeout=15)
        res: ObeliskToken = ObeliskToken(**response.json())
        self.__token = res.access_token
        return True

    def format_given(self, data):
        # clean data 
        cleaned = self.__clean_domx_data((data))

        # format__clean_data
        # formatted = self.__format_data(cleaned)
            
        return cleaned



    def get_data(self, data: DataGrouped):
        """ Get data from obelisk database

        Args:
            data (DataGrouped): the request from the api

        Returns:
            json : a json string with the data in the correct format
        """
        if self.__token:
            self.__house = data.house_id
            response = self.__api_call(data)
            # clean data 
            cleaned = self.__clean_data((response))

            # format
            formatted = self.__format_data(cleaned)
            
            return formatted
        else:
            self.authenticate(data.user_id_obelisk)
            return self.get_data(data)
    
    def __map_data(self, data: DataGrouped) -> ObeliskRequest:
        """ Map the wanted api request to the obelisk request format

        Args:
            data (DataGrouped): the api request

        Returns:
            ObeliskRequest: the obelisk request
        """
        # map the data to an obeslisk object
        for el_d in data.metrics_domx:
            element_value = domx_list[el_d]
            self.metrics.append(element_value)

        for el_b in data.metrics_boiler:
            element_value = boiler_list[el_b]
            self.metrics.append(element_value)

        return ObeliskRequest(self.metrics, data.start, data.end, data.house_id)

    def __format_data(self, data_json):
        """ format the received data from obelisk

        Args:
            data_json (json string): the json received from obelisk

        Returns:
            json string: formatted to own chosen format
        """
        items_parsed: list[ObeliskResponse] = []

        for i in data_json:
            items_parsed.append(ObeliskResponse(**i))
        
        items_parsed.sort(key=lambda x: (x.source, x.timestamp))
        groups = groupby(items_parsed, key=lambda x: x.source)
          
        totals = dict()
        for source, source_it in groups:
            source_list = list(source_it)
            source_list.sort(key=lambda x: (x.timestamp))
            groups_time = groupby(source_list, key=lambda x: x.timestamp)
            source_time = dict()

            for time, time_it in groups_time:
                time_list = dict()
                for el in list(time_it):
                    try:
                        time_list[el.metric.split('::')[0].split('.')[1]] = el.value
                    except Exception:
                        continue
                source_time[time] = time_list
            totals = source_time # only give the house value - some refactoring needed
        return json.dumps(totals)

    def __clean_data(self, df):
        """ Clean the received obelisk data

        Args:
            df (dataframe): The received dataframe from obelisk api calls

        Returns:
            json: cleaned json string
        """
        pd.set_option('display.max_columns', None)
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')

        #  filter out negative values of 
        # domx.t_r::number, domx.t_set::number, domx.t_r_set::number
        df = df.loc[~((df['metric'] == 'domx.t_r::number') & (df['value'] < 0))]
        df = df.loc[~((df['metric'] == 'domx.t_set::number') & (df['value'] < 0))]
        df = df.loc[~((df['metric'] == 'domx.t_r_set::number') & (df['value'] < 0))]

        # put blr_mod_lvl = 0 if heat is 0
        temp = df.drop_duplicates().set_index(['source','timestamp', 'metric'], append=True)
        temp = temp.unstack()
        temp.columns = temp.columns.droplevel()        
        temp = temp.reset_index()

        try:
            temp['boiler.blr_mod_lvl::number'].mask(temp['boiler.heat::number'] == 0, 0, inplace=True)
        except Exception:
            print("NO SUCH VARIABLES NEEDED")
        
        resampled = temp.set_index('timestamp').groupby(['source']).resample("5Min").mean()
        stacked = resampled.stack().to_frame().rename(columns={0:'value'})

        return json.loads(stacked.to_json(orient="table"))["data"]
    
    def __clean_domx_data(self, df):
        """ Clean the received obelisk data

        Args:
            df (dataframe): The received dataframe from obelisk api calls

        Returns:
            json: cleaned json string
        """
        pd.set_option('display.max_columns', None)

        df['timestamp'] = pd.to_datetime(df['timestamp'])#-midnight).seconds
        config = load_config()
        time_interval = config['agent']['trajectory_interval_s']
        resampled = df.set_index('timestamp').resample('5Min').mean()
        resampled = resampled.fillna(method='ffill')

        resampled2 = resampled.resample(f"{time_interval}s").mean()
        return json.loads(resampled2.to_json(orient="index"))


    def __api_call(self, data: DataGrouped):
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.__token}'
        }
        master_df_list = []
        pages = True
        cursor = None
        while pages:
            response = post("https://rc.obelisk.ilabt.imec.be/api/v3/data/query/events", data=self.__map_data(data).mapper(cursor), headers=headers, timeout=15)
            df = pd.DataFrame.from_dict(response.json()['items'])
            master_df_list.append(df)

            if response.json()['cursor'] is None:
                pages = False
            else:
                cursor = response.json()['cursor']
        
        concatenated = pd.concat(master_df_list)
        return concatenated
