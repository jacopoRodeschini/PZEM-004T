# PZEM-004T (v3.0) Microphyton module  
> Micropython module for the PZEM-004T(v3.0) energy meter 

[![GitHub issues](https://img.shields.io/github/issues/)](...)
[![Black & flask8 Build](...)](....)

The PZEM library aims to handle the PZEM-004T (v3.0) energy meter. In particular, read energy values and manage addressing problems. This library is written in micropython to be fully compatible with ESP devices. It communicates using a TTL interface over a Modbus-RTU communication protocol and implements the CRC16 checksum. Pay attention that this library works only with the 3.0 version of the PZEM-004T because the old versions use different communication protocols. Another important consideration is the voltage level used by the UART channel. PZEM devices only support 5v voltage levels on TX and RX channels. If you use a 3.3v device (like ESP8266) you can upgrade your device to support a 3.3v voltage level with a simple trick. You need to replace an R17 resistor with a 430-ohm resistor (good documentation can be found at the following link [PZEM-004T-v30](https://github.com/mandulaj/PZEM-004T-v30)). For easy implementation, a basic example of the PZEM class is provided in the main.py file (details on this example are explained below). Other examples can be done starting from the basic one. 

This module works in python, if you need to flash the ESP8266 device with the micropython firmware, a simple step-by-step guide is available at this [repo](https://github.com/jacopoRodeschini/MicroPython-ESP8266) *(10 min reading)*.

## Features
---
- [x] Tested for ESP8266, ESP32 
- [x] Reading the values of voltage, current, active power, active energy, power factor, frequency
- [ ] Reset the active energy count.
- [ ] The setting of the active power threshold.

## Example 
---
The PZEM object is very simple and includes all methods useful to read the smart meters values. For complete documentation see the methods defined in the PZEM class. The main functions can be summarised in the following examples:  

**Setting up the PZEM device**  

> By default, the address used for communication with the PZEM device is 0xF8 which is used as the general address. This address can be only used in a single-slave environment. If you know the address of the device you can specify the address by replacing the addr=0xF8.

```py
from pzem import PZEM
...

# define hardware uart
uart = machine.UART(1, baudrate=9600,timeout=500); 

# define PZEM device [UART, ADDR = 0xF8 (default)]
dev = PZEM(uart=uart,addr=0xF8)
...

```
is important to define the correct UART port. In the ESP8266 there is only one available UART port, thus if you use the RELP terminal is necessary to detach it for reading values from the PZEM-004T and then attach it to communicate with the terminal (official [documentation](https://docs.micropython.org/en/latest/esp8266/quickref.html?highlight=dht#uart-serial-bus)). In the next example a simple function to handle the UART swap. 


```py
def write(frame):

  # remove RELP terminal 
  os.dupterm(None, 1)
  uart = machine.UART(1, baudrate=9600,timeout=500)
  uart.init(bits=8,parity=None,stop=1,baudrate=9600,timeout=500)

  uart.write(frame)
  time.sleep(1)
  rcv = uart.read(25)

  # Attach relp terminal
  uart = machine.UART(0, 115200)
  os.dupterm(uart, 1)
  print(rcv)

```

**Reading the active energy (every 60 seconds)**  

> Before getting the value from the device is necessary to read the value from the sensor. So use the read() function. This function returns true only if the sensor values are correctly updated.

```py
...
# define spleeping time [sec.]
sleep = 60 

while(True):

  # Read the new values
  if(dev.read()):

    # print the reading value (public filed)
    print(dev.toString())
    print(dev.getCurrent())
    print(dev.getActivePower())

  ...

  # wait for the next reading
  machine.time.sleep(sleep - dev.getReadingTime())
```

**Change the device address**  

> If you want to assign a specific address to a generic device, this can be done device by device (also using the RELP) using the general address 0xF8. Be careful not to use the same address for two different devices in the same sensor network.

```py
...
# define PZEM device [UART, ADDR = 0xF8 (default)]
dev = PZEM(uart=uart)

# Set new address
if(dev.setAddr(0x05)):
  print("New device address is {}".format(dev.getAddr()))
...
```

*Using RELP: (open serial session with terminal emulator, like Picocol)*

```py
>> import PZEM

>> uart = machine.UART(1, baudrate=9600,timeout=500); 

# define PZEM device [UART, ADDR = 0xF8 (default)]
>> dev = PZEM(uart=uart)

# Set new address
>> print(dev.setAddr(0x05))
>> print(dev.getAddr())
```

> If you want to assign a specific address to a specific device, this can be done in a generics script without removing the device from the sensor network and then assigning it a specific address.*

```py
...
# define PZEM device [UART, ADDR = 0x10]
dev = PZEM(uart=uart,0x10)
hi
print(dev.getAddr())

# Set new address
if(dev.setAddr(0x05)):
  print("New device address is {}".format(dev.getAddr()))
...
```


## How to upload file in the ESP8266  
---
To use the PZEM class is necessary to upload the pzem.py file under the /lib folder. This can be done using the [ampy](https://www.digikey.com/en/maker/projects/micropython-basics-load-files-run-code/fb1fcedaf11e4547943abfdd8ad825ce) tool.  

**Download the file**
```bash
$ git clone https://github.com/jacopoRodeschini/PZEM-004T
$ cd PZEM-004T
```

**Upload file**
```bash
$ ampy --port /dev/ttyUSB0 mkdir lib
$ ampy --port /dev/ttyUSB0 put /lib/pzem.py
$ ampy --port /dev/ttyUSB0 put main.py
$ ampy --port /dev/ttyUSB0 reset 
``` 