# Script that stitches a set of 3x3 images together using OpenCV
# DOESN'T WORK. OpenCV Stitcher doesn't find enough corresponding features in EM images

import cv2 as cv
import sys
import os

# Center filename: Name of the tile in the center, to be stitched
center_filename = 'Tile_018-011-000000_0-000.tif'
image_path = '/Users/Joel/Desktop/stitching_images/'
output_filename = '/Users/Joel/Desktop/test_stitch.png'

mode = cv.Stitcher_PANORAMA
# mode = cv.Stitcher_SCANS

filenames = ['Tile_018-010-000000_0-000.tif', center_filename] #'Tile_018-012-000000_0-000.tif'

imgs = []

for img_name in filenames:
    img = cv.imread(os.path.join(image_path, img_name))
    if img is None:
        print("can't read image " + img_name)
        sys.exit(-1)

    imgs.append(img)

stitcher = cv.Stitcher.create(mode)
status, pano = stitcher.stitch(imgs)

if status != cv.Stitcher_OK:
    print("Can't stitch images, error code = %d" % status)
    sys.exit(-1)

cv.imwrite(output_filename, pano)
print("stitching completed successfully. %s saved!" % output_filename)


