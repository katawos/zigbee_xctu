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
#import pandas as pd
#from PIL import Image
import jpeg_ls
from skimage import img_as_ubyte, img_as_float



# TODO: Replace with the serial port where your local module is connected to.
PORT = "COM3"
#MAC: ___FC (right, sticker "2")

# TODO: Replace with the baud rate of your local module.
BAUD_RATE = 115200

DATA_TO_SEND = "Hello XBee!"
REMOTE_NODE_ID = "sensor" #REMOTE


def setParameters(device):
    #set command TO = 0 => MAC ACK and retries, TO = 1 => no MAC ACK, no retries
    device.set_parameter("TO", b"\x00")
    print(f"MAC ACK and retries, TO: {device.get_parameter('TO')}")

    #set Tx Power Level => 0 - lowest, 1 - low, 2 - medium, 3 - high, 4 - highest
    device.set_parameter("PL", b"\x04")
    print(f"Tx Power Level: {device.get_parameter('PL')}")

    #set API Mode => 1 - no escapes, 2 - escaped
    device.set_parameter("AP", b"\x01")
    print(f"API Mode: {device.get_parameter('AP')}")


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

#conversion from float to byte (to save it as image, but it loses the color depth), difference between images
def diff_images(img1, img2):
    img1_float = img_as_float(img1)
    img2_float = img_as_float(img2)
    diff = img2_float - img1_float
    return diff


def divide_to_payload(array, _payload_size, parameters):
    arr = []
    count = 0
    #array = image size in array, _payload_size = size of image part that can be send at a time 
    for i in range(0, len(array), _payload_size):
        new_arr = []

        #slice array to include elements from i to (i+payload_size)
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


    if (img.dtype.name == "float64"):
        convert = img + 1
        convert = convert/2
        cv2.imwrite(img_name, img_as_ubyte(convert))
    else:
        cv2.imwrite(img_name, img)

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
                #set transmission parameters: TO, PL, AP
                setParameters(device)
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
                        #send data Synchronously - wait for the packet response (FrameID = 1, APS ACK)
                        device.send_data(remote_device, bytearray(data_payloads[data_idx])) 
                    elif (transmission == "asynch"):
                        if (firstAsynch == True):
                            time.sleep(transmission_sleep) 
                            firstAsynch = False
                        #send data Asynchronously - do not wait for data response (FrameID = 0, no APS ACK)
                        device.send_data_async(remote_device, bytearray(data_payloads[data_idx]))
                        #time.sleep() slows down sending the packets to: reduce number of dropped packets, avoid collisions and help control data rate
                        time.sleep(transmission_sleep)
                else:
                    device.send_data(remote_device, data_payloads[data_idx])    #for string data type, like "end"
                print("Success")
                data_idx += 1
            except Exception as e:
                print(e)

                #Testing command TO, ignore lost packet, send next
                #data_idx += 1

                dataSendFails += 1

                if (dataSendFails >= dataSendMaxFails):
                    print("Max send fails are reached. Lost connection to device")
                    sys.exit(1)

    finally:
        if device is not None and device.is_open():
            device.close()

        # Important after doing job wait a little so that receiver can recover from reconstruction.
        # Without this it may be possible that callbacks are overlapping (especially for higher resolutions)
        time.sleep(2)


def SendPerfectImage(img_name, image_resolution): #send image to reliably compare and calculate transmission errors (original, synch, no compression)
    run(img_name, image_x = resolutions[image_resolution][0], image_y = resolutions[image_resolution][1], payload_size = 84, experiment = f"original_{image_resolution}_image_save", method = None, transmission="synch", transmission_sleep=0.014, comparison_image=True)


def run(img_name, image_x, image_y, payload_size, experiment, method = None, quality = None, transmission = "synch", transmission_sleep = 0.014, comparison_image = False, diff_map = False):
    img = loadImage(img_name)
    mod_img_1d = modifyImage(img, image_x, image_y, method, quality)

    data_payloads = divide_to_payload(mod_img_1d, payload_size, f"{image_x},{image_y},{payload_size},{method},{experiment},{transmission},{comparison_image},{diff_map}")
    data_size = len(data_payloads)

    XbeeSend(data_payloads, data_size, transmission, transmission_sleep)


def run_diff(image_x, image_y, payload_size, experiment, method = None, quality = None, transmission = "synch", transmission_sleep = 0.014, comparison_image = False, diff_map = False):
    img1_name_first_frame = "goose_1.jpg"
    img2_name_second_frame = "goose_2.jpg"
    
    # img2 - img1 => car2 - car1
    img1 = loadImage(img_name = img1_name_first_frame)
    img2 = loadImage(img_name = img2_name_second_frame)
    diff_img = diff_images(img1, img2)
    mod_img_1d = modifyImage(diff_img, image_x, image_y, method, quality)

    #SendPerfectImage
    run(img2_name_second_frame, image_x = image_x, image_y = image_y, payload_size = 84, experiment = f"original_{image_x}x{image_y}_image_save_2", method = None, transmission="synch", transmission_sleep=0.014, comparison_image=True, diff_map = False)
    run(img1_name_first_frame, image_x = image_x, image_y = image_y, payload_size = 84, experiment = f"original_{image_x}x{image_y}_image_save_1", method = None, transmission="synch", transmission_sleep=0.014, comparison_image=True, diff_map = False)

    data_payloads = divide_to_payload(mod_img_1d, payload_size, f"{image_x},{image_y},{payload_size},{method},{experiment},{transmission},{comparison_image},{diff_map}")
    data_size = len(data_payloads)

    XbeeSend(data_payloads, data_size, transmission, transmission_sleep)

if __name__ == '__main__':

    resolutions = {
        "144p": [192, 144],
        "240p": [320, 240],
        "480p": [640, 480],
        "720p": [1280, 720],
        "1080p": [1920, 1080]
    }

    res = "480p"                 #resolution
    trans_type = ["synch", "asynch"]    #transmission type-like
    img_name = "test.jpg"               #test image name
    

    # # diff test: with compression method, its quality for async
    # exper_name = trans_type[0] + f"_res{res}_diff-TEST"
    # #synch
    # run_diff(image_x = resolutions[res][0], image_y = resolutions[res][1], payload_size = 84, experiment = exper_name, method = None, quality = None, transmission = trans_type[0], diff_map = True)
    #asynch
    # exper_name = trans_type[1] + f"_res{res}_diffTest_ducks"
    # run_diff(image_x = resolutions[res][0], image_y = resolutions[res][1], payload_size = 84, experiment = exper_name, method = None, quality = None, transmission = trans_type[1], diff_map = True)
    #asynch JPEG quality=35 diff images
    # exper_name = trans_type[1] + f"_API2_res{res}_JPEG_diff-TEST-Close"
    # run_diff(image_x = resolutions[res][0], image_y = resolutions[res][1], payload_size = 84, experiment = exper_name, method = "JPEG", quality = 35, transmission = trans_type[1], diff_map = True)


    # # (1) Payload test
    # SendPerfectImage(img_name, res)
    # for payload_bytes in range(70, 88, 2):
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
    #     run(img_name, image_x = resolutions[res][0], image_y = resolutions[res][1], payload_size = 84, experiment = exper_name, method = None, transmission = trans_type[1], transmission_sleep = sleep_time)

    # # (3) Resolution test - not needed now
    # for key in resolutions.keys():  #go through each of resolutions names (key pairs)
    #     SendPerfectImage(img_name, key)
    #     # #synch
    #     # exper_name = trans_type[0] + f"_resolution_{key}"
    #     # run(img_name, image_x = resolutions[key][0], image_y = resolutions[key][1], payload_size = 84, experiment = exper_name, method = None, transmission = trans_type[0])
    #     #asynch
    #     exper_name = trans_type[1] + f"_resolution_{key}"
    #     run(img_name, image_x = resolutions[key][0], image_y = resolutions[key][1], payload_size = 84, experiment = exper_name, method = None, transmission = trans_type[1], transmission_sleep=0.014)


    # # (4) Sleep and payload asynch - two at once
    # SendPerfectImage(img_name, res)
    # for idx in range(12, 18):
    #     sleep_time = idx / 1000
    #     for payload_bytes in range(80, 86, 2):
    #         exper_name = trans_type[1] + f"_res{res}_payload_{payload_bytes}_sleep_{sleep_time}"
    #         run(img_name, image_x = resolutions[res][0], image_y = resolutions[res][1], payload_size = payload_bytes, experiment = exper_name, method = None, transmission = trans_type[1], transmission_sleep = sleep_time)


    # # (5) Compression methods
    # SendPerfectImage(img_name, res)
    # # JPEG - THE BEST COMPRESSION OF SIZE TO QUALITY OF IMAGE RATIO
    # res ="480p"
    # for quality_ in range(95, 25, -10):
    #     # #synch
    #     # exper_name = trans_type[0] + f"_res{res}_compr_JPEG_qual_" + str(quality_)
    #     # run(img_name, image_x = resolutions[res][0], image_y = resolutions[res][1], payload_size = 84, experiment = exper_name, method = "JPEG", quality = quality_, transmission = trans_type[0])
    #     #asynch
    #     exper_name = trans_type[1] + f"_res{res}_compr_JPEG_qual_" + str(quality_)
    #     run(img_name, image_x = resolutions[res][0], image_y = resolutions[res][1], payload_size = 84, experiment = exper_name, method = "JPEG", quality = quality_, transmission = trans_type[1])

    # # JPEG 2000
    # for quality_ in range(360, 20, -40):
    #     #synch str(quality_)
    #     run(img_name, image_x = resolutions[res][0], image_y = resolutions[res][1], payload_size = 84, experiment = exper_name, method = "JPEG-2000", quality = quality_, transmission = trans_type[0])
    #     #asynch
    #     exper_name = trans_type[1] + f"_res{res}_compr_JPEG-2000_qual_" + str(quality_)
    #     run(img_name, image_x = resolutions[res][0], image_y = resolutions[res][1], payload_size = 84, experiment = exper_name, method = "JPEG-2000", quality = quality_, transmission = trans_type[1])

    # # JPEG LS
    # for quality_ in range(95, 25, -10):
    #     #synch
    #     exper_name = trans_type[0] + f"_res{res}_compr_JPEG-LS_qual_" + str(quality_)
    #     run(img_name, image_x = resolutions[res][0], image_y = resolutions[res][1], payload_size = 84, experiment = exper_name, method = "JPEG-LS", quality = quality_, transmission = trans_type[0])
    #     #asynch
    #     exper_name = trans_type[1] + f"_res{res}_compr_JPEG-LS_qual_" + str(quality_)
    #     run(img_name, image_x = resolutions[res][0], image_y = resolutions[res][1], payload_size = 84, experiment = exper_name, method = "JPEG-LS", quality = quality_, transmission = trans_type[1])



    #-------------------------------
    # #quick transmission test
    # SendPerfectImage(img_name, res)
    # #asynch
    # res = "240p"
    # quality_ = 35
    # exper_name = f"QUICK_" + trans_type[1] + f"_res{res}_compr_JPEG_qual_" + str(quality_)
    # run(img_name, image_x = resolutions[res][0], image_y = resolutions[res][1], payload_size = 84, experiment = exper_name, method = "JPEG", quality = quality_, transmission = trans_type[1])
