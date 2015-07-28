"""
    STARBURST ACC/GeoBrick Bridge Server
    Author: Lokbondo Kung
    Email: lkkung@caltech.edu
"""

import socket
import daemon
import sys
import struct

# Define all constants:
#   Currently hard-coded, will eventually be read from acc.ini
HOST = ''
HOST_PORT = 5676
BRICK_HOSTNAME = 'geobrickanta.solar.pvt'
BRICK_PORT = 1025

# Dictionary for ethernet packets to the Brick.
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
    """
    Method: __make_command
        Description:
            Takes a command to the Brick and packages it into an
            ethernet packet recognized by the Brick system.
        Arguments:
            rq_type: type of request, either 'upload' or 'download'.
            rq: nature of request, lookup dictionary defined in RQ.
            val: value associated with the request.
            index: index associated with the request.
            command_string: command to be executed as a string.
    """

    def __make_command(self, rq_type, rq, val, index, command_string):
        buf = RQ_TYPE[rq_type] + RQ[rq]
        buf += struct.pack('H', val)
        buf += struct.pack('H', index)
        buf += struct.pack('H', socket.htons(len(command_string) + 1))
        buf += struct.pack(str(len(command_string)) + 's', command_string)
        buf += struct.pack("B", 0)
        return buf

    def __brick_move(self, acc_command):
        # Error check that the command given is formatted correctly.
        if len(acc_command) != 3:
            print 'usage: BRICKMOVE motor_num position'
            return None
        motor_num = None
        position = None
        try:
            motor_num = int(acc_command[1])
            position = float(acc_command[2])
        except ValueError:
            print 'usage: BRICKMOVE motor_num position'
            return None

        # Build command based on parameters. (This assumes that the
        # position given is in physical units.)
        command = '&'
        command += str(motor_num)
        command += '!'
        command += COORDINATE[motor_num]
        command += str(position)

        return command, self.__make_command('download', 'getresponse',
                                            0, 0, command)

    # Function mapping depending on the command passed from ACC.
    function_map = {'BRICKMOVE': __brick_move}

    def run(self):
        # Setup listener to this box at HOST_PORT.
        acc_listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        print 'Setup listener.'
        try:
            acc_listener.bind((HOST, HOST_PORT))
        except socket.error, msg:
            print ('Unable to listen at port ' + str(HOST_PORT) +
                   '. Error Code: ' + str(msg[0]) + '. Message: ' +
                   str(msg[1]))
            sys.exit()
        acc_listener.listen(1)
        print ('Successfully setup listener..\n')

        while True:
            # Wait for a connection from ACC.
            connection, address = acc_listener.accept()
            print ('Connection from ' + address[0] +
                   ':' + str(address[1]) + '\n')

            # Read packet sent from ACC, currently capped at 1024 bytes.
            acc_command = connection.recv(1024).split()

            # Echo command issued back to ACC.
            connection.sendall(acc_command[0])

            # Verify that the given command exists.
            packet = None
            if acc_command[0] in self.function_map.keys():
                packet = self.function_map[acc_command[0]](
                    self, acc_command)
            else:
                print acc_command[0] + 'is not a recognized command.'
            print 'Issued the following command to brick: ' + packet[0] + '\n'

            if packet is not None:
                brick_socket = socket.socket(socket.AF_INET,
                                             socket.SOCK_STREAM)
                reply = None

                # Get IP address and try pushing message across TCP.
                # Wait for reply of at most 1024 bytes.
                try:
                    brick_ip = socket.gethostbyname(BRICK_HOSTNAME)
                    brick_socket.connect((brick_ip, BRICK_PORT))
                    brick_socket.sendall(packet[1])
                    brick_socket.settimeout(1.5)
                    reply = brick_socket.recv(1024)
                    print (reply + '\n')
                except socket.gaierror:
                    print 'Brick hostname could not be resolved.'
                except socket.error:
                    print 'Unable to send packet to brick.'
                brick_socket.close()


if __name__ == '__main__':
    server_instance = BridgeServer('bridge_server.pid')
    server_instance.start()
