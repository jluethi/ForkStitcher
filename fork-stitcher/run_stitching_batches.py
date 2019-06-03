import logging
from pathlib import Path

from stitch_MAPS_annotations import Stitcher

def main():
    # Paths
    base_path = '/Volumes/staff/zmbstaff/7831/Raw_Data/Group Lopes/Sebastian/Projects/'
    # base_path = 'Z:\\zmbstaff\\7831\\Raw_Data\\Group Lopes\\Sebastian\\Projects\\'
    project_name = '8330_siNeg_CPT_3rd'
    # project_name = '8330_siXRCC3_CPT_3rd_2ul'
    # project_name = '8384_1_siRad51C_CPT_3rd'

    csv_folder = 'annotation_csv'
    output_folder = 'stitchedForks'

    # TODO: Make logging work on Windows and with multiprocessing
    # Logging
    logging.basicConfig(filename=Path(base_path) / project_name / (project_name + '.log'), level=logging.INFO,
                        format='%(asctime)s %(message)s')
    logging.info('Processing experiment {}'.format(project_name))

    # Parameters
    batch_size = 5
    stitch_threshold = 1000
    highmag_layer = 'highmag'
    eight_bit = True
    max_processes = 6

    # Parse and save the metadata
    stitcher = Stitcher(base_path, project_name, csv_folder, output_folder)
    stitcher.parse_create_csv_batches(batch_size=batch_size, highmag_layer=highmag_layer)
    stitcher.manage_batches(stitch_threshold, eight_bit, max_processes=max_processes)
    stitcher.combine_csvs()

if __name__ == "__main__":
    main()



