import os
import logging

from utils import getter

class Logger(object):
    _instance = None

    @staticmethod
    def get(args=None):
        if Logger._instance == None:
            if args != None:
                Logger(args)
            else:
                raise Exception('pass in the arguments')
                
        return Logger._instance
    
    def __init__(self, args):
        if Logger._instance != None:
            raise Exception('logger class is a singleton')

        else: 
            run_id = getter.get_run_id(args)
            folder = getter.get_result_folder(args, action=args.action)

            logger = logging.getLogger(__name__)
            logger.setLevel(logging.DEBUG)

            c_handler = logging.StreamHandler()
            f_handler = logging.FileHandler(os.path.join(folder, run_id + '.log'), mode='w')
            format = logging.Formatter('%(asctime)s - %(levelname)s - %(filename)s - %(message)s', datefmt='%d-%m-%y %H:%M:%S')
            c_handler.setFormatter(format)
            f_handler.setFormatter(format)

            # add handlers to the logger
            logger.addHandler(c_handler)
            logger.addHandler(f_handler)

            Logger._instance = logger