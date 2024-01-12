# Copyright 2017, Digi International Inc.
#
# Permission to use, copy, modify, and/or distribute this software for any
# purpose with or without fee is hereby granted, provided that the above
# copyright notice and this permission notice appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
# OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.

from digi.xbee.devices import XBeeDevice
import time
import sys

# TODO: Replace with the serial port where your local module is connected to.
PORT = "COM4"
#MAC: ___FC (naklejka "2", przód kompa, góra)


# TODO: Replace with the baud rate of your local module.
BAUD_RATE = 115200

DATA_TO_SEND = "Hello XBee!"
REMOTE_NODE_ID = "coord" #REMOTE


def main():
    print(" +--------------------------------------+")
    print(" | XBee Python Library Send Data Sample |")
    print(" +--------------------------------------+\n")

    device = XBeeDevice(PORT, BAUD_RATE)  
        
    try:
        while(True):
            try:
                device.open(force_settings=True)
                print("Connected to device")
                break
            except:
                print("Device is not connected .. resuming in 10 seconds")
                time.sleep(10)

        # Obtain the remote XBee device from the XBee network.
        xbee_network = device.get_network()

        found = False
        dataSendFails = 0
        dataSendMaxFails = 10

        while (True):

            while (found == False):
                if (device.is_open()):
                    remote_device = None
                    try:
                        remote_device = xbee_network.discover_device(REMOTE_NODE_ID)
                    except:
                        pass
                    if remote_device is None:
                        print("Could not find the remote device")
                        time.sleep(10)
                    else:
                        found = True
                else:
                    print("Device is closed")
                    device.open(force_settings=True)
                    xbee_network = device.get_network()
                
            print("Sending data to %s >> %s..." % (remote_device.get_64bit_addr(), DATA_TO_SEND))
            try:
                device.send_data(remote_device, DATA_TO_SEND)
                print("Success")
            except:
                print("duuua lipa")
                time.sleep(0.5)
                dataSendFails += 1

                if (dataSendFails >= dataSendMaxFails):
                    print("Lost connection to device")
                    sys.exit(1)

    finally:
        if device is not None and device.is_open():
            device.close()


if __name__ == '__main__':
    main()
