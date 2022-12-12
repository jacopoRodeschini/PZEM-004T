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

# main.py file

from pzem import PZEM
import machine
import time

# define 60 sec spleeping time [msec.]
sleep = 60 * 1000 

# define hardware uart
uart = machine.UART(2, baudrate=9600)

# define PZEM device [UART, ADDR = 0xF8 (default)]
dev = PZEM(uart=uart)

# Set new address
if dev.setAddress(0x05):
    print("New device address is {}".format(dev.getAddress()))


while True:

    # Read the new values
    if dev.read():

        # print the reading value (public filed)
        print(dev.toString())
        print(dev.getCurrent())

    # wait for the next reading
    time.sleep_ms(sleep - dev.getReadingTime())
