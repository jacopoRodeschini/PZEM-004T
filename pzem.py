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
# You should have received a copy of the GNU General Public License
# along with PZEM. If not, see <http://www.gnu.org/licenses/>.

# pzem.py file

import time

import ustruct as struct
from machine import UART, time


class PZEM:

    # Default single slave address [usefull to set specific address] (see doc)
    addr = 0xF8

    # Device command function admitted (see modbus protocl)
    CMD_RHR = 0x03  # READ HOLDING REGISTRY
    CMD_RIR = 0x04  # READ INPUT REGISTRY
    CMD_WSR = 0x06  # WRITE SINGLE REGISTRY

    ADRR_LIM = 0x0A  # Limit upper register [Note 0x0a is represented as \n in a standard Python]

    # Defualt Modbus-16 CRC generator (Table is at the end of the file)
    INITIAL_MODBUS = 0xFFFF

    # Reading values
    Voltage = 0
    Current = 0
    ActivePower = 0
    ActiveEnergy = 0
    Frequency = 0
    PowerFactor = 0
    Allarms = 0

    # Info value [debug, timing]
    frame = None
    crc16 = 0x00
    rcvFrame = None
    status = False
    readingTime = 0  # Reading & writing time in [ms]

    def __init__(self, uart, addr=0xF8):
        """Costruttore della classe. It's only require the UART connecton (This depent on yout device)


        Args:
            uart (UART) : uart object to communucate with PZEM device
            addr (int)  : ModBus-RTU address of the device

        Exception:
            Address       issues(Code 0x01): The address must be between 0x01 to 0x0F7 (default broadcast address 0xF8). See doc.
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
                "(Code: {}) The address must be between 0x01 to 0x0F8. See doc.".format(
                    0x01
                )
            )

        # Check the connection with the device
        if self.checkConnection():
            self.status = True
        else:
            raise Exception("(Code: {}) No device found. See doc.".format(0x02))

    def checkAddr(self, addr):
        return not (addr > 0xF8 | addr == 0x00)

    def checkConnection(self):
        # TODO: check the connection
        return True

    def getAddr(self):
        return self.addr

    def setAddr(self, addr):
        """
        Set the device protocol address [0x01 ~ 0xF8].
        PZEM Modbus-RTU address holding registry: 0x0002

        Returns:
            addr: PZEM Modbus-RTU addres  (Write registry function 0x06)
        """
        if self.checkAddr(addr):
            return self.sendCommand(cmd=0x06, regAddr=0x02, opt=addr)
        else:
            Exception(
                "(Code: {}) The address must be between 0x01 to 0x0F8. See doc.".format(
                    0x01
                )
            )

    def read(self):
        return self.sendCommand(cmd=0x04, regAddr=0x00, opt=0x0A)

    def resetEnergy(self):
        return False

    def sendCommand(self, cmd, regAddr, opt=None):
        """Send command to PZEM device & wait for the response

        Args:
            cmd       (byte): Command to send (0x03, 0x04, 0x06)
            regAddr   (byte): Start reading register address
            opt       (byte): Number of register to read or set value for the register

        Returns:
            bool: reding status
        """

        # Start writing time
        tStart = start = time.ticks_ms()

        # Start to build hex string command
        # (> = big endian formst)
        # (B = Unsigned char, 1 byte)
        # (H = Unsigned short, 2 byte)
        # [BBhh = 6 bytes]
        self.frame = struct.pack(">BBHH", self.addr, cmd, regAddr, opt)

        # Compute the CRC of frame (2 bytes)
        self.crc16 = self.getCRC16(self.frame)

        # Add crc to frame obj
        self.frame = struct.pack(">BBHHH", self.addr, cmd, regAddr, opt, self.crc16)

        # Send frame to the UART port
        self.uart.write(self.frame)
        time.sleep(1)

        # Read the response, maximun 25 bytes (25 bytes = (2 * 10 + 1 + 1 + 1 ) + 2 CRC )
        self.rcvFrame = self.uart.read(25)

        # Update reading time
        self.readingTime = time.ticks_us() - tStart

        frame = list(self.rcvFrame)
        if self.checkCRC16(frame) & self.checkResponse():
            if (len(frame) == 25) & frame[2] == 0x14 & self.updateValue(frame):
                # Read all register
                return True
            elif (len(frame) == 8) & frame[1] == 0x06:
                # Set / reading the address value
                self.addr = opt
                return True
            else:
                return False
        else:
            Exception(
                "(Code: {}) Error reply, abnormal code analyzed: {}".format(
                    0x03, rcv[2]
                )
            )

    def getCRC16(self, frame):
        crc = self.INITIAL_MODBUS

        for ch in frame:
            crc = (crc >> 8) ^ self.table[(crc ^ ch) & 0xFF]
        return crc

    def checkCRC16(self, frame):

        CRC_low = frame.pop()
        CRC_high = frame.pop()

        # Check CRC
        crc = self.getCRC16(frame)
        return (CRC_high << 8 | CRC_low) == crc

    def checkResponse(self, frame):
        return not (frame[1] == 0x84 or frame[1] == 0x86)

    def updateValue(self, frame):
        # Unpack 25 bytes
        # val = struct.unpack("!25B", frame)

        try:
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
        except:
            return False
        else:
            return True

    def getReadingTime(self):
        return self.readingTime

    def getCurrent(self):
        return self.Current

    def getVoltage(self):
        return self.Voltage

    def getActivePower(self):
        return self.ActivePower

    def getActiveEnergy(self):
        return self.ActiveEnergy

    def getFrequency(self):
        return self.Frequency

    def getPowerFactor(self):
        return self.PowerFactor

    def toString(self):
        return """Voltage[V]: {} \t Current[A]: {} \t ActivePower[W]: {} \t 
      ActiveEnergy[KWh]: {} \t PowerFactor: {} \t Frequency[Hz]: {} \n""".format(
            self.getVoltage(),
            self.getCurrent(),
            self.getActivePower(),
            self.getActiveEnergy(),
            self.getPowerFactor(),
            self.getFrequency(),
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
