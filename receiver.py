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
from skimage.metrics import structural_similarity as ssim
from skimage import io, img_as_ubyte, img_as_float
#from skimage.metrics import mse
import jpeg_ls

# TODO: Replace with the serial port where your local module is connected to.
PORT = "COM4"
#MAC: ___5A, no sticker (left)

# TODO: Replace with the baud rate of your local module.
BAUD_RATE = 115200

payload_list = []
bool_start_gathering = False
bool_get_params = False
image_x = None
image_y = None

experiment = None
experiment_transmission_time_start = None
experiment_transmission_time_end = None
experiment_reconstruction_time_start = None
experiment_reconstruction_time_end = None
transmission = ""
sequence_bytes = 0
prev_packet_num = -1
payload_size = None
comparison_image = False
original_image_name = ""
method = None

#output file
file = open("16bitAddressingColor_receive_buffer.txt", "a+")
write_out_data = ""

def save_image(payload_list):
    global image_x
    global image_y
    global experiment_reconstruction_time_start
    global experiment_reconstruction_time_end
    global file
    global write_out_data
    global experiment
    global transmission
    global sequence_bytes
    global comparison_image
    global original_image_name
    global method
    global diff_map
    arr = []

    experiment_reconstruction_time_start = datetime.now() 

    if (transmission == "synch"):
        #flatten payload list by adding each element separately
        for idx in range(len(payload_list)):
            arr += payload_list[idx]

    elif(transmission == "asynch"):
        prev_packet_num = -1
        for payload in payload_list:
            packet_num_list = payload[0][0:sequence_bytes]
            # print(payload[0][0:sequence_bytes], end="")
            byte_data = bytes(packet_num_list)
            packet_num = int.from_bytes(byte_data, 'big')

            diff = packet_num - prev_packet_num

            for _ in range(0, diff - 1):
                # fill with zeros all missing parts
                arr += np.zeros(len(payload[0]) - sequence_bytes).tolist()

            # add to arr rest of the payload
            arr += payload[0][sequence_bytes:]

            prev_packet_num = packet_num

    np_arr = np.array(arr, dtype = np.uint8)
    # Shape takes (row, column) where row = y, column = x

    try:
        if (method == "None"):
            image = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
        elif (method == "JPEG"):
            image = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
        elif (method == "JPEG-2000"):
            image = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
        elif (method == "JPEG-LS"):
            image = jpeg_ls.decode(np_arr)
        
        if (diff_map == "True"):
            image_2_name = original_image_name[:-6] + "_2.jpg"

            ssim_map = img_as_float(image) * 2 - 1

            image_2_after_map = img_as_float(cv2.imread(original_image_name)) + ssim_map
            image_2_after_map = image_2_after_map - np.min(image_2_after_map)
            image_2_after_map = image_2_after_map / np.max(image_2_after_map)
            # image_2_after_map = np.clip(image_2_after_map, 0, 1)

            # ENHANCEMENTS HERE OR BELOW
            image_2_after_map = img_as_ubyte(image_2_after_map)
            cv2.imwrite(f"diff_{experiment}_image_2_after_map.jpg", image_2_after_map)

            

            # DECODE HERE IF METHOD IS USED FOR FASTER DATA TRANSFER
            experiment_reconstruction_time_end = datetime.now()
            diff_time = experiment_reconstruction_time_end - experiment_reconstruction_time_start
            if (image_2_name != ""):
                image_2 = cv2.imread(image_2_name)
                MSE = np.sum((image_2.astype("float") - image_2_after_map.astype("float")) ** 2) 
                MSE /= float(image_2.shape[0] * image_2_after_map.shape[1])
                img_2_gray = cv2.cvtColor(image_2, cv2.COLOR_BGR2GRAY)
                img_2_after_map_gray = cv2.cvtColor(image_2_after_map, cv2.COLOR_BGR2GRAY)
                SSIM, diff = ssim(img_2_gray, img_2_after_map_gray, full=True)
                cv2.imwrite(f"diff_{experiment}_image_2_after_map_ssim.jpg", img_as_ubyte(diff))

                write_out_data += f', "tr": "{diff_time}", "MSE": {MSE}, "SSIM": {SSIM}' + "}\n"
            else:    
                write_out_data += f', "tr": "{diff_time}", "MSE": X, "SSIM": X' + "}\n"
        else:
            # DECODE HERE IF METHOD IS USED FOR FASTER DATA TRANSFER
            experiment_reconstruction_time_end = datetime.now()
            diff_time = experiment_reconstruction_time_end - experiment_reconstruction_time_start
            if (original_image_name != ""):
                originalImage = cv2.imread(original_image_name)
                # MSE - Mean Squared Error (for absolute diff between pixel values)
                #converts to float (proper arithmetic operations), squared differences and sum of them
                MSE = np.sum((originalImage.astype("float") - image.astype("float")) ** 2) 
                #normalize by number of pixels - divide by (rows0 * columns1)
                MSE /= float(originalImage.shape[0] * image.shape[1])

                #READY FUNCTION, TO BE CHANGED
                #originalImage = img_as_float(originalImage)
                #image = img_as_float(image)
                #MSE = mse(originalImage, image)
                
                # SSIM - Structural Similarity Index Measure (changes in structural information, contrast)
                #modify images to grayscale
                original_gray = cv2.cvtColor(originalImage, cv2.COLOR_BGR2GRAY)
                img_gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
                SSIM, diff = ssim(original_gray, img_gray, full=True)

                # #diff image
                # cv2.imshow("diff_image", diff)
                # cv2.waitKey()
                # Convert to allow for saving
                cv2.imwrite(f"diff_image_{experiment}.jpg", diff)

                write_out_data += f', "tr": "{diff_time}", "MSE": {MSE}, "SSIM": {SSIM}' + "}\n"
            else:    
                write_out_data += f', "tr": "{diff_time}", "MSE": X, "SSIM": X' + "}\n"

        print(write_out_data)
        file.write(write_out_data)
        file.flush()
        write_out_data = ""
        image_name = f'received_image_{experiment}.jpg'

        if (original_image_name == ""):
            original_image_name = image_name

        cv2.imwrite(image_name, image)
    
    except Exception as e:
        print(f"Broken\n{e}")
        write_out_data += f', "tr": "broken"' + "}\n"
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
    global experiment
    global experiment_transmission_time_start
    global experiment_transmission_time_end
    global write_out_data
    global transmission
    global sequence_bytes
    global prev_packet_num
    global payload_size
    global comparison_image
    global original_image_name
    global method
    global diff_map
    received_data = list(xbee_message.data)

    if (bool_get_params == True):
        string = f"{xbee_message.data.decode('utf-8')}"
        string_list = string.split(",")
        image_x = int(string_list[0])
        image_y = int(string_list[1])
        payload_size = int(string_list[2])
        method = string_list[3]
        experiment = string_list[4]
        transmission = string_list[5]
        sequence_bytes = int(string_list[6])
        comparison_image = string_list[7]
        diff_map = string_list[8]
        if (comparison_image == "True"):
            original_image_name = ""
        write_out_data += "{" + f'"X": {image_x}, "Y": {image_y}, "PayloadSize": {payload_size}, "Method": "{method}", "Experiment": "{experiment}", "transmission": "{transmission}", "seq_bytes": {sequence_bytes}'
        bool_start_gathering = True
        bool_get_params = False
        experiment_transmission_time_start = datetime.now()
        return

    if (received_data == [101, 110, 100]):  # END
        diff_time = experiment_transmission_time_end - experiment_transmission_time_start
        write_out_data += f', "t": "{diff_time}"'
        # print("stop gathering")
        bool_start_gathering = False
        save_image(payload_list)
    
    if (bool_start_gathering == True):
        if (transmission == "synch"):
            payload_list.append(received_data) 
        elif (transmission == "asynch"):
            payload_list.append([received_data])
        experiment_transmission_time_end = datetime.now()

    if (received_data == [115, 116, 97, 114, 116]): # START
        print("start gathering")
        write_out_data = ""
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
                print(device.get_parameter("TO"))
                device.set_parameter("TO", b"\x00")
                print(device.get_parameter("TO"))
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