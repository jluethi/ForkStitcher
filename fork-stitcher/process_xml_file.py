import os
import logging
from pathlib import Path
from multiprocessing import Pool

import sites_of_interest_parser
import stitch_MAPS_annotations

# Headers of the categorization & the measurements for forks. Values filled in by users afterwards
base_header = ['Linear DNA', 'Loop', 'Crossing', 'Other False Positive', 'Missing Link Fork',
               'fork symetric', 'fork asymetric', 'reversed fork symetric', 'reversed fork asymetric',
               'size reversed fork (nm)', 'dsDNA RF', 'internal ssDNA RF', 'ssDNA end RF',
               'total ssDNA RF	gaps',
               'gaps', 'sister	gaps', 'parental', 'size gaps (nm)', 'junction ssDNA size (nm)',
               'hemicatenane', 'termination intermediate', 'bubble', 'hemireplicated bubble',
               'comments', 'list for reversed forks (nt)', 'list for gaps (nt)',
               'list for ssDNA at junction (nt)']

def main():
    # Variables that change
    base_path = '/Volumes/staff/zmbstaff/7831/Raw_Data/Group Lopes/Sebastian/Projects/'
    # base_path = 'Z:\\zmbstaff\\7831\\Raw_Data\\Group Lopes\\Sebastian\\Projects\\'
    # project_name = '8330_siNeg_CPT_3rd'
    project_name = '8330_siXRCC3_CPT_3rd_2ul'
    # project_name = '8373_3_siXRCC3_HU_1st_y1'
    batch_size = 5

    # Constant variables
    highmag_layer = 'highmag'
    stitch_radius = 1

    # Set logging & paths
    project_folder_path = os.path.join(base_path, project_name)
    logging.basicConfig(filename=Path(base_path) / project_name / (project_name + '_2.log'), level=logging.INFO,
                        format='%(asctime)s %(message)s')
    logging.info('Processing experiment {}'.format(project_name))

    # Make folders for csv files
    csv_folder = 'annotation_csv'
    csv_base_path = Path(project_folder_path) / csv_folder
    os.makedirs(str(csv_base_path), exist_ok=True)

    csv_path = os.path.join(csv_base_path, project_name + '_annotations' + '.csv')

    parser = sites_of_interest_parser.MapsXmlParser(project_folder=project_folder_path, use_unregistered_pos=True,
                                                    name_of_highmag_layer=highmag_layer, stitch_radius=stitch_radius)
    annotation_tiles = parser.parse_xml()

    # Save annotations to csv file in batches
    annotation_csv_list = sites_of_interest_parser.save_annotation_tiles_to_csv(annotation_tiles, base_header=[],
                                                                                csv_path=csv_path,
                                                                                batch_size=batch_size)



if __name__ == "__main__":
    main()