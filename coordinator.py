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
import numpy as np
import cv2
import pandas as pd

# TODO: Replace with the serial port where your local module is connected to.
PORT = "COM3"
#MAC: ___FC (naklejka "2", po prawej)


# TODO: Replace with the baud rate of your local module.
BAUD_RATE = 115200

DATA_TO_SEND = "Hello XBee!"
REMOTE_NODE_ID = "sensor" #REMOTE

IMAGE_X = 137
IMAGE_Y = 61
PAYLOAD_SIZE = 255

def divide_to_payload(array, chunk_size, img_shape):
    arr = [array[i:i + chunk_size].tolist() for i in range(0, len(array), chunk_size)]
    arr.insert(0, img_shape)
    arr.insert(0, "start")
    arr.append("end")
    return arr

def main():
    # open test image
    img = cv2.imread("test.jpg")
    img = cv2.resize(img, (IMAGE_X*2, IMAGE_Y*2))
    #cv2.imshow("test image", img)
    #cv2.waitKey()
    print(img.shape)
    gray_img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    cv2.imwrite('before_image.jpg', gray_img)

    # ENCODE HERE IF YOU WANT TO USE ANY METHOD FOR FASTER DATA TRANSFER
    
    gray_img_1d = gray_img.flatten()
    data_payloads = divide_to_payload(gray_img_1d, PAYLOAD_SIZE, f"{IMAGE_X*2},{IMAGE_Y*2}")

    DATA_TO_SEND = data_payloads
    data_size = len(data_payloads)
    data_idx = 0

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

        while (data_idx < data_size):

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
                
            print("Sending data to %s >> %s..." % (remote_device.get_64bit_addr(), data_payloads[data_idx]))
            try:
                if (type(data_payloads[data_idx]) != str):
                    device.send_data(remote_device, bytearray(data_payloads[data_idx]))
                else:
                    device.send_data(remote_device, data_payloads[data_idx])
                print("Success")
                data_idx += 1
            except Exception as e:
                print(e)
                time.sleep(0.5)
                dataSendFails += 1

                if (dataSendFails >= dataSendMaxFails):
                    print("Lost connection to device")
                    sys.exit(1)
            # time.sleep(1)

    finally:
        if device is not None and device.is_open():
            device.close()


if __name__ == '__main__':
    main()
