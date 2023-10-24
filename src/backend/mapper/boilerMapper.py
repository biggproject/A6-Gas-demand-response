from src.backend.model.responses.boiler import Boiler
import re


def map_json_boiler(data) -> Boiler:
    try: 
        b = Boiler(**data)
        return b

    except Exception as e:
        result = re.split(r'\'', str(e))
        data.pop(result[1])
        return map_json_boiler(data)