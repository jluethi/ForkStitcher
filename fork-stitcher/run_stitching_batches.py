import os
import subprocess
import logging
from pathlib import Path
import re
from multiprocessing import Pool

def main():
    csv_base_path = 'Z:\\zmbstaff\\7831\\Raw_Data\\Group Lopes\\Sebastian\\Projects\\8330_siXRCC3_CPT_3rd_2ul\\annotation_csv\\'
    items = os.listdir(csv_base_path)
    nb_files = len(items)

    while nb_files > 0:

        try:
            args = ['python', 'stitch_MAPS_annotations.py']
            subprocess.Popen(args)

        except:
            pass


        items = os.listdir(csv_base_path)
        nb_files = len(items)

if __name__ == "__main__":
    main()



