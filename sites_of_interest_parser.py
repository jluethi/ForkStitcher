# Script that parses the Site of Interest annotations from a MAPS XML file

import xml.etree.ElementTree as ET
import os
import sys

project_folder_path = '/Users/Joel/Desktop/'
xml_file_path = '/Users/Joel/Desktop/MapsProject.xml'
name_of_highmag_layer = 'highmag'


# Load the MAPS XML File
try:
    root = ET.parse(xml_file_path).getroot()
except FileNotFoundError:
    print("Can't find the MAPS XML File at the location {}".format(xml_file_path))
    sys.exit(-1)

squares = {}
tiles = {}

# Get all x & y positions of the annotations & the annotation name and save them in a dictionary.
# Keys are the annotation names, values are a dictionary of x & y positions of that annotation
# Also extract the information about all the squares (high magnification acquisition layers)
annotations = {}
for child in root:
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

print(annotations)
print(squares)

metadata_filename = 'StitchingData.xml'
squares = {'Metadata': {'StagePosition_center_x': -0.0004954659535219988, 'StagePosition_center_y': 0.00022218860716983652, 'pixel_size': '4.9912651789441043E-10'}}

# read in all the metadata files for the different squares to get tile positions
for metadata_location in squares:
    tile_image_folder_path = ''
    current_square = ''
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
                                                    if positioning_detail.tag.endswith('CalculatedPosition'):
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

print(squares)
print(tiles)

# DO: Create absolute positions from the relative Tile positions


# for type_tag in root.findall('bar/type'):
#     value = type_tag.get('foobar')
#     print(value)



# Change to using findall() with full tags instead of matching end of tags

# Desired output: A dictionary with the name of the annotation (displayName) as key and a list of all relevant info as value
# (Filename, maybe square, position)


