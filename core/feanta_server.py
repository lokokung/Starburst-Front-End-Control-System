"""
    STARBURST ACC/FEANTA Middle Server
    Author: Lokbondo Kung
    Email: lkkung@caltech.edu
"""

import daemon
import datetime
import socket
import sys
import time

# Logging information.
TIMESTAMP_FMT = '%Y-%m-%d %H:%M:%S'
LOG_FILE = 'bridge_server.log'

# Define all constants:
# Currently hard-coded, will eventually be read from acc.ini
HOST = ''
HOST_PORT = 5676

# region Class Description
"""
Class: ServerDaemon
    Description:
        Implementation of a daemon server that is intended to run on
        the feanta box in order to process commands from the ACC and
        direct and execute the commands to the sub-units connected to
        the feanta computer.
    Arguments:
        pidfile: string designating the .pid file to save the pid for
            this daemon process to allow for the process to be stopped
            by the stop function or to be stopped manually in Linux.
"""
# endregion
class ServerDaemon(daemon.Daemon):
    def __init__(self, pidfile):
        super(ServerDaemon, self).__init__(pidfile)
        self.workers = {}
        self.function_map = {}
        self.log_file = LOG_FILE

    # ---------------------------------------------------------------
    # BASIC ROUTINES:
    # ---------------------------------------------------------------
    def __get_timestamp(self):
        current_time = time.time()
        timestamp = datetime.datetime.fromtimestamp(current_time)
        timestamp = timestamp.strftime(TIMESTAMP_FMT)
        return timestamp

    def __log(self, message):
        log_message = self.__get_timestamp() + ': ' + message + '\n'
        f = open(self.log_file, "a")
        f.write(log_message)
        f.close()
        print log_message

    # ---------------------------------------------------------------
    # CORE ROUTINES
    # ---------------------------------------------------------------

    # region Method Description
    """
    Method: link_worker
        Description:
            This method is used to link a worker extending the i_worker
            class to this server so that commands associated with the
            i_worker can be executed properly through this server.
        Arguments:
            worker: the target worker to be linked to this server
    """
    # endregion
    def link_worker(self, worker):
        self.workers[worker.name] = worker
        for command in worker.get_command_list():
            self.function_map[command] = worker
        worker.set_logger(self.__log)

    # region Method Description
    """
    Method: list_workers
        Description:
            Lists each worker linked to this ServerDaemon.
    """
    # endregion
    def list_workers(self):
        workers_list = ''
        for worker in self.workers.keys():
            workers_list += worker + '\n'
        return workers_list

    # region Method Description
    """
    Method: set_log_file
        Description:
            Sets the destination path for the log file. Defaulted to
            LOG_FILE.
    """
    # endregion
    def set_log_file(self, log_file_destination):
        self.log_file = log_file_destination

    # region Method Description
    """
    Method: list_commands
        Description:
            Lists every command that this server can respond to.
    """
    # endregion
    def list_commands(self):
        return self.function_map.keys()

    # region Method Description
    """
    Method: run
        Description:
            Daemon routine for the ServerDaemon between the ACC and the Brick.
    """
    # endregion
    def run(self):
        # Setup listener to this box at HOST_PORT.
        acc_listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.__log('Attempt to set up listener...')
        try:
            acc_listener.bind((HOST, HOST_PORT))
        except socket.error, msg:
            self.__log('Unable to listen at port ' + str(HOST_PORT) +
                       '. Error Code: ' + str(msg[0]) + '. Message: ' +
                       str(msg[1]))
            sys.exit()
        acc_listener.listen(1)
        self.__log('Successfully setup listener')

        while True:
            # Wait for a connection from ACC.
            connection, address = acc_listener.accept()
            self.__log('Connection from ' + address[0] +
                       ':' + str(address[1]))

            # Read packet sent from ACC, currently capped at 1024 bytes.
            acc_command = connection.recv(1024)
            self.__log('Command issued from connection: ' + acc_command)
            acc_command = acc_command.split()

            # Echo command issued back to ACC.
            connection.sendall(acc_command[0])

            # Verify that the given command exists and execute it with the
            # correct worker if it does.
            try:
                worker = self.function_map[acc_command[0]]
                worker.execute(acc_command)
            except KeyError:
                self.__log('Unrecognized command received: ' +
                           acc_command[0] + '.')

