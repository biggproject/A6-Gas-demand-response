import time
from datetime import datetime
import json
import os
from threading import Event
from requests import get

import time
from flask import Flask, request
from flask_cors import CORS, cross_origin
from src.backend.business_as_usual_controller.BusinessAsUsualController import BusinessAsUsualController
from src.backend.model.requests.datagroupedRequest import DataGrouped
from src.backend.service.action_service import ActionService
import re
from src.backend.service.obelisk_customer import ObeliskConsumer
from src.misc.codelist.level import Level
from src.misc.codelist.type import LogType
from src.misc.logger import get_last_logs, get_log_time, get_logs, get_times, log_error, log_info, log_timestamp, log_variable, log_warn
import signal
from src.misc.codelist.origin import Origin

app = Flask(__name__)
CORS(app)
app.debug = True


# Start the api
action = ActionService()

# Start Business-as-usual controller
dr_event_signal = Event()
bau_controller = BusinessAsUsualController(dr_event_signal)
bau_controller.start()

drtime = 0

@app.route('/senddrevent', methods=['POST'])
@cross_origin()
def senddrevent():
    """ Sends a DR Event to the service

    Returns:
        template:  dr succes/failed page
    """
    if dr_event_signal.is_set():
        return '0'
    else:
        seconds = int(request.form['seconds'])
        energy = float(request.form['energy'])
        log_info("", Origin.START)
        log_info("---------- START OF NEW DR EVENT ----------", Origin.START)

        try: 
            r = get("<private>")
            log_info(f"Latest information fetched for grafana board")
            # TODO DISABLING THE MINUTE UPDATES
            action_service = ActionService()
            action_service.stop_updating()

        except Exception:
            log_error(f"Grafana did not update")
        log_info("DR event", Origin.POST_CALL )
        # # send request to action coordinator algorithm

        now = time.localtime()
        drtime= time.strftime("%Y-%m-%d %H:%M:%S", now)

        log_timestamp(LogType.TIMESTAMP, drtime)
        log_variable(Level.INFO, LogType.DR_PARAM_SECONDS, seconds)
        log_variable(Level.INFO, LogType.DR_PARAM_ENERGY, energy)

        # Signal BaU controller to stop
        dr_event_signal.set()
        while bau_controller.stopped:
            # wait for BaU controller to stop
            time.sleep(0.1)
        log_info("BaU controller stopped, now starting DR-event", Origin.BAU_CONTROLLER)
        # Start Action Coordinator controller
        action.post_dr_event(seconds, energy, dr_event_signal)
        
        return '1'


@app.route('/datagrouped', methods=['GET'])
def getdatagrouped():
    """ Get the data from domx through our own obelisk setup

    Returns:
        string: json string
    """
    log_info("Fetch data from obelisk", Origin.GET_CALL )

    content = json.loads(request.data)
    try:
        k = DataGrouped(**content)
        # Get the request from the obelisk consumer
        obcons = ObeliskConsumer(k.user_id_obelisk)
        data_json = obcons.get_data(k)
        return data_json

    except TypeError as inst:
        # Error msg: DataGrouped.__init__() missing 1 required positional argument: 'start'
        missing_arg = re.split(':', inst.args[0])
        return f"Missing argument:  {missing_arg[1]}"


@app.route('/logs', methods=['GET'])
def getlogs():
    log_info("Fetch local logs", Origin.GET_CALL )

    type = request.args['type']
    try: 
        start = request.args['start']
        start_date = datetime.strptime(start, '%Y-%m-%d %H:%M:%S')

        return get_log_time(type, start_date)
    except:
        print("No start and end")

    results = ''
    results = get_logs(type)
    if results == None:
        return "Nothing"
    else:
        return results



@app.route('/lastlogs', methods=['GET'])
def getlastlogs():
    log_info("Fetch local logs - last", Origin.GET_CALL )

    type = request.args['type']
    
    results = ''
    results = get_last_logs(type)
    if results == None:
        return "Nothing"
    else:
        return results


@app.route('/drtimes', methods=['GET'])     
def getdrtimes():
    log_info("Fetch dr times", Origin.GET_CALL )
    
    results = ''
    results = get_times()
    if results == None:
        return "Nothing"
    else:
        return results

@app.route('/getorigin', methods=['GET'])     
def getorigin():
    log_info("Origin values", Origin.GET_CALL )
    print([e.value for e in Origin], flush=True)
    v = str([e.value for e in Origin])[1:-1].replace('\'', '')
    return v
   
@app.route('/kill', methods=['GET'])    
@cross_origin()
def killed():
    log_warn("KILL", Origin.GET_CALL )

    pw = request.args['pw']

    if pw == '01234':
        dr_event_signal.clear()  # This will stop the DR controller and enable the BaU controller
        return "exitting"
    else:
        return "nice try"
