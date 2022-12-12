# *---------------------------------------------*
# | PZEM (v3.0)                                 |
# |                                             |
# | Micropython driver to communicate with      |
# | PZEM-004T (v0.3) using Modbus-RTU protocol  |
# | on the hardware UART port                   |
# |                                             |
# | Authors: Jacopo Rodeschini                  |
# | License: GPLv3                              |
# *---------------------------------------------*

# PZEM is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 2 of the License, or
# (at your option) any later version.
#
# PZEM is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have receivedd a copy of the GNU General Public License
# along with PZEM. If not, see <http://www.gnu.org/licenses/>.

# pzem.py file

import ustruct as struct
import time


class PZEM:

    # Default single slave address [usefull to set specific address] (see doc)
    addr = 0xF8

    # Device command function admitted (see modbus protocl)
    CMD_RHR = 0x03  # READ HOLDING REGISTRY
    CMD_RIR = 0x04  # READ INPUT REGISTRY
    CMD_WSR = 0x06  # WRITE SINGLE REGISTRY

    # Reading values
    Voltage = 0
    Current = 0
    ActivePower = 0
    ActiveEnergy = 0
    Frequency = 0
    PowerFactor = 0
    Allarms = 0
    threshold = 0

    # Info value [debug, timing]
    frame = None
    crc16 = 0x00
    rcvFrame = None
    status = False
    readingTime = 0  # Reading & writing time in [ms]

    def __init__(self, uart, addr=0xF8):
        """Create a PZEM class object. It's only require the UART connecton
        (this could depent on your device). The default address 0xF8 is used
        as the general address, this address can be only used in single-slave
        environment and can be used for calibration etc.operation.
        Below some remark:

        1) If you know the specifc address of the device it's possible replace
            the default address with the specific one;
        2) If you are working in multi-device setting, it is mandatory to
            provide the specific address of the device;
        3) It is possible set the single device address device by device
            and than create a sensor network;
        4) If you use 0xF8 address in the multi-device setting you will get
            an error.

        Args:
            uart (UART) : uart object to communucate with PZEM device
            addr (int)  : ModBus-RTU address of the device. The address 0xF8
                        is used as the general address, this address can be
                        only used in single-slave environment and can be used
                        for calibration etc. operation.

        Exception:
            Address issues(Code 0x01): The address must be between 0x01
                        ~ 0x0F7 (default broadcast address 0xF8). See doc.
            Communication issues(Code 0x02): No device found. See doc.
        """

        # set uart & update field
        self.uart = uart
        self.uart.init(bits=8, parity=None, stop=1, baudrate=9600, timeout=500)

        # chech the address field
        if self.checkAddr(addr=addr):
            self.addr = addr
        else:
            raise Exception(
                "(Code: {}) The address must be between 0x01 to 0x0F8. \
                    See doc.".format(
                    0x01
                )
            )

        # Check the connection by reading the address and update
        # the default address
        if self.readAddress():
            self.status = True
        else:
            raise Exception(
                "(Code: {}) No device found. \
                See doc.".format(
                    0x02
                )
            )

    def checkAddr(self, addr):
        """
        Check the address validity. The address range of the slave is
        0x01 ~ 0xF7. The address 0x00 is used as the broadcast address,
        the slave does not need to reply the master. The address 0xF8
        is used as the general address, this address can be only used
        in single-slave environment and can be used for calibration etc.

        Args:
            addr (int): address of the slave (0x01 ~ 0xF7)

        Returns:
            (bool): return true if the address is in the address range
        """

        return not (addr > 0xF8 | addr == 0x00)

    def getAddress(self):
        """Return the address of the device (seld.addr)

        Returns:
            (int): the device address
        """

        return self.addr

    def setAddress(self, addr):
        """
        Set the device Modbus-RTU address. The address range of the slave is
        0x01 ~ 0xF7. The address 0x00 is used as the broadcast address, the
        slave does not need to reply the master. The address 0xF8 is used as
        the general address.
        After the set, update the address value (self.addr).

        1) PZEM Modbus-RTU address holding registry: 0x0002

        Returns:
            addr (int): PZEM Modbus-RTU address (cmd = 0x06)
        """

        if self.checkAddr(addr):
            return self.sendCommand(cmd=0x06, regAddr=0x02, opt=addr, buf=8)
        else:
            Exception(
                "(Code: {}) The address must be between 0x01 to 0x0F8. \
                    See doc.".format(
                    0x01
                )
            )

    def readAddress(self):
        """Read device address.
        After the reading, update the address value (self.addr)

        Returns:
            (bool): return true if the address value is correctly read & update
        """
        return self.sendCommand(cmd=0x03, regAddr=0x02, opt=0x01, buf=7)

    def read(self):
        """
        Read the energy values of the PZEM device. This task is performed
        by reading the measurement result. This function must be call every
        times before get the PZEM values.[Note 0x0a is represented as
        \n in a standard Python]

        Returns:
            (bool): return true if the values are correctly read.
        """
        return self.sendCommand(cmd=0x04, regAddr=0x00, opt=0x0A, buf=25)

    def resetEnergy(self):
        """Reset energy count.

        Returns:
            (bool): return true if the reset have be done
        """
        return self.sendCommand(cmd=0x42, buf=4)

    def setThreshold(self, thr):
        """Set power allar threshold (cmd = 0x06, holding registry 0x0001,
        1LSB = 1W). Active power threshold can be set, when the measured
        active power exceeds the threshold, it can alarm.

        Args:
            thr (int): power allarm threshold [W] (0x08FC = 2300W)

        Returns:
            (bool): return true if the threshold setting have be done
        """
        return self.sendCommand(cmd=0x06, regAddr=0x01, opt=thr, buf=8)

    def readThreshold(self):
        """Read the power allarm threshold from the device (holding
        registry 0x0001, 1LSB = 1W).

        Returns:
            (int): power allarm threshold [W]
        """
        return self.sendCommand(cmd=0x03, regAddr=0x01, opt=0x01, buf=7)

    def getThreshold(self):
        """Get power allarm threshold

        Returns:
            (int): power allarm threshold
        """
        return self.threshold

    def sendCommand(self, cmd=0x04, regAddr=None, opt=None, buf=25):
        """Send command to PZEM device & wait for the response

        Args:
            cmd       (byte): Command to send (0x03, 0x04, 0x06)
            regAddr   (byte): Start reading register low byte address
            opt       (byte): Number of register to read (or the value
                            for set the register)
            buf       (int) : Number of byte expected in the reply message

        Returns:
            (bool): reding status
        """

        # Start writing time (ms)
        tStart = time.ticks_ms()

        # Start to build hex string command
        # (> = big endian formst)
        # (B = Unsigned char, 1 byte)
        # (H = Unsigned short, 2 byte)
        # [BBhh = 6 bytes]
        if cmd == 0x42:  # Reset the energy cmd
            self.frame = struct.pack(">BB", self.addr, cmd)
        else:
            self.frame = struct.pack(">BBHH", self.addr, cmd, regAddr, opt)

        # Compute the CRC of frame (2 bytes (high & low))
        self.crc16 = self.getCRC16(self.frame)
        crc_h = self.crc16 >> 8 & 0xFF
        crc_l = self.crc16 & 0xFF

        # Add crc to frame obj
        if cmd == 0x42:
            self.frame = struct.pack(">BBBB", self.addr, cmd, crc_l, crc_h)
        else:
            self.frame = struct.pack(
                ">BBHHBB", self.addr, cmd, regAddr, opt, crc_l, crc_h
            )

        # Send frame to the UART port
        self.uart.write(self.frame)
        time.sleep(1)

        # Read the response, maximun 25 bytes
        # (25 bytes = (2 * 10 + 1 + 1 + 1 ) + 2 CRC )
        self.rcvFrame = self.uart.read(buf)

        # Update reading time
        self.readingTime = time.ticks_ms() - tStart

        frame = list(self.rcvFrame)

        if (
            self.checkCRC16(frame)
            and self.checkResponse(frame)
            and len(frame) == (buf - 2)
            and self.updateValue(frame=frame, reg=regAddr)
        ):
            return True
        else:
            # Check the abnormal code in the reply message
            # self.errorCode = frame[2];
            return False

    def getCRC16(self, frame):
        """Compute the cyclic redundancy check (CRC).

        Args:
            frame (byte): sequence of byte to inclose

        Returns:
            (int): CRC code (16 bit - 2 byte)
        """
        crc = 0xFFFF
        for ch in frame:
            crc = (crc >> 8) ^ self.table[(crc ^ ch) & 0xFF]
        return crc

    def checkCRC16(self, frame):
        """Check the checksum of a received messages

        Args:
            frame (list if int): list of integer received in the message

        Returns:
            (bool): return true if the checksum are correct
        """
        CRC_high = frame.pop()
        CRC_low = frame.pop()

        # Check CRC
        crc = self.getCRC16(frame)
        return (CRC_high << 8 | CRC_low) == crc

    def checkResponse(self, frame):
        """Check the message reply

        Args:
            frame (byte): received message

        Returns:
            (bool): return true if the message are correct
        """
        return not (frame[1] == 0x84 or frame[1] == 0x86 or frame[1] == 0xC2)

    def updateValue(self, frame=frame, reg=None):
        """Update the measurement result after self.read() function is called.

        Args:
            frame (list of byte): list of received byte

        Returns:
            (bool): return true if the values are correctly update
        """

        try:
            # Update the measurement value (input registry, cmd = 0x04)
            if frame[1] == 0x04:

                self.Voltage = (frame[3] << 8 | frame[4]) / 10
                self.Current = (
                    frame[5] << 8 | frame[6] | frame[7] << 24 | frame[8] << 16
                ) / 1000
                self.ActivePower = (
                    frame[9] << 8 | frame[10] | frame[11] << 24 | frame[12] << 16
                ) / 10
                self.ActiveEnergy = (
                    frame[13] << 8 | frame[14] | frame[15] << 24 | frame[16] << 16
                ) / 1000
                self.Frequency = (frame[17] << 8 | frame[18]) / 10
                self.PowerFactor = (frame[19] << 8 | frame[20]) / 100
                self.Allarms = frame[21] << 8 | frame[22]

            # Read the allarm threshold value
            # (holding registry = 0x0001, cmd = 0x03)
            elif frame[1] == 0x03 and reg == 0x01:
                self.threshold = frame[3] << 8 | frame[4]

            # Read the Modbus-RTU address
            # (holding registry = 0x0002, cmd = 0x03)
            elif frame[1] == 0x03 and reg == 0x02:
                self.addr = frame[4]

            # Update the allarm threshold value
            # (holding registry 0x0001, cmd = 0x06)
            elif frame[1] == 0x06 and frame[3] == 0x01:
                self.threshold = frame[4] << 8 | frame[5]

            # Update allarm threshold value
            # (holding registry 0x0002, cmd = 0x06)
            elif frame[1] == 0x06 and frame[3] == 0x02:
                self.addr = frame[5]

        except:
            return False
        else:
            return True

    def getReadingTime(self):
        """Get reading time, the delta time between start and end of
        the communication.

        Returns:
            (int): delta time in ms
        """
        return self.readingTime

    def getCurrent(self):
        """Get the reading current[A]

        Returns:
            (float): current [A]
        """
        return self.Current

    def getVoltage(self):
        """Get the reading voltage[W]

        Returns:
            (float): volatage [V]
        """
        return self.Voltage

    def getActivePower(self):
        """Get the active power [W]

        Returns:
            (float): active power [W]
        """
        return self.ActivePower

    def getActiveEnergy(self):
        """Get the active energy [Wh]

        Returns:
            (float): active energy [Wh]
        """
        return self.ActiveEnergy

    def getFrequency(self):
        """Get the frequancy [Hz]

        Returns:
            (float): frequency [Hz]
        """
        return self.Frequency

    def getPowerFactor(self):
        """Get the power factor

        Returns:
            (float): power factor
        """
        return self.PowerFactor

    def getAllarm(self):
        """Get the allarm

        Returns:
            (bool): return true if active power crossed the threshold
        """
        return self.Allarms

    def toString(self):
        """Get string of the reading measurement. This string can be use to
        save result in a text file.

        Returns:
            (String): reading measurement

        """
        return """Voltage[V]: {} \t Current[A]: {} \t ActivePower[W]: {} \t
      ActiveEnergy[KWh]: {} \t PowerFactor: {} \t Frequency[Hz]: {}
      \t Allarm: {} \n""".format(
            self.getVoltage(),
            self.getCurrent(),
            self.getActivePower(),
            self.getActiveEnergy(),
            self.getPowerFactor(),
            self.getFrequency(),
            self.getAllarm(),
        )

    # Default ModBus-16 CRC Table
    table = (
        0x0000,
        0xC0C1,
        0xC181,
        0x0140,
        0xC301,
        0x03C0,
        0x0280,
        0xC241,
        0xC601,
        0x06C0,
        0x0780,
        0xC741,
        0x0500,
        0xC5C1,
        0xC481,
        0x0440,
        0xCC01,
        0x0CC0,
        0x0D80,
        0xCD41,
        0x0F00,
        0xCFC1,
        0xCE81,
        0x0E40,
        0x0A00,
        0xCAC1,
        0xCB81,
        0x0B40,
        0xC901,
        0x09C0,
        0x0880,
        0xC841,
        0xD801,
        0x18C0,
        0x1980,
        0xD941,
        0x1B00,
        0xDBC1,
        0xDA81,
        0x1A40,
        0x1E00,
        0xDEC1,
        0xDF81,
        0x1F40,
        0xDD01,
        0x1DC0,
        0x1C80,
        0xDC41,
        0x1400,
        0xD4C1,
        0xD581,
        0x1540,
        0xD701,
        0x17C0,
        0x1680,
        0xD641,
        0xD201,
        0x12C0,
        0x1380,
        0xD341,
        0x1100,
        0xD1C1,
        0xD081,
        0x1040,
        0xF001,
        0x30C0,
        0x3180,
        0xF141,
        0x3300,
        0xF3C1,
        0xF281,
        0x3240,
        0x3600,
        0xF6C1,
        0xF781,
        0x3740,
        0xF501,
        0x35C0,
        0x3480,
        0xF441,
        0x3C00,
        0xFCC1,
        0xFD81,
        0x3D40,
        0xFF01,
        0x3FC0,
        0x3E80,
        0xFE41,
        0xFA01,
        0x3AC0,
        0x3B80,
        0xFB41,
        0x3900,
        0xF9C1,
        0xF881,
        0x3840,
        0x2800,
        0xE8C1,
        0xE981,
        0x2940,
        0xEB01,
        0x2BC0,
        0x2A80,
        0xEA41,
        0xEE01,
        0x2EC0,
        0x2F80,
        0xEF41,
        0x2D00,
        0xEDC1,
        0xEC81,
        0x2C40,
        0xE401,
        0x24C0,
        0x2580,
        0xE541,
        0x2700,
        0xE7C1,
        0xE681,
        0x2640,
        0x2200,
        0xE2C1,
        0xE381,
        0x2340,
        0xE101,
        0x21C0,
        0x2080,
        0xE041,
        0xA001,
        0x60C0,
        0x6180,
        0xA141,
        0x6300,
        0xA3C1,
        0xA281,
        0x6240,
        0x6600,
        0xA6C1,
        0xA781,
        0x6740,
        0xA501,
        0x65C0,
        0x6480,
        0xA441,
        0x6C00,
        0xACC1,
        0xAD81,
        0x6D40,
        0xAF01,
        0x6FC0,
        0x6E80,
        0xAE41,
        0xAA01,
        0x6AC0,
        0x6B80,
        0xAB41,
        0x6900,
        0xA9C1,
        0xA881,
        0x6840,
        0x7800,
        0xB8C1,
        0xB981,
        0x7940,
        0xBB01,
        0x7BC0,
        0x7A80,
        0xBA41,
        0xBE01,
        0x7EC0,
        0x7F80,
        0xBF41,
        0x7D00,
        0xBDC1,
        0xBC81,
        0x7C40,
        0xB401,
        0x74C0,
        0x7580,
        0xB541,
        0x7700,
        0xB7C1,
        0xB681,
        0x7640,
        0x7200,
        0xB2C1,
        0xB381,
        0x7340,
        0xB101,
        0x71C0,
        0x7080,
        0xB041,
        0x5000,
        0x90C1,
        0x9181,
        0x5140,
        0x9301,
        0x53C0,
        0x5280,
        0x9241,
        0x9601,
        0x56C0,
        0x5780,
        0x9741,
        0x5500,
        0x95C1,
        0x9481,
        0x5440,
        0x9C01,
        0x5CC0,
        0x5D80,
        0x9D41,
        0x5F00,
        0x9FC1,
        0x9E81,
        0x5E40,
        0x5A00,
        0x9AC1,
        0x9B81,
        0x5B40,
        0x9901,
        0x59C0,
        0x5880,
        0x9841,
        0x8801,
        0x48C0,
        0x4980,
        0x8941,
        0x4B00,
        0x8BC1,
        0x8A81,
        0x4A40,
        0x4E00,
        0x8EC1,
        0x8F81,
        0x4F40,
        0x8D01,
        0x4DC0,
        0x4C80,
        0x8C41,
        0x4400,
        0x84C1,
        0x8581,
        0x4540,
        0x8701,
        0x47C0,
        0x4680,
        0x8641,
        0x8201,
        0x42C0,
        0x4380,
        0x8341,
        0x4100,
        0x81C1,
        0x8081,
        0x4040,
    )
