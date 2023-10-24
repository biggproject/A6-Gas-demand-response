from src.backend.model.responses.domx import Domx
import re


def map_json_domx(data) -> Domx:
    try: 
        d = Domx(**data)
        return d

    except TypeError as e:
        result = re.split(r'\'', str(e))
        data.pop(result[1])
        return map_json_domx(data)

