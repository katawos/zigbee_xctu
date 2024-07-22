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
from datetime import datetime
import time
import sys
import numpy as np
import cv2

# TODO: Replace with the serial port where your local module is connected to.
PORT = "COM4"
#MAC: ___5A (lewo)

# TODO: Replace with the baud rate of your local module.
BAUD_RATE = 115200

payload_list = []
bool_start_gathering = False
bool_get_params = False
image_x = None
image_y = None

experiment_transmission_time_start = None
experiment_transmission_time_end = None
experiment_reconstruction_time_end = None

file = open("receive_buffer.txt", "a+")
write_out_data = ""

def save_image(payload_list):
    global image_x
    global image_y
    global experiment_transmission_time_start
    global experiment_reconstruction_time_end
    global file
    global write_out_data
    arr = []
    for idx in range(len(payload_list)):
        arr += payload_list[idx]

    np_arr = np.array(arr, dtype=np.uint8)
    # Shape takes (row, column) where row = y, column = x

    try:
        np_data_2d = np_arr.reshape(image_y,image_x)

        # DECODE HERE IF METHOD IS USED FOR FASTER DATA TRANSFER
        experiment_reconstruction_time_end = datetime.now()
        diff_time = experiment_reconstruction_time_end - experiment_transmission_time_start
        write_out_data += f", tr: {diff_time}" + "}\n"
        print(write_out_data)
        file.write(write_out_data)
        write_out_data = ""
        cv2.imwrite('received_image.jpg', np_data_2d)
    except:
        print("Broken")
        write_out_data += f", tr: broken" + "}\n"
        print(write_out_data)
        file.write(write_out_data)
        write_out_data = ""
    # cv2.imshow('received_image', np_data_2d)
    # cv2.waitKey(0)

def data_receive_callback(xbee_message):
    global bool_start_gathering
    global bool_get_params
    global payload_list
    global image_x
    global image_y
    global experiment_transmission_time_start
    global experiment_transmission_time_end
    global write_out_data
    # print(f"{datetime.now()} From %s" % (xbee_message.remote_device.get_64bit_addr()))
    received_data = list(xbee_message.data)

    if (bool_get_params == True):
        string = f"{xbee_message.data.decode('utf-8')}"
        string_list = string.split(",")
        image_x = int(string_list[0])
        image_y = int(string_list[1])
        payload_size = int(string_list[2])
        method = string_list[3]
        experiment = string_list[4]
        write_out_data += "{" + f"X: {image_x}, Y: {image_y}, PayloadSize: {payload_size}, Method: {method}, Experiment: {experiment}"
        bool_start_gathering = True
        bool_get_params = False
        experiment_transmission_time_start = datetime.now()
        return

    if (received_data == [101, 110, 100]):
        experiment_transmission_time_end = datetime.now()
        diff_time = experiment_transmission_time_end - experiment_transmission_time_start
        write_out_data += f", t: {diff_time}"
        # print("stop gathering")
        bool_start_gathering = False
        save_image(payload_list)
    
    if (bool_start_gathering == True):
        payload_list.append(received_data) 
        # print(f"Data {received_data}")

    if (received_data == [115, 116, 97, 114, 116]): # start
        print("start gathering")
        bool_get_params = True
        payload_list = []
        

def run():
    print(" +-----------------------------------------+")
    print(" | XBee Python Library Receive Data Sample |")
    print(" +-----------------------------------------+\n")

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

        device.add_data_received_callback(data_receive_callback)

        print("Waiting for data...\n")
        input()
    except:
        print("Lost connection to device")
        if device is not None and device.is_open():
            device.close()
        sys.exit(1)
    finally:
        if device is not None and device.is_open():
            device.close()


if __name__ == '__main__':
    run()