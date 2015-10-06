"""
    STARBURST ACC/FEANTA Server Runner
    Author: Lokbondo Kung
    Email: lkkung@caltech.edu
"""

import feanta_server
import pdu_worker
import brick_worker
import bb_worker
import cryostat_worker


def instantiate(pid_file, log_file):
    # Instantiate workers.
    pdu = pdu_worker.PDUWorker()
    brick = brick_worker.BrickWorker()
    bb = bb_worker.BBWorker()
    cryo = cryostat_worker.CryoWorker()

    # Instantiate server.
    server = feanta_server.ServerDaemon(pid_file)

    # Setup log file.
    server.set_log_file(log_file)

    # Link workers.
    server.link_worker(pdu)
    server.link_worker(brick)
    server.link_worker(bb)
    server.link_worker(cryo)

    return server


def start(server):
    # Start server.
    server.start()


def stop(pid_file):
    # Instantiate server.
    server = feanta_server.ServerDaemon(pid_file)
    server.stop()
