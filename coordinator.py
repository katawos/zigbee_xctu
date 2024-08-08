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
from PIL import Image
import jpeg_ls

#import openjpeg

# TODO: Replace with the serial port where your local module is connected to.
PORT = "COM3"
#MAC: ___FC (right, sticker "2")

# TODO: Replace with the baud rate of your local module.
BAUD_RATE = 115200

DATA_TO_SEND = "Hello XBee!"
REMOTE_NODE_ID = "sensor" #REMOTE


def compressJPEG(image_name, quality):
    print("Im compressing JPEG")
    image = cv2.imread(image_name)
    img_name = 'before_JPEG_image.jpg'
    #save image to the one with the new name and given JPEG quality
    cv2.imwrite(img_name, image, [int(cv2.IMWRITE_JPEG_QUALITY), quality])  # Quality ranges from 0 to 100
    return img_name


def compressJPEG2000(image_name, quality):
    print("Im compressing JPEG-2000")
    image = cv2.imread(image_name)
    img_name = 'before_JPEG-2000_image.jpg'
    #save image to the one with the new name and given JPEG compression ratio
    cv2.imwrite(img_name, image, [int(cv2.IMWRITE_JPEG2000_COMPRESSION_X1000), quality])  # Compression ratio ranges from 0 to 1000
    return img_name


def compressJPEG_LS(image, quality):
    print("Im compressing JPEG-LS")
    image = cv2.imread(image)
    quality = int(((100 - quality) / 100) * 255)    #ranges from 0 to 255
    img_name = 'before_JPEG-LS_image.jpg'
    data_buffer = jpeg_ls.encode(image, quality)

    f = open(img_name, "wb")    #write in binary format
    f.write(data_buffer.tobytes())  #write binary dara to file
    f.close()
    return img_name


def divide_to_payload(array, _payload_size, seq_bytes, parameters):
    arr = []
    count = 0
    # array = image size in array, _payload_size = size of image part that can be send at a time 
    for i in range(0, len(array), _payload_size - seq_bytes):
        new_arr = []

        # If asynch seq number
        if (seq_bytes > 0):
            # Convert the integer to a bytes object in big-endian order
            byte_data = count.to_bytes(seq_bytes, byteorder='big')  #number of bytes required, MSB is stored in smallest memory address -> LSB is first
            # Convert the bytes object to a list
            byte_list = list(byte_data)
        
            new_arr += byte_list
        #slice array to include elements from i to (i+ch-seq)
        new_arr += array[i:i + _payload_size - seq_bytes]
        arr.append(new_arr)
        count += 1

    #pattern for data array
    arr.insert(0, "start")
    arr.insert(1, parameters)
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


def modifyImage(img, image_x, image_y, method = None, quality = None):

    functions = {
        "JPEG": compressJPEG,
        "JPEG-2000": compressJPEG2000,
        "JPEG-LS": compressJPEG_LS
    }
    
    #resize
    img = cv2.resize(img, (image_x, image_y))
    # gray_img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)  #for grayscale

    #rename and save as new image
    img_name = 'before_image.jpg'
    cv2.imwrite(img_name, img)

    # ENCODE HERE IF YOU WANT TO USE ANY METHOD FOR FASTER DATA TRANSFER
    if (method is not None):
        img_name = functions[method](img_name, quality) 

    img_file = open(img_name, "rb") #open in binary read mode
    img_bytes = img_file.read() #read as byte string
    img_1d_arr = np.frombuffer(img_bytes, dtype=np.uint8).tolist()  #numpy array of uint8 -> 0-255 range, then set to list

    return img_1d_arr


def XbeeSend(data_payloads, data_size, transmission = "synch", transmission_sleep = 0.014):
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
                #set ACK parameter, TO = 0 => retries, TO = 1 => no retries
                print(device.get_parameter("TO"))
                device.set_parameter("TO", b"\x00")
                print(device.get_parameter("TO"))
                break
            except Exception as e:
                print("Device is not connected .. resuming in 10 seconds")
                print(e)
                time.sleep(10)

        # Obtain the remote XBee device from the XBee network.
        xbee_network = device.get_network()

        found = False
        dataSendFails = 0
        dataSendMaxFails = 50

        firstAsynch = True
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
               
            print(f"Sending data to {remote_device.get_16bit_addr()}")

            try:
                if (type(data_payloads[data_idx]) != str):  #check the type of particular element, if not string (e.g. "start")
                    if (transmission == "synch"):
                        #send data Synchronously - wait until the data has been fully sent before continuing
                        device.send_data(remote_device, bytearray(data_payloads[data_idx])) 
                    elif (transmission == "asynch"):
                        if (firstAsynch == True):
                            time.sleep(transmission_sleep) 
                            firstAsynch = False
                        #send data Asynchronously - not wait for data to be sent before moving on
                        #time.sleep() slows down sending the packets to: reduce number of dropped packets, avoid collisions and help control data rate
                        device.send_data_async(remote_device, bytearray(data_payloads[data_idx]))   
                        time.sleep(transmission_sleep)
                else:
                    device.send_data(remote_device, data_payloads[data_idx])    #for string data type, like "end"
                print("Success")
                data_idx += 1
            except Exception as e:
                print(e)
                
                dataSendFails += 1

                if (dataSendFails >= dataSendMaxFails):
                    print("Max send fails are reached. Lost connection to device")
                    sys.exit(1)

    finally:
        if device is not None and device.is_open():
            device.close()


def SendPerfectImage(image_resolution): #send image to reliably compare and calculate transmission errors (original, synch, no compression)
    run(image_x = resolutions[image_resolution][0], image_y = resolutions[image_resolution][1], payload_size = 80, experiment = f"original_{image_resolution}_image_save", method = None, transmission="synch", transmission_sleep=0.014, comparison_image=True)


def run(image_x, image_y, payload_size, experiment, method = None, quality = None, transmission = "synch", transmission_sleep = 0.014, comparison_image = False):
    img = loadImage()
    mod_img_1d = modifyImage(img, image_x, image_y, method, quality)

    #set appropriate header size for given number of packets
    #payload size = known, sequence bytes subtracted from payload to ensure that data packets are sequenced in header
    seq_bytes = 0
    if (transmission == "asynch"):
        seq_bytes = 1   #0 - 255
        number_of_packets = image_x * image_y / (payload_size - seq_bytes)
        if (number_of_packets > 255):       #0 - 65,535
            seq_bytes = 2
            number_of_packets = image_x * image_y / (payload_size - seq_bytes)
        elif (number_of_packets > 65535):   #0 - 16,777,216
            seq_bytes = 3
            number_of_packets = image_x * image_y / (payload_size - seq_bytes)

    data_payloads = divide_to_payload(mod_img_1d, payload_size, seq_bytes, f"{image_x},{image_y},{payload_size},{method},{experiment},{transmission},{seq_bytes},{comparison_image}")
    data_size = len(data_payloads)

    XbeeSend(data_payloads, data_size, transmission, transmission_sleep)


if __name__ == '__main__':

    resolutions = {
        #"144p": [192, 144],
        #"240p": [320, 240],
        "480p": [640, 480],
        "720p": [1280, 720],
        "1080p": [1920, 1080]
    }

    #TESTS
    #for resolution ___p
    res = "480p"
    #transmission type-like
    trans_type = ["synch", "asynch"]


    # # (1) asynch transmission sleep test from 5 to 20 ms
    # SendPerfectImage(res)
    # for idx in range(5, 20):
    #     sleep_time = idx / 1000
    #     #asynch
    #     exper_name = trans_type[1] + f"_res{res}_sleep_{sleep_time}"
    #     run(image_x = resolutions[res][0], image_y = resolutions[res][1], payload_size = 80, experiment = exper_name, method = None, transmission = trans_type[1], transmission_sleep = sleep_time)


    # (2) Payload test
    # SendPerfectImage(res)
    # for payload_bytes in range(40, 255, 5):
    #     #synch
    #     exper_name = trans_type[0] + f"_res{res}_payload_{payload_bytes}"
    #     run(image_x = resolutions[res][0], image_y = resolutions[res][1], payload_size = payload_bytes, experiment = exper_name, method = None, transmission = trans_type[0])
    #     #asynch
    #     exper_name = trans_type[1] + f"_res{res}_payload_{payload_bytes}"
    #     run(image_x = resolutions[res][0], image_y = resolutions[res][1], payload_size = payload_bytes, experiment = exper_name, method = None, transmission = trans_type[1])


    # # (3) Resolution test
    # for key in resolutions.keys():  #go through each of resolutions names (key pairs)
    #     SendPerfectImage(key)
    #     #synch
    #     exper_name = trans_type[0] + f"_resolution_{key}"
    #     run(image_x = resolutions[key][0], image_y = resolutions[key][1], payload_size = 80, experiment = exper_name, method = None, transmission = trans_type[0])
    #     #asynch
    #     exper_name = trans_type[1] + f"_resolution_{key}"
    #     run(image_x = resolutions[key][0], image_y = resolutions[key][1], payload_size = 80, experiment = exper_name, method = None, transmission = trans_type[1], transmission_sleep=0.014)


    # # (4) Sleep and payload asynch
    # SendPerfectImage(res)
    # for idx in range(12, 16):
    #     sleep_time = idx / 1000
    #     for payload_bytes in range(40, 255, 5):
    #         exper_name = trans_type[1] + f"_res{res}_payload_{payload_bytes}_sleep_{sleep_time}"
    #         run(image_x = resolutions[res][0], image_y = resolutions[res][1], payload_size = payload_bytes, experiment = exper_name, method = None, transmission = trans_type[1], transmission_sleep = sleep_time)


    # # (5) Compression methods
    SendPerfectImage(res)
    # # JPEG
    # for quality_ in range(95, 75, -10):
    # quality_ = 80
    # #synch
    # exper_name = trans_type[0] + f"_res{res}_compr_JPEG_qual_" + str(quality_)
    # run(image_x = resolutions[res][0], image_y = resolutions[res][1], payload_size = 80, experiment = exper_name, method = "JPEG", quality = quality_, transmission = trans_type[0])
    # #asynch
    # exper_name = trans_type[1] + f"_res{res}_compr_JPEG_qual_" + str(quality_)
    # run(image_x = resolutions[res][0], image_y = resolutions[res][1], payload_size = 80, experiment = exper_name, method = "JPEG", quality = quality_, transmission = trans_type[1])

    # # JPEG 2000
    # for quality_ in range(95, 75, -10):
    quality_ = 272
    #synch
    exper_name = trans_type[0] + f"_res{res}_compr_JPEG-2000_qual_" + str(quality_)
    run(image_x = resolutions[res][0], image_y = resolutions[res][1], payload_size = 80, experiment = exper_name, method = "JPEG-2000", quality = quality_, transmission = trans_type[0])
    #asynch
    exper_name = trans_type[1] + f"_res{res}_compr_JPEG-2000_qual_" + str(quality_)
    run(image_x = resolutions[res][0], image_y = resolutions[res][1], payload_size = 80, experiment = exper_name, method = "JPEG-2000", quality = quality_, transmission = trans_type[1])

    ## # JPEG LS
    ## for quality_ in range(95, 75, -10):
    ##     #synch
    ##     exper_name = trans_type[0] + f"_res{res}_compr_JPEG-LS_qual_" + str(quality_)
    ##     run(image_x = resolutions[res][0], image_y = resolutions[res][1], payload_size = 80, experiment = exper_name, method = "JPEG-LS", quality = quality_, transmission = trans_type[0])
    ##     #asynch
    ##     exper_name = trans_type[1] + f"_res{res}_compr_JPEG-LS_qual_" + str(quality_)
    ##     run(image_x = resolutions[res][0], image_y = resolutions[res][1], payload_size = 80, experiment = exper_name, method = "JPEG-LS", quality = quality_, transmission = trans_type[1])


    #test which jpeg is the best
    # for quality_ in range(65, 25, -10):
    #     exper_name = trans_type[0] + f"_res{res}_compr_JPEG_qual_" + str(quality_)
    #     run(image_x = resolutions[res][0], image_y = resolutions[res][1], payload_size = 80, experiment = exper_name, method = "JPEG", quality = quality_, transmission = trans_type[0])

    #     exper_name = trans_type[0] + f"_res{res}_compr_JPEG-2000_qual_" + str(quality_)
    #     run(image_x = resolutions[res][0], image_y = resolutions[res][1], payload_size = 80, experiment = exper_name, method = "JPEG-2000", quality = quality_, transmission = trans_type[0])

    # quality_ = 55
    # exper_name = trans_type[0] + f"_res{res}_compr_JPEG-LS_qual_" + str(quality_)
    # run(image_x = resolutions[res][0], image_y = resolutions[res][1], payload_size = 80, experiment = exper_name, method = "JPEG-LS", quality = quality_, transmission = trans_type[0])

    # quality_ = 35
    # exper_name = trans_type[0] + f"_res{res}_compr_JPEG-2000_qual_" + str(quality_)
    # run(image_x = resolutions[res][0], image_y = resolutions[res][1], payload_size = 80, experiment = exper_name, method = "JPEG-2000", quality = quality_, transmission = trans_type[0])
