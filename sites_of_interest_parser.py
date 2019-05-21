# Script that parses the Site of Interest annotations from a MAPS XML file
# Developed with data from MAPS Viewer 3.6

import xml.etree.ElementTree as ET
import sys
import numpy as np
import math
from pathlib import Path
import logging


class MapsXmlParser:
    """XML Parser class that processes MAPS XMLs and reveals the image tiles belonging to each annotation

    This class takes XML files from the Thermo MAPS Application, extracts the location of all its annotations and
    compares it to the location of all the image tiles. This gets a bit more complicated, because tiles only have a
    relative position in pixels within their layers and those layers are (potentially) turned at arbitrary angles
    relative to the global coordinate system (which is in meters).
    It is important that the functions are run in the correct order to extract & process this information. Therefore,
    use it by initializing the class and the calling parser.parse_xml().

    Args:
        project_folder (str): The path to the project folder of the MAPS project, containing the XML file, as a string
        name_of_highmag_layer (str): Name of the image layer in MAPS for which tiles containing annotations should
            be found. Defaults to 'highmag'
        use_unregistered_pos (bool): Whether to use the unregistered position of the tiles (where MAPS thinks it
            acquired them => True, default) or a calculated position (e.g. through stitching in MAPS) should be used for
            the tiles (False)
        stitch_radius (int): The number of images in each direction from the tile containing the annotation should be
            stitched. Parser doesn't do the stitching, just extracts relevant information about neighboring tiles.
            Defaults to 1 => 3x3 images would be stitched.

    Attributes:
        project_folder_path (str): The path to the project folder of the MAPS project, containing the XML file, as a
            string
        layers (dict): Contains information about the layers (squares/acquisitions). The keys are local paths to
            the metadata about the layer and the values are dictionaries again. Each layer contains the information
            about the stage position of the center of the layer (in meters, StagePosition_center_x &
            StagePosition_center_y), about the rotation of the layer relative to the global stage positions (in degrees,
            rotation), the number of columns of tiles (images) in the layer (columns), the vertical & horizontal overlap
            between the tiles (overlapVertical, overlapHorizontal), the number of rows of tiles (images) in the layer
            (rows), the horizontal field width of each tile (its width in meters, tileHfw), the horizontal field width
            of the whole layer (its width in meters, totalHfw), the name of the layer (layer_name), the vertical field
            width of each tile (its width in meters, tileVfw), and the global stage position of the corner of the layer
            (in meters, StagePosition_corner_x & StagePosition_corner_y)
        tiles (dict): Contains information about individual tiles. The keys are the combined layer name & filename of
            the tile and the values are a dictionary again. Each tile contains the information about what layer it
            belongs to (layer, key to the layer dict), the path to the image as a Path variable (img_path), its
            filename, the name of the layer (layer_name) and its relative position x & y within that layer
            (RelativeTilePosition_x & RelativeTilePosition_y)
        annotations (dict): Contains the information about all the annotations. The keys are the names of the
            annotations (MAPS enforces uniqueness), its values are a dictionary containing the StagePosition_x &
            StagePosition_y positions of the annotation (in m => global coordinate system for the experiment)
        annotation_tiles (dict): Contains the relevant output of the XML parsing. The keys are the names of the
            annotation. The values are the key to the corresponding layer in the layer dict (layer), the path to the
            image as a Path variable (img_path), its filename, the name of the layer (layer_name) and the relative
            position x & y of the tile within that layer (RelativeTilePosition_x & RelativeTilePosition_y), the
            absolute stage position of the annotation (Annotation_StagePosition_x and Annotation_StagePosition_y), the
            position of the annotation within the tile image (in pixels, Annotation_img_position_x &
            Annotation_img_position_y), a list of the surrounding tile names (surrounding_tile_names) and a list of
            booleans of whether each of the surrounding tiles exist, including the tile itself (surrounding_tile_exists)
        stitch_radius (int): The number of images in each direction from the tile containing the annotation should be
            stitched.
        pixel_size (float): The pixel size of the acquisition in the name_of_highmag_layer [in meters]
        img_height (int): The height of the highmag image in pixels
        img_width (int): The width of the highmag image in pixels

    """

    def __init__(self, project_folder: str, name_of_highmag_layer: str = 'highmag', use_unregistered_pos: bool = True,
                 stitch_radius: int = 1):
        self.project_folder_path = Path(project_folder)
        self.layers = {}
        self.tiles = {}
        self.annotations = {}
        self.annotation_tiles = {}
        self.stitch_radius = stitch_radius
        self.pixel_size = 0.0

        # Usage of width and height may be switched, as Talos images are always square and
        # I couldn't test non-square images
        self.img_height = 0
        self.img_width = 0

        # Internal variables
        self._name_of_highmag_layer = name_of_highmag_layer
        xml_file_name = 'MapsProject.xml'
        xml_file_path = self.project_folder_path / xml_file_name
        self._xml_file = self.load_xml(xml_file_path)
        self._tile_names = []
        self._tile_center_stage_positions = []

        if use_unregistered_pos:
            self._position_to_extract = 'UnalignedPosition'
        else:
            self._position_to_extract = 'CalculatedPosition'

    @staticmethod
    def load_xml(xml_file_path):
        """Loads and returns the MAPS XML File

        Args:
            xml_file_path (Path): Path to the XML file as a pathlib path

        Returns:
            root: The root of the XML file parsed with xml.etree.ElementTree

        """
        try:
            root = ET.parse(xml_file_path).getroot()
        except FileNotFoundError:
            print("Can't find the MAPS XML File at the location {}".format(xml_file_path))
            sys.exit(-1)
        return root

    def parse_xml(self):
        """Run function for the class

        parse_xml calls all the necessary functions of the class in the correct order to parse the XML file. Call this
        function after initializing a class object, then access the results via the annotation_tiles variable

        Returns:
            annotation_tiles (dict): Contains the relevant output of the XML parsing. The keys are the names of the
                annotation. The values are the key to the corresponding layers in the layers dict (layers), the path to
                the image as a Path variable (img_path), its filename, the name of the layers (layer_name) and the
                relative position x & y of the tile within that layers (RelativeTilePosition_x &
                RelativeTilePosition_y), the absolute stage position of the annotation (Annotation_StagePosition_x and
                Annotation_StagePosition_y), the position of the annotation within the tile image (in pixels,
                Annotation_img_position_x & Annotation_img_position_y), a list of the surrounding tile names
                (surrounding_tile_names) and a list of booleans of whether each of the surrounding tiles exist,
                including the tile itself (surrounding_tile_exists)

        """
        self.extract_layer_metadata()
        self.extract_annotation_locations()
        self.get_relative_tile_locations()
        self.calculate_absolute_tile_coordinates()
        self.find_annotation_tile()
        self.determine_surrounding_tiles()
        return self.annotation_tiles

    @staticmethod
    def convert_windows_pathstring_to_path_object(string_path):
        """Converts a windows path string to a path object

        Some paths are provided in the XML file and the metadata as Windows paths. This function creates pathlib Path
        objects out of them.

        Args:
            string_path (str): String of a Windows path containing double backslashes

        Returns:
            path: Path object of the string_path

        """
        folders = string_path.split('\\')
        path = Path()
        for folder in folders:
            path = path / folder
        return path

    def convert_img_path_to_local_path(self, img_path):
        """Converts a local path of the microscope computer to a path of the image in the project folder

        MAPS saves the image paths of the local storage of the image files. In our setup, this path starts with
        'D:\\ProjectName', even though the files aren't actually on the D drive anymore but were copied to a share, into
        the project_folder_path. This function strips 'D:\\ProjectName' away from the path and returns a Path object for
        the location of the images on the share.

        Args:
            img_path (str): Original path to the images on the microscope computer, starting with 'D:\\ProjectName'

        Returns:
            path: Path object of the corrected path on the share

        """
        folders = img_path.split('\\')
        path = self.project_folder_path
        for folder in folders[2:]:
            path = path / folder
        return path

    def extract_layer_metadata(self):
        """Extract the information about all the layers in the high magnification acquisition layers

        Go through the XML file and look at the _name_of_highmag_layer layers group. Within that layers group, get only
        the layers (acquisitions/squares) that contain microscope images (TileLayer), not any annotation layers or
        others. Save them to the self.layers dictionary in the following way: The keys are local paths to
        the metadata about the layers and the values are dictionaries again. Each layers contains the information
        about the stage position of the center of the layers (in meters, StagePosition_center_x &
        StagePosition_center_y), about the rotation of the layers relative to the global stage positions (in degrees,
        rotation), the number of columns of tiles (images) in the layers (columns), the vertical & horizontal overlap
        between the tiles (overlapVertical, overlapHorizontal), the number of rows of tiles (images) in the layers
        (rows), the horizontal field width of each tile (its width in meters, tileHfw), the horizontal field width of
        the whole layers (its width in meters, totalHfw) and the name of the layers (layer_name).
        In a calculate_absolute_tile_coordinates, StagePosition_corner_x and StagePosition_corner_y are calculated and
        added to the layers dictionary.

        Note:
            The parsing is quite ugly with all the if statements, because the tags have huge names and it's easier just
            to check for what the tags end in.

        """
        # Extract the information about all the layers (high magnification acquisition layers)
        for child in self._xml_file:
            if child.tag.endswith('LayerGroups'):
                for grand_child in child:
                    for ggc in grand_child:

                        # Get the path to the metadata xml files for all the highmag layers,
                        # the pixel size and the StagePosition of the layers
                        if ggc.tag.endswith('displayName') and ggc.text == self._name_of_highmag_layer:
                            logging.info('Extracting images from {} layers'.format(ggc.text))

                            for highmag in grand_child:
                                if highmag.tag.endswith('Layers'):
                                    for layer in highmag:
                                        # Check if this layers is a TileLayer or any other kind of layers.
                                        # Only proceed to process TileLayers
                                        layer_type = layer.attrib['{http://www.w3.org/2001/XMLSchema-instance}type']
                                        if layer_type == 'TileLayer':
                                            for layer_content in layer:
                                                if layer_content.tag.endswith('metaDataLocation'):
                                                    metadata_location = layer_content.text
                                                    self.layers[metadata_location] = {}
                                            try:
                                                for layer_content in layer:
                                                    if layer_content.tag.endswith('totalHfw'):
                                                        # noinspection PyUnboundLocalVariable
                                                        self.layers[metadata_location]['totalHfw'] = float(
                                                            list(layer_content.attrib.values())[1])

                                                    if layer_content.tag.endswith('tileHfw'):
                                                        # noinspection PyUnboundLocalVariable
                                                        self.layers[metadata_location]['tileHfw'] = float(
                                                            list(layer_content.attrib.values())[1])

                                                    if layer_content.tag.endswith('overlapHorizontal'):
                                                        # noinspection PyUnboundLocalVariable
                                                        self.layers[metadata_location]['overlapHorizontal'] = float(
                                                            layer_content[0].text) / 100.
                                                    if layer_content.tag.endswith('overlapVertical'):
                                                        # noinspection PyUnboundLocalVariable
                                                        self.layers[metadata_location]['overlapVertical'] = float(
                                                            layer_content[0].text) / 100.

                                                    if layer_content.tag.endswith('rotation'):
                                                        # noinspection PyUnboundLocalVariable
                                                        self.layers[metadata_location]['rotation'] = float(
                                                            list(layer_content.attrib.values())[1])

                                                    if layer_content.tag.endswith('rows'):
                                                        # noinspection PyUnboundLocalVariable
                                                        self.layers[metadata_location]['rows'] = \
                                                            int(layer_content.text)

                                                    if layer_content.tag.endswith('columns'):
                                                        # noinspection PyUnboundLocalVariable
                                                        self.layers[metadata_location]['columns'] = \
                                                            int(layer_content.text)

                                                    if layer_content.tag.endswith('scanResolution'):
                                                        for scanres_info in layer_content:
                                                            if scanres_info.tag.endswith('height'):
                                                                height = int(scanres_info.text)
                                                                if self.img_height == height or self.img_height == 0:
                                                                    self.img_height = height
                                                                else:
                                                                    raise Exception(
                                                                        'Image height needs to be constant for the '
                                                                        'whole {} layers. It was {} before and is {} '
                                                                        'in the current layers'.format(
                                                                            self._name_of_highmag_layer,
                                                                            self.img_height, height))
                                                            if scanres_info.tag.endswith('width'):
                                                                width = int(scanres_info.text)
                                                                if self.img_width == width or self.img_width == 0:
                                                                    self.img_width = width
                                                                else:
                                                                    raise Exception(
                                                                        'Image width needs to be constant for the '
                                                                        'whole {} layers. It was {} before and is {} '
                                                                        'in the current layers'.format(
                                                                            self._name_of_highmag_layer,
                                                                            self.img_width, width))

                                                    if layer_content.tag.endswith('pixelSize'):
                                                        pixel_size = float(layer_content.attrib['Value'])
                                                        if self.pixel_size == pixel_size or self.pixel_size == 0:
                                                            self.pixel_size = pixel_size
                                                        else:
                                                            raise Exception('Pixel size needs to be constant for the '
                                                                            'whole {} layers. It was {} before and is '
                                                                            '{} in the current layers'.format(
                                                                                self._name_of_highmag_layer,
                                                                                self.pixel_size, pixel_size))

                                                    if layer_content.tag.endswith('StagePosition'):
                                                        for positon_info in layer_content:
                                                            if positon_info.tag == '{http://schemas.datacontract.org/' \
                                                                                   '2004/07/Fei.Applications.SAL}x':
                                                                # noinspection PyUnboundLocalVariable
                                                                self.layers[metadata_location][
                                                                    'StagePosition_center_x'] = float(positon_info.text)
                                                            elif positon_info.tag == '{http://schemas.datacontract' \
                                                                                     '.org/2004/07/Fei.Applications' \
                                                                                     '.SAL}y':
                                                                # noinspection PyUnboundLocalVariable
                                                                self.layers[metadata_location][
                                                                    'StagePosition_center_y'] = float(positon_info.text)
                                            except NameError:
                                                print("Can't find the metaDataLocation in the MAPS XML File")
                                                sys.exit(-1)

    def extract_annotation_locations(self):
        """Extract annotation metadata from the XML file


        Goes through all the LayerGroups and looks at any layer in any LayerGroup that is an Annotation Layer. Get all
        x & y positions of the annotations & the annotation name and save them in the annotations dictionary.
        The keys are the names of the annotations (MAPS enforces uniqueness), its values are a dictionary containing the
        StagePosition_x & StagePosition_y positions of the annotation (in m => global coordinate system for the
        experiment)

        """
        # Get all x & y positions of the annotations & the annotation name and save them in a dictionary.
        # Keys are the annotation names, values are a dictionary of x & y positions of that annotation
        for child in self._xml_file:
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
                                                if a.tag == '{http://schemas.datacontract.org/' \
                                                            '2004/07/Fei.Applications.SAL}x':
                                                    # noinspection PyUnboundLocalVariable
                                                    self.annotations[annotation_name]['StagePosition_x'] = float(a.text)
                                                elif a.tag == '{http://schemas.datacontract.org/' \
                                                              '2004/07/Fei.Applications.SAL}y':
                                                    # noinspection PyUnboundLocalVariable
                                                    self.annotations[annotation_name]['StagePosition_y'] = float(a.text)
                                except NameError:
                                    print("Can't find the Annotations Names in the MAPS XML File")
                                    sys.exit(-1)

    def get_relative_tile_locations(self):
        """Read in all the metadata files for the different layers to get the relative tile positions

        Each layer has its own metadata XML file that contains the relative positions of all the tiles in the layer.
        This function goes through all of them, extracts the information and saves it to the tiles dictionary.
        The keys are the combined layer name & filename of the tile and the values are a dictionary again. Each tile
        contains the information about what layer it belongs to (layer, key to the layer dict), the path to the image as
        a Path variable (img_path), its filename, the name of the layer (layer_name) and its relative position x & y
        within that layer (RelativeTilePosition_x & RelativeTilePosition_y)

        """
        metadata_filename = 'StitchingData.xml'
        for metadata_location in self.layers:
            tile_image_folder_path = ''
            metadata_path = self.project_folder_path.joinpath(
                self.convert_windows_pathstring_to_path_object(metadata_location)) / metadata_filename
            metadata_root = ET.parse(metadata_path).getroot()
            for metadata_child in metadata_root:
                if metadata_child.tag.endswith('tileSet'):
                    for metadata_grandchild in metadata_child:
                        if metadata_grandchild.tag.endswith('TileImageFolder'):
                            tile_image_folder_path = metadata_grandchild.text
                            current_layer = tile_image_folder_path.split('\\')[-1]
                            self.layers[metadata_location]['layer_name'] = current_layer

                        if metadata_grandchild.tag.endswith('_tileCollection'):
                            for ggc in metadata_grandchild:
                                if ggc.tag.endswith('_innerCollection'):
                                    for gggc in ggc:
                                        for keyvalue in gggc:
                                            if keyvalue.tag.endswith('Value'):
                                                for value in keyvalue:
                                                    if value.tag.endswith('ImageFileName'):
                                                        # noinspection PyUnboundLocalVariable
                                                        tile_name = current_layer + '_' + value.text
                                                        self.tiles[tile_name] = {'layers': metadata_location,
                                                                                 'img_path': self.convert_img_path_to_local_path(tile_image_folder_path),
                                                                                 'filename': value.text,
                                                                                 'layer_name': current_layer}

                                                for value in keyvalue:
                                                    if value.tag.endswith('PositioningDetails'):
                                                        for positioning_detail in value:
                                                            if positioning_detail.tag.endswith(
                                                                    self._position_to_extract):
                                                                for position in positioning_detail:

                                                                    if position.tag == '{http://schemas.datacontract.' \
                                                                                       'org/2004/07/System.Drawing}x':
                                                                        # noinspection PyUnboundLocalVariable
                                                                        self.tiles[tile_name][
                                                                            'RelativeTilePosition_x'] = float(
                                                                            position.text)
                                                                    elif position.tag == '{http://schemas.' \
                                                                                         'datacontract.org/2004/07/' \
                                                                                         'System.Drawing}y':
                                                                        # noinspection PyUnboundLocalVariable
                                                                        self.tiles[tile_name][
                                                                            'RelativeTilePosition_y'] = float(
                                                                            position.text)

    def calculate_absolute_tile_coordinates(self):
        """Calculate the absolute stage positions of all tiles based on their relative positions

        Calculate the absolute stage position of the center of each tile based on the relative tile positions, the
        rotation of the layer and the absolute stage position of the center of the layer. The resulting position is
        saved to the _tile_center_stage_positions and the corresponding tile name to the _tile_names list.

        """
        for current_layer_key in self.layers:
            current_layer = self.layers[current_layer_key]

            # Unsure if it's height/width or width/height because they are always the same on Talos
            current_layer['tileVfw'] = self.img_height / self.img_width * current_layer['tileHfw']

            horizontal_field_width = (current_layer['columns'] - 1) * current_layer['tileHfw'] * (
                    1 - current_layer['overlapHorizontal']) + current_layer['tileHfw']
            vertical_field_width = (current_layer['rows'] - 1) * current_layer['tileVfw'] * (
                    1 - current_layer['overlapHorizontal']) + current_layer['tileVfw']

            relative_0_x = current_layer['StagePosition_center_x'] - math.sin(
                current_layer['rotation'] / 180 * math.pi) * vertical_field_width / 2 + math.cos(
                current_layer['rotation'] / 180 * math.pi) * horizontal_field_width / 2
            relative_0_y = current_layer['StagePosition_center_y'] - math.cos(
                current_layer['rotation'] / 180 * math.pi) * vertical_field_width / 2 - math.sin(
                current_layer['rotation'] / 180 * math.pi) * horizontal_field_width / 2
            relative_0 = np.array([relative_0_x, relative_0_y])

            self.layers[current_layer_key]['StagePosition_corner_x'] = relative_0[0]
            self.layers[current_layer_key]['StagePosition_corner_y'] = relative_0[1]

            for current_tile_name in self.tiles:
                current_tile = self.tiles[current_tile_name]
                if current_tile['layers'] == current_layer_key:
                    relative_x_stepsize = np.array([self.pixel_size * math.cos(current_layer['rotation']
                                                                               / 180 * math.pi),
                                                    self.pixel_size * math.sin(current_layer['rotation']
                                                                               / 180 * math.pi)])
                    relative_y_stepsize = np.array([self.pixel_size * math.sin(current_layer['rotation']
                                                                               / 180 * math.pi),
                                                    self.pixel_size * math.cos(current_layer['rotation']
                                                                               / 180 * math.pi)])

                    # absolute_tile_pos is the position of the corner of the tile in absolute Stage Position
                    # coordinates, the tile_center_stage_position are the Stage Position coordinates of the tile
                    absolute_tile_pos = relative_0 + current_tile['RelativeTilePosition_x'] * relative_x_stepsize + \
                        current_tile['RelativeTilePosition_y'] * relative_y_stepsize
                    tile_center_stage_position = absolute_tile_pos + self.img_width / 2 * relative_x_stepsize + \
                        self.img_height / 2 * relative_y_stepsize

                    self._tile_center_stage_positions.append(tile_center_stage_position)
                    self._tile_names.append([current_layer['layer_name'], current_tile_name])

    # noinspection PyTypeChecker
    def find_annotation_tile(self):
        """Find the image tile in which each annotation is

        Based on the absolute stage position of the annotations and the calculated stage positions of the center of the
        tiles, this function calculates the tiles within which all annotation are and saves this information to the
        annotation_tiles dictionary. The keys are the names of the annotation. The values are the key to the
        corresponding layer in the layer dict (layer), the path to the image as a Path variable (img_path), its
        filename, the name of the layer (layer_name) and the relative position x & y of the tile within that layer
        (RelativeTilePosition_x & RelativeTilePosition_y), the absolute stage position of the annotation
        (Annotation_StagePosition_x and Annotation_StagePosition_y), the position of the annotation within the tile
        image (in pixels, Annotation_img_position_x & Annotation_img_position_y).
        The surrounding_tile_names and surrounding_tile_exists are added in determine_surrounding_tiles

        """
        # Give annotation_name, layers metadata key, layer_name, tile_name,
        # stage coordinates & pixel position in the image

        # If the min distance is smaller than the diagonal distance to the edge of the image from its center,
        # we have found the closest tile and the annotation is within that tile.
        # If the distance is larger than the diagonal distance to the edge, the annotation is not inside of any tile
        # and thus shouldn't be exported
        distance_threshold = np.square(self.img_height / 2 * self.pixel_size) + \
            np.square(self.img_width / 2 * self.pixel_size)

        for annotation_name in self.annotations:
            a_coordinates = np.array([self.annotations[annotation_name]['StagePosition_x'],
                                      self.annotations[annotation_name]['StagePosition_y']])
            distance_map = np.square(np.array(self._tile_center_stage_positions) - a_coordinates)
            quadratic_distance = distance_map[:, 0] + distance_map[:, 1]
            tile_index = np.argmin(quadratic_distance)
            current_tile = self.tiles[self._tile_names[tile_index][1]]

            if quadratic_distance[tile_index] < distance_threshold:
                self.annotation_tiles[annotation_name] = current_tile
                self.annotation_tiles[annotation_name]['Annotation_StagePosition_x'] = \
                    self.annotations[annotation_name]['StagePosition_x']
                self.annotation_tiles[annotation_name]['Annotation_StagePosition_y'] = \
                    self.annotations[annotation_name]['StagePosition_y']
                # Calculate the position of the fork within the image
                distance_to_center = (np.array(self._tile_center_stage_positions[tile_index]) - a_coordinates)

                # Calculation of annotation position is complicated, because of image rotation.
                rotation = self.layers[self.annotation_tiles[annotation_name]['layers']]['rotation']
                relative_x_stepsize = np.array([self.pixel_size * math.cos(rotation / 180 * math.pi),
                                                self.pixel_size * math.sin(rotation / 180 * math.pi)])
                relative_y_stepsize = np.array([self.pixel_size * math.sin(rotation / 180 * math.pi),
                                                self.pixel_size * math.cos(rotation / 180 * math.pi)])

                # Calculation based on the solution for the linear algebra problem Ax=b solved with Wolfram Alpha for x,
                # A being the relative step_sizes, x the x & y shifts & b being the distance to center.
                # This solution works for relative_y_stepsize[1] * relative_x_stepsize[0] !=
                # relative_x_stepsize[1] * relative_y_stepsize[0] and relative_y_stepsize[1] != 0
                # This generally seems to hold up for all rotations I have tried
                try:
                    x_shift = (relative_y_stepsize[1] * distance_to_center[0] - distance_to_center[1] *
                               relative_y_stepsize[0]) / (relative_y_stepsize[1] * relative_x_stepsize[0] -
                                                          relative_x_stepsize[1] * relative_y_stepsize[0])
                    y_shift = (relative_x_stepsize[1] * distance_to_center[0] - distance_to_center[1] *
                               relative_x_stepsize[0]) / (relative_x_stepsize[1] * relative_y_stepsize[0] -
                                                          relative_y_stepsize[1] * relative_x_stepsize[0])

                except ZeroDivisionError:
                    logging.warning('Formula for the calculation of the annotation position within the image '
                                    'does not work for these parameters, a rotation of {} leads to divison by 0. The '
                                    'annotation marker is placed in the middle of the image because the location '
                                    'could not be calculated'.format(rotation))
                    x_shift = 0
                    y_shift = 0

                annotation_img_position = [int(round(self.img_height / 2 - x_shift)),
                                           int(round(self.img_width / 2 - y_shift))]
                self.annotation_tiles[annotation_name]['Annotation_img_position_x'] = annotation_img_position[0]
                self.annotation_tiles[annotation_name]['Annotation_img_position_y'] = annotation_img_position[1]

            else:
                logging.warning('Annotation {} is not within any of the tiles and will be ignored'.
                                format(annotation_name))

    def determine_surrounding_tiles(self):
        """Checks whether each annotation tile has surrounding tiles to be stitched with it

        For each annotation tile, it checks whether the surrounding tiles in a given stitch_radius exist. It saves a
        boolean list of their existence (including its own existence) to surrounding_tile_exists and the a list of names
        of the surrounding filenames to surrounding_tile_names of the annotation_tiles dictionary

        """
        # Take in the center tile and determine the names & existence of stitch_radius tiles around it.
        # In default stitch-radius = 1, it searches for the 8 tiles surrounding the center tile
        for annotation_name in self.annotation_tiles:
            center_filename = self.annotation_tiles[annotation_name]['filename']

            self.annotation_tiles[annotation_name]['surrounding_tile_names'] = []
            self.annotation_tiles[annotation_name]['surrounding_tile_exists'] = []

            x = int(center_filename[5:8])
            y = int(center_filename[9:12])
            for i in range(-self.stitch_radius, self.stitch_radius + 1):
                for j in range(-self.stitch_radius, self.stitch_radius + 1):
                    # Create the filenames
                    new_filename = center_filename[:5] + f'{x+i:03}' + '-' + f'{y+j:03}' + center_filename[12:]
                    self.annotation_tiles[annotation_name]['surrounding_tile_names'].append(new_filename)

                    # Check whether those files exist
                    img_path = self.annotation_tiles[annotation_name]['img_path'] / new_filename

                    if img_path.is_file():
                        self.annotation_tiles[annotation_name]['surrounding_tile_exists'].append(True)
                    else:
                        self.annotation_tiles[annotation_name]['surrounding_tile_exists'].append(False)
