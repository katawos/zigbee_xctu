import time
import datetime
import sys
import numpy as np
import cv2
import os
from skimage.metrics import structural_similarity as ssim
from skimage.metrics import peak_signal_noise_ratio as psnr
from skimage import img_as_ubyte

SRC_FOLDER = "original_images"
FOLDER_NAME = "test_2"

def loadImage(img_name = "test.jpg"):
    # open test image
    img = cv2.imread(img_name)
    #cv2.imshow("test image", img)
    #cv2.waitKey()
    # Shape will give (row, column) where row = y, column = x
    # print(img.shape)

    return img

def compressJPEG(image, quality, img_name = "compressed_street_1080p.jpg"):
    #print("Im compressing JPEG")
    img_name = f'{FOLDER_NAME}//{img_name}'
    #save image to the one with the new name and given JPEG quality
    cv2.imwrite(img_name, image, [int(cv2.IMWRITE_JPEG_QUALITY), quality])  # Quality ranges from 0 to 100
    return img_name

def compressJPEG2000(image, quality, img_name = "compressed_street_1080p.jpg"):
    #print("Im compressing JPEG-2000")
    img_name = f'{FOLDER_NAME}//{img_name}'
    #save image to the one with the new name and given JPEG compression ratio
    cv2.imwrite(img_name, image, [int(cv2.IMWRITE_JPEG2000_COMPRESSION_X1000), quality])  # Compression ratio ranges from 0 to 1000
    return img_name

def doubleResize(img, percentage, img_name = "new_street_double_resize.jpg"):
    x = img.shape[1]
    y = img.shape[0]
    img_25p = cv2.resize(img, (int(x * percentage), int(y * percentage)))
    new_img = cv2.resize(img_25p, (x, y))
    img_name = f"{FOLDER_NAME}//{img_name}"
    cv2.imwrite(img_name, new_img)
    return img_name

def returnImageSize(image_name):
    img_file = open(image_name, "rb") #open in binary read mode
    img_bytes = img_file.read() #read as byte string
    return len(img_bytes)

def checkSimilarity(img_name1, img_name2, diffmap_name = "diff_map.jpg"):
    img_1 = loadImage(img_name1)
    img_2 = loadImage(img_name2)

    MSE = np.sum((img_1.astype("float") - img_2.astype("float")) ** 2) 
    MSE /= float(img_1.shape[0] * img_2.shape[1])

    img_1_gray = cv2.cvtColor(img_1, cv2.COLOR_BGR2GRAY)
    img_2_gray = cv2.cvtColor(img_2, cv2.COLOR_BGR2GRAY)
    SSIM, diff = ssim(img_1_gray, img_2_gray, full=True)
    # diff can be above 1 for some reason
    diff = np.clip(diff, 0, 1)
    diff = img_as_ubyte(diff)
    cv2.imwrite(f"{FOLDER_NAME}//{diffmap_name}", diff)
    
    psnr_float = psnr(img_1, img_2)

    results = {
        "MSE": MSE,
        "SSIM": SSIM,
        "PSNR": psnr_float
    }

    return results

if __name__ == '__main__':

    if (not os.path.exists(FOLDER_NAME)):
        os.mkdir(FOLDER_NAME)

    # 1080p image
    img_name = f"{SRC_FOLDER}//street-1.jpg"            #test image name
    image = loadImage(img_name)
    print(f"Image shape: {image.shape}")

    f = open(f"{FOLDER_NAME}//test.txt", "w+")

    double_resized_img_name = doubleResize(image, 0.25, "street_double_resize.jpg")
    for quality in range(15, 0, -1):
        compressed_img_name = compressJPEG2000(image, quality, f"compressed_street_1080p_qual_{quality}.jp2")

        results = checkSimilarity(double_resized_img_name, compressed_img_name, f"diff_map_qual_{quality}.jpg")


        results_all = {
            "quality": quality
        }

        results_all.update(results)

        results_all.update({
            "double_resize_bytes": returnImageSize(double_resized_img_name),
            "compressed_bytes": returnImageSize(compressed_img_name)
        })

        print(results_all)
        f.write(str(results_all))








