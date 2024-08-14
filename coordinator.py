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
#from skimage.metrics import structural_similarity as ssim
from skimage import io, img_as_ubyte, img_as_float

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
    img_name = 'before_JPEG-2000_image.jp2'
    #save image to the one with the new name and given JPEG compression ratio
    cv2.imwrite(img_name, image, [int(cv2.IMWRITE_JPEG2000_COMPRESSION_X1000), quality])  # Compression ratio ranges from 0 to 1000
    return img_name


def compressJPEG_LS(image, quality):
    print("Im compressing JPEG-LS")
    image = cv2.imread(image)
    quality = int(((100 - quality) / 100) * 255)    #ranges from 0 to 255
    img_name = 'before_JPEG-LS_image.jls'
    data_buffer = jpeg_ls.encode(image, quality)

    f = open(img_name, "wb")    #write in binary format
    f.write(data_buffer.tobytes())  #write binary dara to file
    f.close()
    return img_name


def diff_images(img1, img2):
    img1_float = img_as_float(img1)
    img2_float = img_as_float(img2)
    diff = img2_float - img1_float

    #conditional substraction eg. when more detailed image is substracted from less detailed one
    # if np.mean(img1) > np.mean(img2):
    #     diff = img1_float - img2_float
    # else:
    #     diff = img2_float - img1_float
    return diff


#def divide_to_payload(array, _payload_size, seq_bytes, parameters):
def divide_to_payload(array, _payload_size, parameters):
    arr = []
    count = 0
    #array = image size in array, _payload_size = size of image part that can be send at a time 
    for i in range(0, len(array), _payload_size):
        new_arr = []

        # ... CUT HERE ...

        #slice array to include elements from i to (i+payload_size-seq)
        new_arr += array[i:i + _payload_size]
        arr.append(new_arr)
        count += 1

    #pattern for data array
    arr.insert(0, "start")
    arr.insert(1, parameters)
    arr.append("end")
    return arr


def loadImage(img_name = "test.jpg"):
    # open test image
    img = cv2.imread(img_name)
    #cv2.imshow("test image", img)
    #cv2.waitKey()
    # Shape will give (row, column) where row = y, column = x
    print(img.shape)

    return img


def modifyImage(_img, image_x, image_y, method = None, quality = None):

    functions = {
        "JPEG": compressJPEG,
        "JPEG-2000": compressJPEG2000,
        "JPEG-LS": compressJPEG_LS
    }
    
    #resize
    img = cv2.resize(_img, (image_x, image_y))
    # gray_img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)  #for grayscale
    #print(img.shape)

    #rename and save as new image
    img_name = 'before_image.jpg'

    #conversion from float to byte (to save it as image, but it loses the color depth)
    if (img.dtype.name == "float64"):
        convert = img + 1
        convert = convert/2
        # convert = convert - np.max(convert) + 1
        cv2.imwrite(img_name, img_as_ubyte(convert))
    else:
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
                #additional
                #data_idx += 1
                dataSendFails += 1

                if (dataSendFails >= dataSendMaxFails):
                    print("Max send fails are reached. Lost connection to device")
                    sys.exit(1)

    finally:
        if device is not None and device.is_open():
            device.close()

        # Important after doing job wait a little so that receiver can recover from reconstruction.
        # Without this it may be possible that callbacks are overlapping
        time.sleep(2)


def SendPerfectImage(img_name, image_resolution): #send image to reliably compare and calculate transmission errors (original, synch, no compression)
    run(img_name, image_x = resolutions[image_resolution][0], image_y = resolutions[image_resolution][1], payload_size = 80, experiment = f"original_{image_resolution}_image_save", method = None, transmission="synch", transmission_sleep=0.014, comparison_image=True)


def run(img_name, image_x, image_y, payload_size, experiment, method = None, quality = None, transmission = "synch", transmission_sleep = 0.014, comparison_image = False, diff_map = False):
    img = loadImage(img_name)
    mod_img_1d = modifyImage(img, image_x, image_y, method, quality)

   #... CUT HERE ...

    data_payloads = divide_to_payload(mod_img_1d, payload_size, f"{image_x},{image_y},{payload_size},{method},{experiment},{transmission},{comparison_image},{diff_map}")
    data_size = len(data_payloads)

    XbeeSend(data_payloads, data_size, transmission, transmission_sleep)

def run_diff(image_x, image_y, payload_size, experiment, method = None, quality = None, transmission = "synch", transmission_sleep = 0.014, comparison_image = False, diff_map = False):
    img1_name_first_frame = "test-2-car.jpg"
    img2_name_second_frame = "test-1-car.jpg"
    
    # img2 - img1 => car1 - car2
    img1 = loadImage(img_name = img1_name_first_frame)    #test1.jpg
    img2 = loadImage(img_name = img2_name_second_frame)    #test2.jpg
    diff_img = diff_images(img1, img2)  #animal2 - animal1 = OK, 1-2 float out of range
    mod_img_1d = modifyImage(diff_img, image_x, image_y, method, quality)

    #SendPerfectImage
    run(img2_name_second_frame, image_x = image_x, image_y = image_y, payload_size = 80, experiment = f"original_{image_x}x{image_y}_image_save_2", method = None, transmission="synch", transmission_sleep=0.014, comparison_image=True, diff_map = False)
    run(img1_name_first_frame, image_x = image_x, image_y = image_y, payload_size = 80, experiment = f"original_{image_x}x{image_y}_image_save_1", method = None, transmission="synch", transmission_sleep=0.014, comparison_image=True, diff_map = False)


    # ... CUT HERE ...

    data_payloads = divide_to_payload(mod_img_1d, payload_size, f"{image_x},{image_y},{payload_size},{method},{experiment},{transmission},{comparison_image},{diff_map}")
    data_size = len(data_payloads)

    XbeeSend(data_payloads, data_size, transmission, transmission_sleep)

if __name__ == '__main__':

    resolutions = {
        # "144p": [192, 144],
        # "240p": [320, 240],
        # "480p": [640, 480],
        # "720p": [1280, 720],
        "1080p": [1920, 1080]
    }

    #TESTS
    #for resolution ___p
    res = "1080p"
    #transmission type-like
    trans_type = ["synch", "asynch"]
    #img_name = "test.jpg"
    img_name = "test.jpg"
    

    # #diff test: with compression method, its quality for async
    # exper_name = trans_type[1] + f"_res{res}_diff-TEST"
    # #synch
    # run_diff(image_x = resolutions[res][0], image_y = resolutions[res][1], payload_size = 80, experiment = exper_name, method = None, quality = None, transmission = trans_type[0], diff_map = True)
    # #asynch
    # run_diff(image_x = resolutions[res][0], image_y = resolutions[res][1], payload_size = 80, experiment = exper_name, method = None, quality = None, transmission = trans_type[1], diff_map = True)


    # # (1) Payload test
    # SendPerfectImage(img_name, res)
    # for payload_bytes in range(85, 110, 5): # (40, 260, 5)
    #     # #synch
    #     # exper_name = trans_type[0] + f"_res{res}_payload_{payload_bytes}"
    #     # run(img_name, image_x = resolutions[res][0], image_y = resolutions[res][1], payload_size = payload_bytes, experiment = exper_name, method = None, transmission = trans_type[0])
    #     #asynch
    #     exper_name = trans_type[1] + f"_res{res}_payload_{payload_bytes}"
    #     run(img_name, image_x = resolutions[res][0], image_y = resolutions[res][1], payload_size = payload_bytes, experiment = exper_name, method = None, transmission = trans_type[1])

    
    # # (2) asynch transmission sleep test from 5 to 20 ms
    # SendPerfectImage(img_name, res)
    # for idx in range(5, 21):
    #     sleep_time = idx / 1000
    #     #asynch
    #     exper_name = trans_type[1] + f"_res{res}_sleep_{sleep_time}"
    #     run(img_name, image_x = resolutions[res][0], image_y = resolutions[res][1], payload_size = 80, experiment = exper_name, method = None, transmission = trans_type[1], transmission_sleep = sleep_time)
    #     time.sleep(5)

    # # (3) Resolution test - not needed now?
    # for key in resolutions.keys():  #go through each of resolutions names (key pairs)
    #     SendPerfectImage(img_name, key)
    #     #synch
    #     exper_name = trans_type[0] + f"_resolution_{key}"
    #     run(img_name, image_x = resolutions[key][0], image_y = resolutions[key][1], payload_size = 80, experiment = exper_name, method = None, transmission = trans_type[0])
    #     #asynch
    #     exper_name = trans_type[1] + f"_resolution_{key}"
    #     run(img_name, image_x = resolutions[key][0], image_y = resolutions[key][1], payload_size = 80, experiment = exper_name, method = None, transmission = trans_type[1], transmission_sleep=0.014)


    # # (4) Sleep and payload asynch
    # SendPerfectImage(img_name, res)
    # for idx in range(12, 16):
    #     sleep_time = idx / 1000
    #     for payload_bytes in range(40, 255, 5):
    #         exper_name = trans_type[1] + f"_res{res}_payload_{payload_bytes}_sleep_{sleep_time}"
    #         run(img_name, image_x = resolutions[res][0], image_y = resolutions[res][1], payload_size = payload_bytes, experiment = exper_name, method = None, transmission = trans_type[1], transmission_sleep = sleep_time)


    # (5) Compression methods
    SendPerfectImage(img_name, res)
    # JPEG - THE BEST COMPRESSION TO QUALITY RATIO
    for quality_ in range(55, 25, -10):
    #quality_ = 80
        #synch
        exper_name = trans_type[0] + f"_res{res}_compr_JPEG_qual_" + str(quality_)
        run(img_name, image_x = resolutions[res][0], image_y = resolutions[res][1], payload_size = 80, experiment = exper_name, method = "JPEG", quality = quality_, transmission = trans_type[0])
        #asynch
        exper_name = trans_type[1] + f"_res{res}_compr_JPEG_qual_" + str(quality_)
        run(img_name, image_x = resolutions[res][0], image_y = resolutions[res][1], payload_size = 80, experiment = exper_name, method = "JPEG", quality = quality_, transmission = trans_type[1])

    # # # JPEG 2000
    # for quality_ in range(80, 20, -40):
    # #quality_ = 240
    #     #synch str(quality_)
    #     run(img_name, image_x = resolutions[res][0], image_y = resolutions[res][1], payload_size = 80, experiment = exper_name, method = "JPEG-2000", quality = quality_, transmission = trans_type[0])
    #     #asynch
    #     exper_name = trans_type[1] + f"_res{res}_compr_JPEG-2000_qual_" + str(quality_)
    #     run(img_name, image_x = resolutions[res][0], image_y = resolutions[res][1], payload_size = 80, experiment = exper_name, method = "JPEG-2000", quality = quality_, transmission = trans_type[1])

    # ## # JPEG LS
    # for quality_ in range(95, 25, -10):
    #     #synch
    #     exper_name = trans_type[0] + f"_res{res}_compr_JPEG-LS_qual_" + str(quality_)
    #     run(img_name, image_x = resolutions[res][0], image_y = resolutions[res][1], payload_size = 80, experiment = exper_name, method = "JPEG-LS", quality = quality_, transmission = trans_type[0])
    #     #asynch
    #     exper_name = trans_type[1] + f"_res{res}_compr_JPEG-LS_qual_" + str(quality_)
    #     run(img_name, image_x = resolutions[res][0], image_y = resolutions[res][1], payload_size = 80, experiment = exper_name, method = "JPEG-LS", quality = quality_, transmission = trans_type[1])

    #     exper_name = trans_type[0] + f"_res{res}_compr_JPEG-2000_qual_" +