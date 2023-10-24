from enum import Enum


class Origin(Enum):
    TEST = 'test'
    START = 'start'
    BAU_CONTROLLER = 'Business-as-usual controller'
    ACTION_SERVICE = 'Action service'
    BACKUP_CONTROLLER = 'Backup controller'
    COORDINATOR = 'Coordinator'
    DISPATCHER = 'Dispatcher'
    DOMX_CONTROLLER = 'domX controller'
    GET_CALL = 'Get'
    POST_CALL = 'Post' 
      
    