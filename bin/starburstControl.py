#!/usr/bin/python2.6

"""
    STARBURST ACC/FEANTA Control System
    Author: Lokbondo Kung
    Email: lkkung@caltech.edu
"""

import sys
import getopt
import server_runner

def main(argv):
    pid_file = '/tmp/server.pid'
    log_file = '/tmp/log.txt'

    # Process command arguments and execute.
    try:
        opts, args = getopt.getopt(argv, 'hp:l:',
                                   ['logfile=',
                                    'pidfile=',
                                    'start',
                                    'stop'])
    except getopt.GetoptError:
        print 'starburstControl -p <pidfile> -l <logfile> <command>'
        sys.exit(2)
    if len(args) != 1:
        print 'starburstControl -p <pidfile> -l <logfile> <command>'
        sys.exit(2)

    for opt, arg in opts:
        if opt == '-h':
            print 'starburstControl -p <pidfile> -l <logfile> <command>'
            sys.exit()
        elif opt in ['-l', '--logfile']:
            log_file = arg
        elif opt in ['-p', '--pipdfile']:
            pid_file = arg

    if args[0] == 'start':
        server_runner.start(pid_file, log_file)
    else:
        server_runner.stop(pid_file)

if __name__ == '__main__':
    main(sys.argv[1:])
