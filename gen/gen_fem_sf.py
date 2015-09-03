"""
    STARBURST Front End Item Struct Decomposition
    (Based on gen_schedule_sf.py)
    Author: Lokbondo Kung
    Email: lkkung@caltech.edu
"""

import numpy as np
import struct
import shutil

# NUMBER OF ELEMENTS IN CLUSTERS:
NELEMENTS = ['FEMA', 'FEMB']

NELEMENTS_ANTENNA = 4

NELEMENTS_ANTENNA_POWERSTRIP = 10

NELEMENTS_ANTENNA_THERMAL = 9

NELEMENTS_ANTENNA_RECEIVER = 7
NELEMENTS_ANTENNA_RECEIVER_LNA = 3

NELEMENTS_ANTENNA_SERVO = 3
NELEMENTS_ANTENNA_SERVO_AXIS = 20

# POWERSTRIP DEFINITIONS
POWERSTRIP_DEF = ['RFSwitchStatus',
                  'OpticalTxRabbitStatus',
                  'DeltaTauBrickStatus',
                  'ComputerStatus',
                  '12VLNABiasStatus',
                  '5VLNABiasBBStatus',
                  '2ndAmpsStatus',
                  'NoiseDiodeStatus']

# THERMAL DEFINITIONS
THERMAL_DEF = ['70KStageTemp',
               'HiFreq15KPlateTemp',
               'HiFreqLNATemp',
               'HiFreqFeedhornTemp',
               '15KStageTemp',
               'LowFreqLNATemp',
               '70KRadiationShieldTemp',
               'LowFreqFeedhornTemp']

# Version Number for FEM stateframe
VERSION = 1               # Version Date: 9/1/15
VERSION_DATE = '9.1.15'   # Most recent update (used to write backup file)

def gen_fem_sf(sf_dict, mk_xml=False):
    # Set up file name, format string, and buffer.
    xmlFile = r'tmp/fem_stateframe.xml'
    fmt = '<'
    buf = ''
    xml = None

    # Append XML for antenna clusters. (Note there are two antennas.)
    if mk_xml:
        xml = open(xmlFile, "w")
        xml.write('<Cluster>\n')
        xml.write('<Name>FEM</Name>\n')
        xml.write('<NumElts>' + str(len(NELEMENTS))
                  + '</NumElts>\n')

    for antenna in NELEMENTS:
        item = sf_dict.get(antenna, {})
        append_fmt, append_buf = __antenna(item, antenna, xml, mk_xml)
        fmt += append_fmt
        buf += append_buf

    # Append for end of data cluster
    if mk_xml:
        xml.write('</Cluster>\n')
        xml.close()

        # Make backup copy of XML file
        backup_file = ('starburst/fem_stateframe_v' +
                       str(VERSION) + '_' + VERSION_DATE + '.xml')
        shutil.copyfile(xmlFile, backup_file)

        # Print size of buf
        print 'fem size =', len(buf)
        print 'Modify acc.ini to reflect this if this is a change in size'

    return fmt, buf, xmlFile

def __powerstrip(dict, xml, mk_xml):
    fmt = ""
    buf = ""

    # ----------------------------------------------------------------------
    # Defaults - PowerStrip:
    # ----------------------------------------------------------------------
    default_statuses = np.zeros(8)
    default_volt = np.zeros(2)
    default_current = np.zeros(2)

    # ----------------------------------------------------------------------
    # XML Cluster setup.
    # ----------------------------------------------------------------------
    if mk_xml:
        xml.write('<Cluster>\n')
        xml.write('<Name>PowerStrip</Name>\n')
        xml.write('<NumElts>' + str(NELEMENTS_ANTENNA_POWERSTRIP)
                  + '</NumElts>\n')

    # ----------------------------------------------------------------------
    # ELEMENT 1-8> Status of each device: 0 = off, 1 = on (unsigned int)
    # ----------------------------------------------------------------------
    # Devices are as follows:
    #   0: RF Switch
    #   1: Optical Tx/Rabbit
    #   2: Delta Tau Brick
    #   3: Computer
    #   4: 12V LNA Bias
    #   5: 5V LNA Bias/Beaglebone
    #   6: 2nd Amps (5V)
    #   7: Noise Diode
    # ----------------------------------------------------------------------

    # Pack each status as unsigned int.
    item = dict.get('STATUS', default_statuses)
    for i in range(0, 8):
        fmt += 'I'
        buf += struct.pack('I', item[i])

        # Append to XML file
        if mk_xml:
            xml.write('<U32>\n')
            xml.write('<Name>' + POWERSTRIP_DEF[i] + '</Name>\n')
            xml.write('<Val></Val>\n')
            xml.write('</U32>\n')

    # ----------------------------------------------------------------------
    # ELEMENT 9> Volts (2x1 double)
    # ----------------------------------------------------------------------

    # Pack 2x1 array of doubles.
    fmt += 'I'
    buf += struct.pack('I', 2)
    item = dict.get('VOLTS', default_volt)
    fmt += '2d'
    for i in item:
        buf += struct.pack('d', i)
    if mk_xml:
        xml.write('<Array>\n')
        xml.write('<Name>Volts</Name>\n')
        xml.write('<Dimsize>2</Dimsize>\n')
        xml.write('<DBL>\n<Name></Name>\n<Val></Val>\n</DBL>\n')
        xml.write('</Array>\n')

    # ----------------------------------------------------------------------
    # ELEMENT 10> Current (2x1 double)
    # ----------------------------------------------------------------------

    # Pack 2x1 array of doubles.
    fmt += 'I'
    buf += struct.pack('I', 2)
    item = dict.get('CURRENT', default_current)
    fmt += '2d'
    for i in item:
        buf += struct.pack('d', i)
    if mk_xml:
        xml.write('<Array>\n')
        xml.write('<Name>Current</Name>\n')
        xml.write('<Dimsize>2</Dimsize>\n')
        xml.write('<DBL>\n<Name></Name>\n<Val></Val>\n</DBL>\n')
        xml.write('</Array>\n')

    # ----------------------------------------------------------------------
    # XML Cluster closure.
    # ----------------------------------------------------------------------
    if mk_xml:
        xml.write('</Cluster>\n')
    return fmt, buf

def __thermal(dict, xml, mk_xml):
    fmt = ""
    buf = ""

    # ----------------------------------------------------------------------
    # Defaults - Thermal:
    # ----------------------------------------------------------------------
    default_cryostat_temp = np.zeros(8)
    default_focusbox_temp = 0

    # ----------------------------------------------------------------------
    # XML Cluster setup.
    # ----------------------------------------------------------------------
    if mk_xml:
        xml.write('<Cluster>\n')
        xml.write('<Name>Thermal</Name>\n')
        xml.write('<NumElts>' + str(NELEMENTS_ANTENNA_THERMAL)
                  + '</NumElts>\n')

    # ----------------------------------------------------------------------
    # ELEMENT 1-8> Temperature of cryostat element (double)
    # ----------------------------------------------------------------------
    # Devices are as follows:
    #   0: 70K Stage
    #   1: Hi Freq 15K Plate
    #   2: Hi Freq LNA
    #   3: Hi Freq Feedhorn
    #   4: 15K Stage
    #   5: Low Freq LNA
    #   6: 70K Radiation Shield
    #   7: Low Freq Feedhorn
    # ----------------------------------------------------------------------

    # Pack each status as unsigned int.
    item = dict.get('CRYOSTAT', default_cryostat_temp)
    for i in range(0, 8):
        fmt += 'd'
        buf += struct.pack('d', item[i])

        # Append to XML file
        if mk_xml:
            xml.write('<DBL>\n')
            xml.write('<Name>' + THERMAL_DEF[i] + '</Name>\n')
            xml.write('<Val></Val>\n')
            xml.write('</DBL>\n')

    # ----------------------------------------------------------------------
    # ELEMENT 9> Focus Box Temperature (double)
    # ----------------------------------------------------------------------

    # Pack a double for the temperature.
    item = dict.get('FOCUSBOX', default_focusbox_temp)
    fmt += 'd'
    buf += struct.pack('d', item)
    if mk_xml:
        xml.write('<DBL>\n')
        xml.write('<Name>FocusBoxTemp</Name>\n')
        xml.write('<Val></Val>\n')
        xml.write('</DBL>\n')

    # ----------------------------------------------------------------------
    # XML Cluster closure.
    # ----------------------------------------------------------------------
    if mk_xml:
        xml.write('</Cluster>\n')
    return fmt, buf

def __receiver_lna(dict, lna, xml, mk_xml):
    fmt = ""
    buf = ""

    # ----------------------------------------------------------------------
    # Defaults - Receiver_LNA:
    # ----------------------------------------------------------------------
    default_lna_drainvoltage = 0
    default_lna_draincurrent = 0
    default_lna_gatevoltage = 0

    # ----------------------------------------------------------------------
    # XML Cluster setup.
    # ----------------------------------------------------------------------
    if mk_xml:
        xml.write('<Cluster>\n')
        xml.write('<Name>LNA' + str(lna) + '</Name>\n')
        xml.write('<NumElts>' + str(NELEMENTS_ANTENNA_RECEIVER_LNA)
                  + '</NumElts>\n')

    # ----------------------------------------------------------------------
    # ELEMENT 1> Drain voltage (double)
    # ----------------------------------------------------------------------

    # Pack a double for the temperature.
    item = dict.get('DRAINVOLTAGE', default_lna_drainvoltage)
    fmt += 'd'
    buf += struct.pack('d', item)
    if mk_xml:
        xml.write('<DBL>\n')
        xml.write('<Name>DrainVoltage</Name>\n')
        xml.write('<Val></Val>\n')
        xml.write('</DBL>\n')

    # ----------------------------------------------------------------------
    # ELEMENT 2> Drain current (double)
    # ----------------------------------------------------------------------

    # Pack a double for the temperature.
    item = dict.get('DRAINCURRENT', default_lna_draincurrent)
    fmt += 'd'
    buf += struct.pack('d', item)
    if mk_xml:
        xml.write('<DBL>\n')
        xml.write('<Name>DrainCurrent</Name>\n')
        xml.write('<Val></Val>\n')
        xml.write('</DBL>\n')

    # ----------------------------------------------------------------------
    # ELEMENT 3> Gate voltage (double)
    # ----------------------------------------------------------------------

    # Pack a double for the temperature.
    item = dict.get('GATEVOLTAGE', default_lna_gatevoltage)
    fmt += 'd'
    buf += struct.pack('d', item)
    if mk_xml:
        xml.write('<DBL>\n')
        xml.write('<Name>GateVoltage</Name>\n')
        xml.write('<Val></Val>\n')
        xml.write('</DBL>\n')

    # ----------------------------------------------------------------------
    # XML Cluster closure.
    # ----------------------------------------------------------------------
    if mk_xml:
        xml.write('</Cluster>\n')
    return fmt, buf

def __receiver(dict, xml, mk_xml):
    fmt = ""
    buf = ""

    # ----------------------------------------------------------------------
    # Defaults - Receiver:
    # ----------------------------------------------------------------------
    default_status = 0

    # ----------------------------------------------------------------------
    # XML Cluster setup.
    # ----------------------------------------------------------------------
    if mk_xml:
        xml.write('<Cluster>\n')
        xml.write('<Name>Receiver</Name>\n')
        xml.write('<NumElts>' + str(NELEMENTS_ANTENNA_RECEIVER)
                  + '</NumElts>\n')

    # ----------------------------------------------------------------------
    # ELEMENT 1> Lo Freq Status: 0 = disable, 1 = enable (unsigned int)
    # ----------------------------------------------------------------------

    # Pack an unsigned integer for the status.
    item = dict.get('LOFREQSTATUS', default_status)
    fmt += 'I'
    buf += struct.pack('I', item)
    if mk_xml:
        xml.write('<U32>\n')
        xml.write('<Name>LoFreqEnabled</Name>\n')
        xml.write('<Val></Val>\n')
        xml.write('</U32>\n')

    # ----------------------------------------------------------------------
    # ELEMENT 2> Hi Freq Status: 0 = disable, 1 = enable (unsigned int)
    # ----------------------------------------------------------------------

    # Pack an unsigned integer for the status.
    item = dict.get('HIFREQSTATUS', default_status)
    fmt += 'I'
    buf += struct.pack('I', item)
    if mk_xml:
        xml.write('<U32>\n')
        xml.write('<Name>HiFreqEnabled</Name>\n')
        xml.write('<Val></Val>\n')
        xml.write('</U32>\n')

    # ----------------------------------------------------------------------
    # ELEMENT 3> Noise Diode Status: 0 = disable, 1 = enable (unsigned int)
    # ----------------------------------------------------------------------

    # Pack an unsigned integer for the status.
    item = dict.get('NOISESTATUS', default_status)
    fmt += 'I'
    buf += struct.pack('I', item)
    if mk_xml:
        xml.write('<U32>\n')
        xml.write('<Name>NoiseDiodeEnabled</Name>\n')
        xml.write('<Val></Val>\n')
        xml.write('</U32>\n')

    # ----------------------------------------------------------------------
    # ELEMENT 4-7> LNA Clusters (cluster of 3 doubles)
    # ----------------------------------------------------------------------

    # Call __receiver_lna on each LNA to generate clusters.
    for i in range(0, 4):
        item = dict.get('LNA' + str(i), {})
        append_fmt, append_buf = __receiver_lna(item, i, xml, mk_xml)
        fmt += append_fmt
        buf += append_buf

    # ----------------------------------------------------------------------
    # XML Cluster closure.
    # ----------------------------------------------------------------------
    if mk_xml:
        xml.write('</Cluster>\n')
    return fmt, buf

def __servo_axis(dict, axis, xml, mk_xml):
    fmt = ""
    buf = ""

    # ----------------------------------------------------------------------
    # Defaults - Servo_Axis:
    # ----------------------------------------------------------------------
    default_stopped = 0
    default_positivelimit = 0
    default_negativelimit = 0
    default_inposition = 0
    default_warningfollerror = 0
    default_fatalfollerror = 0
    default_i2tfault = 0
    default_phasingerrorfault = 0
    default_adcstatus = 0
    default_commandedposition = 0
    default_actualposition = 0
    default_targetposition = 0
    default_quadcurrent = 0
    default_directcurrent = 0
    default_quadintegrator = 0
    default_directintegrator = 0
    default_scalefactor = 0
    default_motorposition = 0
    default_motorvelocity = 0
    default_motorerror = 0

    # ----------------------------------------------------------------------
    # XML Cluster setup.
    # ----------------------------------------------------------------------
    if mk_xml:
        xml.write('<Cluster>\n')
        xml.write('<Name>Axis' + str(axis) + '</Name>\n')
        xml.write('<NumElts>' + str(NELEMENTS_ANTENNA_SERVO_AXIS)
                  + '</NumElts>\n')

    # ----------------------------------------------------------------------
    # ELEMENT 1> Stopped: 0 = false, 1 = true (unsigned int)
    # ----------------------------------------------------------------------

    # Pack an unsigned integer for the status.
    item = dict.get('STOPPED', default_stopped)
    fmt += 'I'
    buf += struct.pack('I', item)
    if mk_xml:
        xml.write('<U32>\n')
        xml.write('<Name>Stopped</Name>\n')
        xml.write('<Val></Val>\n')
        xml.write('</U32>\n')

    # ----------------------------------------------------------------------
    # ELEMENT 2> Positive Limit: 0 = false, 1 = true (unsigned int)
    # ----------------------------------------------------------------------

    # Pack an unsigned integer for the status.
    item = dict.get('POSLIMIT', default_positivelimit)
    fmt += 'I'
    buf += struct.pack('I', item)
    if mk_xml:
        xml.write('<U32>\n')
        xml.write('<Name>PositiveLimit</Name>\n')
        xml.write('<Val></Val>\n')
        xml.write('</U32>\n')

    # ----------------------------------------------------------------------
    # ELEMENT 3> Negative Limit: 0 = false, 1 = true (unsigned int)
    # ----------------------------------------------------------------------

    # Pack an unsigned integer for the status.
    item = dict.get('NEGLIMIT', default_negativelimit)
    fmt += 'I'
    buf += struct.pack('I', item)
    if mk_xml:
        xml.write('<U32>\n')
        xml.write('<Name>NegativeLimit</Name>\n')
        xml.write('<Val></Val>\n')
        xml.write('</U32>\n')

    # ----------------------------------------------------------------------
    # ELEMENT 4> In Position: 0 = false, 1 = true (unsigned int)
    # ----------------------------------------------------------------------

    # Pack an unsigned integer for the status.
    item = dict.get('INPOS', default_inposition)
    fmt += 'I'
    buf += struct.pack('I', item)
    if mk_xml:
        xml.write('<U32>\n')
        xml.write('<Name>InPosition</Name>\n')
        xml.write('<Val></Val>\n')
        xml.write('</U32>\n')

    # ----------------------------------------------------------------------
    # ELEMENT 5> Warning Foll Error: 0 = false, 1 = true (unsigned int)
    # ----------------------------------------------------------------------

    # Pack an unsigned integer for the status.
    item = dict.get('WARNFOLLERR', default_warningfollerror)
    fmt += 'I'
    buf += struct.pack('I', item)
    if mk_xml:
        xml.write('<U32>\n')
        xml.write('<Name>WarningFollError</Name>\n')
        xml.write('<Val></Val>\n')
        xml.write('</U32>\n')

    # ----------------------------------------------------------------------
    # ELEMENT 6> Fatal Foll Error: 0 = false, 1 = true (unsigned int)
    # ----------------------------------------------------------------------

    # Pack an unsigned integer for the status.
    item = dict.get('FATALFOLLERR', default_fatalfollerror)
    fmt += 'I'
    buf += struct.pack('I', item)
    if mk_xml:
        xml.write('<U32>\n')
        xml.write('<Name>FatalFollError</Name>\n')
        xml.write('<Val></Val>\n')
        xml.write('</U32>\n')

    # ----------------------------------------------------------------------
    # ELEMENT 7> I2T Fault: 0 = false, 1 = true (unsigned int)
    # ----------------------------------------------------------------------

    # Pack an unsigned integer for the status.
    item = dict.get('I2TFAULT', default_i2tfault)
    fmt += 'I'
    buf += struct.pack('I', item)
    if mk_xml:
        xml.write('<U32>\n')
        xml.write('<Name>I2TFault</Name>\n')
        xml.write('<Val></Val>\n')
        xml.write('</U32>\n')

    # ----------------------------------------------------------------------
    # ELEMENT 8> Phasing Error Fault: 0 = false, 1 = true (unsigned int)
    # ----------------------------------------------------------------------

    # Pack an unsigned integer for the status.
    item = dict.get('PHASEERRFAULT', default_phasingerrorfault)
    fmt += 'I'
    buf += struct.pack('I', item)
    if mk_xml:
        xml.write('<U32>\n')
        xml.write('<Name>PhasingErrorFault</Name>\n')
        xml.write('<Val></Val>\n')
        xml.write('</U32>\n')

    # ----------------------------------------------------------------------
    # ELEMENT 9> ADC Status: 0 = false, 1 = true (unsigned int)
    # ----------------------------------------------------------------------

    # Pack an unsigned integer for the status.
    item = dict.get('ADCSTATUS', default_adcstatus)
    fmt += 'I'
    buf += struct.pack('I', item)
    if mk_xml:
        xml.write('<U32>\n')
        xml.write('<Name>AdcStatus</Name>\n')
        xml.write('<Val></Val>\n')
        xml.write('</U32>\n')

    # ----------------------------------------------------------------------
    # ELEMENT 10> Commanded Position (double)
    # ----------------------------------------------------------------------

    # Pack an unsigned integer for the status.
    item = dict.get('ACTUALMPOS', default_actualposition)
    fmt += 'd'
    buf += struct.pack('d', item)
    if mk_xml:
        xml.write('<DBL>\n')
        xml.write('<Name>ActualPosition</Name>\n')
        xml.write('<Val></Val>\n')
        xml.write('</DBL>\n')

    # ----------------------------------------------------------------------
    # ELEMENT 11> Actual Position (double)
    # ----------------------------------------------------------------------

    # Pack an unsigned integer for the status.
    item = dict.get('COMMPOS', default_commandedposition)
    fmt += 'd'
    buf += struct.pack('d', item)
    if mk_xml:
        xml.write('<DBL>\n')
        xml.write('<Name>CommandedPosition</Name>\n')
        xml.write('<Val></Val>\n')
        xml.write('</DBL>\n')

    # ----------------------------------------------------------------------
    # ELEMENT 12> Target Position (double)
    # ----------------------------------------------------------------------

    # Pack an unsigned integer for the status.
    item = dict.get('TARGETPOS', default_targetposition)
    fmt += 'd'
    buf += struct.pack('d', item)
    if mk_xml:
        xml.write('<DBL>\n')
        xml.write('<Name>TargetPosition</Name>\n')
        xml.write('<Val></Val>\n')
        xml.write('</DBL>\n')

    # ----------------------------------------------------------------------
    # ELEMENT 13> Quad Current (double)
    # ----------------------------------------------------------------------

    # Pack an unsigned integer for the status.
    item = dict.get('QUADCURRENT', default_quadcurrent)
    fmt += 'd'
    buf += struct.pack('d', item)
    if mk_xml:
        xml.write('<DBL>\n')
        xml.write('<Name>QuadCurrent</Name>\n')
        xml.write('<Val></Val>\n')
        xml.write('</DBL>\n')

    # ----------------------------------------------------------------------
    # ELEMENT 14> Direct Current (double)
    # ----------------------------------------------------------------------

    # Pack an unsigned integer for the status.
    item = dict.get('DIRECTCURRENT', default_directcurrent)
    fmt += 'd'
    buf += struct.pack('d', item)
    if mk_xml:
        xml.write('<DBL>\n')
        xml.write('<Name>DirectCurrent</Name>\n')
        xml.write('<Val></Val>\n')
        xml.write('</DBL>\n')

    # ----------------------------------------------------------------------
    # ELEMENT 15> Quad Integrator (double)
    # ----------------------------------------------------------------------

    # Pack an unsigned integer for the status.
    item = dict.get('QUADINTEG', default_quadintegrator)
    fmt += 'd'
    buf += struct.pack('d', item)
    if mk_xml:
        xml.write('<DBL>\n')
        xml.write('<Name>QuadIntegrator</Name>\n')
        xml.write('<Val></Val>\n')
        xml.write('</DBL>\n')

    # ----------------------------------------------------------------------
    # ELEMENT 16> Direct Integrator (double)
    # ----------------------------------------------------------------------

    # Pack an unsigned integer for the status.
    item = dict.get('DIRECTINTEG', default_directintegrator)
    fmt += 'd'
    buf += struct.pack('d', item)
    if mk_xml:
        xml.write('<DBL>\n')
        xml.write('<Name>DirectIntegrator</Name>\n')
        xml.write('<Val></Val>\n')
        xml.write('</DBL>\n')

    # ----------------------------------------------------------------------
    # ELEMENT 17> Scale Factor (double)
    # ----------------------------------------------------------------------

    # Pack an unsigned integer for the status.
    item = dict.get('SCALEFAC', default_scalefactor)
    fmt += 'd'
    buf += struct.pack('d', item)
    if mk_xml:
        xml.write('<DBL>\n')
        xml.write('<Name>ScaleFactor</Name>\n')
        xml.write('<Val></Val>\n')
        xml.write('</DBL>\n')

    # ----------------------------------------------------------------------
    # ELEMENT 18> Motor Position (double)
    # ----------------------------------------------------------------------

    # Pack an unsigned integer for the status.
    item = dict.get('MOTORPOS', default_motorposition)
    fmt += 'd'
    buf += struct.pack('d', item)
    if mk_xml:
        xml.write('<DBL>\n')
        xml.write('<Name>MotorPosition</Name>\n')
        xml.write('<Val></Val>\n')
        xml.write('</DBL>\n')

    # ----------------------------------------------------------------------
    # ELEMENT 19> Motor Velocity (double)
    # ----------------------------------------------------------------------

    # Pack an unsigned integer for the status.
    item = dict.get('MOTORVEL', default_motorvelocity)
    fmt += 'd'
    buf += struct.pack('d', item)
    if mk_xml:
        xml.write('<DBL>\n')
        xml.write('<Name>MotorVelocity</Name>\n')
        xml.write('<Val></Val>\n')
        xml.write('</DBL>\n')

    # ----------------------------------------------------------------------
    # ELEMENT 20> Motor Error (double)
    # ----------------------------------------------------------------------

    # Pack an unsigned integer for the status.
    item = dict.get('MOTORERR', default_motorerror)
    fmt += 'd'
    buf += struct.pack('d', item)
    if mk_xml:
        xml.write('<DBL>\n')
        xml.write('<Name>MotorError</Name>\n')
        xml.write('<Val></Val>\n')
        xml.write('</DBL>\n')

    # ----------------------------------------------------------------------
    # XML Cluster closure.
    # ----------------------------------------------------------------------
    if mk_xml:
        xml.write('</Cluster>\n')
    return fmt, buf

def __servo(dict, xml, mk_xml):
    fmt = ""
    buf = ""

    # ----------------------------------------------------------------------
    # XML Cluster setup.
    # ----------------------------------------------------------------------
    if mk_xml:
        xml.write('<Cluster>\n')
        xml.write('<Name>ApparatusServo</Name>\n')
        xml.write('<NumElts>' + str(NELEMENTS_ANTENNA_SERVO)
                  + '</NumElts>\n')

    # ----------------------------------------------------------------------
    # ELEMENT 1-3> Axis Clusters (cluster of 9 booleans and 11 doubles)
    # ----------------------------------------------------------------------

    # Call __receiver_lna on each LNA to generate clusters.
    for i in range(0, 3):
        item = dict.get('AXIS' + str(i), {})
        append_fmt, append_buf = __servo_axis(item, i, xml, mk_xml)
        fmt += append_fmt
        buf += append_buf

    # ----------------------------------------------------------------------
    # XML Cluster closure.
    # ----------------------------------------------------------------------
    if mk_xml:
        xml.write('</Cluster>\n')
    return fmt, buf

def __antenna(sf_dict, antenna, xml, mk_xml):
    fmt = ""
    buf = ""

    # ----------------------------------------------------------------------
    # XML Cluster setup.
    # ----------------------------------------------------------------------
    if mk_xml:
        xml.write('<Cluster>\n')
        xml.write('<Name>' + antenna + '</Name>\n')
        xml.write('<NumElts>' + str(NELEMENTS_ANTENNA)
                  + '</NumElts>\n')

    # ----------------------------------------------------------------------
    # Dump PowerStrip
    # ----------------------------------------------------------------------
    item = sf_dict.get(antenna, {}).get('POWERSTRIP', {})
    append_fmt, append_buf = __powerstrip(item, xml, mk_xml)
    fmt += append_fmt
    buf += append_buf

    # ----------------------------------------------------------------------
    # Dump Thermal
    # ----------------------------------------------------------------------
    item = sf_dict.get(antenna, {}).get('THERMAL', {})
    append_fmt, append_buf = __thermal(item, xml, mk_xml)
    fmt += append_fmt
    buf += append_buf

    # ----------------------------------------------------------------------
    # Dump Receiver
    # ----------------------------------------------------------------------
    item = sf_dict.get(antenna, {}).get('RECEIVER', {})
    append_fmt, append_buf = __receiver(item, xml, mk_xml)
    fmt += append_fmt
    buf += append_buf

    # ----------------------------------------------------------------------
    # Dump Servo
    # ----------------------------------------------------------------------
    item = sf_dict.get(antenna, {}).get('SERVO', {})
    append_fmt, append_buf = __servo(item, xml, mk_xml)
    fmt += append_fmt
    buf += append_buf

    # ----------------------------------------------------------------------
    # XML Cluster closure.
    # ----------------------------------------------------------------------
    if mk_xml:
        xml.write('</Cluster>\n')

    return fmt, buf
