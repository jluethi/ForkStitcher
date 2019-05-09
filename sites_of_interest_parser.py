# Script that parses the Site of Interest annotations from a MAPS XML file

import xml.etree.ElementTree as ET
import os
import sys

project_folder_path = '/Users/Joel/Desktop/'
name_of_highmag_layer = 'highmag'

# In the samples I had, MAPS didn't show any aligned positions. Therefore, unaligned positions is what we want to
# extract. If positions are moved somehow in MAPS (I assume through stitching), calculatedPositions may be revelant
position_to_use = 0
position_to_extract = ['UnalignedPosition', 'CalculatedPosition']
xml_file_name = 'MapsProject.xml'

xml_file_path = os.path.join(project_folder_path, xml_file_name)

def extract_square_metadata(xml_file, name_of_highmag_layer):
    # Extract the information about all the squares (high magnification acquisition layers)
    squares = {}
    for child in xml_file:
        if child.tag.endswith('LayerGroups'):
            for grand_child in child:
                for ggc in grand_child:

                    # Get the path to the metadata xml files for all the highmag squares,
                    # the pixel size and the StagePosition of the square
                    if ggc.tag.endswith('displayName') and ggc.text == name_of_highmag_layer:
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
                                            squares[metadata_location] = {}

                                    try:
                                        for layer_content in square:
                                            if layer_content.tag.endswith('totalHfw'):
                                                # noinspection PyUnboundLocalVariable
                                                squares[metadata_location]['totalHfw'] = list(layer_content.attrib.values())[1]

                                            if layer_content.tag.endswith('tileHfw'):
                                                # noinspection PyUnboundLocalVariable
                                                squares[metadata_location]['tileHfw'] = list(layer_content.attrib.values())[1]

                                            if layer_content.tag.endswith('overlapHorizontal'):
                                                # noinspection PyUnboundLocalVariable
                                                squares[metadata_location]['overlapHorizontal'] = float(layer_content[0].text)/100.
                                            if layer_content.tag.endswith('overlapVertical'):
                                                # noinspection PyUnboundLocalVariable
                                                squares[metadata_location]['overlapVertical'] = float(layer_content[0].text)/100.

                                            if layer_content.tag.endswith('rotation'):
                                                # noinspection PyUnboundLocalVariable
                                                squares[metadata_location]['rotation'] = list(layer_content.attrib.values())[1]

                                            if layer_content.tag.endswith('rows'):
                                                # noinspection PyUnboundLocalVariable
                                                squares[metadata_location]['rows'] = int(layer_content.text)

                                            if layer_content.tag.endswith('columns'):
                                                # noinspection PyUnboundLocalVariable
                                                squares[metadata_location]['columns'] = int(layer_content.text)


                                            if layer_content.tag.endswith('pixelSize'):
                                                    # noinspection PyUnboundLocalVariable
                                                    squares[metadata_location]['pixel_size'] = layer_content.attrib['Value']

                                            if layer_content.tag.endswith('StagePosition'):
                                                for positon_info in layer_content:
                                                    if positon_info.tag == '{http://schemas.datacontract.org/2004/07/Fei.Applications.SAL}x':
                                                        # noinspection PyUnboundLocalVariable
                                                        squares[metadata_location]['StagePosition_center_x'] = float(positon_info.text)
                                                    elif positon_info.tag == '{http://schemas.datacontract.org/2004/07/Fei.Applications.SAL}y':
                                                        # noinspection PyUnboundLocalVariable
                                                        squares[metadata_location]['StagePosition_center_y'] = float(positon_info.text)
                                    except NameError:
                                        print("Can't find the metaDataLocation in the MAPS XML File")
                                        sys.exit(-1)
    return squares

def extract_annotation_locations(xml_file_path):
    # Get all x & y positions of the annotations & the annotation name and save them in a dictionary.
    # Keys are the annotation names, values are a dictionary of x & y positions of that annotation
    annotations = {}
    for child in root:
        if child.tag.endswith('LayerGroups'):
            for grand_child in child:
                for ggc in grand_child:
                    # Finds all the layers that contain annotation and reads out the annotation details
                    for gggc in ggc:
                        if gggc.tag.endswith('anyType') and 'AnnotationLayer' in gggc.attrib.values():
                            for annotation_content in gggc:
                                if annotation_content.tag.endswith('RealDisplayName'):
                                    annotation_name = annotation_content.text
                                    annotations[annotation_name] = {}
                            try:
                                for annotation_content in gggc:
                                    if annotation_content.tag.endswith('StagePosition'):
                                        for a in annotation_content:
                                            if a.tag == '{http://schemas.datacontract.org/2004/07/Fei.Applications.SAL}x':
                                                # noinspection PyUnboundLocalVariable
                                                annotations[annotation_name]['StagePosition_x'] = float(a.text)
                                            elif a.tag == '{http://schemas.datacontract.org/2004/07/Fei.Applications.SAL}y':
                                                # noinspection PyUnboundLocalVariable
                                                annotations[annotation_name]['StagePosition_y'] = float(a.text)
                            except NameError:
                                print("Can't find the Annotations Names in the MAPS XML File")
                                sys.exit(-1)
    return annotations

def get_relative_tile_locations(squares):
    tiles = {}
    # read in all the metadata files for the different squares to get tile positions
    metadata_filename = 'StitchingData.xml'
    for metadata_location in squares:
        tile_image_folder_path = ''
        metadata_root = ET.parse(os.path.join(project_folder_path, metadata_location, metadata_filename)).getroot()
        # print('1. ' + metadata_root.tag)
        for metadata_child in metadata_root:
            # print('2. ' + metadata_child.tag)

            if metadata_child.tag.endswith('tileSet'):

                for metadata_grandchild in metadata_child:
                    if metadata_grandchild.tag.endswith('TileImageFolder'):
                        tile_image_folder_path = metadata_grandchild.text
                        current_square = tile_image_folder_path.split('\\')[-1]
                        squares[metadata_location]['square_name'] = current_square

                    if metadata_grandchild.tag.endswith('_tileCollection'):
                        # print('3. ' + metadata_grandchild.tag)
                        for ggc in metadata_grandchild:
                            if ggc.tag.endswith('_innerCollection'):
                                # print('4. ' + ggc.tag)
                                for gggc in ggc:
                                    # print('5. ' + gggc.tag)
                                    for keyvalue in gggc:
                                        if keyvalue.tag.endswith('Value'):
                                            for value in keyvalue:
                                                if value.tag.endswith('ImageFileName'):
                                                    tile_name = value.text
                                                    tiles[tile_name] = {'square' : metadata_location,
                                                                        'img_path': tile_image_folder_path}

                                            for value in keyvalue:
                                                # print('7. ' + value.tag)
                                                # print(value.attrib)
                                                # print(value.text)
                                                if value.tag.endswith('PositioningDetails'):
                                                    for positioning_detail in value:
                                                        # if positioning_detail.tag.endswith('CalculatedPosition'):
                                                        if positioning_detail.tag.endswith(position_to_extract[position_to_use]):
                                                            for position in positioning_detail:
                                                                # print('9. ' + position.tag)
                                                                # print(position.attrib)
                                                                # print(position.text)

                                                                if position.tag == '{http://schemas.datacontract.org/2004/07/System.Drawing}x':
                                                                    # noinspection PyUnboundLocalVariable
                                                                    tiles[tile_name]['SquarePosition_x'] = float(
                                                                        position.text)
                                                                elif position.tag == '{http://schemas.datacontract.org/2004/07/System.Drawing}y':
                                                                    # noinspection PyUnboundLocalVariable
                                                                    tiles[tile_name]['SquarePosition_y'] = float(
                                                                        position.text)
    return [squares, tiles]

# Load the MAPS XML File
try:
    root = ET.parse(xml_file_path).getroot()
except FileNotFoundError:
    print("Can't find the MAPS XML File at the location {}".format(xml_file_path))
    sys.exit(-1)

# squares = extract_square_metadata(root, name_of_highmag_layer)
# annotations = extract_annotation_locations(root)
# print(annotations)
# print(squares)

squares = {'MetaData': {'StagePosition_center_x': -0.0004954659535219988, 'StagePosition_center_y': 0.00022218860716983652, 'rotation': '90.026172973267862', 'columns': 22, 'overlapHorizontal': 0.1, 'overlapVertical': 0.1, 'pixel_size': '4.9912651789441043E-10', 'rows': 23, 'tileHfw': '2.0444222172955051E-06', 'totalHfw': '4.068400212418055E-05'}}

[squares, tiles] = get_relative_tile_locations(squares)

print(squares)
print(tiles)

# DO: Create absolute positions from the relative Tile positions
# Calculate the edge Stage position of the square based on the parameters extracted
current_square_key = (list(squares.keys())[0])
current_square = squares[current_square_key]
print(current_square)

# If the rotation is 90 degrees, the case is relatively simple

# Change to using findall() with full tags instead of matching end of tags
# for type_tag in root.findall('bar/type'):
#     value = type_tag.get('foobar')
#     print(value)



