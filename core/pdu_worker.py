"""
    STARBURST ACC/FEANTA PDU Worker
    Author: Lokbondo Kung
    Email: lkkung@caltech.edu
"""

import mechanize
import urllib
import i_worker

PDU_HOSTNAME = 'http://pduanta.solar.pvt'
PDU_USERNAME = 'admin'
PDU_PASSWORD = 'power'

ON_OFF_MAP = {0: 'OFF',
              1: 'ON'}


class PDUWorker(i_worker.IWorker):
    def __init__(self):
        super(PDUWorker, self).__init__()
        self.commands = ['OUTLET', 'ND-ON', 'ND-OFF']
        self.browser = None

    def __login(self):
        self.browser = mechanize.Browser()
        self.browser.set_handle_robots(False)
        self.browser.set_handle_refresh(False)

        login_data = {'Username': PDU_USERNAME,
                      'Password': PDU_PASSWORD}
        encoded_data = urllib.urlencode(login_data)
        self.browser.open(PDU_HOSTNAME + '/login.tgi', encoded_data, timeout=3)
        self.browser.open(PDU_HOSTNAME + '/index.htm', timeout=3)
        if self.browser.geturl() == PDU_HOSTNAME + '/index.htm':
            self.logger('Successfully logged into PDU.')
            return True
        return False

    def __logout(self):
        self.browser.open(PDU_HOSTNAME + '/logout')
        self.browser.close()
        self.browser = None
        self.logger('Successfully logged out.')

    def __outlet(self, acc_command):
        # Error check that the command given is formatted correctly.
        if len(acc_command) != 3:
            self.logger('Invalid call to OUTLET.')
            return None
        outlet_num = None
        on_off = None
        try:
            outlet_num = int(acc_command[1])
            on_off = int(acc_command[2])
            if (outlet_num < 1) or (outlet_num > 8) or \
                    (on_off < 0) or (on_off > 1):
                self.logger('Invalid call to OUTLET.')
                return None
        except ValueError:
            self.logger('Invalid call to OUTLET.')
            return None

        # Given that the parameters are all correct, we return the
        # link string to be processed later.
        command = PDU_HOSTNAME + '/outlet?' + str(outlet_num) + '=' + \
                  ON_OFF_MAP[on_off]
        return command

    function_map = {'OUTLET': __outlet}

    def get_command_list(self):
        return self.commands

    def execute(self, acc_command):
        is_logged_in = self.__login()
        if not is_logged_in:
            self.logger('Unable to login to PDU.')
            return None

        command_string = self.function_map[acc_command[0]](self, acc_command)
        if command_string is not None:
            self.browser.open(command_string)
            self.logger('The following link was followed for the PDU: ' +
                        command_string)
        self.__logout()
