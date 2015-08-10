"""
    STARBURST ACC/FEANTA Worker Interface
    Author: Lokbondo Kung
    Email: lkkung@caltech.edu
"""

class IWorker(object):
    def __init__(self):
        self.logger = None

    def get_command_list(self):
        raise NotImplementedError

    def execute(self, acc_command):
        raise NotImplementedError

    def set_logger(self, logging_method):
        self.logger = logging_method

