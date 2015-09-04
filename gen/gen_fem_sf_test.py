"""
    STARBURST Front End Item Struct Decomposition Test Suite
    Author: Lokbondo Kung
    Email: lkkung@caltech.edu
"""

import unittest
import struct
import numpy as np
import xml.etree.ElementTree as etree
import copy
import gen_fem_sf as go
import os
import sys

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

# RECEIVER DEFINITIONS
RECEIVER_REGISTERS = {'LOFREQSTATUS': 'LoFreqEnabled',
                     'HIFREQSTATUS': 'HiFreqEnabled',
                     'NOISESTATUS': 'NoiseDiodeEnabled'}
LNA_REGISTERS = {'DRAINVOLTAGE': 'DrainVoltage',
                 'DRAINCURRENT': 'DrainCurrent',
                 'GATEAVOLTAGE': 'GateAVoltage',
                 'GATEBVOLTAGE': 'GateBVoltage',
                 'GATEACURRENT': 'GateACurrent',
                 'GATEBCURRENT': 'GateBCurrent'}

# AXIS DEFINITIONS
AXIS_DEF = {1: 'ZAxis',
            3: 'RotationAxis',
            4: 'XAxis'}
SERVO_REGISTERS = {'STOPPED': 'Stopped',
                   'POSLIMIT': 'PositiveLimit',
                   'NEGLIMIT': 'NegativeLimit',
                   'INPOS': 'InPosition',
                   'WARNFOLLERR': 'WarningFollError',
                   'FATALFOLLERR': 'FatalFollError',
                   'I2TFAULT': 'I2TFault',
                   'PHASEERRFAULT': 'PhasingErrorFault',
                   'ADCSTATUS': 'AdcStatus',
                   'ACTUALMPOS': 'ActualPosition',
                   'COMMPOS': 'CommandedPosition',
                   'TARGETPOS': 'TargetPosition',
                   'QUADCURRENT': 'QuadCurrent',
                   'DIRECTCURRENT': 'DirectCurrent',
                   'QUADINTEG': 'QuadIntegrator',
                   'DIRECTINTEG': 'DirectIntegrator'}


"""
TestGenerateFrontEndBinary Test Group Description:
    This group of tests makes sure that gen_fem_sf.py correctly packs its data
    into structs and returns a binary string of the information. The tests
    also verify that the binary string returned can then be properly read
    back into the correct values.

    Test Count: 3
"""
class TestGenerateFrontEndBinary(unittest.TestCase):
    # Redefine methods already used in Starburst pipeline so that the
    # tests can be ran without unnecessary dependencies.

    # handle_cluster copied from read_xml2.py
    def handle_cluster(self, child):
        '''This element of the XML tree is the head of a Cluster.  Step through
        each element of the branch and return the keys, the empty dictionary,
        and the fmt string.  This routine is reentrant'''
        # Clusters have a name, a NumElts, and one or more objects
        c = list(child)
        fmt = ''
        if c[0].tag == "Name":
            keys = [c[0].text]
            mydict = {}    # Start an empty dictionary
            c.pop(0)
        else:
            print 'Illegal format for item',child
            return None, None
        if c[0].tag == "NumElts":
            n = int(c[0].text)
            c.pop(0)
        else:
            print 'Illegal format for item',child
            return None, None
        # Loop through all items in the cluster
        for i in range(n):
            datatype = c[0].tag
            if datatype == "Array":
                ch = c[0]
                key, arr, dims, fmt1 = self.handle_array(ch)
                keys += key
                fmt += fmt1
                mydict.update({key[0]:arr})
                c.pop(0)
            elif datatype == "Cluster":
                ch = c[0]
                key, newdict, fmt1 = self.handle_cluster(ch)
                if not key is None:
                    keys += key
                fmt += fmt1
                mydict.update({key[0]:newdict})
                c.pop(0)
            else:
                ch = c[0]
                key, fmt1 = self.handle_item(ch)
                keys += key
                fmt += fmt1
                mydict.update({key[0]:0})
                c.pop(0)
        return keys, mydict, fmt

    # handle_array copied from read_xml2.py
    def handle_array(self, child):
        '''This element of the XML tree is an Array.  Step through the items
           of the array (which may contain clusters, other arrays, etc.) and return the keys, array, dimensions of the array, and fmt string.
           This routine is reentrant.
        '''
        # Arrays have a name and one or more dimension statements, then one or more objects
        c = list(child)
        if c[0].tag == "Name":
            keys = [c[0].text]
            c.pop(0)
        else:
            print 'Illegal format for item',child
            return None, None, None, None
        # Handle up to four levels of dimension
        d1, d2, d3, d4 = 1, 1, 1, 1
        if c[0].tag == "Dimsize":
            d1 = int(c[0].text)
            fmt = 'I'
            c.pop(0)
        else:
            print 'Illegal format for item',child
            return None, None
        if c[0].tag == "Dimsize":
            d2 = int(c[0].text)
            fmt += 'I'
            c.pop(0)
        if d2 != 1:
            if c[0].tag == "Dimsize":
                d3 = int(c[0].text)
                fmt += 'I'
                c.pop(0)
            if d3 != 1:
                if c[0].tag == "Dimsize":
                    d4 = int(c[0].text)
                    fmt += 'I'
                    c.pop(0)
        dims = [d1, d2, d3, d4]
        datatype = c[0].tag
        dtype_dict = {'U8':'s','B8':'B','U16':'H','U32':'I','I16':'h',
                      'I32':'i','SGL':'f','DBL':'d'}
        fmt += str(d1*d2*d3*d4)+dtype_dict.get(datatype,'[')
        if datatype == "Cluster":
            ch = list(c[0])
            key, mydict, fmt1 = self.handle_cluster(ch)
            keys += key
            fmt += fmt1+']'
            arr = [mydict]  # Return cluster dictionary as 1-element list place holder
            c.pop(0)
        else:
            arr = dims   # Return list of dims as place holder
        return keys, arr, dims, fmt

    # handle_item copied from read_xml2.py
    def handle_item(self, c):
        '''This element of the XML tree is a simple, single item.
           Simply return its key and fmt string.
        '''
        dtype_dict = {'U8':'s','B8':'B','U16':'H','U32':'I','I16':'h',
                      'I32':'i','SGL':'f','DBL':'d'}
        fmt = dtype_dict.get(c.tag,'*')
        if c[0].tag == "Name":
            key = [c[0].text]
        else:
            print 'Illegal format for item',c
            return None, None
        return key, fmt

    # xml_read adapted from read_xml2.py
    def xml_read(self, fileName):
        if fileName is not None:
            f = open(fileName)
            tree = etree.parse(f)
            f.close()

            root = tree.getroot()
            try:
                # Stateframe version number is supposed to be included
                # in the second element of the stateframe cluster
                # (after the timestamp)
                version = float(root[3][1].text)
            except:
                # It seems not to be there, so set version to 3.0
                version = 3.0

            keys, mydict, fmt = self.handle_cluster(root)
            return keys, mydict, fmt, version
        return None

    # handle_key copied from read_xml2.py
    def handle_key(self, keys, dictlist, fmt, off):
        key = keys.pop(0)
        if key is None:
            #Skip any "None" key
            return keys, dictlist, fmt, off
        mydict = dictlist.pop()      # Get the inner-most dict for processing
        try:
            val = mydict[key]
        except:
            # We must be done with this dictionary, so go back and try again
            # Note that dictlist is one item shorter than before
            keys = [key] + keys  # Put key back in list
            return keys, dictlist, fmt, off
        valtype = type(val)
        if valtype == int or valtype == float:
            # This is just a single value
            f = fmt[0]
            fmt = fmt[len(f):]
            try:
                mydict[key] = [f, off] # Assign fmt, offset pair as value to
                                       # key. Increment off by number of bytes
                                       # taken by f
                off += struct.calcsize(f)
            except:
                print key, fmt
            dictlist.append(mydict)   # Put original dictionary back
        elif valtype == list:
            # This is an array of values
            if type(val[0]) == int:
                # This is a simple array of numbers
                dims = val  # List of dimensions from XML file
                arrsiz = 1  # Total array size (product of dimensions)
                ndim = 0    # Number of dimensions
                for dim in dims:
                   arrsiz *= dim
                   if dim != 1:
                       # Count only non-unity dimensions
                       ndim += 1
                dims = dims[:ndim]
                # Read dimensions of array
                while fmt[0] == 'I':
                    f = fmt[0]
                    fmt = fmt[len(f):]
                    # Skip dimension variables
                    # Increment off by number of bytes taken by f
                    off += struct.calcsize(f)
                f = fmt[:len(str(arrsiz))+1]
                fmt = fmt[len(f):]
                if f[-1] == 's':
                    mydict[key] = [f, off] # If f is 'string', do not save dims
                else:
                    mydict[key] = [f, off, dims] # Assign fmt, offset and dims
                                                 # as value to key. Increment
                                                 # off by number of bytes
                                                 # taken by f (to prepare for
                                                 # next iteration)
                off += struct.calcsize(f)
                dictlist.append(mydict)    # Put original dictionary back
            else:
                # This is something more complicated (e.g. an array of dicts)
                if type(val[0]) == dict:
    #                dims = []   # List of dimensions
                    arrsiz = 1  # Total array size (product of dimensions)
                    dictarr = []
                    # Read dimensions of array
                    while fmt[0] == 'I':
                        f = fmt[0]
                        fmt = fmt[len(f):]
                        # Skip dimension variables
                        # Increment off by number of bytes taken by f
                        off += struct.calcsize(f)
    #                    dims.append(vals[0])
    #                    arrsiz *= vals[0]
                    # Extract array size (number just before '[')
                    arrsiz = int(fmt[:fmt.index('[')])

                    newfmt = fmt[fmt.index('[')+1:fmt.index(']')]
                    fmt = fmt[fmt.index(']')+1:]

                    for j in range(arrsiz):
                        newdictarr = [copy.deepcopy(val[0])]
                        tmpfmt = newfmt
                        tmpkeys = copy.deepcopy(keys)
                        while tmpfmt != '':
                            tmpkeys, newdictarr, tmpfmt, off \
                                = self.handle_key(tmpkeys, newdictarr,
                                                  tmpfmt, off)
                        while len(newdictarr) > 1:
                            newdictarr.pop()  # Remove all but the original
                                              # dictionary

                        # Dictionary is all filled in, and only one copy
                        # remains.  Copy it to dictarray being assembled
                        dictarr.append(copy.deepcopy(newdictarr.pop()))
                    keys = tmpkeys
                mydict[key] = dictarr    # Assign array of dicts to mydict key
                dictlist.append(mydict)  # Put original dictionary back
        elif valtype == dict:
            # This is a dictionary.
            dictlist.append(mydict)  # Put original dictionary back
            dictlist.append(val)     # Add new dictionary
        else:
            print 'Unknown value type',valtype
        return keys, dictlist, fmt, off

    # xml_ptrs copied from read_xml2.py
    def xml_ptrs(self, filename=None):
        inkeys, indict, infmt, version = self.xml_read(filename)
        # Pre-processing step
        keys = copy.deepcopy(inkeys)
        mydict = copy.deepcopy(indict)
        fmt = infmt
        keys.pop(0)
        dictlist = [mydict]  # A list of dictionaries.
                             # The one at the end is the one
                             # currently being manipulated
        off = 0
        while fmt != '':
            keys, dictlist, fmt, off = self.handle_key(keys, dictlist,
                                                       fmt, off)
        mydict = dictlist.pop()   # Should be the original, but now
                                  # updated dictionary
        if dictlist != []:
            mydict = dictlist.pop() # Should be the original, but now updated
                                    # dictionary
        return mydict, version

    # extract copied from stateframe.py
    def extract(self, data, k):
        '''Helper function that extracts a value from data, based on stateframe
           info pair k (k[0] is fmt string, k[1] is byte offset into data)
        '''
        if len(k) == 3:
           k[2].reverse()
           val = np.array(struct.unpack_from(k[0],data,k[1]))
           val.shape = k[2]
           k[2].reverse()
        else:
           val = struct.unpack_from(k[0],data,k[1])[0]
        return val

    def setUp(self):
        # Setup the values to be returned.
        self.data = {'FEM': {'POWERSTRIP': {'STATUS':
                                             [11011, 11012, 11013, 11014,
                                              11015, 11016, 11017, 11018],
                                             'VOLTS': [11021, 11022],
                                             'CURRENT': [11031, 11032]},
                              'THERMAL': {'CRYOSTAT':
                                          [12011, 12012, 12013, 12014,
                                           12015, 12016, 12017, 12018],
                                          'FOCUSBOX': 12021},
                              'RECEIVER': {'LOFREQSTATUS': 13011,
                                           'HIFREQSTATUS': 13021,
                                           'NOISESTATUS': 13031,
                                           'LNAS': [{'DRAINVOLTAGE': 13041,
                                                     'DRAINCURRENT': 13042,
                                                     'GATEAVOLTAGE': 13043,
                                                     'GATEACURRENT': 13042,
                                                     'GATEBVOLTAGE': 13042,
                                                     'GATEBCURRENT': 13042},
                                                    {'DRAINVOLTAGE': 13051,
                                                     'DRAINCURRENT': 13052,
                                                     'GATEAVOLTAGE': 13053,
                                                     'GATEACURRENT': 13052,
                                                     'GATEBVOLTAGE': 13052,
                                                     'GATEBCURRENT': 13052},
                                                    {'DRAINVOLTAGE': 13061,
                                                     'DRAINCURRENT': 13062,
                                                     'GATEAVOLTAGE': 13063,
                                                     'GATEACURRENT': 13062,
                                                     'GATEBVOLTAGE': 13062,
                                                     'GATEBCURRENT': 13062},
                                                    {'DRAINVOLTAGE': 13071,
                                                     'DRAINCURRENT': 13072,
                                                     'GATEAVOLTAGE': 13073,
                                                     'GATEACURRENT': 13072,
                                                     'GATEBVOLTAGE': 13072,
                                                     'GATEBCURRENT': 13072}]},
                              'SERVO': {'AXIS1': {'STOPPED': 140011,
                                                  'POSLIMIT': 140021,
                                                  'NEGLIMIT': 14031,
                                                  'INPOS': 140041,
                                                  'WARNFOLLERR': 140051,
                                                  'FATALFOLLERR': 140061,
                                                  'I2TFAULT': 140071,
                                                  'PHASEERRFAULT': 140081,
                                                  'ADCSTATUS': 140091,
                                                  'ACTUALMPOS': 140101,
                                                  'COMMPOS': 140111,
                                                  'TARGETPOS': 140121,
                                                  'QUADCURRENT': 140131,
                                                  'DIRECTCURRENT': 140141,
                                                  'QUADINTEG': 140151,
                                                  'DIRECTINTEG': 140161},
                                        'AXIS3': {'STOPPED': 141011,
                                                  'POSLIMIT': 141021,
                                                  'NEGLIMIT': 14131,
                                                  'INPOS': 141041,
                                                  'WARNFOLLERR': 141051,
                                                  'FATALFOLLERR': 141061,
                                                  'I2TFAULT': 141071,
                                                  'PHASEERRFAULT': 141081,
                                                  'ADCSTATUS': 141091,
                                                  'ACTUALMPOS': 141101,
                                                  'COMMPOS': 141111,
                                                  'TARGETPOS': 141121,
                                                  'QUADCURRENT': 141131,
                                                  'DIRECTCURRENT': 141141,
                                                  'QUADINTEG': 141151,
                                                  'DIRECTINTEG': 141161},
                                        'AXIS4': {'STOPPED': 142011,
                                                  'POSLIMIT': 142021,
                                                  'NEGLIMIT': 14231,
                                                  'INPOS': 142041,
                                                  'WARNFOLLERR': 142051,
                                                  'FATALFOLLERR': 142061,
                                                  'I2TFAULT': 142071,
                                                  'PHASEERRFAULT': 142081,
                                                  'ADCSTATUS': 142091,
                                                  'ACTUALMPOS': 142101,
                                                  'COMMPOS': 142111,
                                                  'TARGETPOS': 142121,
                                                  'QUADCURRENT': 142131,
                                                  'DIRECTCURRENT': 142141,
                                                  'QUADINTEG': 142151,
                                                  'DIRECTINTEG': 142161}}}}

        self.nameMap = {}

    """
    Test - test_XMLFileIsGenerated:
        Given that gen_fem_sf is called to create the XML file for parsing,
        Then the XML file exists at the location returned.
    """
    def test_XMLFileIsGenerated(self):
        fmt, buf, xmlFile = go.gen_fem_sf(self.data, True)
        self.assertTrue(os.path.exists(xmlFile))

    """
    Test - test_sensibleEvenIfDictionaryIsEmpty:
        Given that gen_fem_sf is passed an empty dictionary,
        Then the buffer string generated is not an empty string.
    """
    def test_sensibleEvenIfDictionaryIsEmpty(self):
        fmt, buf, xmlFile = go.gen_fem_sf({})
        self.assertTrue(sys.getsizeof(buf) != 0)

    """
    Test - test_stringBufferRevertsToActualValues:
        Given that self.data is defined and passed to gen_fem_sf,
        Then the buffer generated decodes to the values in self.data.
    """
    def test_stringBufferRevertsToActualValues(self):
        fmt, buf, xmlFile = go.gen_fem_sf(self.data, True)
        treeDict, version = self.xml_ptrs(xmlFile)

        # -----------------------------------------------------------------
        # Test PowerStrip
        # -----------------------------------------------------------------
        testDic = treeDict['PowerStrip']

        # Test status of all devices.
        actualValues = self.data['FEM']['POWERSTRIP']['STATUS']
        tempArray = []
        for device in POWERSTRIP_DEF:
            pointer = testDic[device]
            val = self.extract(buf, pointer)
            tempArray.append(val)
        for extracted, actual in zip(tempArray, actualValues):
            self.assertEqual(extracted, actual)

        # Test volt.
        actualValues = self.data['FEM']['POWERSTRIP']['VOLTS']
        tempArray = self.extract(buf, testDic['Volts'])
        for extracted, actual in zip(tempArray, actualValues):
            self.assertEqual(extracted, actual)

        # Test current.
        actualValues = self.data['FEM']['POWERSTRIP']['CURRENT']
        tempArray = self.extract(buf, testDic['Current'])
        for extracted, actual in zip(tempArray, actualValues):
            self.assertEqual(extracted, actual)

        # -----------------------------------------------------------------
        # Test Thermal
        # -----------------------------------------------------------------
        testDic = treeDict['Thermal']

        # Test temperature of all devices.
        actualValues = self.data['FEM']['THERMAL']['CRYOSTAT']
        tempArray = []
        for device in THERMAL_DEF:
            pointer = testDic[device]
            val = self.extract(buf, pointer)
            tempArray.append(val)
        for extracted, actual in zip(tempArray, actualValues):
            self.assertEqual(extracted, actual)

        # Test focus box themperature.
        actual = self.data['FEM']['THERMAL']['FOCUSBOX']
        pointer = testDic['FocusBoxTemp']
        extracted = self.extract(buf, pointer)
        self.assertEqual(extracted, actual)

        # -----------------------------------------------------------------
        # Test Receiver
        # -----------------------------------------------------------------
        testDic = treeDict['Receiver']

        # Test Enabled registers.
        for data_key, dict_key in RECEIVER_REGISTERS.items():
            actual = self.data['FEM']['RECEIVER'][data_key]
            pointer = testDic[dict_key]
            extracted = self.extract(buf, pointer)
            self.assertEqual(extracted, actual)

        # Test LNAs.
        for extracted_dict, actual_dict in \
                zip(testDic['LNAs'], self.data['FEM']['RECEIVER']['LNAS']):
            for data_key, dict_key in LNA_REGISTERS.items():
                actual = actual_dict[data_key]
                pointer = extracted_dict[dict_key]
                extracted = self.extract(buf, pointer)
                self.assertEqual(extracted, actual)

        # -----------------------------------------------------------------
        # Test Servo
        # -----------------------------------------------------------------
        testDic = treeDict['ApparatusServo']

        # Test each axis
        for axis_num in [1, 3, 4]:
            extracted_dict = testDic[AXIS_DEF[axis_num]]
            actual_dict = self.data['FEM']['SERVO']['AXIS' + str(axis_num)]
            for data_key, dict_key in SERVO_REGISTERS.items():
                actual = actual_dict[data_key]
                pointer = extracted_dict[dict_key]
                extracted = self.extract(buf, pointer)
                self.assertEqual(extracted, actual)


# Main Method
if __name__ == '__main__':
    testGroups = [TestGenerateFrontEndBinary]
    for tG in testGroups:
        print "\nTesting: " + str(tG.__name__)
        suite = unittest.TestLoader().loadTestsFromTestCase(
            tG)
        unittest.TextTestRunner(verbosity=2).run(suite)