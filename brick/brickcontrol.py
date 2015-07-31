"""
    STARBURST ACC/GeoBrick Bridge Server
    Author: Lokbondo Kung
    Email: lkkung@caltech.edu
"""

import daemon
import datetime
import os
import socket
import struct
import sys
import time

# Logging information.
TIMESTAMP_FMT = '%Y-%m-%d %H:%M:%S'
LOG_FILE = 'bridge_server.log'

# Define all constants:
# Currently hard-coded, will eventually be read from acc.ini
HOST = ''
HOST_PORT = 5676

BRICK_HOSTNAME = 'geobrickanta.solar.pvt'
BRICK_PORT = 1025

MOTOR3POS_CTS = -2121054
MOTOR4POS_CTS = -1218574

RX_SELECT_LOW_Z = 200
RX_SELECT_LOW_X = -500
RX_SELECT_HIGH_Z = 75
RX_SELECT_HIGH_X = 500

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


class BridgeServer(daemon.Daemon):
    # ---------------------------------------------------------------
    # COMMON ROUTINES:
    # ---------------------------------------------------------------
    def __get_timestamp(self):
        current_time = time.time()
        timestamp = datetime.datetime.fromtimestamp(current_time)
        timestamp = timestamp.strftime(TIMESTAMP_FMT)
        return timestamp

    def __log(self, message):
        log_message = self.__get_timestamp() + ': ' + message + '\n'
        f = open(LOG_FILE, "a")
        f.write(log_message)
        f.close()
        print log_message

    # ---------------------------------------------------------------
    # BRICK ROUTINES:
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
            self.__log('Invalid call to BRICKCAL.')
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
            self.__log('Invalid call to BRICKMOVE.')
            return None
        motor_num = None
        position = None
        try:
            motor_num = int(acc_command[1])
            position = float(acc_command[2])
        except ValueError:
            self.__log('Invalid call to BRICKMOVE.')
            return None
        if motor_num not in COORDINATE.keys():
            self.__log('Invalid call to BRICKMOVE.')
            return None

        # Build command based on parameters. (This assumes that the
        # position given is in physical units.)
        command_packets = []

        command = 'CLOSE ALL'
        command += 'CMD "#1J/" \r'
        command += 'CMD "#3J/" \r'
        command += 'CMD "#4J/" \r'
        command += '&'
        command += str(motor_num)
        command += '!'
        command += COORDINATE[motor_num]
        command += str(position)
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
            self.__log('Invalid call to BRICKOFF.')
            return None
        motor_num = None
        offset = None
        try:
            motor_num = int(acc_command[1])
            offset = float(acc_command[2])
        except ValueError:
            self.__log('Invalid call to BRICKOFF.')
            return None
        if motor_num not in COORDINATE.keys():
            self.__log('Invalid call to BRICKOFF.')
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
        command += 'ADDRESS &' + str(motor_num) + '#' + str(motor_num) + '\r'
        command += 'CMD "B' + str(PROG_PROGRAM_SPACE) + 'R" \r'
        command += 'WHILE (M' + str(motor_num) + '40=0)\r'
        command += 'WAIT\r'
        command += 'ENDWHILE\r'
        command_packets.append(command)

        command = 'CMD "DISABLE PLC ' + str(PLC_PROGRAM_SPACE) + '" \r'
        command += 'CLOSE \r'
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
            self.__log('Invalid call to BRICKHALT.')
            return None
        motor_num = None
        try:
            motor_num = int(acc_command[1])
        except ValueError:
            self.__log('Invalid call to BRICKHALT.')
            return None
        if motor_num not in COORDINATE.keys():
            self.__log('Invalid call to BRICKHALT.')
            return None

        # Build command based on parameters.
        command_packets = []

        command = '#' + str(motor_num) + 'K \r'
        command += '#' + str(motor_num) + 'J/'
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
            self.__log('Invalid call to BRICKLOC.')
            return None
        position1 = None
        position3 = None
        position4 = None
        try:
            position1 = float(acc_command[1])
            position3 = float(acc_command[2])
            position4 = float(acc_command[3])
        except ValueError:
            self.__log('Invalid call to BRICKLOC.')
            return None

        # Build command based on parameters. (This assumes that the
        # position given is in physical units.)
        command_packets = []

        command = '#1J/ \r #3J/ \r #4J/'
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
            self.__log('Invalid call to BRICKANGLE.')
            return None
        motor_num = None
        position = None
        try:
            angle = int(acc_command[1])
        except ValueError:
            self.__log('Invalid call to BRICKANGLE.')
            return None

        # Build command based on parameters.
        command_packets = []

        command = '#3J/ \r'
        command += '&'
        command += str(3)
        command += '!'
        command += COORDINATE[3]
        command += str(angle)
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
            self.__log('Invalid call to BRICKRESET.')
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

        return command_packets, \
               self.__make_brick_command('download', 'getresponse',
                                         0, 0, command_packets)

    # Function mapping depending on the command passed from ACC.
    function_map = {'BRICKCAL': __brick_cal,
                    'BRICKMOVE': __brick_move,
                    'BRICKOFF': __brick_off,
                    'BRICKHALT': __brick_halt,
                    'BRICKLOC' : __brick_loc,
                    'BRICKANGLE': __brick_angle,
                    'BRICKRESET': __brick_reset}

    #region Method Description
    """
    Method: run
        Description:
            Daemon routine for the BridgeServer between the ACC and the Brick.
    """
    #endregion
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

            # Verify that the given command exists.
            packets = None
            if acc_command[0] in self.function_map.keys():
                packets = self.function_map[acc_command[0]](
                    self, acc_command)
            else:
                self.__log('Unrecognized command received: ' +
                           acc_command[0] + '.')

            if packets is not None:
                self.__log('Issued the following commands to brick:')
                for packet in packets[0]:
                    self.__log(repr(packet))

                brick_socket = socket.socket(socket.AF_INET,
                                             socket.SOCK_STREAM)
                reply = None

                # Get IP address and try pushing message across TCP.
                # Wait for reply of at most 1024 bytes.
                try:
                    brick_ip = socket.gethostbyname(BRICK_HOSTNAME)
                    brick_socket.connect((brick_ip, BRICK_PORT))
                    for packet in packets[1]:
                        brick_socket.sendall(packet)
                        brick_socket.settimeout(1.5)
                        reply = brick_socket.recv(1024)
                        self.__log('Reply from brick: ' + reply)
                except socket.gaierror:
                    self.__log('Brick hostname could not be resolved.')
                except socket.error:
                    self.__log('Unable to send packet to brick.')
                brick_socket.close()

"""
Main Method.
"""
if __name__ == '__main__':
    server_instance = BridgeServer('bridge_server.pid')
    server_instance.start()
