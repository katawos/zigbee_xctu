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
from skimage.metrics import peak_signal_noise_ratio as psnr
from skimage import img_as_ubyte
#from skimage.metrics import mse
import jpeg_ls
import os
import shutil

# TODO: Replace with the serial port where your local module is connected to.
PORT = "COM4"
#MAC: ___5A, no sticker (left)

# TODO: Replace with the baud rate of your local module.
BAUD_RATE = 115200

device = None

payload_list = []
bool_start_gathering = False
bool_get_params = False
image_x = None
image_y = None

experiment_sub_name = None
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
experiment_name = ""

method = None
payload_bytes_sent = 0

#check if folder "out" exists, if not - create one
if (not os.path.exists("out")):
    os.mkdir("out")

file = open("out//test.txt", "a+")
write_out_data = ""


def move_files():
    global experiment_name
    global file

    print(f"End of experiment: {experiment_name}")

    file.close()
    extensions = [".jpg", ".txt"]

    source_dir = os.getcwd()    #get current working directory X
    out_folder_path = os.path.join(source_dir, "out")   #X\out
    out_folder_dest_path = os.path.join(out_folder_path, experiment_name)   #X\out\experiment
    os.mkdir(out_folder_dest_path)  #create folder
    
    # Loop through all files in the source directory
    for filename in os.listdir(out_folder_path):
        for extension in extensions:
            # Check if the file has the specified extension
            if filename.endswith(extension):
                # Construct the full file path
                file_path = os.path.join(out_folder_path, filename)
                
                # Move the file to the destination directory
                shutil.move(file_path, out_folder_dest_path)

    file = open("out//test.txt", "a+")


def save_image(payload_list):
    global image_x
    global image_y
    global experiment_reconstruction_time_start
    global experiment_reconstruction_time_end
    global file
    global write_out_data
    global transmission
    global comparison_image
    global original_image_name
    global method
    global diff_map
    global payload_bytes_sent
    experiment_reconstruction_time_start = datetime.now() 

    arr = []
    #flatten payload list by adding each element separately
    for idx in range(len(payload_list)):
        arr += payload_list[idx]

    # convert list to np array of bytes
    np_arr = np.array(arr, dtype = np.uint8)

    try:
        #decode data to ndarray (n-dimensional array)
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

            #change 0 255 data to -255 +255, int16 and add diff
            cv2.imwrite(f"out//diff_{experiment_sub_name}_map.jpg", image)
            ssim_map = np.int16(image) * 2 - 255

            image_1_original = cv2.imread(original_image_name)
            image_1_original = np.int16(image_1_original)
            image_2_after_map = image_1_original + ssim_map

            # image_2_after_map = image_2_after_map - np.min(image_2_after_map)
            # image_2_after_map = image_2_after_map / np.max(image_2_after_map) * 255

            #cut values that goes over 255, change type to uint8 (jpg compatible)
            image_2_after_map = np.clip(image_2_after_map, 0, 255)
            image_2_after_map = np.uint8(image_2_after_map)

            # ENHANCEMENTS HERE OR ABOVE
            cv2.imwrite(f"out//diff_{experiment_sub_name}_image_2_after_map.jpg", image_2_after_map)

            #CLAHE - adaptive histogram equalization, additional contrast limiting          
            # create a CLAHE object, conversion BGR -> LAB -> BGR
            # https://stackoverflow.com/questions/25008458/how-to-apply-clahe-on-rgb-color-images
            # lab = cv2.cvtColor(image_2_after_map, cv2.COLOR_BGR2LAB)
            # #set the threshold limiting the contrast and tile size
            # clahe = cv2.createCLAHE(clipLimit=2.0,tileGridSize=(2,2))
            # #0 to 'L' channel, 1 to 'a' channel, and 2 to 'b' channel
            # lab[:,:,0] = clahe.apply(lab[:,:,0])
            # image_2_after_map = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)
            
            # cv2.imwrite(f"out//diff_{experiment}_image_2_after_map_ssim_CLAHE.jpg", image_2_after_map)

            
            experiment_reconstruction_time_end = datetime.now()
            diff_time = experiment_reconstruction_time_end - experiment_reconstruction_time_start
            if (image_2_name != ""):
                original_image_2 = cv2.imread(image_2_name)
                MSE = np.sum((original_image_2.astype("float") - image_2_after_map.astype("float")) ** 2) 
                MSE /= float(original_image_2.shape[0] * image_2_after_map.shape[1])

                original_img_2_gray = cv2.cvtColor(original_image_2, cv2.COLOR_BGR2GRAY)
                img_2_after_map_gray = cv2.cvtColor(image_2_after_map, cv2.COLOR_BGR2GRAY)
                SSIM, diff = ssim(original_img_2_gray, img_2_after_map_gray, full=True)
                # diff can be above 1 for some reason
                diff = np.clip(diff, 0, 1)
                diff = img_as_ubyte(diff)
                cv2.imwrite(f"out//diff_{experiment_sub_name}_image_2_after_map_ssim.jpg", diff)
                
                psnr_float = psnr(original_image_2, image_2_after_map)

                write_out_data += f', "tr": "{diff_time}", "MSE": {MSE:04f}, "SSIM": {SSIM:04f}, "PSNR": {psnr_float:04f}, "payload_bytes_sent": {payload_bytes_sent}, "payload_bytes_received": {len(np_arr)}' + "}\n"
            else:    
                write_out_data += f', "tr": "{diff_time}", "MSE": 0, "SSIM": 0, "PSNR": 0, "payload_bytes_sent": {payload_bytes_sent}, "payload_bytes_received": {len(np_arr)}' + "}\n"
        else:
            experiment_reconstruction_time_end = datetime.now()
            diff_time = experiment_reconstruction_time_end - experiment_reconstruction_time_start
            if (original_image_name != ""):
                originalImage = cv2.imread(original_image_name)
                # MSE - Mean Squared Error
                #converts to float (proper arithmetic operations)
                MSE = np.sum((originalImage.astype("float") - image.astype("float")) ** 2) 
                #normalize
                MSE /= float(originalImage.shape[0] * image.shape[1])

                #READY FUNCTION, TO BE CHANGED
                #originalImage = img_as_float(originalImage)
                #image = img_as_float(image)
                #MSE = mse(originalImage, image)
                
                # SSIM - Structural Similarity Index Measure
                original_gray = cv2.cvtColor(originalImage, cv2.COLOR_BGR2GRAY)
                img_gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
                SSIM, diff = ssim(original_gray, img_gray, full=True)

                psnr_float = psnr(originalImage, image)

                write_out_data += f', "tr": "{diff_time}", "MSE": {MSE:04f}, "SSIM": {SSIM:04f}, "PSNR": {psnr_float:04f}, "payload_bytes_sent": {payload_bytes_sent}, "payload_bytes_received": {len(np_arr)}' + "}\n"
            else:    
                write_out_data += f', "tr": "{diff_time}", "MSE": 0, "SSIM": 0, "PSNR": 0, "payload_bytes_sent": {payload_bytes_sent}, "payload_bytes_received": {len(np_arr)}' + "}\n"

        print(write_out_data)
        file.write(write_out_data)
        file.flush()
        write_out_data = ""
        image_name = f'received_image_{experiment_sub_name}.jpg'

        if (original_image_name == ""):
            original_image_name = "out//" + image_name

        cv2.imwrite("out//" + image_name, image)
    
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
    global experiment_sub_name
    global experiment_transmission_time_start
    global experiment_transmission_time_end
    global write_out_data
    global transmission
    global prev_packet_num
    global payload_size
    global comparison_image
    global original_image_name
    global method
    global diff_map
    global experiment_name
    global payload_bytes_sent
    global device
    received_data = list(xbee_message.data)

    if (bool_get_params == True):
        string = f"{xbee_message.data.decode('utf-8')}"
        string_list = string.split(",")
        image_x = int(string_list[0])
        image_y = int(string_list[1])
        payload_size = int(string_list[2])
        method = string_list[3]
        experiment_sub_name = string_list[4]
        transmission = string_list[5]
        comparison_image = string_list[6]
        diff_map = string_list[7]
        payload_bytes_sent = int(string_list[8])
        to_coord = string_list[9]
        to_recv = string_list[10]

        if (to_recv != "None"):
            if (int(to_recv) == 0):
                device.set_parameter("TO", b"\x00")
            elif (int(to_recv) == 1):
                device.set_parameter("TO", b"\x01")
            print("payload Parameter TO: ", device.get_parameter("TO"))
        
        if (comparison_image == "True"):
            original_image_name = ""
        
        write_out_data += "{" + f'"X": {image_x}, "Y": {image_y}, "PayloadSize": {payload_size}, "Method": "{method}", "Experiment": "{experiment_sub_name}", "transmission": "{transmission}", "to_coord":{to_coord}, "to_recv":{to_recv}'
        bool_start_gathering = True
        bool_get_params = False
        return

    if (received_data == [101, 110, 100]):  # END
        diff_time = experiment_transmission_time_end - experiment_transmission_time_start
        write_out_data += f', "t": "{diff_time}"'
        device.set_parameter("TO", b"\x00")
        print("end Parameter TO: ", device.get_parameter("TO"))
        # print("stop gathering")
        bool_start_gathering = False
        save_image(payload_list)
    
    if (bool_start_gathering == True):
        if (experiment_transmission_time_start is None):
            experiment_transmission_time_start = datetime.now()
        payload_list.append(received_data)
        experiment_transmission_time_end = datetime.now()

    if (received_data == [115, 116, 97, 114, 116]): # START
        print("start gathering")
        device.set_parameter("TO", b"\x00")
        print("start Parameter TO: ", device.get_parameter("TO"))
        write_out_data = ""
        bool_get_params = True
        experiment_transmission_time_start = None
        payload_list = []

    if (received_data[0:4] == [101, 110, 100, 50]):  # END2
        string = f"{xbee_message.data.decode('utf-8')}"
        string_list = string.split(",")
        experiment_name = string_list[1]
        move_files()

def run():
    global device
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

        #does not block the application, adds user defined callback
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