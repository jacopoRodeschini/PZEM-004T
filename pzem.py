'''Main script.
Author @Jacopo Rodeschini
Date 18 October 2022 
URL (github): 
DOC: https://docs.micropython.org/en/latest/esp8266/quickref.html#pins-and-gpio

ENERGY METER PZEM-004T

doc: https://github.com/mandulaj/PZEM-004T-v30/blob/master/LINKS.md

ModBus: 
1) https://www.overdigit.com/data/Blog/RS485-Modbus/Protocollo%20Modbus%20su%20RS485.pdf
2) (Addresing) https://github.com/mandulaj/PZEM-004T-v30/issues/63

CRC: 
1) https://www.digi.com/resources/documentation/digidocs/90001537/references/r_python_crc16_modbus.htm 
2) https://github.com/Kalebu/crc16-modbus-in-Python

UART: 
1) https://www.analog.com/en/analog-dialogue/articles/uart-a-hardware-communication-protocol.html

'''

import time

import ustruct as struct
from machine import UART


class PZEM:

    # Default single slave address (see doc)
    addr = 0xF8

    # Device command function admitted (see modbus protocl)
    CMD_RHR = 0x03 # READ HOLDING REGISTRY  
    CMD_RIR = 0x04 # READ INPUT REGISTRY
    CMD_WSR = 0x06 # WRITE SINGLE REGISTRY 


    # Defualt Modbus-16 CRC generator (Table is at the end of the file)
    INITIAL_MODBUS = 0xFFFF

    # Reading values 
  
    Voltage = 0 
    Current = 0
    ActivePower = 0 
    ActiveEnergy = 0
    Frequency = 0
    PowerFactor = 0
    Allarms = 0; 


    def __init__(self, uart, addr= 0xF8):
      """Costruttore della classe. It's only require the UART connecton (This depent on yout device)

      Args:
          uart (UART): uart object to communucate with PZEM device
      """

      # TODO: Check the UART connection (required PZEM stadard)
      # TODO: Checj the Correct address

      self.uart = uart

    def setAddr(self):
      # TODO
      return False
    def getAddr(self): 
      return self.addr

    def readValue(self):
      """Read address of the device. Read holding registry command. PZEM Modbus-RTU address holding registry: 0x0002

      Returns:
          addr: PZEM Modbus-RTU addres  (function 0x03)  
      """

      return self.sendCommand(cmd = self.CMD_RIR, nAddr = 0x0A)

    def sendCommand(self, cmd, nAddr, value = 0x01):
      """Send command to PZEM device & wait for the response

      Args:
          cmd (byte): Command to send (0x03, 0x04, 0x06)
          nAddr (byte): Number of reading address, starting from 0x0000.  
          value (byte): Setting value in the register (only woth 0x03 command)
    
      Returns:
          bool: reding status
      """

      # Start to build hex string command 
      # (> = big endian formst)
      # (B = Unsigned char, 1 byte)
      # (H = Unsigned short, 2 byte) 
      # [BBhh = 6 bytes]
      frame = struct.pack(">BBHH",self.addr,cmd,nAddr,value)

      # Compute the CRC of frame (2 bytes)
      crc16 = self.getCRC16(frame)

      # Add crc to frame obj
      frame = frame = struct.pack(">BBHHH",self.addr,cmd,nAddr,value,crc16)
 
      # Send frame to the UART port 
      self.uart.write(frame)
      time.sleep(1)

      # read the response (25 bytes = (2 * 10 + 1 + 1 + 1 ) + 2 CRC )
      rcv = self.uart.read(25)

      if (len(rcv) == 25) & self.checkCRC16(rcv) & self.updateValue(rcv):
        return True
      else:
        return False
    
    def updateValue(self,frame):
      # Unpack 25 bytes
      val = struct.unpack("!25B", frame)

      self.Voltage = (val[3] << 8 | val[4]) / 10
      self.Current = (val[5] << 8 | val[6] | val[7] << 24 | val[8] << 16) / 1000
      self.ActivePower = (val[9] << 8 | val[10] | val[11] << 24 | val[12] << 16) / 10
      self.ActiveEnergy = (val[13] << 8 | val[14] | val[15] << 24 | val[16] << 16) / 1000
      self.Frequency = (val[17] << 8 | val[18] ) / 10
      self.PowerFactor = (val[19] << 8 | val[20] ) / 100
      self.Allarms = (val[21] << 8 | val[22] )

      return True



    def getCRC16(self,frame):
      crc = self.INITIAL_MODBUS; 

      for ch in frame: 
        crc = (crc >> 8) ^ self.table[(crc ^ ch) & 0xFF]  
      return crc    
    
    def checkCRC16(self,frame):
      rcv = list(struct.unpack("!25", frame)) 
      
      CRC_low = rcv.pop()
      CRC_high= rcv.pop()

      # Check CRC
      crc = self.getCRC16(list[0]); 
      return (CRC_high << 8 | CRC_low) == crc


  # Default ModBus-16 CRC Table 
    table = (0x0000, 0xC0C1, 0xC181, 0x0140, 0xC301, 0x03C0, 0x0280, 0xC241, 0xC601, 0x06C0, 0x0780, 0xC741, 0x0500, 0xC5C1, 0xC481, 0x0440, 0xCC01, 0x0CC0, 0x0D80, 0xCD41, 0x0F00, 0xCFC1, 0xCE81, 0x0E40, 0x0A00, 0xCAC1, 0xCB81, 0x0B40, 0xC901, 0x09C0, 0x0880, 0xC841,  0xD801, 0x18C0, 0x1980, 0xD941, 0x1B00, 0xDBC1, 0xDA81, 0x1A40,    0x1E00, 0xDEC1, 0xDF81, 0x1F40, 0xDD01, 0x1DC0, 0x1C80, 0xDC41,    0x1400, 0xD4C1, 0xD581, 0x1540, 0xD701, 0x17C0, 0x1680, 0xD641,    0xD201, 0x12C0, 0x1380, 0xD341, 0x1100, 0xD1C1, 0xD081, 0x1040,    0xF001, 0x30C0, 0x3180, 0xF141, 0x3300, 0xF3C1, 0xF281, 0x3240,    0x3600, 0xF6C1, 0xF781, 0x3740, 0xF501, 0x35C0, 0x3480, 0xF441,    0x3C00, 0xFCC1, 0xFD81, 0x3D40, 0xFF01, 0x3FC0, 0x3E80, 0xFE41,    0xFA01, 0x3AC0, 0x3B80, 0xFB41, 0x3900, 0xF9C1, 0xF881, 0x3840,    0x2800, 0xE8C1, 0xE981, 0x2940, 0xEB01, 0x2BC0, 0x2A80, 0xEA41,    0xEE01, 0x2EC0, 0x2F80, 0xEF41, 0x2D00, 0xEDC1, 0xEC81, 0x2C40,    0xE401, 0x24C0, 0x2580, 0xE541, 0x2700, 0xE7C1, 0xE681, 0x2640,    0x2200, 0xE2C1, 0xE381, 0x2340, 0xE101, 0x21C0, 0x2080, 0xE041,    0xA001, 0x60C0, 0x6180, 0xA141, 0x6300, 0xA3C1, 0xA281, 0x6240,    0x6600, 0xA6C1, 0xA781, 0x6740, 0xA501, 0x65C0, 0x6480, 0xA441,    0x6C00, 0xACC1, 0xAD81, 0x6D40, 0xAF01, 0x6FC0, 0x6E80, 0xAE41,    0xAA01, 0x6AC0, 0x6B80, 0xAB41, 0x6900, 0xA9C1, 0xA881, 0x6840,    0x7800, 0xB8C1, 0xB981, 0x7940, 0xBB01, 0x7BC0, 0x7A80, 0xBA41,    0xBE01, 0x7EC0, 0x7F80, 0xBF41, 0x7D00, 0xBDC1, 0xBC81, 0x7C40,    0xB401, 0x74C0, 0x7580, 0xB541, 0x7700, 0xB7C1, 0xB681, 0x7640,    0x7200, 0xB2C1, 0xB381, 0x7340, 0xB101, 0x71C0, 0x7080, 0xB041,    0x5000, 0x90C1, 0x9181, 0x5140, 0x9301, 0x53C0, 0x5280, 0x9241,    0x9601, 0x56C0, 0x5780, 0x9741, 0x5500, 0x95C1, 0x9481, 0x5440,    0x9C01, 0x5CC0, 0x5D80, 0x9D41, 0x5F00, 0x9FC1, 0x9E81, 0x5E40,    0x5A00, 0x9AC1, 0x9B81, 0x5B40, 0x9901, 0x59C0, 0x5880, 0x9841,    0x8801, 0x48C0, 0x4980, 0x8941, 0x4B00, 0x8BC1, 0x8A81, 0x4A40,    0x4E00, 0x8EC1, 0x8F81, 0x4F40, 0x8D01, 0x4DC0, 0x4C80, 0x8C41,    0x4400, 0x84C1, 0x8581, 0x4540, 0x8701, 0x47C0, 0x4680, 0x8641,    0x8201, 0x42C0, 0x4380, 0x8341, 0x4100, 0x81C1, 0x8081, 0x4040 )