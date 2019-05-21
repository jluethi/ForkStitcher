import logging
import os
from pathlib import Path
import pandas as pd
import re
import numpy as np
# import cv2
# import shutil

import imagej

from sites_of_interest_parser import MapsXmlParser


def stitch_annotated_tiles(annotation_tiles: dict, output_path: Path, pixel_size: float, stitch_radius: int = 1,
                           eight_bit: bool = False):
    # This function takes the parser object containing all the information about the MAPS project and its annotations.
    # It the performs stitching
    # TODO: Find a way to call the Fiji stitching without falling back to the local Fiji library
    # Stitching plugin only runs when the local Fiji installation is being used. When a current imageJ gateway
    # is used, it does not find the plugin. Maybe have a distinct local Fiji installation that is hidden otherwise?
    # Maven-based initialization doesn't currently work for ImageJ1 plugins like Grid stitching, but I can use lower
    # level Java APIs directly via pyimagej. Wait for necessary fixes in
    # https://forum.image.sc/t/using-imagej-functions-like-type-conversion-and-setting-pixel-size-via-pyimagej/25755/10
    # Maven initialization
    # ij = imagej.init('sc.fiji:fiji:2.0.0-pre-10')

    # Maven initialization with stitching plugin wrappers
    ij = imagej.init('sc.fiji:fiji:2.0.0-pre-10+ch.fmi:faim-ij2-visiview-processing:0.0.1')

    # Local imageJ initialization
    # ij = imagej.init('/Applications/Fiji.app')
    from jnius import autoclass
    for annotation_name in annotation_tiles:
        number_existing_neighbor_tiles = sum(annotation_tiles[annotation_name]['surrounding_tile_exists'])
        # If the image files for the 8 neighbors and the tile exist, stitch the images
        if number_existing_neighbor_tiles == 9:
            logging.info('Stitching {}'.format(annotation_name))
            center_filename = annotation_tiles[annotation_name]['filename']

            img_path = annotation_tiles[annotation_name]['img_path']

            # TODO: Change to running plugin with lower level APIs, directly extracting the stitching configuration.
            # See here: https://github.com/imagej/pyimagej/issues/35

            # load images: figure out how to load multiple images into the same container
            # BF = autoclass('ij.BioFormats')
            # img = BF.open(str(img_path / center_filename))

            ImagePlusClass = autoclass('ij.ImagePlus')
            imagej2_img = ij.io().open(str(img_path / center_filename))
            imps = [ij.convert().convert(imagej2_img, ImagePlusClass)]

            for neighbor in annotation_tiles[annotation_name]['surrounding_tile_names']:
                print(neighbor)
                imagej2_img = ij.io().open(str(img_path / neighbor))
                imps.append(ij.convert().convert(imagej2_img, ImagePlusClass))
            print(type(imps))
            print(imps)
            # Define starting positions
            positions = [[3686, 3686], [0, 0], [3686, 0], [7373, 0], [0, 3686], [7373, 3686], [0, 7373],
                         [3686, 7373], [7373, 7373]]

            dimensionality = 2
            computeOverlap = True
            StitchingUtils = autoclass('ch.fmi.visiview.StitchingUtils')
            models = StitchingUtils.computeStitching(imps, positions, dimensionality, computeOverlap)

            resultImp = StitchingUtils.fuseTiles(imps, models, dimensionality)

            # Stop here for testing purposes. Runs fine through whole dataset
            break


            # Potentially: Test if 'Save computation time (but use more RAM)' option speeds up the stitching
            plugin = 'Grid/Collection stitching'
            index_x = int(center_filename[9:12]) - stitch_radius
            index_y = int(center_filename[5:8]) - stitch_radius
            args = {'type': '[Filename defined position]', 'order': '[Defined by filename         ]',
                    'grid_size_x': '3', 'grid_size_y': '3', 'tile_overlap': '8', 'first_file_index_x': str(index_x),
                    'first_file_index_y': str(index_y), 'directory': img_path,
                    'file_names': 'Tile_{yyy}-{xxx}-000000_0-000.tif', 'output_textfile_name': 'TileConfiguration.txt',
                    'fusion_method': '[Intensity of random input tile]', 'regression_threshold': '0.15',
                    'max/avg_displacement_threshold': '0.20', 'absolute_displacement_threshold': '0.30',
                    'compute_overlap': True, 'computation_parameters': '[Save memory (but be slower)]',
                    'image_output': '[Fuse and display]'}
            ij.py.run_plugin(plugin, args)

            # Use imageJ to set bit depth, pixel size & save the image.
            from jnius import autoclass
            IJ = autoclass('ij.IJ')

            # Get the open window with the stitched image
            WindowManager = autoclass('ij.WindowManager')
            stitched_img = WindowManager.getCurrentImage()

            # Set the pixel size. Fiji seems to round 0.499 nm to 0.5 nm and I can't see anything I can do about that
            pixel_size_nm = str(pixel_size * 10e8)
            pixel_size_command = "channels=1 slices=1 frames=1 unit=nm pixel_width=" + pixel_size_nm + \
                                 " pixel_height=" + pixel_size_nm + " voxel_depth=1.0 global"
            IJ.run(stitched_img, "Properties...", pixel_size_command)

            # Convert to 8 bit
            if eight_bit:
                IJ.run(stitched_img, "8-bit", "")

            # Convert it to an ImageJ2 dataset. It was an imageJ1 ImagePlus before and the save function can't handle
            # that. See: https://github.com/imagej/pyimagej/issues/35
            stitched_img_dataset = ij.py.to_dataset(stitched_img)

            output_filename = annotation_name + '.png'
            ij.io().save(stitched_img_dataset, str(output_path / output_filename))

            # Get the information about how much the center image has been shifted, where the fork is placed in
            # the stitched image
            config_path_registered = img_path / 'TileConfiguration.registered.txt'
            with open(config_path_registered, 'r') as f:
                stitching_config = f.read()

            original_annotation_coord = [annotation_tiles[annotation_name]['Annotation_img_position_x'],
                                         annotation_tiles[annotation_name]['Annotation_img_position_y']]
            stitched_annotation_coordinates = check_stitching_result(stitching_config, original_annotation_coord)

            # Add the information about where the fork is in the stitched image back to the dictionary, such that it
            # can be saved to csv afterwards
            annotation_tiles[annotation_name]['Stitched_annotation_img_position_x'] = \
                stitched_annotation_coordinates[0]
            annotation_tiles[annotation_name]['Stitched_annotation_img_position_y'] = \
                stitched_annotation_coordinates[1]

            # TODO: Deal with possibility of stitching not having worked well (e.g. by trying again with changed
            #  parameters or by putting the individual images in a folder so that they could be stitched manually)

            # TODO: Add an arrow to the image

        else:
            # TODO: Potentially implement stitching for edge-cases of non 3x3 tiles
            logging.warning('Not stitching fork {} at the moment, because it is not surrounded by other tiles'.format(
                    annotation_name))

    # return the annotation_tiles dictionary that now contains the information about whether a fork was stitched and
    # where the fork is in the stitched image
    return annotation_tiles


def check_stitching_result(stitching_config, annotation_coordinates):
    nb_files = 9
    stitch_coord_strings = re.findall('\(([^\)]+)\)', stitching_config)
    assert(len(stitch_coord_strings) == nb_files)
    stitch_coordinates = np.zeros((nb_files, 2))
    for i, coordinates in enumerate(stitch_coord_strings):
        stitch_coordinates[i, 0] = round(float(coordinates.split(',')[0]))
        stitch_coordinates[i, 1] = round(float(coordinates.split(',')[1]))
    min_coords = np.min(stitch_coordinates, axis=0)

    stitched_annotation_coordinates = annotation_coordinates + stitch_coordinates[4, :] - min_coords

    # TODO: Calculate distance between all stitched positions to find potential issues

    return stitched_annotation_coordinates.astype(int)


def save_annotation_info_to_csv(annotation_tiles, csv_path):
    # Saves the annotation_tiles information to a csv file, so that the fork position could be used in
    # quality control and so that users assign whether an annotation was a fork or a false positive.
    # Needs to have the information about fork location both in MAPS (global coordinates) and in the stitched image
    # (img coordinates)

    # From self.annotation_tiles: img_path, filename, layer_name, stage coordinates, pixel coordinates in the raw
    # image and pixel coordinates in the stitched image (need to figure out how to get the pixel coordinates in the
    # stitched image)
    base_header = ['Image', 'False Positive', 'Loop', 'Crossing', 'fork symetric', 'fork asymetric',
                                   'reversed fork symetric', 'reversed fork asymetric',	'size reversed fork (nm)',
                                   'dsDNA RF', 'internal ssDNA RF', 'ssDNA end RF', 'total ssDNA RF	gaps',
                                   'gaps', 'sister	gaps', 'parental', 'size gaps (nm)', 'junction ssDNA size (nm)',
                                   'hemicatenane', 'termination intermediate', 'bubble', 'hemireplicated bubble',
                                   'comments', 'list for reversed forks (nt)', 'list for gaps (nt)',
                                   'list for ssDNA at junction (nt)']
    header_addition = list(list(annotation_tiles.values())[0].keys())
    header_addition.remove('surrounding_tile_exists')
    header_addition.remove('surrounding_tile_names')
    csv_header = pd.DataFrame(columns=base_header + header_addition)
    csv_header.to_csv(csv_path, index=False)

    for annotation_name in annotation_tiles:
        current_annotation = {}
        current_annotation['Image'] = annotation_name
        for header in base_header[1:]:
            current_annotation[header] = ''

        for info_key in annotation_tiles[annotation_name]:
            current_annotation[info_key] = annotation_tiles[annotation_name][info_key]

        if 'surrounding_tile_exists' in current_annotation:
            del current_annotation['surrounding_tile_exists']

        if 'surrounding_tile_names' in current_annotation:
            del current_annotation['surrounding_tile_names']

        current_annotation_pd = pd.DataFrame(current_annotation, index=[0])
        with open(csv_path, 'a') as f:
            current_annotation_pd.to_csv(f, header=False, index=False)


def main():
    base_path = '/Volumes/staff/zmbstaff/7831/Raw_Data/Group Lopes/Sebastian/Projects/'
    project_name = '8330_siNeg_CPT_3rd'
    # project_name = 'siXRCC3_CPT_3rd_2ul'
    project_folder_path = os.path.join(base_path + project_name)
    logging.basicConfig(filename=Path(base_path) / (project_name + '.log'), level=logging.INFO,
                        format='%(asctime)s %(message)s')
    logging.info('Processing experiment {}'.format(project_name))
    # project_folder_path = '/Volumes/staff/zmbstaff/7831/Raw_Data/Group Lopes/Sebastian/Projects//'
    stitch_radius = 1

    # Check if a folder for the stitched forks already exists. If not, create that folder
    output_folder = 'stitchedForks'
    output_path = Path(project_folder_path) / Path(output_folder)

    os.makedirs(str(output_path), exist_ok=True)

    highmag_layer = 'highmag'
    parser = MapsXmlParser(project_folder=project_folder_path, use_unregistered_pos=True,
                           name_of_highmag_layer=highmag_layer, stitch_radius=stitch_radius)
    annotation_tiles = parser.parse_xml()
    # print(parser.annotation_tiles['fork74'])
    print(annotation_tiles)
    csv_path = '/Users/Joel/Desktop/' + project_name + '.csv'

    # annotation_tiles = stitch_annotated_tiles(annotation_tiles=annotation_tiles, output_path=output_path,
    #                                           pixel_size = parser.pixel_size, stitch_radius=stitch_radius,
    #                                           eight_bit=True)

    # save_annotation_info_to_csv(parser.annotation_tiles, csv_path)
    # save_annotation_info_to_csv(annotation_tiles, csv_path)



if __name__ == "__main__":
    main()
