import sites_of_interest_parser
import imagej
import shutil
import os
from pathlib import Path


# Stitching plugin only runs when the local Fiji installation is being used. When a current imageJ gateway is installed,
# it does not find the plugin

def stitch_annotated_tiles(parser, output_path, stitch_radius=1):
    # This function takes the parser object containing all the information about the MAPS project and its annotations.
    # It the performs stitching
    # TODO: Find a way to call the Fiji stitching without falling back to the local Fiji library
    # ij = imagej.init('sc.fiji:fiji')
    ij = imagej.init('/Applications/Fiji.app')
    for annotation_name in parser.annotation_tiles:
        number_existing_neighbor_tiles = sum(parser.annotation_tiles[annotation_name]['surrounding_tile_exists'])
        # If the image files for the 8 neighbors and the tile exist, stitch the images
        if number_existing_neighbor_tiles == 9:
            print('Stitching {}'.format(annotation_name))
            center_filename = parser.annotation_tiles[annotation_name]['filename']

            img_path = parser.convert_img_path_to_local_path(parser.annotation_tiles[annotation_name]['img_path'])

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



        else:
            # TODO: Potentially implement stitching for edge-cases of non 3x3 tiles
            print(
                'WARNING! Not stitching fork {} at the moment, because it is not surrounded by other tiles'.format(
                    annotation_name))


def main():
    project_folder_path = '/Volumes/staff/zmbstaff/7831/Raw_Data/Group Lopes/Sebastian/Projects/8330_siNeg_CPT_3rd/'
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

    stitch_annotated_tiles(parser=parser, output_path=output_path, stitch_radius=stitch_radius)


if __name__ == "__main__":
    main()
