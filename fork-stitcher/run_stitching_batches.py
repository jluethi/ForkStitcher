import logging
import logging.config
from pathlib import Path
import multiprocessing
# logging.basicConfig(level=logging.DEBUG)
from stitch_MAPS_annotations import Stitcher
from sites_of_interest_parser import MapsXmlParser

# TODO: Write a command line parsing to input the parameters and run the stitcher
def main():
    # Paths
    # base_path = '/Volumes/staff/zmbstaff/7831/Raw_Data/Group Lopes/Sebastian/Projects/'
    # project_name = '8330_siXRCC3_CPT_3rd_2ul'
    base_path = 'Z:\\zmbstaff\\7831\\Raw_Data\\Group Lopes\\Sebastian\\Projects\\'
    # project_name = '8330_siXRCC3_CPT_3rd_2ul'
    project_name = '8373_2_siLuc_HU_3rd'
    # project_name = '7831_0.1M-NaCl_BND'
    # base_path = '/Volumes/staff/zmbstaff/8377/Raw_Data'
    # project_name = '8377'
    # highmag_layer = 'Array Tile Set 001'

    csv_folder = 'annotation_test'
    output_folder = 'stitchedForks_forkTiles'

    # TODO: Make logging work on Windows and with multiprocessing
    # Logging
    # logging.basicConfig(filename=str(Path(base_path) / project_name / (project_name + '.log')), level=logging.INFO,
    #                     format='%(asctime)s %(message)s') # handlers=[logging.FileHandler(Path(base_path) / project_name / (project_name + '_test.log')), logging.StreamHandler()]
    # logger = logging.getLogger(__name__)
    # #
    # # # Create file logging handler
    # logger_filename = str(Path(base_path) / project_name / (project_name + '.log'))
    # fh = logging.FileHandler(logger_filename)
    # fh.setLevel(logging.INFO)
    # logger.addHandler(fh)
    # #
    # # # Create console logging handler
    # ch = logging.StreamHandler()
    # ch.setLevel(logging.INFO)
    # logger.addHandler(ch)
    # logger.info('Processing experiment {}'.format(project_name))
    logger_filename = str(Path(base_path) / project_name / (project_name + '.log'))
    logger = MapsXmlParser.create_logger(logger_filename)
    logger.info('Processing experiment {}'.format(project_name))

    # Parameters
    batch_size = 5
    stitch_threshold = 2000
    highmag_layer = 'highmag'
    eight_bit = True
    max_processes = 1
    show_arrow = True
    enhance_contrast = True

    # classifier_csv = '/Volumes/staff/zmbstaff/7831/Raw_Data/Group Lopes/Sebastian/joel/forks_only.csv'

    # Parse and save the metadata
    stitcher = Stitcher(base_path, project_name, csv_folder, output_folder)
    stitcher.parse_create_csv_batches(batch_size=batch_size, highmag_layer=highmag_layer)
    # stitcher.parse_create_classifier_csv_batches(batch_size=batch_size, classifier_csv_path=classifier_csv,
    #                                              highmag_layer=highmag_layer)
    # stitcher.manage_batches(stitch_threshold, eight_bit, show_arrow=show_arrow, max_processes=max_processes,
    #                         enhance_contrast=enhance_contrast)
    # stitcher.combine_csvs(delete_batches=False, to_excel=True)


if __name__ == "__main__":
    main()
