from dataclasses import dataclass
import json


@dataclass
class ObeliskRequest:
    """ The parameters for making a request to the obelisk database
    """ 
    metrics: list[str]
    start: int
    end: int
    house: str
    datasets: str = "63a1ccd441485f345165dbf8"

    def mapper(self, cursor):
        """ Maps the parameters to the correct json format to send a request

        Returns:
            json : contains the parameters in json format
        """
        if cursor: 
            concatstring = {
                "dataRange": {
                    "datasets": [
                        self.datasets
                    ],
                    "metrics": 
                        self.metrics
                },
                "from": self.start,
                "to": self.end,
                "limit": 100000,
                "filter": {
                    "source": {
                        "_eq": self.house
                    }
                },
                "cursor": cursor
            }
        else: 
            concatstring = {
                "dataRange": {
                    "datasets": [
                        self.datasets
                    ],
                    "metrics": 
                        self.metrics
                },
                "from": self.start,
                "to": self.end,
                "limit": 100000,
                "filter": {
                    "source": {
                        "_eq": self.house
                    }
                }
            }
        return json.dumps(concatstring) 
