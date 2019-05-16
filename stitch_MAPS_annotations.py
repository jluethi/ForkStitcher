import sites_of_interest_parser
import imagej
import shutil
import os
from pathlib import Path
import pandas as pd
import re
import numpy as np

def stitch_annotated_tiles(xml_parser, output_path, stitch_radius=1):
    # This function takes the parser object containing all the information about the MAPS project and its annotations.
    # It the performs stitching
    # TODO: Find a way to call the Fiji stitching without falling back to the local Fiji library
    # Stitching plugin only runs when the local Fiji installation is being used. When a current imageJ gateway
    # is used, it does not find the plugin
    # ij = imagej.init('sc.fiji:fiji')
    # ij = imagej.init('/Applications/Fiji.app')
    for annotation_name in xml_parser.annotation_tiles:
        number_existing_neighbor_tiles = sum(xml_parser.annotation_tiles[annotation_name]['surrounding_tile_exists'])
        # If the image files for the 8 neighbors and the tile exist, stitch the images
        if number_existing_neighbor_tiles == 9:
            print('Stitching {}'.format(annotation_name))
            center_filename = xml_parser.annotation_tiles[annotation_name]['filename']

            img_path = xml_parser.annotation_tiles[annotation_name]['img_path']

            plugin = 'Grid/Collection stitching'

            index_x = int(center_filename[9:12]) - stitch_radius
            index_y = int(center_filename[5:8]) - stitch_radius
            # args = {'type': '[Filename defined position]', 'order': '[Defined by filename         ]',
            #         'grid_size_x': '3', 'grid_size_y': '3', 'tile_overlap': '8', 'first_file_index_x': str(index_x),
            #         'first_file_index_y': str(index_y), 'directory': img_path,
            #         'file_names': 'Tile_{yyy}-{xxx}-000000_0-000.tif', 'output_textfile_name': 'TileConfiguration.txt',
            #         'fusion_method': '[Intensity of random input tile]', 'regression_threshold': '0.15',
            #         'max/avg_displacement_threshold': '0.20', 'absolute_displacement_threshold': '0.30',
            #         'compute_overlap': True, 'computation_parameters': '[Save memory (but be slower)]',
            #         'image_output': '[Write to disk]'}

            args = {'type': '[Filename defined position]', 'order': '[Defined by filename         ]',
                    'grid_size_x': '3', 'grid_size_y': '3', 'tile_overlap': '8', 'first_file_index_x': str(index_x),
                    'first_file_index_y': str(index_y), 'directory': img_path,
                    'file_names': 'Tile_{yyy}-{xxx}-000000_0-000.tif', 'output_textfile_name': 'TileConfiguration.txt',
                    'fusion_method': '[Intensity of random input tile]', 'regression_threshold': '0.15',
                    'max/avg_displacement_threshold': '0.20', 'absolute_displacement_threshold': '0.30',
                    'compute_overlap': True, 'computation_parameters': '[Save memory (but be slower)]',
                    'image_output': '[Write to disk]'}

            # ij.py.run_plugin(plugin, args)

            # TODO: Add an 8 bit export option => change from direct saving to saving via ij.py call



            # output_filename = annotation_name + '.tiff'
            # shutil.move(img_path / 'img_t1_z1_c1', output_path / output_filename)

            # Get the information about how much the center image has been shifted, where the fork is placed in
            # the stitched image
            config_path_registered = img_path / 'TileConfiguration.registered.txt'
            with open(config_path_registered, 'r') as f:
                stitching_config = f.read()

            original_annotation_coord = [xml_parser.annotation_tiles[annotation_name]['Annotation_img_position_x'],
                                         xml_parser.annotation_tiles[annotation_name]['Annotation_img_position_y']]
            stitched_annotation_coordinates = check_stitching_result(stitching_config, original_annotation_coord)  # , xml_parser.img_width, xml_parser.img_height
            print(stitched_annotation_coordinates)

            xml_parser.annotation_tiles[annotation_name]['Stitched_annotation_img_position_x'] = \
                stitched_annotation_coordinates[0]
            xml_parser.annotation_tiles[annotation_name]['Stitched_annotation_img_position_y'] = \
                stitched_annotation_coordinates[1]
            break

            # TODO: Add an arrow to the image

        else:
            # TODO: Potentially implement stitching for edge-cases of non 3x3 tiles
            # TODO: Change warning to some log entry (print console is full of fiji stitching info)
            print(
                'WARNING! Not stitching fork {} at the moment, because it is not surrounded by other tiles'.format(
                    annotation_name))

    # return the annotation_tiles dictionary that now contains the information about whether a fork was stitched and
    # where the fork is in the stitched image
    return xml_parser.annotation_tiles


def check_stitching_result(stitching_config, annotation_coordinates):
    nb_files = 9
    stitch_coord_strings = re.findall('\(([^\)]+)\)', stitching_config)
    assert(len(stitch_coord_strings) == nb_files)
    stitch_coordinates = np.zeros((nb_files, 2))
    for i, coordinates in enumerate(stitch_coord_strings):
        stitch_coordinates[i, 0] = round(float(coordinates.split(',')[0]))
        stitch_coordinates[i, 1] = round(float(coordinates.split(',')[1]))
    # print(stitch_coordinates)
    min_coords = np.min(stitch_coordinates, axis=0)
    # max_coords = np.max(stitch_coordinates, axis=0) + [4096, 4096]
    # img_size = max_coords - min_coords
    # print(img_size)

    stitched_annotation_coordinates = annotation_coordinates + stitch_coordinates[4, :] - min_coords

    return stitched_annotation_coordinates.astype(int)


def save_annotation_info_to_csv(annotation_tiles, csv_path):
    # Saves the annotation_tiles information to a csv file, so that the fork position could be used in
    # quality control and so that users assign whether an annotation was a fork or a false positive.
    # Needs to have the information about fork location both in MAPS (global coordinates) and in the stitched image
    # (img coordinates)

    # From self.annotation_tiles: img_path, filename, square_name, stage coordinates, pixel coordinates in the raw
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

        current_annotation_pd = pd.DataFrame(current_annotation, index=[0])
        with open(csv_path, 'a') as f:
            current_annotation_pd.to_csv(f, header=False, index=False)


def main():
    base_path = '/Volumes/staff/zmbstaff/7831/Raw_Data/Group Lopes/Sebastian/Projects/'
    project_name = '8330_siNeg_CPT_3rd'
    project_folder_path = os.path.join(base_path + project_name)
    # project_folder_path = '/Volumes/staff/zmbstaff/7831/Raw_Data/Group Lopes/Sebastian/Projects/siXRCC3_CPT_3rd_2ul/'
    stitch_radius = 1

    # Check if a folder for the stitched forks already exists. If not, create that folder
    output_folder = 'stitchedForks'
    output_path = Path(project_folder_path) / Path(output_folder)

    os.makedirs(str(output_path), exist_ok=True)

    highmag_layer = 'highmag'
    parser = sites_of_interest_parser.Xml_MAPS_Parser(project_folder=project_folder_path, position_to_use=0,
                                                      name_of_highmag_layer=highmag_layer, stitch_radius=stitch_radius)
    parser.parse_xml()
    print(parser.annotation_tiles['fork74'])

    csv_path = '/Users/Joel/Desktop/' + project_name + '.csv'

    annotation_tiles = stitch_annotated_tiles(xml_parser=parser, output_path=output_path, stitch_radius=stitch_radius)

    # save_annotation_info_to_csv(parser.annotation_tiles, csv_path)
    # save_annotation_info_to_csv(annotation_tiles, csv_path)



if __name__ == "__main__":
    main()
