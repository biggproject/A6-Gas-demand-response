""" Storage controller """
import os
import pickle
import re
from datetime import datetime
from glob import glob

from typing import Optional

from src.misc.logger import log_debug, log_warn
from rltraining.rl_agents.offline_fqi import OfflineAgent
from src.backend.model.filetype import FileType


class Storage:
    """ 
    Class that will directly access the persistent storage
    """
    filepath: str
    __housepath = 'houses/'
    __actions = "action-coordinator/"
    __models_filename = 'models.pkl'

    def __init__(self) -> None:
        """Init function description
        Loads in the environment variables
        """
        # TODO: MS+NIELS: Should we keep the JSON Loader here?
        # with open(sys.path[0]+'./src/assets/dev.json', 'r') as j:
        #     jsono = json.loads(j.read())
        #     env = Environment(**jsono)
        #     self.filepath = env.filelocation
        pass

    def get_file(self, date: str, type: FileType, house: Optional[str]):
        """ Gets the file from the persistent storage location

        Args:
            date (str): the date of the file
            type (FileType): the type of the file, given through an enum value
            house (Optional[str]): when fetching data from a household the house id must be added

        Returns:
            file : returns the file if it exists
        """
        filename = f'{type.value}_{date}.pkl'

        path = self.filepath
        if house:
            path+=f'{self.__housepath}house-{house}/'
        else:
            path+=self.__actions

        path+=f'{type.value}{filename}'
        return path

    def load_agent(self, house_id: str) -> OfflineAgent:
        # root = os.path.join(os.path.dirname(__file__), '..', '..', '..')
        path_training = os.path.join('.', 'data', 'training')
        assert os.path.isdir(path_training), 'Training directory does not exist: {}'.format(path_training)

        agent = self._get_newest_model_by_house_id(path_training, house_id)
        return agent


    def _get_newest_model_by_house_id(self, path_training: str, house_id: str) -> OfflineAgent:
        # Get all directories in path_training that contain house_id
        log_debug('Searching for directories containing house_id: {}'.format(house_id))
        matching_folders = {}  # dict of {date: folder_path}
        for folder in glob(os.path.join(path_training, '*')):
            folder_name = os.path.basename(folder)
            folder_household_id = re.split(r'(?<=\d)\D', folder_name)[0]  # Extract str until first int (e.g. house_99)
            if house_id == folder_household_id:
                # Validate folder file name format
                regex = house_id + '_\d{1,2}_\d{1,2}_\d{4}'
                if not re.match(regex, folder_name):
                    log_warn(f'Unexpected folder name: {folder_name}')
                    continue

                # Parse date from folder name
                date = folder_name.split(house_id)[-1]  # e.g. '_1_1_2021'
                date = date[1:]  # remove leading underscore
                date = datetime.strptime(date, '%d_%m_%Y')  # Date object
                # Check if this directory has a 'models.pkl' file
                if os.path.isfile(os.path.join(folder, self.__models_filename)):
                    matching_folders[date] = folder
                else:
                    log_debug(f'No model file found in folder: {folder}, ignoring folder')

        # Sort dictionary by key descending
        assert len(matching_folders) > 0, 'No matching folders found for house_id: {}'.format(house_id)
        log_debug("Found {} dirs for house_id '{}'".format(len(matching_folders), house_id))
        dates_sorted = sorted(matching_folders.keys(), reverse=True)
        newest_dir = matching_folders[dates_sorted[0]]
        log_debug('Newest dir of {}: {}'.format(house_id, newest_dir))
        return self._get_agent_from_dir(newest_dir)

    def _get_agent_from_dir(self, model_dir: str) -> OfflineAgent:
        log_debug('Loading agent from dir: {}'.format(model_dir))
        model_path = os.path.join(model_dir, self.__models_filename)
        with open(model_path, 'rb') as f_open:
            model = pickle.load(f_open)
        log_debug("Model is successfully loaded!")
        return model


