import logging
from pathlib import Path
import re
import numpy as np


import imagej

# TODO: Fix logging, not going to file but to console at the moment


def stitch_annotated_tiles(annotation_tiles: dict, output_path: Path, pixel_size: float, ij, stitch_radius: int = 1,
                           eight_bit: bool = False):
    # This function takes the parser object containing all the information about the MAPS project and its annotations.
    # It the performs stitching
    # Stitching plugin only runs when the local Fiji installation is being used. When a current imageJ gateway
    # is used, it does not find the plugin. Maybe have a distinct local Fiji installation that is hidden otherwise?
    # Maven-based initialization doesn't currently work for ImageJ1 plugins like Grid stitching, but I can use lower
    # level Java APIs directly via pyimagej. Wait for necessary fixes in
    # https://forum.image.sc/t/using-imagej-functions-like-type-conversion-and-setting-pixel-size-via-pyimagej/25755/10
    # Maven initialization
    # ij = imagej.init('sc.fiji:fiji:2.0.0-pre-10')

    # Maven initialization with stitching plugin wrappers
    # ij = imagej.init('sc.fiji:fiji:2.0.0-pre-10+ch.fmi:faim-ij2-visiview-processing:0.0.1')

    # Local imageJ initialization
    # ij = imagej.init('/Applications/Fiji.app')
    # ij = imagej.init('C:\\Program Files\\Fiji')
    for annotation_name in annotation_tiles:
        number_existing_neighbor_tiles = sum(annotation_tiles[annotation_name]['surrounding_tile_exists'])
        # If the image files for the 8 neighbors and the tile exist, stitch the images
        if number_existing_neighbor_tiles == 9:
            logging.info('Stitching {}'.format(annotation_name))
            center_filename = annotation_tiles[annotation_name]['filename']

            img_path = annotation_tiles[annotation_name]['img_path']

            # TODO: Change to running plugin with lower level APIs, directly extracting the stitching configuration.
            #  I'm working on this on the imagej_api branch
            # See here: https://github.com/imagej/pyimagej/issues/35
            # https://forum.image.sc/t/using-imagej-functions-like-type-conversion-and-setting-pixel-size-via-pyimagej/25755/10


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
            # Closing any ImageJ1 windows
            ij.window().clear()

            # TODO: Check stitching results directly from API => Will allow parallelization of stitching without race
            #  conditions about reading out the stitching coordinates
            # Get the information about how much the center image has been shifted, where the fork is placed in
            # the stitched image
            config_path_registered = img_path / 'TileConfiguration.registered.txt'
            with open(config_path_registered, 'r') as f:
                stitching_config = f.read()

            original_annotation_coord = [annotation_tiles[annotation_name]['Annotation_tile_img_position_x'],
                                         annotation_tiles[annotation_name]['Annotation_tile_img_position_y']]
            stitched_annotation_coordinates = check_stitching_result(stitching_config, original_annotation_coord)

            # Add the information about where the fork is in the stitched image back to the dictionary, such that it
            # can be saved to csv afterwards
            annotation_tiles[annotation_name]['annotation_position_x'] = stitched_annotation_coordinates[0]
            annotation_tiles[annotation_name]['annotation_position_y'] = stitched_annotation_coordinates[1]

            # TODO: Deal with possibility of stitching not having worked well (e.g. by trying again with changed
            #  parameters or by putting the individual images in a folder so that they could be stitched manually)

        else:
            # TODO: Potentially implement stitching for edge-cases of non 3x3 tiles
            logging.warning('Not stitching fork {}, because it is not surrounded by other tiles'.format(
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





# def main():
#     base_path = '/Volumes/staff/zmbstaff/7831/Raw_Data/Group Lopes/Sebastian/Projects/'
#     # base_path = 'Z:\\zmbstaff\\7831\\Raw_Data\\Group Lopes\\Sebastian\\Projects\\'
#     project_name = '8330_siNeg_CPT_3rd'
#     # project_name = '8330_siXRCC3_CPT_3rd_2ul'
#     # project_name = '8373_3_siXRCC3_HU_1st_y1'
#     project_folder_path = os.path.join(base_path + project_name)
#     logging.basicConfig(filename=Path(base_path) / project_name / (project_name + '_2.log'), level=logging.INFO,
#                         format='%(asctime)s %(message)s')
#     logging.info('Processing experiment {}'.format(project_name))
#     # project_folder_path = '/Volumes/staff/zmbstaff/7831/Raw_Data/Group Lopes/Sebastian/Projects//'
#     stitch_radius = 1
#     batch_size = 20
#
#     # Check if a folder for the stitched forks already exists. If not, create that folder
#     output_folder = 'stitchedForks'
#     output_path = Path(project_folder_path) / Path(output_folder)
#
#     os.makedirs(str(output_path), exist_ok=True)
#
#     highmag_layer = 'highmag'
#
#     # csv_path = os.path.join(base_path, project_name + '_annotations' + '.csv')
#     csv_path = '/Users/Joel/Desktop/test_annotations.csv'
#
#     parser = MapsXmlParser(project_folder=project_folder_path, use_unregistered_pos=True,
#                            name_of_highmag_layer=highmag_layer, stitch_radius=stitch_radius)
#     annotation_tiles = parser.parse_xml()
#     annotation_csvs = parser.save_annotation_tiles_to_csv(annotation_tiles, base_header, csv_path, batch_size=batch_size)
#
#     for annotation_csv in annotation_csvs:
#         annotation_tiles_loaded = parser.load_annotations_from_csv(base_header, annotation_csv)
#         print(annotation_tiles_loaded)
#
#         # stitched_annotation_tiles = stitch_annotated_tiles(annotation_tiles=annotation_tiles, output_path=output_path,
#         #                                           pixel_size=parser.pixel_size, stitch_radius=stitch_radius,
#         #                                           eight_bit=True)
#         #
#         # csv_stitched_path = '/Users/Joel/Desktop/test_annotations.csv'
#         # parser.save_annotation_tiles_to_csv(stitched_annotation_tiles, base_header, csv_stitched_path, batch_size=batch_size)




# if __name__ == "__main__":
#     main()
