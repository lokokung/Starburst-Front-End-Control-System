"""
    STARBURST ACC/FEANTA BeagleBone Worker
    Author: Lokbondo Kung
    Email: lkkung@caltech.edu
"""

import i_worker
import socket

# Description of the BeagleBone device. Currently hard-coded.
BB_HOSTNAME = 'lna14.solar.pvt'
BB_PORT = 50002

class BBWorker(i_worker.IWorker):
    def __init__(self):
        super(BBWorker, self).__init__()
        self.commands = ['LNAGATEA',
                         'LNAGATEB',
                         'LNADRAIN',
                         'LNABIAS']
        self.name = 'BB-Worker'
        self.bb_socket = None
        self.bb_ip = socket.gethostbyname(BB_HOSTNAME)

    # ---------------------------------------------------------------
    # COMMAND ROUTINES
    # ---------------------------------------------------------------

    # region Method Description
    """
    Method: __lnagatea
        Description:
            Routine to build command to change voltage on the LNA
            Gate A.
        Arguments:
            acc_command: list of the strings sent from the ACC. List format:
                ['LNAGATEA', amp_number, voltage]
        Returns:
            command: command designated to complete task.
    """
    # endregion
    def __lnagatea(self, acc_command):
        # Error check that the command given is formatted correctly.
        if len(acc_command) != 3:
            self.logger('Invalid call to LNAGATEA.')
            return None
        amp_num = None
        voltage = None
        try:
            amp_num = int(acc_command[1])
            voltage = float(acc_command[2])
        except ValueError:
            self.logger('Invalid call to LNAGATEA.')
            return None
        if amp_num < 0 or amp_num > 3:
            self.logger('Invalid call to LNAGATEA.')
            return None

        # Given that the parameters are all reasonable, we return the
        # command string to be processed later.
        command = 'set amp ' + str(amp_num) + ' gatea ' + str(voltage)
        return command

    # region Method Description
    """
    Method: __lnagateb
        Description:
            Routine to build command to change voltage on the LNA
            Gate B.
        Arguments:
            acc_command: list of the strings sent from the ACC. List format:
                ['LNAGATEB', amp_number, voltage]
        Returns:
            command: command designated to complete task.
    """
    # endregion
    def __lnagateb(self, acc_command):
        # Error check that the command given is formatted correctly.
        if len(acc_command) != 3:
            self.logger('Invalid call to LNAGATEB.')
            return None
        amp_num = None
        voltage = None
        try:
            amp_num = int(acc_command[1])
            voltage = float(acc_command[2])
        except ValueError:
            self.logger('Invalid call to LNAGATEB.')
            return None
        if amp_num < 0 or amp_num > 3:
            self.logger('Invalid call to LNAGATEB.')
            return None

        # Given that the parameters are all reasonable, we return the
        # command string to be processed later.
        command = 'set amp ' + str(amp_num) + ' gateb ' + str(voltage)
        return command

    # region Method Description
    """
    Method: __lnadrain
        Description:
            Routine to build command to change voltage on the LNA drain.
        Arguments:
            acc_command: list of the strings sent from the ACC. List format:
                ['LNADRAIN', amp_number, voltage]
        Returns:
            command: command designated to complete task.
    """
    # endregion
    def __lnadrain(self, acc_command):
        # Error check that the command given is formatted correctly.
        if len(acc_command) != 3:
            self.logger('Invalid call to LNADRAIN.')
            return None
        amp_num = None
        voltage = None
        try:
            amp_num = int(acc_command[1])
            voltage = float(acc_command[2])
        except ValueError:
            self.logger('Invalid call to LNADRAIN.')
            return None
        if amp_num < 0 or amp_num > 3:
            self.logger('Invalid call to LNADRAIN.')
            return None

        # Given that the parameters are all reasonable, we return the
        # command string to be processed later.
        command = 'set amp ' + str(amp_num) + ' drain ' + str(voltage)
        return command

    # region Method Description
    """
    Method: __lnabias
        Description:
            Routine to latch changed to the LNA.
        Arguments:
            acc_command: list of the strings sent from the ACC. List format:
                ['LNABIAS', amp_number, positive_value_to_latch]
        Returns:
            command: command designated to complete task.
    """
    # endregion
    def __lnabias(self, acc_command):
        # Error check that the command given is formatted correctly.
        if len(acc_command) != 3:
            self.logger('Invalid call to LNABIAS.')
            return None
        amp_num = None
        state = None
        try:
            amp_num = int(acc_command[1])
            state = int(acc_command[2])
        except ValueError:
            self.logger('Invalid call to LNABIAS.')
            return None
        if amp_num < 0 or amp_num > 3:
            self.logger('Invalid call to LNABIAS.')
            return None
        if state <= 0:
            return None

        # Given that the parameters are all reasonable, we return the
        # command string to be processed later.
        command = 'latch'
        return command

    # ---------------------------------------------------------------
    # FUNCTION MAP
    # ---------------------------------------------------------------
    function_map = {'LNAGATEA': __lnagatea,
                    'LNAGATEB': __lnagateb,
                    'LNADRAIN': __lnadrain,
                    'LNABIAS': __lnabias}

    # ---------------------------------------------------------------
    # INTERFACE IMPLEMENTATIONS
    # ---------------------------------------------------------------

    # region Method Description
    """
    Method: get_command_list
        Description:
            Refer to abstract class IWorker located in i_worker.py
            for full description.
    """
    # endregion
    def get_command_list(self):
        return self.commands

    # region Method Description
    """
    Method: execute
        Description:
            Refer to abstract class IWorker located in i_worker.py
            for full description.
    """
    # endregion
    def execute(self, acc_command):

        # Use the routine calls to generate url commands.
        command_string = self.function_map[acc_command[0]](self, acc_command)
        if command_string is not None:
            self.bb_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.bb_socket.connect((self.bb_ip, BB_PORT))
            self.logger('The following link was followed for the PDU: ' +
                        command_string)

            command_string += '\r\n'
            self.bb_socket.sendall(command_string)
            self.bb_socket.close()
            self.bb_socket = None

