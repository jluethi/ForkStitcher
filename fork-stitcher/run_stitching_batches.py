import os
import logging
from pathlib import Path
import re
from multiprocessing import Pool

import imagej

import sites_of_interest_parser
import stitch_MAPS_annotations

# ij = imagej.init('/Applications/Fiji.app')
ij = imagej.init('C:\\Program Files\\Fiji')

# Headers of the categorization & the measurements for forks. Values filled in by users afterwards
base_header = ['Linear DNA', 'Loop', 'Crossing', 'Other False Positive', 'Missing Link Fork',
               'fork symetric', 'fork asymetric', 'reversed fork symetric', 'reversed fork asymetric',
               'size reversed fork (nm)', 'dsDNA RF', 'internal ssDNA RF', 'ssDNA end RF',
               'total ssDNA RF	gaps',
               'gaps', 'sister	gaps', 'parental', 'size gaps (nm)', 'junction ssDNA size (nm)',
               'hemicatenane', 'termination intermediate', 'bubble', 'hemireplicated bubble',
               'comments', 'list for reversed forks (nt)', 'list for gaps (nt)',
               'list for ssDNA at junction (nt)']


def stitch_batch(annotation_csv, output_path, pixel_size, stitch_radius):
    annotation_tiles_loaded = sites_of_interest_parser.load_annotations_from_csv(base_header, annotation_csv)
    stitched_annotation_tiles = stitch_MAPS_annotations.stitch_annotated_tiles(annotation_tiles=annotation_tiles_loaded,
                                                                               output_path=output_path,
                                                                               pixel_size=pixel_size, ij=ij,
                                                                               stitch_radius=stitch_radius,
                                                                               eight_bit=True)

    csv_stitched_path = annotation_csv[:-4] + '_stitched.csv'

    sites_of_interest_parser.save_annotation_tiles_to_csv(stitched_annotation_tiles, base_header, csv_stitched_path)
    os.remove(annotation_csv)


def main():
    # Variables that change
    base_path = '/Volumes/staff/zmbstaff/7831/Raw_Data/Group Lopes/Sebastian/Projects/'
    # base_path = 'Z:\\zmbstaff\\7831\\Raw_Data\\Group Lopes\\Sebastian\\Projects\\'
    # project_name = '8330_siNeg_CPT_3rd'
    project_name = '8330_siXRCC3_CPT_3rd_2ul'
    # project_name = '8373_3_siXRCC3_HU_1st_y1'

    # Constant variables
    highmag_layer = 'highmag'
    stitch_radius = 1

    # Set logging & paths
    project_folder_path = os.path.join(base_path, project_name)
    logging.basicConfig(filename=Path(base_path) / project_name / (project_name + '_2.log'), level=logging.INFO,
                        format='%(asctime)s %(message)s')
    logging.info('Processing experiment {}'.format(project_name))

    # Make folders for stitched Forks
    output_folder = 'stitchedForks'
    output_path = Path(project_folder_path) / Path(output_folder)
    # Check if a folder for the stitched forks already exists. If not, create that folder
    os.makedirs(str(output_path), exist_ok=True)

    csv_folder = 'annotation_csv'
    csv_base_path = Path(project_folder_path) / csv_folder
    os.makedirs(str(csv_base_path), exist_ok=True)

    parser = sites_of_interest_parser.MapsXmlParser(project_folder=project_folder_path, use_unregistered_pos=True,
                                                    name_of_highmag_layer=highmag_layer, stitch_radius=stitch_radius)

    # Populate annotation_csv_list by looking at csv files in directory
    items = os.listdir(csv_base_path)
    annotation_csv_list = []
    regex = re.compile('_annotations_\d+\.csv')
    for name in items:
        if regex.search(name):
            annotation_csv_list.append(csv_base_path / name)

    max_processes = 1
    with Pool(processes=max_processes) as pool:
        for annotation_csv in annotation_csv_list:
            pool.apply_async(stitch_batch, args=(annotation_csv, output_path, parser.pixel_size, stitch_radius, ))

        pool.close()
        pool.join()


    # TODO: Fuse the csv files of the stitched forks into a single csv file


if __name__ == "__main__":
    main()



