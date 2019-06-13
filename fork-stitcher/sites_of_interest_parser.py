# Script that parses the Site of Interest annotations from a MAPS XML file
# Developed with data from MAPS Viewer 3.6

import xml.etree.ElementTree as ET
import csv
import ast
import numpy as np
import pandas as pd
import math
from pathlib import Path
import logging
import copy
import multiprocessing


class XmlParsingFailed(Exception):
    def __init__(self, message):
        logging.error(message)


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
            position of the annotation within the tile image (in pixels, Annotation_tile_img_position_x &
            Annotation_tile_img_position_y), a list of the surrounding tile names (surrounding_tile_names) and a list of
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
            raise XmlParsingFailed("Can't find the MAPS XML File at the location {}".format(xml_file_path))
        return root

    def parse_xml(self):
        """Run function for the class

        parse_xml calls all the necessary functions of the class in the correct order to parse the XML file. Call this
        function after initializing a class object, then access the results via the annotation_tiles variable that
        contains the relevant output of the XML parsing

        Returns:
            dict: annotation_tiles

        """
        self.extract_layers_and_annotations()
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
        try:
            layersdata_index = folders.index('LayersData')
        except ValueError:
            raise XmlParsingFailed('Could not find the folder LayersData that should contain the raw data in the '
                                   'filepath for the iamge_files: {}'.format(img_path))
        for folder in folders[layersdata_index:]:
            path = path / folder
        return path

    @staticmethod
    def create_logger(log_file_path, multiprocessing_logger: bool = False):
        """ Returns a logger and creates it if it doesn't yet exist

        Gets the correct logger for normal or multiprocessing. If it already exists, just returns this logger. If it
        doesn't exist yet, sets it up correctly.

        Args:
            log_file_path (str): Path to the log file
            multiprocessing_logger (bool): Whether a multiprocessing logger is needed. Defaults to False.

        Returns:
            logger: Logger object that has the correct handlers

        """
        if multiprocessing_logger:
            logger = multiprocessing.get_logger()
            logger.setLevel(logging.INFO)
            logger.propagate = True
        else:
            logger = logging.getLogger(__name__)

        # If the logger doesn't have any handlers yet, add them. Otherwise, just return the logger
        if not len(logger.handlers):
            logger.setLevel(logging.INFO)

            formatter = logging.Formatter('%(asctime)s : %(levelname)s : %(message)s')

            # Create file logging handler
            fh = logging.FileHandler(log_file_path)
            fh.setLevel(logging.INFO)
            fh.setFormatter(formatter)
            logger.addHandler(fh)

            # Create console logging handler
            ch = logging.StreamHandler()
            ch.setLevel(logging.INFO)
            logger.addHandler(ch)

        return logger

    def extract_layers_and_annotations(self, check_for_annotations: bool = True):
        """Extract the information about all the layers in the high magnification acquisition layers and the annotations

        Go through the XML file and submit all LayerGroups for processing. The LayerGroups contain both the Layer with
        the _name_of_highmag_layer (=> the actual images) as well as the Annotation Layers containing the annotations.
        At the end of processing, check whether the self.layers and the self.annotations dictionaries were filled. If
        one of them was not filled, the parser could not find the highmag images or the annotations and raises an
        exception.

        Args:
            check_for_annotations (bool): Whether the parsing should check for the existence of annotations and throw an
                error if none are found. Defaults to True, thus checking for annotations.

        """
        # Extract the information about all the layers (high magnification acquisition layers)
        for xml_category in self._xml_file:
            if xml_category.tag.endswith('LayerGroups'):
                for sub_category in xml_category:
                    if sub_category.tag.endswith('LayerGroup'):
                        self._process_layer_group(sub_category)

        # If the parsing did not find any tiles, raise an error
        if not self.layers:
            raise XmlParsingFailed('Parsing the XML File did not find any tiles (images). Therefore, cannot map '
                                   'annotations')

        if check_for_annotations and not self.annotations:
            raise XmlParsingFailed('No annotations were found on tiles. Are there annotations in the MAPS project? '
                                   'Are those annotations on the highmag tiles? If so, there may be an issue with the '
                                   'calculation of the positions of the annotations. Check whether '
                                   'find_annotation_tile gave any warnings.')

    def _process_layer_group(self, layer_group):
        """Recursively go through the LayerGroup and send TileLayer & AnnotationLayer for processing

        Goes through a given LayerGroup. If there are nested LayerGroups, it calls the function recursively. If a Layer
        is a TileLayer and its name is the name of the highmag layer, it sends it for processing to
        self._process_tile_layer. If a Layer is a Annotation Layer (independent of whether it's in a Layer Group that
        has the highmag name or not), it is sent for processing in self._extract_annotation_locations.

        Args:
            layer_group: Part of the XML object that contains the information for a LayerGroup

        """
        log_file_path = str(self.project_folder_path / (self.project_folder_path.name + '.log'))
        logger = self.create_logger(log_file_path)
        for ggc in layer_group:
            # Get the path to the metadata xml files for all the highmag layers,
            # the pixel size and the StagePosition of the layers
            if ggc.tag.endswith('displayName') and ggc.text == self._name_of_highmag_layer:
                logger.info('Extracting images from {} layers'.format(ggc.text))

                for highmag in layer_group:
                    if highmag.tag.endswith('Layers'):
                        for layer in highmag:
                            # Check if this layers is a TileLayer or any other kind of layers.
                            # Only proceed to process TileLayers
                            layer_type = layer.attrib['{http://www.w3.org/2001/XMLSchema-instance}type']
                            if layer_type == 'TileLayer':
                                self._process_tile_layer(layer)
                            elif layer_type == 'LayerGroup':
                                # If there are nested LayerGroups, recursively call the function again
                                # with this LayerGroup
                                self._process_layer_group(layer)
                            elif layer_type == 'AnnotationLayer':
                                self._extract_annotation_locations(layer)
                            else:
                                logger.warning('XML Parser does not know how to deal with {} Layers and '
                                               'therefore does not parse them'.format(layer_type))
            else:
                if ggc.tag.endswith('Layers'):
                    for layer in ggc:
                        layer_type = layer.attrib['{http://www.w3.org/2001/XMLSchema-instance}type']
                        if layer_type == 'AnnotationLayer':
                            self._extract_annotation_locations(layer)
                        elif layer_type == 'LayerGroup':
                            # If there are nested LayerGroups, recursively call the function again
                            # with this LayerGroup
                            self._process_layer_group(layer)

    def _process_tile_layer(self, layer):
        """Extracts all necessary information of a highmag Tile Layer and saves it to self.layers

        Args:
            layer: Part of the XML object that contains the information for a TileLayer

        """
        layer_type = layer.attrib['{http://www.w3.org/2001/XMLSchema-instance}type']
        assert (layer_type == 'TileLayer')
        for layer_content in layer:
            if layer_content.tag.endswith('metaDataLocation'):
                metadata_location = layer_content.text
                self.layers[metadata_location] = {}
        try:
            for layer_content in layer:
                if layer_content.tag.endswith('totalHfw'):
                    # noinspection PyUnboundLocalVariable
                    self.layers[metadata_location]['totalHfw'] = float(list(layer_content.attrib.values())[1])

                if layer_content.tag.endswith('tileHfw'):
                    # noinspection PyUnboundLocalVariable
                    self.layers[metadata_location]['tileHfw'] = float(list(layer_content.attrib.values())[1])

                if layer_content.tag.endswith('overlapHorizontal'):
                    # noinspection PyUnboundLocalVariable
                    self.layers[metadata_location]['overlapHorizontal'] = float(layer_content[0].text) / 100.
                if layer_content.tag.endswith('overlapVertical'):
                    # noinspection PyUnboundLocalVariable
                    self.layers[metadata_location]['overlapVertical'] = float(layer_content[0].text) / 100.

                if layer_content.tag.endswith('rotation'):
                    # noinspection PyUnboundLocalVariable
                    self.layers[metadata_location]['rotation'] = float(list(layer_content.attrib.values())[1])

                if layer_content.tag.endswith('rows'):
                    # noinspection PyUnboundLocalVariable
                    self.layers[metadata_location]['rows'] = int(layer_content.text)

                if layer_content.tag.endswith('columns'):
                    # noinspection PyUnboundLocalVariable
                    self.layers[metadata_location]['columns'] = int(layer_content.text)

                if layer_content.tag.endswith('scanResolution'):
                    for scanres_info in layer_content:
                        if scanres_info.tag.endswith('height'):
                            height = int(scanres_info.text)
                            if self.img_height == height or self.img_height == 0:
                                self.img_height = height
                            else:
                                raise Exception(
                                    'Image height needs to be constant for the whole {} layer. It was {} before and '
                                    'is {} in the current layer'.format(self._name_of_highmag_layer,
                                                                        self.img_height, height))
                        if scanres_info.tag.endswith('width'):
                            width = int(scanres_info.text)
                            if self.img_width == width or self.img_width == 0:
                                self.img_width = width
                            else:
                                raise Exception(
                                    'Image width needs to be constant for the whole {} layer. It was {} before and '
                                    'is {} in the current layer'.format(self._name_of_highmag_layer,
                                                                        self.img_width, width))

                if layer_content.tag.endswith('pixelSize'):
                    pixel_size = float(layer_content.attrib['Value'])
                    if self.pixel_size == pixel_size or self.pixel_size == 0:
                        self.pixel_size = pixel_size
                    else:
                        raise Exception('Pixel size needs to be constant for the whole {} layer. It was {} before and '
                                        'is {} in the current layer'.format(self._name_of_highmag_layer,
                                                                            self.pixel_size, pixel_size))

                if layer_content.tag.endswith('StagePosition'):
                    for positon_info in layer_content:
                        if positon_info.tag == '{http://schemas.datacontract.org/2004/07/Fei.Applications.SAL}x':
                            # noinspection PyUnboundLocalVariable
                            self.layers[metadata_location][
                                'StagePosition_center_x'] = float(positon_info.text)
                        elif positon_info.tag == '{http://schemas.datacontract.org/2004/07/Fei.Applications.SAL}y':
                            # noinspection PyUnboundLocalVariable
                            self.layers[metadata_location][
                                'StagePosition_center_y'] = float(positon_info.text)
        except NameError:
            raise XmlParsingFailed("Can't find the metaDataLocation in the MAPS XML File")

    def _extract_annotation_locations(self, annotation_layer):
        """Extract annotation metadata from the XML file and saves them to the self.annotations dictionary

        Only Sites Of Interest Annotations are processed. Areas of Interest are ignored. Gets the
        x & y position of the annotation & the annotation name and saves them in the annotations dictionary.
        The keys are the names of the annotations (MAPS enforces uniqueness), its values are a dictionary containing the
        StagePosition_x & StagePosition_y positions of the annotation (in m => global coordinate system for the
        experiment)

        """
        for potential_annotation_content in annotation_layer:
            # Only check Sites Of Interest, not Area of Interest. Both are Annotation Layers, but Areas of Interest
            # have the isArea value as true
            if potential_annotation_content.tag.endswith('isArea') and potential_annotation_content.text == 'false':
                for annotation_content in annotation_layer:
                    if annotation_content.tag.endswith('RealDisplayName'):
                        annotation_name = annotation_content.text
                        self.annotations[annotation_name] = {}
                try:
                    for annotation_content in annotation_layer:
                        if annotation_content.tag.endswith('StagePosition'):
                            for a in annotation_content:
                                if a.tag == '{http://schemas.datacontract.org/2004/07/Fei.Applications.SAL}x':
                                    # noinspection PyUnboundLocalVariable
                                    self.annotations[annotation_name]['StagePosition_x'] = float(a.text)
                                elif a.tag == '{http://schemas.datacontract.org/2004/07/Fei.Applications.SAL}y':
                                    # noinspection PyUnboundLocalVariable
                                    self.annotations[annotation_name]['StagePosition_y'] = float(a.text)
                except NameError:
                    raise XmlParsingFailed("Can't find the Annotations Names in the MAPS XML File")

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
                                                                                 'img_path': self.convert_img_path_to_local_path(
                                                                                     tile_image_folder_path),
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
                    absolute_tile_pos = relative_0 + current_tile['RelativeTilePosition_x'] * relative_x_stepsize \
                                        + current_tile['RelativeTilePosition_y'] * relative_y_stepsize
                    tile_center_stage_position = absolute_tile_pos + self.img_width / 2 * relative_x_stepsize \
                                                 + self.img_height / 2 * relative_y_stepsize

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
        image (in pixels, Annotation_tile_img_position_x & Annotation_tile_img_position_y).
        The surrounding_tile_names and surrounding_tile_exists are added in determine_surrounding_tiles

        """
        # If the min distance is smaller than the diagonal distance to the edge of the image from its center,
        # we have found the closest tile and the annotation is within that tile.
        # If the distance is larger than the diagonal distance to the edge, the annotation is not inside of any tile
        # and thus shouldn't be exported
        log_file_path = str(self.project_folder_path / (self.project_folder_path.name + '.log'))
        logger = self.create_logger(log_file_path)
        distance_threshold = np.square(self.img_height / 2 * self.pixel_size) \
                             + np.square(self.img_width / 2 * self.pixel_size)

        for annotation_name in self.annotations:
            a_coordinates = np.array([self.annotations[annotation_name]['StagePosition_x'],
                                      self.annotations[annotation_name]['StagePosition_y']])
            distance_map = np.square(np.array(self._tile_center_stage_positions) - a_coordinates)
            quadratic_distance = distance_map[:, 0] + distance_map[:, 1]
            tile_index = np.argmin(quadratic_distance)
            current_tile = self.tiles[self._tile_names[tile_index][1]]

            if quadratic_distance[tile_index] < distance_threshold:
                self.annotation_tiles[annotation_name] = copy.deepcopy(current_tile)
                self.annotation_tiles[annotation_name]['pixel_size'] = self.pixel_size
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
                    logger.warning('Formula for the calculation of the annotation position within the image '
                                   'does not work for these parameters, a rotation of {} leads to divison by 0. The '
                                   'annotation marker is placed in the middle of the image because the location '
                                   'could not be calculated'.format(rotation))
                    x_shift = 0
                    y_shift = 0

                annotation_img_position = [int(round(self.img_height / 2 - x_shift)),
                                           int(round(self.img_width / 2 - y_shift))]
                self.annotation_tiles[annotation_name]['Annotation_tile_img_position_x'] = annotation_img_position[0]
                self.annotation_tiles[annotation_name]['Annotation_tile_img_position_y'] = annotation_img_position[1]

            else:
                logger.warning('Annotation {} is not within any of the tiles and will be ignored'
                               .format(annotation_name))

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
                    new_filename = center_filename[:5] + f'{x + i:03}' + '-' + f'{y + j:03}' + center_filename[12:]
                    self.annotation_tiles[annotation_name]['surrounding_tile_names'].append(new_filename)

                    # Check whether those files exist
                    img_path = self.annotation_tiles[annotation_name]['img_path'] / new_filename

                    if img_path.is_file():
                        self.annotation_tiles[annotation_name]['surrounding_tile_exists'].append(True)
                    else:
                        self.annotation_tiles[annotation_name]['surrounding_tile_exists'].append(False)

    @staticmethod
    def save_annotation_tiles_to_csv(annotation_tiles, base_header, csv_path, batch_size=0):
        """Saves the information about all annotations to a csv file

        Goes through the annotation_tiles dictionary and saves it to a csv file. Overwrites any existing file in
        the same location. Can write everything into one csv file (default) or into multiple batches of a given size

        Args:
            annotation_tiles (dict): annotation tiles dictionary with a structure like self.annotation_tiles
            base_header (list): list of strings that will be headers but will not contain any content
            csv_path (Path): pathlib Path to the csv file that will be created. Must end in .csv
            batch_size (int): The size of each batch. Defaults to 0. If it's 0, everything is saved into one csv file.
                Otherwise, the dataframe is divided into batches of batch_size and saved to separate csv files

        Returns:
            list: list of all the paths to the saved csv files

        """
        assert (str(csv_path).endswith('.csv'))
        csv_files = []
        # Initialize empty csv file (or csv files if batch mode is used)
        base_header_2 = ['Image'] + base_header
        # If there are annotations, save them. Otherwise, log a warning.
        if annotation_tiles:
            header_addition = list(list(annotation_tiles.values())[0].keys())
            if batch_size == 0:
                csv_header = pd.DataFrame(columns=base_header_2 + header_addition)
                csv_header.to_csv(str(csv_path), index=False)
                csv_files.append(str(csv_path))
            else:
                nb_batches = int(math.ceil(len(annotation_tiles.keys()) / batch_size))
                for j in range(nb_batches):
                    csv_batch_path = str(csv_path)[:-4] + '_{}.csv'.format(f'{j:05}')
                    csv_header = pd.DataFrame(columns=base_header_2 + header_addition)
                    csv_header.to_csv(csv_batch_path, index=False)
                    csv_files.append(csv_batch_path)

            for i, annotation_name in enumerate(annotation_tiles):
                current_annotation = {'Image': annotation_name}
                for header in base_header:
                    current_annotation[header] = ''

                for info_key in annotation_tiles[annotation_name]:
                    current_annotation[info_key] = annotation_tiles[annotation_name][info_key]
                    if type(current_annotation[info_key]) == list:
                        current_annotation[info_key] = '[' + ','.join(map(str, current_annotation[info_key])) + ']'

                current_annotation_pd = pd.DataFrame(current_annotation, index=[0])

                # Default: everything is saved into one csv file
                if batch_size == 0:
                    with open(str(csv_path), 'a') as f:
                        current_annotation_pd.to_csv(f, header=False, index=False)
                else:
                    current_batch = int(i / batch_size)
                    csv_batch_path = str(csv_path)[:-4] + '_{}.csv'.format(f'{current_batch:05}')
                    with open(str(csv_batch_path), 'a') as f:
                        current_annotation_pd.to_csv(f, header=False, index=False)

            return csv_files

        else:
            return []

    @staticmethod
    def load_annotations_from_csv(base_header, csv_path):
        """Load the annotations saved by sites_of_interest_parser.save_annotation_tiles_to_csv

        Recreates a dictionary for all the contents except the columns of the base_header
        Parses the string of a list for surrounding_tile_exists & surrounding_tile_names back to a list

        Args:
            base_header (list): list of column headers that will be ignored when loading the data
            csv_path (Path): pathlib Path to the csv file that will be created. Must end in .csv

        Returns:
            dict: annotation_tiles

        """
        annotation_tiles = {}
        annotation_dataframe = pd.read_csv(str(csv_path))
        column_names = list(annotation_dataframe.columns.values)
        # Loop through all the rows of the dataframe, add them one by one to the annotation tiles
        for index, row in annotation_dataframe.iterrows():
            annotation_tiles[row['Image']] = {}

            # Loop through all the columns of the dataframe. If they are not part of the base header or the Image name,
            # add them to the dictionary
            for column in column_names:
                if column not in base_header + ['Image']:
                    if column == 'surrounding_tile_names':
                        content_list = row[column].strip('[]').split(',')
                        annotation_tiles[row['Image']][column] = content_list
                    elif column == 'surrounding_tile_exists':
                        content_list = [i == 'True' for i in row[column].strip('[]').split(',')]
                        annotation_tiles[row['Image']][column] = content_list
                    elif column == 'img_path':
                        annotation_tiles[row['Image']][column] = Path(row[column])
                    else:
                        annotation_tiles[row['Image']][column] = row[column]

        return annotation_tiles

    def parse_classifier_output(self, file_path, annotation_shift: int = 128):
        """Parses the output of the classifier and returns the annotation_tiles

        Goes through the csv file produced by the classifier, parses the corresponding MAPS XML File and builds the
        necessary MapsXmlParser dictionaries so that they can be saved to csv afterwards. Excpects the following
        structure in the classifier csv:
        Dictionary with TileSets as keys and a dictionary as value. The value dictionary contains dictionaries for each
        tile with annotations. The name of the tile is the key and the top left corner of the annotations are the
        values, saved as a list of tuples (x,y)

        Args:
            file_path (str): Path to the classifier output csv
            annotation_shift (int): How much the center of the annotation is shifted from the top left corner. Defaults
                to 128 (for 256x256 images from the classifier)

        Returns:
            self.annotation_tiles: Dictionary of all annotation tiles
        """
        # Load the csv containing classifier info
        base_annotation_name = 'Fork_'
        annotation_index = 0
        annotations_per_tileset = {}
        with open(file_path) as csv_file:
            csv_reader = csv.reader(csv_file, delimiter=',')
            for tile_set in csv_reader:
                tile_set_name = tile_set[0]
                annotations_per_tileset[tile_set_name] = ast.literal_eval(tile_set[1])

        # Parse the MAPS experiment (without annotations) to get the positions of all tiles
        self.extract_layers_and_annotations(check_for_annotations=False)
        self.get_relative_tile_locations()
        self.calculate_absolute_tile_coordinates()

        # Map the annotations to the corresponding tiles
        for current_tile_set in annotations_per_tileset:
            for tile in annotations_per_tileset[current_tile_set]:
                tile_key = current_tile_set + '_' + tile
                current_tile = self.tiles[tile_key]
                for annotation in annotations_per_tileset[current_tile_set][tile]:
                    # Get Annotation_Names => Create increasing names
                    annotation_index += 1
                    annotation_name = base_annotation_name + str(annotation_index).zfill(5)

                    self.annotation_tiles[annotation_name] = copy.deepcopy(current_tile)
                    self.annotation_tiles[annotation_name]['pixel_size'] = self.pixel_size
                    # If relevant, the StagePositions could be calculated and added here. As they are only used to find
                    # the tile of interest and the classifier output already provides that, it's not done here
                    self.annotation_tiles[annotation_name]['Annotation_StagePosition_x'] = None
                    self.annotation_tiles[annotation_name]['Annotation_StagePosition_y'] = None
                    self.annotation_tiles[annotation_name]['Annotation_tile_img_position_x'] = annotation[0] \
                                                                                               + annotation_shift
                    self.annotation_tiles[annotation_name]['Annotation_tile_img_position_y'] = annotation[1] \
                                                                                               + annotation_shift
        self.determine_surrounding_tiles()

        return self.annotation_tiles
