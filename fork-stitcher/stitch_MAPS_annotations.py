import logging
from pathlib import Path
import re
import numpy as np

import sites_of_interest_parser as sip
import os

import imagej

# ij = imagej.init('/Applications/Fiji.app')
# ij = imagej.init('sc.fiji:fiji:2.0.0-pre-10+ch.fmi:faim-ij2-visiview-processing:0.0.1')

class Stitcher:
    def __init__(self, ij, highmag_layer, stitch_radius, base_path, project_name):
        self.ij = ij
        self.highmag_layer = highmag_layer
        self.stitch_radius = stitch_radius

        self.project_name = project_name
        self.project_folder_path = Path(base_path) / project_name
        output_folder = 'stitchedForks'
        self.output_path = Path(self.project_folder_path) / Path(output_folder)

        csv_folder = 'annotation_csv'
        self.csv_base_path = Path(self.project_folder_path) / csv_folder

        # Headers of the categorization & the measurements for forks. Values filled in by users afterwards
        self.base_header = ['Linear DNA', 'Loop', 'Crossing', 'Other False Positive', 'Missing Link Fork',
                            'fork symetric', 'fork asymetric', 'reversed fork symetric', 'reversed fork asymetric',
                            'size reversed fork (nm)', 'dsDNA RF', 'internal ssDNA RF', 'ssDNA end RF',
                            'total ssDNA RF	gaps', 'gaps', 'sister	gaps', 'parental', 'size gaps (nm)',
                            'junction ssDNA size (nm)', 'hemicatenane', 'termination intermediate', 'bubble',
                            'hemireplicated bubble', 'comments', 'list for reversed forks (nt)', 'list for gaps (nt)',
                            'list for ssDNA at junction (nt)',
                            ]

    def stitch_annotated_tiles(self, annotation_tiles: dict, stitch_threshold, eight_bit: bool = False):
        # This function takes the parser object containing all the information about the MAPS project and its annotations.
        # It performs the stitching.

        for annotation_name in annotation_tiles:
            number_existing_neighbor_tiles = sum(annotation_tiles[annotation_name]['surrounding_tile_exists'])
            # If the image files for the 8 neighbors and the tile exist, stitch the images
            if number_existing_neighbor_tiles == 9:
                logging.info('Stitching {}'.format(annotation_name))
                img_path = annotation_tiles[annotation_name]['img_path']

                # Uses lower level ImageJ APIs to do the stitching. Avoiding calling ImageJ1 plugins allows to use a maven
                # distribution of ImageJ and makes this parallelizable as no temporary files are written and read anymore.
                # See here: https://github.com/imagej/pyimagej/issues/35
                # https://forum.image.sc/t/using-imagej-functions-like-type-conversion-and-setting-pixel-size-via-pyimagej/25755/10

                from jnius import autoclass
                image_plus_class = autoclass('ij.ImagePlus')
                imps = []

                for neighbor in annotation_tiles[annotation_name]['surrounding_tile_names']:
                    print(neighbor)
                    imagej2_img = self.ij.io().open(str(img_path / neighbor))
                    imps.append(self.ij.convert().convert(imagej2_img, image_plus_class))

                java_imgs = self.ij.py.to_java(imps)
                # Define starting positions
                positions_jlist = self.ij.py.to_java([])
                positions_jlist.add([0.0, 0.0])
                positions_jlist.add([3686.0, 0.0])
                positions_jlist.add([7373.0, 0.0])
                positions_jlist.add([0.0, 3686.0])
                positions_jlist.add([3686.0, 3686.0])
                positions_jlist.add([7373.0, 3686.0])
                positions_jlist.add([0.0, 7373.0])
                positions_jlist.add([3686.0, 7373.0])
                positions_jlist.add([7373.0, 7373.0])
                original_positions = np.array(positions_jlist)

                dimensionality = 2
                compute_overlap = True
                StitchingUtils = autoclass('ch.fmi.visiview.StitchingUtils')
                models = StitchingUtils.computeStitching(java_imgs, positions_jlist, dimensionality, compute_overlap)

                # Get the information about how much the center image has been shifted, where the fork is placed in
                # the stitched image
                stitching_params = []
                for model in models:
                    params = [0.0] * 6
                    model.toArray(params)
                    stitching_params.append(params[4:])

                original_annotation_coord = [annotation_tiles[annotation_name]['Annotation_tile_img_position_x'],
                                             annotation_tiles[annotation_name]['Annotation_tile_img_position_y']]

                [perform_stitching, stitched_coordinates] = self.process_stitching_params(stitching_params,
                                                                                          original_annotation_coord,
                                                                                          stitch_threshold,
                                                                                          original_positions)

                # If the calculate stitching is reasonable, perform the stitching. Otherwise, log a warning
                if perform_stitching:
                    # Add the information about where the fork is in the stitched image back to the dictionary,
                    # such that it can be saved to csv afterwards
                    annotation_tiles[annotation_name]['annotation_position_x'] = stitched_coordinates[0]
                    annotation_tiles[annotation_name]['annotation_position_y'] = stitched_coordinates[1]

                    Fusion = autoclass('mpicbg.stitching.fusion.Fusion')
                    UnsignedShortType = autoclass('net.imglib2.type.numeric.integer.UnsignedShortType')
                    target_type = UnsignedShortType()
                    subpixel_accuracy = False
                    ignore_zero_values = False
                    stitched_img = Fusion.fuse(target_type, java_imgs, models, dimensionality, subpixel_accuracy, 5,
                                               None, False, ignore_zero_values, False)

                    # # Use imageJ to set bit depth, pixel size & save the image.
                    IJ = autoclass('ij.IJ')

                    # Set the pixel size. Fiji rounds 0.499 nm to 0.5 nm and I can't see anything I can do about that
                    pixel_size_nm = str(annotation_tiles[annotation_name]['pixel_size'] * 10e8)
                    pixel_size_command = "channels=1 slices=1 frames=1 unit=nm pixel_width=" + pixel_size_nm + \
                                         " pixel_height=" + pixel_size_nm + " voxel_depth=1.0 global"
                    IJ.run(stitched_img, "Properties...", pixel_size_command)

                    # Convert to 8 bit
                    if eight_bit:
                        IJ.run(stitched_img, "8-bit", "")

                    # Convert it to an ImageJ2 dataset. It was an imageJ1 ImagePlus before and the save function can't
                    # handle that. See: https://github.com/imagej/pyimagej/issues/35
                    stitched_img_dataset = self.ij.py.to_dataset(stitched_img)

                    output_filename = annotation_name + '.png'
                    self.ij.io().save(stitched_img_dataset, str(self.output_path / output_filename))

                    # TODO: Find a way to do improved memory management or reset the running instance, e.g.:
                    #  https://forum.image.sc/t/how-to-find-memory-leaks-in-plugins-what-needs-to-get-disposed/10211/12
                    # ij.getContext().dispose()
                    self.ij.window().clear()

                else:
                    # TODO: Deal with possibility of stitching not having worked well (e.g. by trying again with
                    #  changed parameters or by putting the individual images in a folder so that they could be
                    #  stitched manually)
                    logging.warning('Not stitching fork {}, because the stitching calculations displaced the images more '
                                    'than {} pixels'.format(annotation_name, stitch_threshold))


            else:
                # TODO: Potentially implement stitching for edge-cases of non 3x3 tiles
                logging.warning('Not stitching fork {}, because it is not surrounded by other tiles'.format(
                        annotation_name))

        # return the annotation_tiles dictionary that now contains the information about whether a fork was stitched and
        # where the fork is in the stitched image
        return annotation_tiles


    def process_stitching_params(self, stitch_params, annotation_coordinates, stitch_threshold, original_positions):
        nb_imgs = len(stitch_params)
        stitch_coordinates = np.zeros((nb_imgs, 2))
        for i, coordinates in enumerate(stitch_params):
            stitch_coordinates[i, 0] = int(round(coordinates[0]))
            stitch_coordinates[i, 1] = int(round(coordinates[1]))
        min_coords = np.min(stitch_coordinates, axis=0)
        stitched_annotation_coordinates = annotation_coordinates + stitch_coordinates[4, :] - min_coords

        stitch_shift = stitch_coordinates - original_positions
        max_shift = np.max(stitch_shift)
        if max_shift < stitch_threshold:
            good_stitching = True
        else:
            good_stitching = False
            logging.warning('Current stitching moves images more than the threshold of {}. '
                            'The stitching calculated the following image displacements from their '
                            'starting positions: {}.'.format(stitch_threshold, stitch_shift))

        return [good_stitching, stitched_annotation_coordinates.astype(int)]

    def parse_create_csv_batches(self, batch_size):
        # Make folders for csv files
        os.makedirs(str(self.csv_base_path), exist_ok=True)
        csv_path = self.csv_base_path / (self.project_name + '_annotations' + '.csv')

        parser = sip.MapsXmlParser(project_folder=self.project_folder_path, use_unregistered_pos=True,
                                   name_of_highmag_layer=self.highmag_layer, stitch_radius=self.stitch_radius)

        annotation_tiles = parser.parse_xml()
        annotation_csvs = sip.save_annotation_tiles_to_csv(annotation_tiles, self.base_header, csv_path,
                                                           batch_size=batch_size)

        return [annotation_tiles, annotation_csvs]

    def stitch_batch(self, annotation_csv_path, stitch_threshold, eight_bit):
        # Check if a folder for the stitched forks already exists. If not, create that folder
        os.makedirs(str(self.output_path), exist_ok=True)
        annotation_tiles_loaded = sip.load_annotations_from_csv(self.base_header, annotation_csv_path)

        stitched_annotation_tiles = self.stitch_annotated_tiles(annotation_tiles=annotation_tiles_loaded,
                                                                stitch_threshold=stitch_threshold,
                                                                eight_bit=eight_bit)
        csv_stitched_path = annotation_csv_path[:-4] + '_stitched.csv'

        sip.save_annotation_tiles_to_csv(stitched_annotation_tiles, self.base_header, csv_stitched_path)
        os.remove(annotation_csv_path)

    def manage_batches(self, stitch_threshold, eight_bit):
        # Populate annotation_csv_list by looking at csv files in directory
        items = os.listdir(self.csv_base_path)
        annotation_csv_list = []
        regex = re.compile('_annotations_\d+\.csv')
        for name in items:
            if regex.search(name):
                annotation_csv_list.append(self.csv_base_path / name)

        for annotation_csv_path in annotation_csv_list:
            self.stitch_batch(annotation_csv_path, stitch_threshold, eight_bit)


def main():
    # Paths
    base_path = '/Volumes/staff/zmbstaff/7831/Raw_Data/Group Lopes/Sebastian/Projects/'
    # base_path = 'Z:\\zmbstaff\\7831\\Raw_Data\\Group Lopes\\Sebastian\\Projects\\'
    project_name = '8330_siNeg_CPT_3rd'
    # project_name = '8330_siXRCC3_CPT_3rd_2ul'
    # project_name = '8373_3_siXRCC3_HU_1st_y1'

    # Logging
    logging.basicConfig(filename=Path(base_path) / project_name / (project_name + '_2.log'), level=logging.INFO,
                        format='%(asctime)s %(message)s')
    logging.info('Processing experiment {}'.format(project_name))

    # Parameters
    stitch_radius = 1
    batch_size = 5
    stitch_threshold = 2000
    highmag_layer = 'highmag'
    eight_bit = True

    # Initialize ImageJ VM
    ij = imagej.init('sc.fiji:fiji:2.0.0-pre-10+ch.fmi:faim-ij2-visiview-processing:0.0.1')

    # Parse and save the metadata
    stitcher = Stitcher(ij, highmag_layer, stitch_radius, base_path, project_name)
    stitcher.parse_create_csv_batches(batch_size=batch_size)
    stitcher.manage_batches(stitch_threshold, eight_bit)


if __name__ == "__main__":
    main()
