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

def compress1(image):
    print("Im compressing1")
    # Compress method here
    return image

def compress2(image):
    print("Im compressing2")
    # Compress method here
    return image

def divide_to_payload(array, chunk_size, parameters):
    arr = [array[i:i + chunk_size].tolist() for i in range(0, len(array), chunk_size)]
    arr.insert(0, parameters)
    arr.insert(0, "start")
    arr.append("end")
    return arr

def loadImage():
    # open test image
    img = cv2.imread("test.jpg")
    #cv2.imshow("test image", img)
    #cv2.waitKey()
    # Shape will give (row, column) where row = y, column = x
    print(img.shape)

    return img

def modifyImage(img, image_x, image_y, method = None):

    functions = {
        "compress1": compress1,
        "compress2": compress2,
    }
    
    img = cv2.resize(img, (image_x, image_y))
    gray_img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    cv2.imwrite('before_image.jpg', gray_img)

    # ENCODE HERE IF YOU WANT TO USE ANY METHOD FOR FASTER DATA TRANSFER
    if (method is not None):
        mod_img = functions[method](gray_img) 
    else:
        mod_img = gray_img

    mod_img_1d = mod_img.flatten()

    return mod_img_1d

def XbeeSend(data_payloads, data_size, transmission = "tcp", transmission_sleep = 0.014):
    print(" +--------------------------------------+")
    print(" | XBee Python Library Send Data Sample |")
    print(" +--------------------------------------+\n")

    data_idx = 0

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
                
            print(f"Sending data to {remote_device.get_64bit_addr()}")
            # print(f" >> {data_payloads[data_idx]}\n")
            try:
                if (type(data_payloads[data_idx]) != str):
                    if (transmission == "tcp"):
                        device.send_data(remote_device, bytearray(data_payloads[data_idx]))
                    elif (transmission == "udp"):
                        device.send_data_async(remote_device, bytearray(data_payloads[data_idx]))
                        time.sleep(transmission_sleep)
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

def run(image_x, image_y, payload_size, experiment, method = None, transmission = "tcp", transmission_sleep = 0.014):
    img = loadImage()
    mod_img_1d = modifyImage(img, image_x, image_y, method)
    data_payloads = divide_to_payload(mod_img_1d, payload_size, f"{image_x},{image_y},{payload_size},{method},{experiment}")
    data_size = len(data_payloads)


    XbeeSend(data_payloads, data_size, transmission, transmission_sleep)

if __name__ == '__main__':
    # for idx in range(40,255, 5):
    #     run(image_x = 75, image_y = 150, payload_size = idx, method = "compress1", experiment = "payload size")

# 1-3 4:3, 4-5 16:9
    resolutions = {
        "144p": [192, 144],
        "240p": [320, 240],
        "480p": [720, 480],
        "720p": [1280, 720],
        "1080p": [1920, 1080]
    }

    # for key in resolutions.keys():
    #     run(image_x = resolutions[key][0], image_y = resolutions[key][1], payload_size = 80, experiment = f"resolution {key}", method = None)

    run(image_x = resolutions["144p"][0], image_y = resolutions["144p"][1], payload_size = 80, experiment = f"tcp", method = None)

    for idx in range(10, 20):
        sleep_time = idx / 1000
        run(image_x = resolutions["144p"][0], image_y = resolutions["144p"][1], payload_size = 80, experiment = f"udp-sleep-{sleep_time}", method = None, transmission="udp", transmission_sleep=sleep_time)


