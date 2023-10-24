import logging
import logging_loki

class LokiLogger:

    def __init__(self) -> None:
        self.handler = logging_loki.LokiHandler(
            url="<private>", 
            tags={"application": "action-coord"},
            version="1",
        )
        print("loki loggin creating ", flush=True)
        self.logger = logging.getLogger("action-coord")
        self.logger.addHandler(self.handler)



    def log_loki(self, origin : str, msg, level):
        self.logger.warning(
            msg, 
            extra={"tags": {"origin" : origin, "level": level}},
        )

    def log_debug(self, origin : str, msg):
        self.logger.debug(
            msg, 
            extra={"tags": {"origin" : origin}},
        )

    def log_warn(self, origin : str, msg):
        self.logger.warn(
            msg, 
            extra={"tags": {"origin" : origin}},
        )

    def log_info(self, origin : str, msg):
        self.logger.info(
            msg, 
            extra={"tags": {"origin" : origin}},
        )