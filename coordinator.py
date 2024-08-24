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
import datetime
import sys
import numpy as np
import cv2
#import pandas as pd
#from PIL import Image
import jpeg_ls

# TODO: Replace with the serial port where your local module is connected to.
PORT = "COM3"
#MAC: ___FC (right, sticker "2")

# TODO: Replace with the baud rate of your local module.
BAUD_RATE = 115200

DATA_TO_SEND = "Hello XBee!"
REMOTE_NODE_ID = "sensor" #REMOTE

RESOLUTIONS = {
    "144p": [192, 144],
    "240p": [320, 240],
    "480p": [640, 480],
    "720p": [1280, 720],
    "1080p": [1920, 1080]
}

COMPRESS_METHODS = ["JPEG","JPEG-2000","JPEG-LS"]

TRANSMISSION_TYPE = ["synch", "asynch"]


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
    #print("Im compressing JPEG")
    image = cv2.imread(image_name)
    img_name = 'before_JPEG_image.jpg'
    #save image to the one with the new name and given JPEG quality
    cv2.imwrite(img_name, image, [int(cv2.IMWRITE_JPEG_QUALITY), quality])  # Quality ranges from 0 to 100
    return img_name


def compressJPEG2000(image_name, quality):
    #print("Im compressing JPEG-2000")
    image = cv2.imread(image_name)
    img_name = 'before_JPEG-2000_image.jp2'
    #save image to the one with the new name and given JPEG compression ratio
    cv2.imwrite(img_name, image, [int(cv2.IMWRITE_JPEG2000_COMPRESSION_X1000), quality])  # Compression ratio ranges from 0 to 1000
    return img_name


def compressJPEG_LS(image, quality):
    #print("Im compressing JPEG-LS")
    image = cv2.imread(image)
    quality = int(((100 - quality) / 100) * 255)    #ranges from 0 to 255
    img_name = 'before_JPEG-LS_image.jls'
    data_buffer = jpeg_ls.encode(image, quality)

    f = open(img_name, "wb")    #write in binary format
    f.write(data_buffer.tobytes())  #write binary dara to file
    f.close()
    return img_name

# substract images as int - value after conversion to int16 is the same 
# it allows for negative values after substraction, int8 <-128,127> is too small
# value after conversion back to uint8 -> only halfs are rounded down
def diff_images(img1, img2):
    diff = np.int16(img2) - np.int16(img1)  #range of values <-255,255>
    diff = diff + 255                       #range <0,510>
    diff = diff / 2                         #range <0,255>
    diff = np.uint8(diff)                   #conversion to proper type (JPEG compatible)
    #cv2.imwrite("diff.jpg", diff)
    return diff


def divide_to_payload(array, _payload_size, parameters):
    arr = []
    #count = 0
    #array = image size in array, _payload_size = size of image part that can be send at a time 
    for i in range(0, len(array), _payload_size):
        new_arr = []

        #slice array to include elements from i to (i+payload_size)
        new_arr += array[i:i + _payload_size]
        arr.append(new_arr)
        #count += 1

    #pattern for data array
    arr.insert(0, "start")
    arr.insert(1, parameters)
    arr.append("end")
    return arr


def loadImage(img_name = "test.jpg"):
    # open test image
    img = cv2.imread("original_images//" + img_name)
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

    cv2.imwrite(img_name, img)

    if (method is not None):
        img_name = functions[method](img_name, quality) #use compression method with given quality parameter

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
                        #time.sleep() slows down sending the packets to: reduce number of dropped packets
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

def SendExperimentFinish(experiment_name):
    arr = []
    arr.append(f"end2,{experiment_name}")
    print(arr)
    XbeeSend(arr, len(arr), transmission="synch")

def SendPerfectImage(img_name, image_resolution): #send image to reliably compare and calculate transmission errors (original, synch, no compression)
    run(img_name, RESOLUTIONS[image_resolution], payload_size = 84, experiment_sub_name = f"original_{image_resolution}_image_save", method = None, transmission="synch", transmission_sleep=0.014, comparison_image=True)


def run(img_name, resolution, payload_size, experiment_sub_name, method = None, quality = None, transmission = "synch", transmission_sleep = 0.014, comparison_image = False, diff_map = False):
    image_x = resolution[0]
    image_y = resolution[1]
    
    img = loadImage(img_name)
    mod_img_1d = modifyImage(img, image_x, image_y, method, quality)

    data_payloads = divide_to_payload(mod_img_1d, payload_size, f"{image_x},{image_y},{payload_size},{method},{experiment_sub_name},{transmission},{comparison_image},{diff_map},{len(mod_img_1d)}")
    data_size = len(data_payloads)

    XbeeSend(data_payloads, data_size, transmission, transmission_sleep)


def run_diff(img_names, resolution, payload_size, experiment_sub_name, method = None, quality = None, transmission = "synch", transmission_sleep = 0.014, comparison_image = False, diff_map = False):
    image_x = resolution[0]
    image_y = resolution[1]
    
    img1_name_first_frame = img_names[0]
    img2_name_second_frame = img_names[1]
    
    # img2 - img1 => goose_2 - goose_1
    img1 = loadImage(img_name = img1_name_first_frame)
    img2 = loadImage(img_name = img2_name_second_frame)
    #resize, then calculate diff
    img1 = cv2.resize(img1, (image_x, image_y))
    img2 = cv2.resize(img2, (image_x, image_y))
    diff_img = diff_images(img1, img2)
    mod_img_1d = modifyImage(diff_img, image_x, image_y, method, quality)

    #SendPerfectImage
    run(img2_name_second_frame, resolution, payload_size = 84, experiment_sub_name = f"original_{image_x}x{image_y}_image_save_2", method = None, transmission="synch", transmission_sleep=0.014, comparison_image=True, diff_map = False)
    run(img1_name_first_frame, resolution, payload_size = 84, experiment_sub_name = f"original_{image_x}x{image_y}_image_save_1", method = None, transmission="synch", transmission_sleep=0.014, comparison_image=True, diff_map = False)

    data_payloads = divide_to_payload(mod_img_1d, payload_size, f"{image_x},{image_y},{payload_size},{method},{experiment_sub_name},{transmission},{comparison_image},{diff_map},{len(mod_img_1d)}")
    data_size = len(data_payloads)

    XbeeSend(data_payloads, data_size, transmission, transmission_sleep)

# ----------------- EXPERIMENTS METHODS ------------------------
def createExperimentName(experiment_name):
    """Creates full experiment name with datetime

    Args:
      experiment_name: normal string explaining experiment

    Returns:
        experiment_name_full: full experiment name with appended datetime
    """
    now = datetime.datetime.now()
    dt = now.strftime("%Y-%m-%d_%H-%M-%S")
    experiment_name_full = f"{experiment_name}_{dt}"

    return experiment_name_full

def test_diff_with_compr(experiment_name, img_names):
    """Performs diff tests with compression method. First and second frames are send and then difference. Measurement takes place in receiver.

    Args:
      experiment_name: name of experiment
      img_name: image full name
    """
    # diff test: with compression method, its quality for async
    
    res = "144p" 
    # synch
    exper_sub_name = TRANSMISSION_TYPE[0] + f"_res{res}_diffTest_ducks"
    run_diff(img_names = img_names, resolution= RESOLUTIONS[res], payload_size = 84, experiment_sub_name = exper_sub_name, method = None, quality = None, transmission = TRANSMISSION_TYPE[0], diff_map = True)
    #synch JPEG quality=35 diff images
    exper_sub_name = TRANSMISSION_TYPE[0] + f"_res{res}_diffTest_JPEG-35"
    run_diff(img_names = img_names, resolution= RESOLUTIONS[res], payload_size = 84, experiment_sub_name = exper_sub_name, method = "JPEG", quality = 35, transmission = TRANSMISSION_TYPE[0], diff_map = True)
    #synch JPEG quality=55 diff images
    exper_sub_name = TRANSMISSION_TYPE[0] + f"_res{res}_diffTest_JPEG-55"
    run_diff(img_names = img_names, resolution= RESOLUTIONS[res], payload_size = 84, experiment_sub_name = exper_sub_name, method = "JPEG", quality = 55, transmission = TRANSMISSION_TYPE[0], diff_map = True)

    # asynch
    exper_sub_name = TRANSMISSION_TYPE[1] + f"_res{res}_diffTest_ducks"
    run_diff(img_names = img_names, resolution= RESOLUTIONS[res], payload_size = 84, experiment_sub_name = exper_sub_name, method = None, quality = None, transmission = TRANSMISSION_TYPE[1], diff_map = True)
    #asynch JPEG quality=35 diff images
    exper_sub_name = TRANSMISSION_TYPE[1] + f"_res{res}_diffTest_JPEG-35"
    run_diff(img_names = img_names, resolution= RESOLUTIONS[res], payload_size = 84, experiment_sub_name = exper_sub_name, method = "JPEG", quality = 35, transmission = TRANSMISSION_TYPE[1], diff_map = True)
    #asynch JPEG quality=55 diff
    exper_sub_name = TRANSMISSION_TYPE[1] + f"_res{res}_diffTest_JPEG-55"
    run_diff(img_names = img_names, resolution= RESOLUTIONS[res], payload_size = 84, experiment_sub_name = exper_sub_name, method = "JPEG", quality = 55, transmission = TRANSMISSION_TYPE[1], diff_map = True)
    
    # Send status to receiver that experiment was finished and to create new folder under "experiment_name" and datetime name
    SendExperimentFinish(experiment_name=createExperimentName(experiment_name))

def test_jpeg_vs_jpeg2k(experiment_name, img_name):
    """Performs comparison between JPEG and JPEG2k compressions

    Args:
      experiment_name: name of experiment
      img_name: image full name
    """

    res = "144p"
    SendPerfectImage(img_name, res)
    exper_sub_name = TRANSMISSION_TYPE[0] + f"_res{res}_compr_JPEG_qual_" + str(35)
    run(img_name, resolution=RESOLUTIONS[res], payload_size = 84, experiment_sub_name = exper_sub_name, method = "JPEG", quality = 35, transmission = TRANSMISSION_TYPE[0])
    exper_sub_name = TRANSMISSION_TYPE[0] + f"_res{res}_compr_JPEG2k_qual_" + str(90)
    run(img_name, resolution=RESOLUTIONS[res], payload_size = 84, experiment_sub_name = exper_sub_name, method = "JPEG-2000", quality = 90, transmission = TRANSMISSION_TYPE[0])

    # res = "480p"
    # SendPerfectImage(img_name, res)
    # exper_sub_name = TRANSMISSION_TYPE[0] + f"_res{res}_compr_JPEG_qual_" + str(35)
    # run(img_name, resolution=RESOLUTIONS[res], payload_size = 84, experiment_sub_name = exper_sub_name, method = "JPEG", quality = 35, transmission = TRANSMISSION_TYPE[0])
    # exper_sub_name = TRANSMISSION_TYPE[0] + f"_res{res}_compr_JPEG2k_qual_" + str(90)
    # run(img_name, resolution=RESOLUTIONS[res], payload_size = 84, experiment_sub_name = exper_sub_name, method = "JPEG-2000", quality = 90, transmission = TRANSMISSION_TYPE[0])
    
    # Send status to receiver that experiment was finished and to create new folder under "experiment_name" and datetime name
    SendExperimentFinish(experiment_name=createExperimentName(experiment_name))

def test_payload(experiment_name, img_name, res, parameters):
    """Performs payload tests, coordinator sends hardoded sequence

    Args:
      experiment_name: name of experiment
      img_name: image full name
      res: resolution for image scaling
      parameters: (start, stop, iter) - for payload bytes tests
    """
    SendPerfectImage(img_name, res)

    for payload_bytes in range(parameters["start"], parameters["stop"], parameters["iter"]):
        # synch
        exper_sub_name = TRANSMISSION_TYPE[0] + f"_res{res}_payload_{payload_bytes}"
        run(img_name, resolution=RESOLUTIONS[res], payload_size = payload_bytes, experiment_sub_name = exper_sub_name, method = None, transmission = TRANSMISSION_TYPE[0])
        # asynch
        exper_sub_name = TRANSMISSION_TYPE[1] + f"_res{res}_payload_{payload_bytes}"
        run(img_name, resolution=RESOLUTIONS[res], payload_size = payload_bytes, experiment_sub_name = exper_sub_name, method = None, transmission = TRANSMISSION_TYPE[1])

    # Send status to receiver that experiment was finished and to create new folder under "experiment_name" and datetime name
    SendExperimentFinish(experiment_name=createExperimentName(experiment_name))


def test_asynch_trans(experiment_name, img_name, res):
    """Performs payload tests, coordinator sends hardoded sequence

    Args:
      experiment_name: name of experiment
      img_name: image full name
      res: resolution for image scaling
    """

    SendPerfectImage(img_name, res)
    for idx in range(5, 21):
        sleep_time = idx / 1000
        #asynch
        exper_sub_name = TRANSMISSION_TYPE[1] + f"_res{res}_sleep_{sleep_time}"
        run(img_name, resolution=RESOLUTIONS[res], payload_size = 84, experiment_sub_name = exper_sub_name, method = None, transmission = TRANSMISSION_TYPE[1], transmission_sleep = sleep_time)


    # Send status to receiver that experiment was finished and to create new folder under "experiment_name" and datetime name
    SendExperimentFinish(experiment_name=createExperimentName(experiment_name))    

def test_resolution(experiment_name, img_name, res):
    """Performs resolution tests, coordinator sends hardoded sequence.

    Args:
      experiment_name: name of experiment
      img_name: image full name
      res: resolution for image scaling
    """

    SendPerfectImage(img_name, res)
    #synch
    exper_sub_name = TRANSMISSION_TYPE[0] + f"_resolution_{res}"
    run(img_name, resolution=RESOLUTIONS[res], payload_size = 84, experiment_sub_name = exper_sub_name, method = None, transmission = TRANSMISSION_TYPE[0])
    #synch JPEG quality=35 diff images
    exper_sub_name = TRANSMISSION_TYPE[0] + f"_resolution_{res}_JPEG-35"
    run(img_name, resolution=RESOLUTIONS[res], payload_size = 84, experiment_sub_name = exper_sub_name, method = "JPEG", quality = 35, transmission = TRANSMISSION_TYPE[0])
    #synch JPEG quality=55 diff images
    exper_sub_name = TRANSMISSION_TYPE[0] + f"_resolution_{res}_JPEG-55"
    run(img_name, resolution=RESOLUTIONS[res], payload_size = 84, experiment_sub_name = exper_sub_name, method = "JPEG", quality = 55, transmission = TRANSMISSION_TYPE[0])

    #asynch
    exper_sub_name = TRANSMISSION_TYPE[1] + f"_resolution_{res}"
    run(img_name, resolution=RESOLUTIONS[res], payload_size = 84, experiment_sub_name = exper_sub_name, method = None, transmission = TRANSMISSION_TYPE[1], transmission_sleep=0.014)
    #asynch JPEG quality=35 diff images
    exper_sub_name = TRANSMISSION_TYPE[1] + f"_resolution_{res}_JPEG-35"
    run(img_name, resolution=RESOLUTIONS[res], payload_size = 84, experiment_sub_name = exper_sub_name, method = "JPEG", quality = 35, transmission = TRANSMISSION_TYPE[1])
    #asynch JPEG quality=55 diff images
    exper_sub_name = TRANSMISSION_TYPE[1] + f"_resolution_{res}_JPEG-55"
    run(img_name, resolution=RESOLUTIONS[res], payload_size = 84, experiment_sub_name = exper_sub_name, method = "JPEG", quality = 55, transmission = TRANSMISSION_TYPE[1])

    # Send status to receiver that experiment was finished and to create new folder under "experiment_name" and datetime name
    SendExperimentFinish(experiment_name=createExperimentName(experiment_name))


def test_sleep_payload_async(experiment_name, img_name, res, parameters):
    """Performs payload tests, coordinator sends hardoded sequence

    Args:
      experiment_name: name of experiment
      img_name: image full name
      res: resolution for image scaling
      parameters: (sleepTimeStart, sleepTimeStop, sleepTimeIter, payloadStart, PayloadStop, PayloadIter) - for payload bytes tests
    """

    SendPerfectImage(img_name, res)
    for idx in range(parameters["sleepTimeStart"], parameters["sleepTimeStop"], parameters["sleepTimeIter"]):
        sleep_time = idx / 1000
        for payload_bytes in range(parameters["payloadStart"], parameters["payloadStop"], parameters["PayloadIter"]):
            exper_sub_name = TRANSMISSION_TYPE[1] + f"_res{res}_payload_{payload_bytes}_sleep_{sleep_time}"
            run(img_name, RESOLUTIONS[res], payload_size = payload_bytes, experiment_sub_name = exper_sub_name, method = None, transmission = TRANSMISSION_TYPE[1], transmission_sleep = sleep_time)

    # Send status to receiver that experiment was finished and to create new folder under "experiment_name" and datetime name
    SendExperimentFinish(experiment_name=createExperimentName(experiment_name))

def test_compression(experiment_name, img_name, res):
    """Performs compression tests for JPEG, JPEG2k, JPEGLS. Coordinator sends hardoded sequence

    Args:
      experiment_name: name of experiment
      img_name: image full name
      res: resolution for image scaling
    """

    SendPerfectImage(img_name, res)
    # JPEG - THE BEST COMPRESSION OF SIZE TO QUALITY OF IMAGE RATIO
    #res ="480p"
    for quality_ in range(95, 25, -10):
        #synch
        exper_sub_name = TRANSMISSION_TYPE[0] + f"_res{res}_compr_JPEG_qual_" + str(quality_)
        run(img_name, RESOLUTIONS[res], payload_size = 84, experiment_sub_name = exper_sub_name, method = "JPEG", quality = quality_, transmission = TRANSMISSION_TYPE[0])
        #asynch
        exper_sub_name = TRANSMISSION_TYPE[1] + f"_res{res}_compr_JPEG_qual_" + str(quality_)
        run(img_name, RESOLUTIONS[res], payload_size = 84, experiment_sub_name = exper_sub_name, method = "JPEG", quality = quality_, transmission = TRANSMISSION_TYPE[1])

    # JPEG 2000
    for quality_ in range(360, 20, -40):
        #synch str(quality_)
        run(img_name, RESOLUTIONS[res], payload_size = 84, experiment_sub_name = exper_sub_name, method = "JPEG-2000", quality = quality_, transmission = TRANSMISSION_TYPE[0])
        #asynch
        exper_sub_name = TRANSMISSION_TYPE[1] + f"_res{res}_compr_JPEG-2000_qual_" + str(quality_)
        run(img_name, RESOLUTIONS[res], payload_size = 84, experiment_sub_name = exper_sub_name, method = "JPEG-2000", quality = quality_, transmission = TRANSMISSION_TYPE[1])

    # JPEG LS
    for quality_ in range(95, 25, -10):
        #synch
        exper_sub_name = TRANSMISSION_TYPE[0] + f"_res{res}_compr_JPEG-LS_qual_" + str(quality_)
        run(img_name, RESOLUTIONS[res], payload_size = 84, experiment_sub_name = exper_sub_name, method = "JPEG-LS", quality = quality_, transmission = TRANSMISSION_TYPE[0])
        #asynch
        exper_sub_name = TRANSMISSION_TYPE[1] + f"_res{res}_compr_JPEG-LS_qual_" + str(quality_)
        run(img_name, RESOLUTIONS[res], payload_size = 84, experiment_sub_name = exper_sub_name, method = "JPEG-LS", quality = quality_, transmission = TRANSMISSION_TYPE[1])

    # Send status to receiver that experiment was finished and to create new folder under "experiment_name" and datetime name
    SendExperimentFinish(experiment_name=createExperimentName(experiment_name))

def test_function_template(experiment_name, img_name):
    """Performs payload tests, coordinator sends hardoded sequence

    Args:
      experiment_name: name of experiment
      img_name: image full name
    """

    # PLACE FOR EXPERIMENTS

    # Send status to receiver that experiment was finished and to create new folder under "experiment_name" and datetime name
    SendExperimentFinish(experiment_name=createExperimentName(experiment_name))

if __name__ == '__main__':
    img_name = "test.jpg"               #test image name

    img_names_first_second_frame = ["goose_1.jpg", "goose_2.jpg"]
    # (1) diff test
    # test_diff_with_compr("diff_with_compr_test", img_names_first_second_frame)

    # (2) JPEG vs JPEG2000
    # test_jpeg_vs_jpeg2k("jpeg_jpeg2k_compr", img_name)

    # (1) Payload test
    parameters = {
        "start": 70,
        "stop": 86,
        "iter": 2
    }
    # test_payload("payload_test", img_name, res = "144p", parameters = parameters)

    # (2) asynch transmission sleep test from 5 to 20 ms
    test_asynch_trans("asynch_transmission_sleep_2_20_ms", img_name, res = "144p")

    # (3) Resolution test 
    # test_resolution("resolution_test_144p", img_name, res="144p")

    # (4) Sleep and payload asynch - two at once (narrow range)
    parameters = {
        "sleepTimeStart": 12,
        "sleepTimeStop": 18,
        "sleepTimeIter": 1,
        "payloadStart": 80,
        "payloadStop": 86,
        "PayloadIter": 2
    }
    # test_sleep_payload_async("sleep_payload_async_test", img_name, res="144p", parameters=parameters)

    # (5) Compression methods
    # test_compression("compr_JPEG_JPEG2k_JPEG-LS", img_name, res="144p")