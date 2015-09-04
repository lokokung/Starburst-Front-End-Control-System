"""
    STARBURST ACC/FEANTA GeoBrick Worker
    Author: Lokbondo Kung
    Email: lkkung@caltech.edu
"""

import i_worker
import socket
import struct

# Description of the GeoBrick device. Currently hard-coded.
BRICK_HOSTNAME = 'geobrickanta.solar.pvt'
BRICK_PORT = 1025

# Calibration counts for BRICKCAL method. These are temporary values with
# no substantial meaning and should be changed as necessary.
MOTOR3POS_CTS = -2121054
MOTOR4POS_CTS = -1218574

# Program spaces that can be used in the GeoBrick.
PLC_PROGRAM_SPACE = 10
PROG_PROGRAM_SPACE = 1

# Dictionaries for ethernet packets to the Brick.
RQ_TYPE = {'upload': '\xc0',
           'download': '\x40'}
RQ = {'sendline': '\xb0',
      'getline': '\xb1',
      'flush': '\xb3',
      'getmem': '\xb4',
      'setmem': '\xb5',
      'setbit': '\xba',
      'setbits': '\xbb',
      'port': '\xbe',
      'getresponse': '\xbf',
      'readready': '\xc2',
      'response': '\xc4',
      'getbuffer': '\xc5',
      'writebuffer': '\xc6',
      'writeerror': '\xc7',
      'fwdownload': '\xcb',
      'ipaddress': '\xe0'}
COORDINATE = {1: 'Z',
              3: 'A',
              4: 'X'}
AXIS_SCALING = {1: 42.5636 * 96 * 32,
                3: 23181.5208 * 96 * 32,
                4: 3973.477 * 96 * 32}

# Query Dictionary
QUERY_STATUS_DICT = {'30': 'STOPPED',
              '31': 'POSLIMIT',
              '32': 'NEGLIMIT',
              '40': 'INPOS',
              '41': 'WARNFOLLERR',
              '42': 'FATALFOLLERR',
              '47': 'I2TFAULT',
              '48': 'PHASEERRFAULT'}
QUERY_MOTOR_DICT = {'61': 'ACTUALMPOS',
                    '62': 'COMMPOS',
                    '63': 'TARGETPOS'}
QUERY_FLOAT_DICT = {'75': 'QUADCURRENT',
                    '76': 'DIRECTCURRENT',
                    '77': 'QUADINTEG',
                    '78': 'DIRECTINTEG'}

class BrickWorker(i_worker.IWorker):
    def __init__(self):
        super(BrickWorker, self).__init__()
        self.commands = ['BRICKCAL',
                         'BRICKHALT',
                         'BRICKMOVE',
                         'BRICKOFF',
                         'BRICKLOC',
                         'BRICKANGLE',
                         'BRICKRESET']
        self.brick_socket = None
        self.brick_ip = socket.gethostbyname(BRICK_HOSTNAME)
        self.name = 'GeoBrick-Worker'

    # ---------------------------------------------------------------
    # COMMAND PACKAGING ROUTINES SPECIFIC TO GEOBRICK
    # ---------------------------------------------------------------

    #region Method Description
    """
    Method: __make_brick_command
        Description:
            Takes a command to the Brick and packages it into an
            ethernet packet recognized by the Brick system.
        Arguments:
            rq_type: type of request, either 'upload' or 'download'.
            rq: nature of request, lookup dictionary defined in RQ.
            val: value associated with the request.
            index: index associated with the request.
            command_packets: list of strings to be packed into TCP packets.
    """
    #endregion
    def __make_brick_command(self, rq_type, rq, val, index, command_packets):
        packets = []
        for packet in command_packets:
            buf = RQ_TYPE[rq_type] + RQ[rq]
            buf += struct.pack('H', val)
            buf += struct.pack('H', index)
            buf += struct.pack('H', socket.htons(len(packet) + 1))
            buf += struct.pack(str(len(packet)) + 's', packet)
            buf += struct.pack("B", 0)
            packets.append(buf)
        return packets

    # ---------------------------------------------------------------
    # COMMAND ROUTINES
    # ---------------------------------------------------------------

    #region Method Description
    """
    Method: __brick_cal
        Description:
            Routine to build custom homing PLC program on Brick and
            execute. This method is dependent on the values PLC_PROGRAM_SPACE,
            MOTOR3POS_CTS, and MOTOR4POS_CTS. PLC_PROGRAM_SPACE dictates where
            to save the PLC program on the Brick while the MOTORPOS values
            dictate how far from the positive end for the apparatus to move
            in motor counts before zero-ing for calibration. Do NOT use this
            method on its own. This method is error checked before execution.
        Arguments:
            acc_command: list of the strings sent from the ACC. List format:
                ['BRICKCAL']
        Returns:
            [0]: A list of packets as strings before compression.
            [1]: A list of TCP/Ethernet packets ready to be sent to the Brick.
    """
    #endregion
    def __brick_cal(self, acc_command):
        # Error check that the command given is formatted correctly.
        if len(acc_command) != 1:
            self.logger('Invalid call to BRICKCAL.')
            return None

        # Build homing procedure and execute commands.
        command_packets = []

        command = 'CLOSE ALL \r'
        command += 'OPEN PLC ' + str(PLC_PROGRAM_SPACE) + '\r'
        command += 'CLEAR \r'
        command += 'CMD "#1J/" \r'
        command += 'CMD "#3J/" \r'
        command += 'CMD "#4J/" \r'
        command += 'CMD "#3J+" \r'
        command += 'CMD "#4J+" \r'
        command += 'WHILE (M331=0 OR M431=0)\r'
        command += 'WAIT\r'
        command += 'ENDWHILE\r'
        command_packets.append(command)

        command = 'CMD "#1J/" \r'
        command += 'CMD "#3J/" \r'
        command += 'CMD "#4J/" \r'
        command += 'CMD "#3$*" \r'
        command += 'CMD "#4$*" \r'
        command += 'CMD "#3J/" \r'
        command += 'CMD "#4J/" \r'
        command += 'CMD "#3J=' + str(MOTOR3POS_CTS) + '" \r'
        command += 'CMD "#4J=' + str(MOTOR4POS_CTS) + '" \r'
        command += 'WHILE (M340=0 OR M440=0)\r'
        command += 'WAIT\r'
        command += 'ENDWHILE\r'
        command_packets.append(command)

        command = 'CMD "#1$*" \r'
        command += 'CMD "#3$*" \r'
        command += 'CMD "#4$*" \r'
        command += 'CMD "#1J/" \r'
        command += 'CMD "#3J/" \r'
        command += 'CMD "#4J/" \r'
        command += 'CMD "DISABLE PLC ' + str(PLC_PROGRAM_SPACE) + '" \r'
        command += 'CLOSE \r'
        command += 'ENABLE PLC ' + str(PLC_PROGRAM_SPACE)
        command_packets.append(command)

        command = 'CLOSE ALL'
        command_packets.append(command)

        return command_packets, \
               self.__make_brick_command('download', 'getresponse',
                                         0, 0, command_packets)

    #region Method Description
    """
    Method: __brick_move
        Description:
            Routine to move designated motor to an absolute position
            defined by the conversion factors to physical units. This
            routine should only be called after a BRICKCAL command has
            been issued. Do NOT use this method on its own.
        Arguments:
            acc_command: list of strings sent from the ACC. List format:
                ['BRICKMOVE', motor_number, destination] where motor_number
                is the motor to be moved and destination is the destination
                in physical units. For motor 1 and 4 the units are mm and
                for motor 3 the units are degrees.
        Returns:
            [0]: A list of packets as strings before compression.
            [1]: A list of TCP/Ethernet packets ready to be sent to the Brick.
    """
    #endregion
    def __brick_move(self, acc_command):
        # Error check that the command given is formatted correctly.
        if len(acc_command) != 3:
            self.logger('Invalid call to BRICKMOVE.')
            return None
        motor_num = None
        position = None
        try:
            motor_num = int(acc_command[1])
            position = float(acc_command[2])
        except ValueError:
            self.logger('Invalid call to BRICKMOVE.')
            return None
        if motor_num not in COORDINATE.keys():
            self.logger('Invalid call to BRICKMOVE.')
            return None

        # Build command based on parameters. (This assumes that the
        # position given is in physical units.)
        command_packets = []

        command = 'CLOSE ALL \r'
        command += '#1J/ \r'
        command += '#3J/ \r'
        command += '#4J/ \r'
        command += '&'
        command += str(motor_num)
        command += '!'
        command += COORDINATE[motor_num]
        command += str(position)
        command_packets.append(command)

        command = 'CLOSE ALL'
        command_packets.append(command)

        return command_packets, \
               self.__make_brick_command('download', 'getresponse',
                                         0, 0, command_packets)

    #region Method Description
    """
    Method: __brick_off
        Description:
            Routine to move designated motor an offset of some value in
            physical units. This routine should only be called after a
            BRICKCAL command has been issued. Do NOT use this method on
            its own.
        Arguments:
            acc_command: list of strings sent from the ACC. List format:
                ['BRICKMOVE', motor_number, offset] where motor_number
                is the motor to be moved and offset is the offset
                in physical units. For motor 1 and 4 the units are mm and
                for motor 3 the units are degrees.
        Returns:
            [0]: A list of packets as strings before compression.
            [1]: A list of TCP/Ethernet packets ready to be sent to the Brick.
    """
    #endregion
    def __brick_off(self, acc_command):
        # Error check that the command given is formatted correctly.
        if len(acc_command) != 3:
            self.logger('Invalid call to BRICKOFF.')
            return None
        motor_num = None
        offset = None
        try:
            motor_num = int(acc_command[1])
            offset = float(acc_command[2])
        except ValueError:
            self.logger('Invalid call to BRICKOFF.')
            return None
        if motor_num not in COORDINATE.keys():
            self.logger('Invalid call to BRICKOFF.')
            return None

        # Build offset procedure into a program and execute.
        command_packets = []

        command = 'CLOSE ALL \r'
        command += '#1J/ \r'
        command += '#3J/ \r'
        command += '#4J/ \r'
        command += 'OPEN PROG ' + str(PROG_PROGRAM_SPACE) + '\r'
        command += 'CLEAR \r'
        command += 'INC \r'
        command += COORDINATE[motor_num] + str(offset) + '\r'
        command += 'CLOSE \r'
        command_packets.append(command)

        command = 'OPEN PLC ' + str(PLC_PROGRAM_SPACE) + '\r'
        command += 'CLEAR \r'
        command += 'ADDRESS &' + str(motor_num) + '#' + str(motor_num)
        command += 'CMD "B' + str(PROG_PROGRAM_SPACE) + 'R" \r'
        command += 'WHILE (M' + str(motor_num) + '40=0)\r'
        command += 'WAIT\r'
        command += 'ENDWHILE\r'
        command_packets.append(command)

        command = 'CMD "DISABLE PLC ' + str(PLC_PROGRAM_SPACE) + '" \r'
        command += 'CLOSE ALL'
        command += 'ENABLE PLC' + str(PLC_PROGRAM_SPACE)
        command_packets.append(command)

        return command_packets, \
               self.__make_brick_command('download', 'getresponse',
                                         0, 0, command_packets)

    #region Method Description
    """
    Method: __brick_halt
        Description:
            Routine to kill a motor and reset it so that it can be moved
            again as necessary. This does not immediately stop the motors,
            rather it brakes them and resets them. Do NOT use this method on
            its own. (Also, note that repeated use of this command can wear
            down the brakes system and should only be used when necessary.)
        Arguments:
            acc_command: list of strings sent from the ACC. List format:
                ['BRICKHALT', motor_number] where motor_number is self
                explanatory.
        Returns:
            [0]: A list of packets as strings before compression.
            [1]: A list of TCP/Ethernet packets ready to be sent to the Brick.
    """
    #endregion
    def __brick_halt(self, acc_command):
        # Error check that the command given is formatted correctly.
        if len(acc_command) != 2:
            self.logger('Invalid call to BRICKHALT.')
            return None
        motor_num = None
        try:
            motor_num = int(acc_command[1])
        except ValueError:
            self.logger('Invalid call to BRICKHALT.')
            return None
        if motor_num not in COORDINATE.keys():
            self.logger('Invalid call to BRICKHALT.')
            return None

        # Build command based on parameters.
        command_packets = []

        command = 'CLOSE ALL \r'
        command += '#' + str(motor_num) + 'K \r'
        command += '#' + str(motor_num) + 'J/'
        command_packets.append(command)

        command = 'CLOSE ALL'
        command_packets.append(command)

        return command_packets, \
               self.__make_brick_command('download', 'getresponse',
                                         0, 0, command_packets)

    #region Method Description
    """
    Method: __brick_loc
        Description:
            Routine to move all motors to a designated coordinate defined
            in absolute physical units. This routine should only be called
            after a BRICKCAL command has been issued. Do NOT use this method
            on its own.
        Arguments:
            acc_command: list of strings sent from the ACC. List format:
                ['BRICKLOC', motor1_pos, motor3_pos, motor4_pos] where the
                motor_pos values are the absolute locations for the three
                motors. Note that motor 1 and 4 are in mm and motor 3 is in
                degrees.
        Returns:
            [0]: A list of packets as strings before compression.
            [1]: A list of TCP/Ethernet packets ready to be sent to the Brick.
    """
    #endregion
    def __brick_loc(self, acc_command):
        # Error check that the command given is formatted correctly.
        if len(acc_command) != 4:
            self.logger('Invalid call to BRICKLOC.')
            return None
        position1 = None
        position3 = None
        position4 = None
        try:
            position1 = float(acc_command[1])
            position3 = float(acc_command[2])
            position4 = float(acc_command[3])
        except ValueError:
            self.logger('Invalid call to BRICKLOC.')
            return None

        # Build command based on parameters. (This assumes that the
        # position given is in physical units.)
        command_packets = []

        command = 'CLOSE ALL \r'
        command += '#1J/ \r #3J/ \r #4J/'
        command += '&'
        command += str(1)
        command += '!'
        command += COORDINATE[1]
        command += str(position1)
        command += '&'
        command += str(3)
        command += '!'
        command += COORDINATE[3]
        command += str(position3)
        command += '&'
        command += str(4)
        command += '!'
        command += COORDINATE[4]
        command += str(position4)
        command_packets.append(command)

        command = 'CLOSE ALL'
        command_packets.append(command)

        return command_packets, \
               self.__make_brick_command('download', 'getresponse',
                                         0, 0, command_packets)

    #region Method Description
    """
    Method: __brick_angle
        Description:
            Routine to move motor 3 to a given angle. This routine should only
            be called after a BRICKCAL command has been issued. Do NOT use
            this method on its own.
        Arguments:
            acc_command: list of strings sent from the ACC. List format:
                ['BRICKANGLE', angle] where angle is the absolute angle to be
                set.
        Returns:
            [0]: A list of packets as strings before compression.
            [1]: A list of TCP/Ethernet packets ready to be sent to the Brick.
    """
    #endregion
    def __brick_angle(self, acc_command):
        # Error check that the command given is formatted correctly.
        if len(acc_command) != 2:
            self.logger('Invalid call to BRICKANGLE.')
            return None
        motor_num = None
        position = None
        try:
            angle = int(acc_command[1])
        except ValueError:
            self.logger('Invalid call to BRICKANGLE.')
            return None

        # Build command based on parameters.
        command_packets = []

        command = 'CLOSE ALL \r'
        command += '#3J/ \r'
        command += '&'
        command += str(3)
        command += '!'
        command += COORDINATE[3]
        command += str(angle)
        command_packets.append(command)

        command = 'CLOSE ALL'
        command_packets.append(command)

        return command_packets, self.__make_brick_command('download', 'getresponse',
                                            0, 0, command_packets)

    #region Method Description
    """
    Method: __brick_reset
        Description:
            Routine to reset the Brick cleanly. Do NOT use this method on its
            own.
        Arguments:
            acc_command: list of strings sent from the ACC. List format:
                ['BRICKRESET'].
        Returns:
            [0]: A list of packets as strings before compression.
            [1]: A list of TCP/Ethernet packets ready to be sent to the Brick.
    """
    #endregion
    def __brick_reset(self, acc_command):
        # Error check that the command given is formatted correctly.
        if len(acc_command) != 1:
            self.logger('Invalid call to BRICKRESET.')
            return None

        # Build homing procedure and execute commands.
        command_packets = []

        command = 'CLOSE ALL \r'
        command += 'OPEN PROG ' + str(PROG_PROGRAM_SPACE) + '\r'
        command += 'CLEAR \r'
        command += 'M6014=0 \r'
        command += 'DWELL2000 \r'
        command += 'CMD"$$$" \r'
        command += 'CLOSE \r'
        command += 'B' + str(PROG_PROGRAM_SPACE) + 'R'
        command_packets.append(command)

        command = 'CLOSE ALL'
        command_packets.append(command)

        return command_packets, \
               self.__make_brick_command('download', 'getresponse',
                                         0, 0, command_packets)

    # ---------------------------------------------------------------
    # FUNCTION MAP
    # ---------------------------------------------------------------
    function_map = {'BRICKCAL': __brick_cal,
                    'BRICKMOVE': __brick_move,
                    'BRICKOFF': __brick_off,
                    'BRICKHALT': __brick_halt,
                    'BRICKLOC' : __brick_loc,
                    'BRICKANGLE': __brick_angle,
                    'BRICKRESET': __brick_reset}

    # ---------------------------------------------------------------
    # STATEFRAME HELPERS
    # ---------------------------------------------------------------
    def __brickmonitor_query(self, axis):
        self.brick_socket = socket.socket(socket.AF_INET,
                                          socket.SOCK_STREAM)
        self.brick_socket.settimeout(1.5)
        self.brick_socket.connect((self.brick_ip, BRICK_PORT))
        axis_poll = {}

        # Handle status polling.
        for key, value in QUERY_STATUS_DICT.items():
            cmd_string = ['M' + str(axis) + key]
            cmd = self.__make_brick_command('download', 'getresponse',
                                            0, 0, cmd_string)
            self.brick_socket.sendall(cmd[0])
            response = self.brick_socket.recv(1024)
            response = response[:-2]
            response_value = 0
            try:
                response_value = int(response)
            except ValueError:
                pass
            axis_poll[value] = response_value

        # Handle motor polling.
        for key, value in QUERY_MOTOR_DICT.items():
            cmd_string = ['M' + str(axis) + key]
            cmd = self.__make_brick_command('download', 'getresponse',
                                            0, 0, cmd_string)
            self.brick_socket.sendall(cmd[0])
            response = self.brick_socket.recv(1024)
            response = response[:-2]
            response_value = 0
            try:
                response_value = float(response)
                response_value /= AXIS_SCALING[axis]
            except ValueError:
                pass
            axis_poll[value] = response_value

        # Handle float polling.
        for key, value in QUERY_FLOAT_DICT.items():
            cmd_string = ['M' + str(axis) + key]
            cmd = self.__make_brick_command('download', 'getresponse',
                                            0, 0, cmd_string)
            self.brick_socket.sendall(cmd[0])
            response = self.brick_socket.recv(1024)
            response = response[:-2]
            response_value = 0
            try:
                response_value = float(response)
            except ValueError:
                pass
            axis_poll[value] = response_value

        # Close connections.
        self.brick_socket.close()
        self.brick_socket = None

        return axis_poll

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
        # Use the routine functions to get the commands to push.
        packets = self.function_map[acc_command[0]](
                    self, acc_command)

        if packets is not None:
            self.logger('Issued the following commands to brick:')
            for packet in packets[0]:
                self.logger(repr(packet))

            # Try pushing message across TCP.
            # Wait for reply of at most 1024 bytes.
            try:
                for packet in packets[1]:
                    reply = None
                    self.brick_socket = socket.socket(socket.AF_INET,
                                              socket.SOCK_STREAM)
                    self.brick_socket.connect((self.brick_ip, BRICK_PORT))
                    self.brick_socket.sendall(packet)
                    self.brick_socket.settimeout(1.5)
                    reply = self.brick_socket.recv(1024)

                    self.logger('Reply from brick: ' + reply)
                    self.brick_socket.close()
                    self.brick_socket = None
            except socket.gaierror:
                self.logger('Brick hostname could not be resolved.')
            except socket.error:
                self.logger('Unable to send packet to brick.')

    # region Method Description
    """
    Method: stateframe_query
        Description:
            Refer to abstract class IWorker located in i_worker.py
            for full description.
    """
    # endregion
    def stateframe_query(self):
        stateframe_data = {}
        for axis in [1, 3, 4]:
            axis_dict = self.__brickmonitor_query(axis)
            stateframe_data['AXIS' + str(axis)] = axis_dict
        return stateframe_data
