# Script that parses the Site of Interest annotations from a MAPS XML file

import xml.etree.ElementTree as ET
import sys
import numpy as np
import math
from pathlib import Path


class Xml_MAPS_Parser():

    def __init__(self, project_folder, name_of_highmag_layer='highmag', position_to_use=0, stitch_radius=1):
        self.project_folder_path = Path(project_folder)
        self.name_of_highmag_layer = name_of_highmag_layer

        # In the samples I had, MAPS didn't show any aligned positions. Therefore, unaligned positions is what
        # we want to extract. If positions are moved somehow in MAPS (I assume through stitching),
        # calculatedPositions may be revelant
        potential_positions_to_extract = ['UnalignedPosition', 'CalculatedPosition']
        self.position_to_extract = potential_positions_to_extract[position_to_use]
        xml_file_name = 'MapsProject.xml'

        xml_file_path = self.project_folder_path / xml_file_name
        self.xml_file = self.load_xml(xml_file_path)
        self.squares = {}
        self.tiles = {}
        self.annotations = {}
        self.tile_names = []
        self.tile_center_stage_positions = []
        self.annotation_tiles = {}
        self.stitch_radius = stitch_radius

    def load_xml(self, xml_file_path):
        # Load the MAPS XML File
        try:
            root = ET.parse(xml_file_path).getroot()
        except FileNotFoundError:
            print("Can't find the MAPS XML File at the location {}".format(xml_file_path))
            sys.exit(-1)
        return root

    def parse_xml(self):
        # run function to call all the internal functions.
        # Parses the XML file and saves the results in the class variables
        self.extract_square_metadata()
        self.extract_annotation_locations()
        self.get_relative_tile_locations()
        self.calculate_absolute_tile_coordinates()
        self.find_annotation_tile()
        self.determine_surrounding_sites()

    def convert_windows_pathstring_to_path_object(self, string_path):
        folders = string_path.split('\\')
        path = Path()
        for folder in folders:
            path = path / folder
        return path

    def convert_img_path_to_local_path(self, img_path):
        # The paths contained in the XML files contain a 'D:\\ProjectName', even though the files aren't actually
        # on the D drive. Correct by using the project_folder_path
        folders = img_path.split('\\')
        path = self.project_folder_path
        for folder in folders[2:]:
            path = path / folder
        return path

    def extract_square_metadata(self):
        # Extract the information about all the squares (high magnification acquisition layers)
        for child in self.xml_file:
            if child.tag.endswith('LayerGroups'):
                for grand_child in child:
                    for ggc in grand_child:

                        # Get the path to the metadata xml files for all the highmag squares,
                        # the pixel size and the StagePosition of the square
                        if ggc.tag.endswith('displayName') and ggc.text == self.name_of_highmag_layer:
                            print('Extracting images from {} layer'.format(ggc.text))

                            for highmag in grand_child:
                                if highmag.tag.endswith('Layers'):
                                    for square in highmag:
                                        # print(first_layer.tag)
                                        # print(first_layer.attrib)
                                        # print(first_layer.text)
                                        for layer_content in square:
                                            if layer_content.tag.endswith('metaDataLocation'):
                                                metadata_location = layer_content.text
                                                self.squares[metadata_location] = {}

                                        try:
                                            for layer_content in square:
                                                if layer_content.tag.endswith('totalHfw'):
                                                    # noinspection PyUnboundLocalVariable
                                                    self.squares[metadata_location]['totalHfw'] = float(
                                                        list(layer_content.attrib.values())[1])

                                                if layer_content.tag.endswith('tileHfw'):
                                                    # noinspection PyUnboundLocalVariable
                                                    self.squares[metadata_location]['tileHfw'] = float(
                                                        list(layer_content.attrib.values())[1])

                                                if layer_content.tag.endswith('overlapHorizontal'):
                                                    # noinspection PyUnboundLocalVariable
                                                    self.squares[metadata_location]['overlapHorizontal'] = float(
                                                        layer_content[0].text) / 100.
                                                if layer_content.tag.endswith('overlapVertical'):
                                                    # noinspection PyUnboundLocalVariable
                                                    self.squares[metadata_location]['overlapVertical'] = float(
                                                        layer_content[0].text) / 100.

                                                if layer_content.tag.endswith('rotation'):
                                                    # noinspection PyUnboundLocalVariable
                                                    self.squares[metadata_location]['rotation'] = float(
                                                        list(layer_content.attrib.values())[1])

                                                if layer_content.tag.endswith('rows'):
                                                    # noinspection PyUnboundLocalVariable
                                                    self.squares[metadata_location]['rows'] = int(layer_content.text)

                                                if layer_content.tag.endswith('columns'):
                                                    # noinspection PyUnboundLocalVariable
                                                    self.squares[metadata_location]['columns'] = int(layer_content.text)

                                                if layer_content.tag.endswith('scanResolution'):
                                                    for scanres_info in layer_content:
                                                        if scanres_info.tag.endswith('height'):
                                                            # noinspection PyUnboundLocalVariable
                                                            self.squares[metadata_location]['img_height'] = int(
                                                                scanres_info.text)
                                                        if scanres_info.tag.endswith('width'):
                                                            # noinspection PyUnboundLocalVariable
                                                            self.squares[metadata_location]['img_width'] = int(
                                                                scanres_info.text)

                                                if layer_content.tag.endswith('pixelSize'):
                                                    # noinspection PyUnboundLocalVariable
                                                    self.squares[metadata_location]['pixel_size'] = float(
                                                        layer_content.attrib['Value'])

                                                if layer_content.tag.endswith('StagePosition'):
                                                    for positon_info in layer_content:
                                                        if positon_info.tag == '{http://schemas.datacontract.org/2004/07/Fei.Applications.SAL}x':
                                                            # noinspection PyUnboundLocalVariable
                                                            self.squares[metadata_location][
                                                                'StagePosition_center_x'] = float(positon_info.text)
                                                        elif positon_info.tag == '{http://schemas.datacontract.org/2004/07/Fei.Applications.SAL}y':
                                                            # noinspection PyUnboundLocalVariable
                                                            self.squares[metadata_location][
                                                                'StagePosition_center_y'] = float(positon_info.text)
                                        except NameError:
                                            print("Can't find the metaDataLocation in the MAPS XML File")
                                            sys.exit(-1)

    def extract_annotation_locations(self):
        # Get all x & y positions of the annotations & the annotation name and save them in a dictionary.
        # Keys are the annotation names, values are a dictionary of x & y positions of that annotation
        for child in self.xml_file:
            if child.tag.endswith('LayerGroups'):
                for grand_child in child:
                    for ggc in grand_child:
                        # Finds all the layers that contain annotation and reads out the annotation details
                        for gggc in ggc:
                            if gggc.tag.endswith('anyType') and 'AnnotationLayer' in gggc.attrib.values():
                                for annotation_content in gggc:
                                    if annotation_content.tag.endswith('RealDisplayName'):
                                        annotation_name = annotation_content.text
                                        self.annotations[annotation_name] = {}
                                try:
                                    for annotation_content in gggc:
                                        if annotation_content.tag.endswith('StagePosition'):
                                            for a in annotation_content:
                                                if a.tag == '{http://schemas.datacontract.org/2004/07/Fei.Applications.SAL}x':
                                                    # noinspection PyUnboundLocalVariable
                                                    self.annotations[annotation_name]['StagePosition_x'] = float(a.text)
                                                elif a.tag == '{http://schemas.datacontract.org/2004/07/Fei.Applications.SAL}y':
                                                    # noinspection PyUnboundLocalVariable
                                                    self.annotations[annotation_name]['StagePosition_y'] = float(a.text)
                                except NameError:
                                    print("Can't find the Annotations Names in the MAPS XML File")
                                    sys.exit(-1)

    def get_relative_tile_locations(self):
        # read in all the metadata files for the different squares to get tile positions
        metadata_filename = 'StitchingData.xml'
        for metadata_location in self.squares:
            tile_image_folder_path = ''
            metadata_path = self.project_folder_path.joinpath(
                self.convert_windows_pathstring_to_path_object(metadata_location)) / metadata_filename
            metadata_root = ET.parse(metadata_path).getroot()
            for metadata_child in metadata_root:
                if metadata_child.tag.endswith('tileSet'):
                    for metadata_grandchild in metadata_child:
                        if metadata_grandchild.tag.endswith('TileImageFolder'):
                            tile_image_folder_path = metadata_grandchild.text
                            current_square = tile_image_folder_path.split('\\')[-1]
                            self.squares[metadata_location]['square_name'] = current_square

                        if metadata_grandchild.tag.endswith('_tileCollection'):
                            for ggc in metadata_grandchild:
                                if ggc.tag.endswith('_innerCollection'):
                                    for gggc in ggc:
                                        for keyvalue in gggc:
                                            if keyvalue.tag.endswith('Value'):
                                                for value in keyvalue:
                                                    if value.tag.endswith('ImageFileName'):
                                                        # noinspection PyUnboundLocalVariable
                                                        tile_name = current_square + '_' + value.text
                                                        self.tiles[tile_name] = {'square': metadata_location,
                                                                                 'img_path': tile_image_folder_path,
                                                                                 'filename': value.text,
                                                                                 'square_name': current_square}

                                                for value in keyvalue:
                                                    if value.tag.endswith('PositioningDetails'):
                                                        for positioning_detail in value:
                                                            if positioning_detail.tag.endswith(
                                                                    self.position_to_extract):
                                                                for position in positioning_detail:

                                                                    if position.tag == '{http://schemas.datacontract.org/2004/07/System.Drawing}x':
                                                                        # noinspection PyUnboundLocalVariable
                                                                        self.tiles[tile_name][
                                                                            'RelativeTilePosition_x'] = float(
                                                                            position.text)
                                                                    elif position.tag == '{http://schemas.datacontract.org/2004/07/System.Drawing}y':
                                                                        # noinspection PyUnboundLocalVariable
                                                                        self.tiles[tile_name][
                                                                            'RelativeTilePosition_y'] = float(
                                                                            position.text)

    def calculate_absolute_tile_coordinates(self):
        # Create absolute positions from the relative Tile positions
        # Calculate the edge Stage position of the square based on the parameters extracted

        current_square_key = (list(self.squares.keys())[0])
        current_square = self.squares[current_square_key]

        # Unsure if it's height/width or width/height because they are always the same on Talos
        current_square['tileVfw'] = current_square['img_height'] / current_square['img_width'] * current_square[
            'tileHfw']

        horizontal_field_width = (current_square['columns'] - 1) * current_square['tileHfw'] * (
                1 - current_square['overlapHorizontal']) + current_square['tileHfw']
        vertical_field_width = (current_square['rows'] - 1) * current_square['tileVfw'] * (
                1 - current_square['overlapHorizontal']) + current_square['tileVfw']

        relative_0_x = current_square['StagePosition_center_x'] - math.sin(
            current_square['rotation'] / 180 * math.pi) * vertical_field_width / 2 + math.cos(
            current_square['rotation'] / 180 * math.pi) * horizontal_field_width / 2
        relative_0_y = current_square['StagePosition_center_y'] - math.cos(
            current_square['rotation'] / 180 * math.pi) * vertical_field_width / 2 - math.sin(
            current_square['rotation'] / 180 * math.pi) * horizontal_field_width / 2
        relative_0 = np.array([relative_0_x, relative_0_y])

        self.squares[current_square_key]['StagePosition_corner_x'] = relative_0[0]
        self.squares[current_square_key]['StagePosition_corner_y'] = relative_0[1]

        for current_tile_name in self.tiles:
            current_tile = self.tiles[current_tile_name]

            relative_x_stepsize = np.array([current_square['pixel_size'] * math.cos(current_square['rotation']
                                                                                    / 180 * math.pi),
                                            current_square['pixel_size'] * math.sin(
                                                current_square['rotation'] / 180 * math.pi)])
            relative_y_stepsize = np.array([current_square['pixel_size'] * math.sin(current_square['rotation']
                                                                                    / 180 * math.pi),
                                            current_square['pixel_size'] * math.cos(
                                                current_square['rotation'] / 180 * math.pi)])

            # absolute_tile_pos is the position of the corner of the tile in absolute Stage Position coordinates,
            # the tile_center_stage_position are the Stage Position coordinates of the tile
            absolute_tile_pos = relative_0 + current_tile['RelativeTilePosition_x'] * relative_x_stepsize + \
                                current_tile[
                                    'RelativeTilePosition_y'] * relative_y_stepsize
            tile_center_stage_position = absolute_tile_pos + current_square['img_width'] / 2 * relative_x_stepsize + \
                                         current_square['img_height'] / 2 * relative_y_stepsize

            self.tile_center_stage_positions.append(tile_center_stage_position)
            self.tile_names.append([current_square['square_name'], current_tile_name])

    def find_annotation_tile(self):
        # Give annotation_name, square metadata key, square_name, tile_name,
        # stage coordinates & pixel position in the image
        # TODO: Save the other relevant output information besides the tile_name

        # If the min distance is smaller than the diagonal distance to the edge of the image from its center,
        # we have found the closest tile and the annotation is within that tile.
        # If the distance is larger than the diagonal distance to the edge, the annotation is not inside of any tile
        # and thus shouldn't be exported
        # This calculation contains the assumption that the image dimensions & pixel size of the first square
        # is applicable for all squares
        first_square = self.squares[list(self.squares.keys())[0]]
        distance_threshold = np.square(first_square['img_height'] / 2 * first_square['pixel_size']) + \
                             np.square(first_square['img_width'] / 2 * first_square['pixel_size'])

        for annotation_name in self.annotations:
            a_coordinates = np.array([self.annotations[annotation_name]['StagePosition_x'],
                                      self.annotations[annotation_name]['StagePosition_y']])
            distance_map = np.square(np.array(self.tile_center_stage_positions) - a_coordinates)
            quandratic_distance = distance_map[:, 0] + distance_map[:, 1]
            tile_index = np.argmin(quandratic_distance)
            # noinspection PyTypeChecker
            current_tile = self.tiles[self.tile_names[tile_index][1]]

            if quandratic_distance[tile_index] < distance_threshold:
                self.annotation_tiles[annotation_name] = current_tile
            else:
                print('WARNING! Annotation {} is not within any of the tiles and will be ignored'.format(annotation_name))

            # TODO: Calculate the position of the fork within the image and return it as well

    def determine_surrounding_sites(self):
        # Take in the center tile and determine the names & existence of stitch_radius tiles around it.
        # In default stitch-radius = 1, it searches for the 8 tiles surrounding the center tile
        for annotation_name in self.annotation_tiles:
            center_filename = self.annotation_tiles[annotation_name]['filename']

            # self.annotation_tiles[annotation_name]['surrounding_tile_names']=[]
            self.annotation_tiles[annotation_name]['surrounding_tile_exists'] = []

            x = int(center_filename[5:8])
            y = int(center_filename[9:12])
            for i in range(-self.stitch_radius, self.stitch_radius + 1):
                for j in range(-self.stitch_radius, self.stitch_radius + 1):
                    # Create the filenames
                    new_filename = center_filename[:5] + f'{x+i:03}' + '-' + f'{y+j:03}' + center_filename[12:]
                    # self.annotation_tiles[annotation_name]['surrounding_tile_names'].append(new_filename)

                    # Check whether those files exist
                    img_path = self.convert_img_path_to_local_path(
                        self.annotation_tiles[annotation_name]['img_path']) / new_filename

                    if img_path.is_file():
                        self.annotation_tiles[annotation_name]['surrounding_tile_exists'].append(True)
                    else:
                        self.annotation_tiles[annotation_name]['surrounding_tile_exists'].append(False)


def main():
    pass
    project_folder_path = '/Volumes/staff/zmbstaff/7831/Raw_Data/Group Lopes/Sebastian/Projects/8330_siNeg_CPT_3rd/'
    highmag_layer = 'highmag'
    parser = Xml_MAPS_Parser(project_folder=project_folder_path, position_to_use=0,
                             name_of_highmag_layer=highmag_layer, stitch_radius=1)

    parser.parse_xml()
    # parser.extract_square_metadata()
    # parser.extract_annotation_locations()
    # parser.get_relative_tile_locations()
    # parser.calculate_absolute_tile_coordinates()
    # annotation_tiles = parser.find_annotation_tile()
    # print(annotation_tiles)
    # print(parser.tile_names)

    # print(parser.annotations)
    # print(parser.squares)
    # print(parser.tiles['28000 (6)_Tile_003-011-000000_0-000.tif'])
    # print(tile_center_stage_positions)
    # print(tile_names)


if __name__ == "__main__":
    main()

# Change to using findall() with full tags instead of matching end of tags
# for type_tag in root.findall('bar/type'):
#     value = type_tag.get('foobar')
#     print(value)
