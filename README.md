# PZEM-004T (v3.0) Microphyton module  
> Micropython module for the PZEM-004T(v3.0) energy meter 

The PZEM library aims to handle the PZEM-004T (v3.0) energy meter. In particular, read energy values and manage addressing problems. This library is written in micropython to be fully compatible with ESP devices. It communicates using a TTL interface over a [Modbus-RTU] communication protocol and implements the CRC16 checksum. Pay attention that this library works only with the 3.0 version of the PZEM-004T because the old versions use different communication protocols.   
Another important consideration is the voltage level used by the UART channel. PZEM devices only support 5v voltage levels on TX and RX channels. If you use a 3.3v device (like ESP8266) you can upgrade your device to support a 3.3v voltage level with a simple trick, by replacing single resistor (good documentation for this step can be found at the following link: [hardware connections](https://tasmota.github.io/docs/PZEM-0XX/)).  
For easy implementation, a basic example of the PZEM class is provided in the [main.py](https://github.com/jacopoRodeschini/PZEM-004T/blob/master/main.py) file (details on this example are explained below). Other examples can be done starting from this basic one. 

This module works in python, if you need to flash the ESP device (ESP8266 or ESP32) with the micropython firmware, a simple step-by-step guide is available at this [repo](https://github.com/jacopoRodeschini/MicroPython-ESP8266) *(10 min reading)*.

## Features :star:

- [x] Tested for ESP32 :heavy_check_mark:
- [x] Reading the values of voltage, current, active power, active energy, power factor, frequency
- [x] Reset the active energy count.
- [x] The setting of the active power threshold.
- [x] The cyclic redundancy check (CRC) is performed every times. 
- [x] The application layer use the [Modbus-RTU](https://en.wikipedia.org/wiki/Modbus) protocol to communicate (Possibility to create a PZEM measurement network)
- [ ] Calibration 

## Example :mega:

The PZEM object is simple and includes all methods useful to read the smart meters values. For a complete documentation see the methods defined in the PZEM class. The main functions can be summarised in the following examples:  

**Remark** 
 - Setting method (e.g. setAddress()): are use to set value in the PZEM device;
 - Getter method (e.g. getAddress() or getCurrent()): are use to get the value from the pzem object
 - Reading method (e.g. readAddress() or read()): are use to read the value save in the pzed device.  
 - The device neet to be connected with load source power, and with DC power necessary to communicate using UART port.

### Setting up the PZEM device   

The Modbus-RTU protocol is of the Master/Slave type; therefore, there is always only one master in the network. The master device manages communication with one or more Slave devices. All Slaves usually listened to the Master's requests. Only the specific interrogated Slave captures the information sent by the Master, executes the command and replies to the Master by sending the processed information. The Master initiates communication with one of the Slaves, inserting in the message the address of the Slave concerned, the function to be performed and any data associated with the function and the packet control checksum.  
By default, the address used for communication with the PZEM device is 0xF8 which is used as generic address. The address range of the slave is 0x01 ~ 0xF7. The address 0x00 is used as the broadcast address, the slave does not need to reply the master. The address 0xF8 is used as the general address, this address can be only used in single-slave environment. If you know the specific address of the device you can specify the address by replacing the addr=0xF8.  
When you call the **dev = PZEM(...)** the constructor search (using the address _addr_) the device in the network by reading the device address. In this way, if you are in a single-device environment you have the access to a specific device address

```py
from pzem import PZEM
...

# define hardware uart
uart = machine.UART(1, baudrate=9600,timeout=500); 

# define PZEM device [UART, ADDR = 0xF8 (default)]
dev = PZEM(uart=uart,addr=0xF8)

# Get the PZEM real device address (e.g 0x10 = 16)
print(dev.getAddress())
...

```
Is important to define the correct UART port. See the official [documentation](https://docs.micropython.org/en/latest/esp32/quickref.html#uart-serial-bus) to set the correct UART and related GPIOs based on your device. In the ESP8266 there is only one available UART port, thus if you use the RELP terminal is necessary to detach it for reading values from the PZEM-004T and then attach it to communicate with the terminal (official [documentation](https://docs.micropython.org/en/latest/esp8266/quickref.html?highlight=dht#uart-serial-bus)). In the next example a simple function to handle the ESP8266 UART swap (_this function is not tested, it's only a trace to build a more reliable one_). 

```py
def write(frame):

  # remove RELP terminal 
  os.dupterm(None, 1)
  uart = machine.UART(1)
  uart.init(bits=8,parity=None,stop=1,baudrate=9600,timeout=500)

  uart.write(frame)
  time.sleep(1)
  rcv = uart.read(25)

  # Attach relp terminal
  uart = machine.UART(0, 115200)
  os.dupterm(uart, 1)
  print(rcv)

```

### Reading the active energy (every 60 seconds)  
Before getting the value is necessary to read the value from the from the PZEM device. So use the **.read()** function. This function returns true only if the values are correctly updated. Then print the results. 

```py
...
# define 60 sec spleeping time [sec.]
sleep = 60 * 1000

while(True):

  # Read the new values
  if(dev.read()):

    # print the reading value (public filed)
    print(dev.toString())
    print(dev.getCurrent())
    print(dev.getActivePower())

    # wait for the next reading
    machine.time.sleep_ms(sleep - dev.getReadingTime())
```

### Change the device address
If you want to assign a specific address to a generic device, this can be done device by device (also using the RELP) using the general address 0xF8. Be careful not to use the same address for two different devices in the same sensor network.

```py
...
# define PZEM device [UART, ADDR = 0xF8 (default)]
dev = PZEM(uart=uart)

# Set new address
if(dev.setAddress(0x05)):
  print("New device address is {}".format(dev.getAddress()))
...
```

*Using RELP: (open serial session with terminal emulator, like Picocol)*

```py
>> import PZEM
>> import machine

>> uart = machine.UART(1, baudrate=9600,timeout=500); 

# define PZEM device [UART, ADDR = 0xF8 (default)]
>> dev = PZEM(uart=uart)

# Set new address
>> print(dev.setAddress(0x05))
>> print(dev.getAddress())
```

If you want to assign a specific address to a specific device, this can be done in a generics script without removing the device from the sensor network and then assigning it a specific address.

```py
...
# define PZEM device [UART, ADDR = 0x10]
dev = PZEM(uart=uart,0x10)

print(dev.getAddress())

# Set new address (take care that no other device must use the new address)
if(dev.setAddress(0x05)):
  print("New device address is {}".format(dev.getAddress()))
...
```

### Set power allarm threshold
The power alarm threshold is used to check whether the active power has exceeded the set threshold. This is really useful because it could be used to check the peak even when you are not measuring the values (eg if sampling every minute, with this method you can check some peak inside the minute).

```py
...
# define hardware uart
uart = machine.UART(2, baudrate=9600)

# define PZEM device [UART, ADDR = 0xF8 (default)]
dev = PZEM(uart=uart)

# Set the power allarm threshold (in this case 20[W])
if(dev.setThreshold(20))
  print(dev.setThreshold())

# (optional) check the threshold saved in the device
if(dev.readThreshold())
  print(dev.setThreshold())
...
```
than, to check if the active power has cross the threshold:

```py
...

if(dev.read())
  # do some statement
  print(dev.getAllarm())
...
```

### Reset the active energy
This method is useful to reset the energy count (Wh)

```py
...

# 
if(dev.resetEnergy() and dev.read())
  print(dev.toString())
  
...
```

## How to upload file in the ESP8266 and ESP32

To use the PZEM class is necessary to upload the pzem.py file under the /lib folder. This can be done using the [ampy](https://www.digikey.com/en/maker/projects/micropython-basics-load-files-run-code/fb1fcedaf11e4547943abfdd8ad825ce) tool.  

**Download the file**
```bash
$ git clone https://github.com/jacopoRodeschini/PZEM-004T
$ cd PZEM-004T
```

**Upload file**
```bash
$ ampy --port /dev/ttyUSB0 mkdir lib
$ ampy --port /dev/ttyUSB0 put pzem.py /lib/pzem.py
$ ampy --port /dev/ttyUSB0 put main.py
$ ampy --port /dev/ttyUSB0 reset 
``` 

## Acknowledge
---
To build this library I was inspired by [PZEM-004T v3.0](https://github.com/mandulaj/PZEM-004T-v30/blob/master/README.md)
