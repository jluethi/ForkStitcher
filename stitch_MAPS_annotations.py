import sites_of_interest_parser
import imagej
import shutil
import os
from pathlib import Path

def stitch_annotated_tiles(xml_parser, output_path, stitch_radius=1):
    # This function takes the parser object containing all the information about the MAPS project and its annotations.
    # It the performs stitching
    # TODO: Find a way to call the Fiji stitching without falling back to the local Fiji library
    # Stitching plugin only runs when the local Fiji installation is being used. When a current imageJ gateway
    # is used, it does not find the plugin
    # ij = imagej.init('sc.fiji:fiji')
    ij = imagej.init('/Applications/Fiji.app')
    for annotation_name in xml_parser.annotation_tiles:
        number_existing_neighbor_tiles = sum(xml_parser.annotation_tiles[annotation_name]['surrounding_tile_exists'])
        # If the image files for the 8 neighbors and the tile exist, stitch the images
        if number_existing_neighbor_tiles == 9:
            print('Stitching {}'.format(annotation_name))
            center_filename = xml_parser.annotation_tiles[annotation_name]['filename']

            img_path = xml_parser.convert_img_path_to_local_path(xml_parser.annotation_tiles[annotation_name]['img_path'])

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
                    'image_output': '[Write to disk]'}

            ij.py.run_plugin(plugin, args)

            output_filename = annotation_name + '.tiff'
            shutil.move(img_path / 'img_t1_z1_c1', output_path / output_filename)

            # TODO: Add an 8 bit export option

            # TODO: Add an arrow to the image

        else:
            # TODO: Potentially implement stitching for edge-cases of non 3x3 tiles
            # TODO: Change warning to some log entry (print console is full of fiji stitching info
            print(
                'WARNING! Not stitching fork {} at the moment, because it is not surrounded by other tiles'.format(
                    annotation_name))


def save_annotation_info_to_csv(xml_parser):
    # TODO: Saves the annotation_tiles information to a csv file, so that the fork position could be used in
    # quality control and so that users assign whether an annotation was a fork or a false positive.
    # Needs to have the information about fork location both in MAPS (global coordinates) and in the stitched image
    # (img coordinates)

    # From self.annotation_tiles: img_path, filename, square_name, stage coordinates, pixel coordinates in the raw
    # image and pixel coordinates in the stitched image (need to figure out how to get the pixel coordinates in the
    # stitched image)
    pass


def main():
    # project_folder_path = '/Volumes/staff/zmbstaff/7831/Raw_Data/Group Lopes/Sebastian/Projects/8330_siNeg_CPT_3rd/'
    project_folder_path = '/Volumes/staff/zmbstaff/7831/Raw_Data/Group Lopes/Sebastian/Projects/siXRCC3_CPT_3rd_2ul/'
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

    stitch_annotated_tiles(xml_parser=parser, output_path=output_path, stitch_radius=stitch_radius)


if __name__ == "__main__":
    main()
