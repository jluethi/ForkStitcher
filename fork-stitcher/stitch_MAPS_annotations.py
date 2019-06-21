import logging
from pathlib import Path
import re
import numpy as np
import multiprocessing
import shutil
import pandas as pd
from StyleFrame import StyleFrame, Styler

import sites_of_interest_parser as sip
import os

import imagej

# Using lower level ImageJ APIs to do the stitching. Avoiding calling ImageJ1 plugins allows to use a maven
# distribution of ImageJ and makes this parallelizable as no temporary files are written and read anymore.
# See here: https://github.com/imagej/pyimagej/issues/35
# https://forum.image.sc/t/using-imagej-functions-like-type-conversion-and-setting-pixel-size-via-pyimagej/25755/10
ij = imagej.init('sc.fiji:fiji:2.0.0-pre-10+ch.fmi:faim-ij2-visiview-processing:0.0.1')


class Stitcher:
    """ Stitches Talos images based on csv files containing the necessary information

    This class handles the stitching of Talos images based on a csv file like the one created by the MapsXmlParser.
    It creates the necessary folders, calls MapsXmlParser for the parsing and saving of the necessary metadata and then
    manages the stitching of all annotations. Current implementation of stitching is hard-coded to stitch_radius = 1,
    the size of the Talos images and an overlap of 10% in its stitching parameters in the stitch_annotated_tiles
    function

    Args:
        base_path (str): Path (as a string) to the directory containing the project_name folder.
        project_name (str): Name of the directory containing the MAPSProject.xml file and the LayersData
            folder of the MAPS project. Will be used as the location for the output folders. Must be in base_path folder
        csv_folder (str): Name of the folders where the csv files are saved to
        output_folder (str): Name of the folder where the stitched forks are saved to
        stitch_radius (int): The number of images in each direction from the tile containing the annotation should be
            stitched.

    Attributes:
        stitch_radius (int): The number of images in each direction from the tile containing the annotation should be
            stitched.
        project_name (str): Name of the current project being processed
        project_folder_path (Path): Full path to the project folder, containing the MAPSProject.xml file and the
            LayersData folder
        output_path (Path): Full path to the output folder where the stitched images are stored
        csv_base_path (Path): Full path to the folder where the csv files with all annotation metadata are stored
        base_header (list): List of all the column headers that should be added to the csv file (for classification of
            annotations and for measurements made on them)

    """
    def __init__(self, base_path: str, project_name: str, csv_folder: str = 'annotation_csv',
                 output_folder: str = 'stitchedForks', stitch_radius: int = 1):
        self.stitch_radius = stitch_radius

        self.project_name = project_name
        self.project_folder_path = Path(base_path) / project_name
        self.output_path = Path(self.project_folder_path) / Path(output_folder)

        self.csv_base_path = Path(self.project_folder_path) / csv_folder

        self.log_file_path = str(self.project_folder_path / (self.project_folder_path.name + '.log'))

        # Headers of the categorization & the measurements for forks. Values filled in by users afterwards
        self.base_header = ['Linear DNA', 'Loop', 'Crossing', 'Other False Positive', 'Missing Link Fork',
                            'fork symetric', 'fork asymetric', 'reversed fork symetric', 'reversed fork asymetric',
                            'size reversed fork (nm)', 'dsDNA RF', 'internal ssDNA RF', 'ssDNA end RF',
                            'total ssDNA RF	gaps', 'gaps', 'sister	gaps', 'parental', 'size gaps (nm)',
                            'junction ssDNA size (nm)', 'hemicatenane', 'termination intermediate', 'bubble',
                            'hemireplicated bubble', 'list for reversed forks (nt)', 'list for gaps (nt)',
                            'list for ssDNA at junction (nt)', 'Remarks',
                            ]

    def stitch_annotated_tiles(self, annotation_tiles: dict, logger, stitch_threshold: int = 1000,
                               eight_bit: bool = True, show_arrow: bool = True, enhance_contrast: bool = True):
        """Stitches 3x3 images for all annotations in annotation_tiles

        Goes through all annotations in annotation_tiles dict, load the center file and the existing surrounding files.
        Sets up the stitching configuration according to the neighboring tiles and calculates the stitching parameters.
        If the calculated stitching moves all images by less than the threshold in any direction, it performs the
        stitching. Otherwise, a log message is made and the center image is copied to the results folder.
        Finally, it sets the pixel size and converts the stitched image to 8bit before saving it to disk. Everything is
        performed using pyimagej api to use imageJ Java APIs.
        Can deal with 3x3, 3x2, 2x3 and 2x2 squares with 10% overlap.

        Args:
            annotation_tiles (dict): annotation_tiles dictionary, e.g. from MapsXmlParser. See MapsXmlParser for content
                details. Needs to contain img_path, pixel_size, Annotation_tile_img_position_x,
                Annotation_tile_img_position_y, surrounding_tile_names & surrounding_tile_exists for this function
                to work
            logger (Logging): Logging object that is configured for the logging either in multiprocessing or normal
                processing
            stitch_threshold (int): Threshold to judge stitching quality by. If images would be moved more than this
                threshold, the stitching is not performed
            eight_bit (bool): Whether the stitched image should be saved as an 8bit image. Defaults to True, thus saving
                images as 8bit
            show_arrow (bool): Whether an arrow should be added to the image overlay that points to the annotation in
                the stitched image. Defaults to True, thus adding an arrow to the overlay
            enhance_contrast (bool): Whether contrast enhancement should be performed on the images before stitching.
                Defaults to True (thus enhancing contrast in the images)

        Returns:
            dict: annotation_tiles, now includes information about the position of the annotation in the stitched image

        """
        from jnius import autoclass

        for annotation_name in annotation_tiles:
            number_existing_neighbor_tiles = sum(annotation_tiles[annotation_name]['surrounding_tile_exists'])

            logger.info('Stitching {}'.format(annotation_name))
            img_path = annotation_tiles[annotation_name]['img_path']

            imps = []

            for i, neighbor in enumerate(annotation_tiles[annotation_name]['surrounding_tile_names']):
                if annotation_tiles[annotation_name]['surrounding_tile_exists'][i]:
                    imps.append(self.local_contrast_enhancement(str(img_path / neighbor), '', logger, save_img=False,
                                                                eight_bit=eight_bit,
                                                                use_norm_local_contrast=enhance_contrast,
                                                                return_java_img=True, center=True))
            java_imgs = ij.py.to_java(imps)

            # Define starting positions based on what neighbor tiles exist
            # TODO: Calculate these starting positions based on the overlap metadata
            positions_jlist = ij.py.to_java([])
            # All tiles exist
            if number_existing_neighbor_tiles == 9:
                positions = [[0.0, 0.0], [3686.0, 0.0], [7373.0, 0.0], [0.0, 3686.0], [3686.0, 3686.0],
                             [7373.0, 3686.0], [0.0, 7373.0], [3686.0, 7373.0], [7373.0, 7373.0]]
                # TODO: Change center_index calculation to: Sum of existing tiles before the center tile, based on the
                #  surrounding_tile_exists list
                center_index = 4
            # Edge tile: Top or bottom row is missing
            elif annotation_tiles[annotation_name]['surrounding_tile_exists'] == [True, True, True, True, True, True,
                                                                                  False, False, False]:
                positions = [[0.0, 0.0], [3686.0, 0.0], [7373.0, 0.0], [0.0, 3686.0], [3686.0, 3686.0],
                             [7373.0, 3686.0]]
                center_index = 4
            elif annotation_tiles[annotation_name]['surrounding_tile_exists'] == [False, False, False, True, True,
                                                                                  True, True, True, True]:
                positions = [[0.0, 0.0], [3686.0, 0.0], [7373.0, 0.0], [0.0, 3686.0], [3686.0, 3686.0],
                             [7373.0, 3686.0]]
                center_index = 1
            # Edge tile: Left or right column is missing
            elif annotation_tiles[annotation_name]['surrounding_tile_exists'] == [False, True, True, False, True, True,
                                                                                  False, True, True]:
                positions = [[0.0, 0.0], [3686.0, 0.0], [0.0, 3686.0], [3686.0, 3686.0], [0.0, 7373.0],
                             [3686.0, 7373.0]]
                center_index = 2
            elif annotation_tiles[annotation_name]['surrounding_tile_exists'] == [True, True, False, True, True,
                                                                                  False, True, True, False]:
                positions = [[0.0, 0.0], [3686.0, 0.0], [0.0, 3686.0], [3686.0, 3686.0], [0.0, 7373.0],
                             [3686.0, 7373.0]]
                center_index = 3
            # Corner Tile: Only 2x2 tiles to stitch
            elif number_existing_neighbor_tiles == 4:
                positions = [[0.0, 0.0], [3686.0, 0.0], [0.0, 3686.0], [3686.0, 3686.0]]
                if annotation_tiles[annotation_name]['surrounding_tile_exists'] == [True, True, False, True, True,
                                                                                    False, False, False, False]:
                    center_index = 3
                elif annotation_tiles[annotation_name]['surrounding_tile_exists'] == [False, True, True, False, True,
                                                                                      True, False, False, False]:
                    center_index = 2
                elif annotation_tiles[annotation_name]['surrounding_tile_exists'] == [False, False, False, True, True,
                                                                                      False, True, True, False]:
                    center_index = 1
                elif annotation_tiles[annotation_name]['surrounding_tile_exists'] == [False, False, False, False, True,
                                                                                      True, False, True, True]:
                    center_index = 0
                else:
                    logger.warning('Not stitching fork {}, because there is no rectangle of images to stitch. '
                                   'This stitching function is only made for 3x3, 2x3, 3x2 and 2x2 stitching. '
                                   'Those tiles do exist: {}'.format(annotation_name,
                                                                     annotation_tiles[annotation_name]
                                                                     ['surrounding_tile_exists']))
                    # Instead of stitching, copy the center tile to the output folder
                    center_file_path = Path(img_path) / annotation_tiles[annotation_name]['surrounding_tile_names'][4]
                    output_filename = self.output_path / (annotation_name + '_StitchingFailed_centerOnly.tiff')
                    shutil.copy(center_file_path, output_filename)
                    break

            else:
                logger.warning('Not stitching fork {}, because there is no rectangle of images to stitch. '
                               'This stitching function is only made for 3x3, 2x3, 3x2 and 2x2 stitching. '
                               'Those tiles do exist: {}'.format(annotation_name, annotation_tiles[annotation_name]
                                                                                        ['surrounding_tile_exists']))
                # Instead of stitching, copy the center tile to the output folder
                center_file_path = Path(img_path) / annotation_tiles[annotation_name]['surrounding_tile_names'][4]
                output_filename = self.output_path / (annotation_name + '_StitchingFailed_centerOnly.tiff')
                shutil.copy(center_file_path, output_filename)
                break

            for pos in positions:
                positions_jlist.add(pos)
            original_positions = np.array(positions_jlist)

            dimensionality = 2
            compute_overlap = True
            StitchingUtils = autoclass('ch.fmi.visiview.StitchingUtils')
            models = StitchingUtils.computeStitching(java_imgs, positions_jlist, dimensionality, compute_overlap)

            # Get the information about how much the center image has been shifted, where the fork is placed in
            # the stitched image
            stitching_params = []
            for model in models:
                params = [0.0] * 6
                model.toArray(params)
                stitching_params.append(params[4:])

            original_annotation_coord = [annotation_tiles[annotation_name]['Annotation_tile_img_position_x'],
                                         annotation_tiles[annotation_name]['Annotation_tile_img_position_y']]

            [perform_stitching, stitched_coordinates] = self.process_stitching_params(stitching_params,
                                                                                      original_annotation_coord,
                                                                                      stitch_threshold,
                                                                                      original_positions, center_index,
                                                                                      logger)

            # If the calculate stitching is reasonable, perform the stitching. Otherwise, log a warning
            if perform_stitching:
                # Add the information about where the fork is in the stitched image back to the dictionary,
                # such that it can be saved to csv afterwards
                annotation_tiles[annotation_name]['annotation_position_x'] = stitched_coordinates[0]
                annotation_tiles[annotation_name]['annotation_position_y'] = stitched_coordinates[1]

                Fusion = autoclass('mpicbg.stitching.fusion.Fusion')
                UnsignedShortType = autoclass('net.imglib2.type.numeric.integer.UnsignedShortType')
                target_type = UnsignedShortType()
                subpixel_accuracy = False
                ignore_zero_values = False
                stitched_img = Fusion.fuse(target_type, java_imgs, models, dimensionality, subpixel_accuracy, 5,
                                           None, False, ignore_zero_values, False)

                # # Use imageJ to set bit depth, pixel size & save the image.
                IJ = autoclass('ij.IJ')

                # Set the pixel size. Fiji rounds 0.499 nm to 0.5 nm and I can't see anything I can do about that
                pixel_size_nm = str(annotation_tiles[annotation_name]['pixel_size'] * 10e8)
                pixel_size_command = "channels=1 slices=1 frames=1 unit=nm pixel_width=" + pixel_size_nm + \
                                     " pixel_height=" + pixel_size_nm + " voxel_depth=1.0 global"
                IJ.run(stitched_img, "Properties...", pixel_size_command)

                # Convert to 8 bit
                if eight_bit:
                    IJ.run(stitched_img, "8-bit", "")

                # Add an arrow pointing to the annotation
                if show_arrow:
                    ArrowTool = autoclass('fiji.util.ArrowTool')
                    ArrowStyle = autoclass('fiji.util.ArrowShape$ArrowStyle')
                    roi = ArrowTool.makeRoi(ArrowStyle.DELTA, stitched_coordinates[0] - 400, stitched_coordinates[1]
                                            + 400, stitched_coordinates[0] - 40, stitched_coordinates[1] + 40,
                                            25.0, 50.0)

                    Color = autoclass('java.awt.Color')
                    stitched_img.setOverlay(roi, Color.green, 50, Color.green)

                # Saving the ImagePlus directly as Tiff, without converting to ImageJ2 Dataset or converting to PNG,
                # as both of those interfere with displaying the overlay arrow
                output_filename = annotation_name + '.tiff'
                IJ.saveAsTiff(stitched_img, str(self.output_path / output_filename))

                stitched_img.close()

            else:
                logger.warning('Not stitching fork {}, because the stitching calculations displaced the images more '
                               'than {} pixels. Instead, just copying the center image to the target folder'
                               .format(annotation_name, stitch_threshold))
                center_file_path = Path(img_path) / annotation_tiles[annotation_name]['surrounding_tile_names'][4]
                output_filename = self.output_path / (annotation_name + '_StitchingFailed_centerOnly.tiff')
                shutil.copy(center_file_path, output_filename)
                # Save the original positions to the file. Otherwise, the csv files have missing entries which can lead
                # to issues.
                annotation_tiles[annotation_name]['annotation_position_x'] = annotation_tiles[annotation_name]['Annotation_tile_img_position_x']
                annotation_tiles[annotation_name]['annotation_position_y'] = annotation_tiles[annotation_name]['Annotation_tile_img_position_y']

            # Close any open images to free up RAM. Otherwise, get an OutOfMemory Exception after a few rounds
            # ij.getContext().dispose()
            for img in imps:
                img.close()
            for java_img in java_imgs:
                java_img.close()
            ij.window().clear()

        # return the annotation_tiles dictionary that now contains the information about where the fork is in the
        # stitched image
        return annotation_tiles

    @staticmethod
    def process_stitching_params(stitch_params, annotation_coordinates, stitch_threshold, original_positions,
                                 center_index: int, logger):
        """Calculates the position of the annotation in the stitched image and decides if stitching worked well

        Based on the stitch_threshold, this function decides whether the stitching has worked well. If any image was
        moved by more than the threshold, it returns False.

        Args:
            stitch_params (np.array): Array of the stitching parameters calculated by imageJ stitching
            annotation_coordinates (np.array): Array of the coordinates of the annotation in the image before stitching
            stitch_threshold (int): Threshold to decide whether stitching should be performed
            original_positions (np.Array): Array of the initial positions of the images before stitching, used to
                calculate the shift by stitching
            center_index (int): Index of which tile in the stitched image was the original center. Used to calculate
                the position of the annotation in the stitched image
            logger (Logging): Logging object that is configured for the logging either in multiprocessing or normal
                processing

        Returns:
            list: First value is a bool that informs whether the stitching should be done. Second value is an array with
                the coordinates of the annotations in the stitched image

        """
        nb_imgs = len(stitch_params)
        stitch_coordinates = np.zeros((nb_imgs, 2))
        for i, coordinates in enumerate(stitch_params):
            stitch_coordinates[i, 0] = int(round(coordinates[0]))
            stitch_coordinates[i, 1] = int(round(coordinates[1]))
        min_coords = np.min(stitch_coordinates, axis=0)
        stitched_annotation_coordinates = annotation_coordinates + stitch_coordinates[center_index, :] - min_coords

        stitch_shift = stitch_coordinates - original_positions
        max_shift = np.max(stitch_shift)
        if max_shift < stitch_threshold:
            good_stitching = True
        else:
            good_stitching = False
            logger.warning('Current stitching moves images more than the threshold of {}. '
                            'The stitching calculated the following image displacements from their '
                            'starting positions: {}.'.format(stitch_threshold, stitch_shift))

        return [good_stitching, stitched_annotation_coordinates.astype(int)]

    @staticmethod
    def local_contrast_enhancement(img_path, output_path, logger=None, save_img: bool = False, eight_bit: bool = True,
                                   use_norm_local_contrast: bool = False, use_CLAHE: bool = False,
                                   return_java_img: bool = False, return_numpy_img: bool = False, **kwargs):
        """Loads an image and performs local contrast enhancement

        Loads the specified image, performs either NormalizeLocalContrast (default), CLAHE or no local contrast
        enhancement (in that order, thus performs NormalizeLocalContrast if both it and CLAHE are True).
        Optionally converts the image to 8bit and saves it. The parameters for NormalizeLocalContrast and
        CLAHE have default values that can be overwritten using the **kwargs by providing an argument with the specific
        name of the parameter to be changed

        Args:
            img_path (Path or str): Full path to the image to be processed
            output_path (Path or str): Full path to where the output image should be saved (if save_img is True)
            logger (Logging): Logging object that is configured for the logging either in multiprocessing or normal
                processing. Defaults to None, thus loading the logger
            save_img (bool): Whether the processed image should be saved. Defaults to False (not saving the image)
            eight_bit (bool): Whether the image should be converted to 8 bit . Defaults to True (converting to 8 bit)
            use_norm_local_contrast (bool): Whether NormalizeLocalContrast Fiji Plugin should be run on the image.
                Defaults to False (not running NormalizeLocalContrast on the image)
            use_CLAHE (bool): Whether CLAHE Fiji Plugin should be run on the image. Defaults to False (not running
                CLAHE on the image)
            return_java_img (bool): Whether the function should return the java image. Defaults to False (not returning
                the image)
            return_numpy_img (bool): Whether the function should return a numpy version of the image. Defaults to False
                (not returning the image)

        Returns:
            ImagePlus: The processed image as an ImageJ1 ImagePlus image (if return_image is True)

                """
        from jnius import autoclass
        IJ = autoclass('ij.IJ')

        if logger is None:
            logger = logging.getLogger()

        image_plus_img = IJ.openImage(str(img_path))

        if use_norm_local_contrast:
            logger.debug('Loading {} and performing NormalizeLocalContrast on it'.format(str(img_path)))
            NormLocalContrast = autoclass('mpicbg.ij.plugin.NormalizeLocalContrast')
            brx = kwargs.get('brx', 300)
            bry = kwargs.get('bry', 300)
            stds = kwargs.get('stds', 4)
            center = kwargs.get('cent', True)
            stretch = kwargs.get('stret', True)

            NormLocalContrast.run(image_plus_img.getChannelProcessor(), brx, bry, stds, center, stretch)

        elif use_CLAHE:
            logger.debug('Loading {} and performing CLAHE on it'.format(str(img_path)))
            Flat = autoclass('mpicbg.ij.clahe.Flat')
            blockRadius = kwargs.get('blockRadius', 63)
            bins = kwargs.get('bins', 255)
            slope = kwargs.get('slope', 3)
            mask = kwargs.get('mask', None)
            composite = kwargs.get('composite', False)

            Flat.getFastInstance().run(image_plus_img, blockRadius, bins, slope, mask, composite)

        else:
            logger.debug('Loading {}. Not performing any contrast enhancements'.format(str(img_path)))

        if eight_bit:
            IJ.run(image_plus_img, "8-bit", "")
        if save_img:
            IJ.saveAsTiff(image_plus_img, str(output_path))

        if return_java_img:
            return image_plus_img
        elif return_numpy_img:
            np_img = ij.py.from_java(image_plus_img)
            image_plus_img.close()
            return np_img
        else:
            image_plus_img.close()
            return

    def parse_create_csv_batches(self, batch_size: int, highmag_layer: str = 'highmag'):
        """Creates the batch csv files of annotation_tiles

        Calls the MapsXmlParser to parse the XML file of the acquisition and save the annotation_tiles as a csv in
        batches

        Args:
            batch_size (int): Batch size of the csv files
            highmag_layer (str): Name of the image layer in MAPS for which tiles containing annotations should
                be found. Defaults to 'highmag'

        Returns:
            list: First value: The annotation_tiles dictionary. Second value: A list of the filenames of the csv files
                that were created

        """
        # Make folders for csv files
        os.makedirs(str(self.csv_base_path), exist_ok=True)
        csv_path = self.csv_base_path / (self.project_name + '_annotations' + '.csv')

        parser = sip.MapsXmlParser(project_folder=self.project_folder_path, use_unregistered_pos=True,
                                   name_of_highmag_layer=highmag_layer, stitch_radius=self.stitch_radius)

        annotation_tiles = parser.parse_xml()
        annotation_csvs = sip.MapsXmlParser.save_annotation_tiles_to_csv(annotation_tiles, self.base_header, csv_path,
                                                                         batch_size=batch_size)

        return [annotation_tiles, annotation_csvs]

    def parse_create_classifier_csv_batches(self, batch_size: int, classifier_csv_path: str,
                                            highmag_layer: str = 'highmag'):
        """Creates the batch csv files of annotation_tiles based on classifier output

        Calls the MapsXmlParser to parse the XML file of the acquisition and save the annotation_tiles as a csv in
        batches

        Args:
            batch_size (int): Batch size of the csv files
            classifier_csv_path (str): Path to the classifier output csv file
            highmag_layer (str): Name of the image layer in MAPS for which tiles containing annotations should
                be found. Defaults to 'highmag'

        Returns:
            list: First value: The annotation_tiles dictionary. Second value: A list of the filenames of the csv files
                that were created

        """
        # Make folders for csv files
        os.makedirs(str(self.csv_base_path), exist_ok=True)
        csv_path = self.csv_base_path / (self.project_name + '_annotations' + '.csv')

        parser = sip.MapsXmlParser(project_folder=self.project_folder_path, use_unregistered_pos=True,
                                   name_of_highmag_layer=highmag_layer, stitch_radius=self.stitch_radius)

        annotation_tiles = parser.parse_classifier_output(classifier_csv_path)
        annotation_csvs = sip.MapsXmlParser.save_annotation_tiles_to_csv(annotation_tiles, self.base_header, csv_path,
                                                                         batch_size=batch_size)

        return [annotation_tiles, annotation_csvs]

    def stitch_batch(self, annotation_csv_path, stitch_threshold: int = 1000, eight_bit: bool = True,
                     show_arrow: bool = True, enhance_contrast: bool = True, multiprocessing_logger: bool = False):
        """Submits the stitching of a batch, the writing of an updated csv file and the deletion of the old csv file

        Args:
            annotation_csv_path (Path): The path to the folder containing the annotation_tiles csvs.
            stitch_threshold (int): Threshold to judge stitching quality by. If images would be moved more than this
                threshold, the stitching is not performed
            eight_bit (bool): Whether the stitched image should be saved as an 8bit image. Defaults to True, thus saving
                images as 8bit
            show_arrow (bool): Whether an arrow should be added to the image overlay that points to the annotation in
                the stitched image. Defaults to True, thus adding an arrow to the overlay
            enhance_contrast (bool): Whether contrast enhancement should be performed on the images before stitching.
                Defaults to True (thus enhancing contrast in the images)
            multiprocessing_logger (bool): Whether a multiprocessing logger or a normal logger should be used. Defaults
                to False, thus using a normal logger

        """
        # Check if a folder for the stitched forks already exists. If not, create that folder
        os.makedirs(str(self.output_path), exist_ok=True)
        annotation_tiles_loaded = sip.MapsXmlParser.load_annotations_from_csv(self.base_header, annotation_csv_path)

        logger = sip.MapsXmlParser.create_logger(self.log_file_path, multiprocessing_logger)
        stitched_annotation_tiles = self.stitch_annotated_tiles(annotation_tiles=annotation_tiles_loaded, logger=logger,
                                                                stitch_threshold=stitch_threshold,
                                                                eight_bit=eight_bit, show_arrow=show_arrow,
                                                                enhance_contrast=enhance_contrast)
        csv_stitched_path = Path(str(annotation_csv_path)[:-4] + '_stitched.csv')

        sip.MapsXmlParser.save_annotation_tiles_to_csv(stitched_annotation_tiles, self.base_header, csv_stitched_path)
        os.remove(str(annotation_csv_path))

    def manage_batches(self, stitch_threshold: int = 1000, eight_bit: bool = True, show_arrow: bool = True,
                       max_processes: int = 4, enhance_contrast: bool = True):
        """Manages the parallelization of the stitching of batches

        As multiprocessing can make some issues, if max_processes is set to 1, it does not use multiprocessing calls.

        Args:
            stitch_threshold (int): Threshold to judge stitching quality by. If images would be moved more than this
                threshold, the stitching is not performed
            eight_bit (bool): Whether the stitched image should be saved as an 8bit image. Defaults to True, thus saving
                images as 8bit
            show_arrow (bool): Whether an arrow should be added to the image overlay that points to the annotation in
                the stitched image. Defaults to True, thus adding an arrow to the overlay
            max_processes (int): The number of parallel processes that should be used to process the batches.
                Be careful, each batch needs a lot of memory
            enhance_contrast (bool): Whether contrast enhancement should be performed on the images before stitching.
                Defaults to True (thus enhancing contrast in the images)

        """
        # Populate annotation_csv_list by looking at csv files in directory
        items = os.listdir(self.csv_base_path)
        annotation_csv_list = []
        regex = re.compile('_annotations_\d+\.csv')
        for name in items:
            if regex.search(name):
                annotation_csv_list.append(self.csv_base_path / name)
        # There is an issue with an ImageJ library that only occurs in non-multiprocessing.
        # Therefore, always use multiprocessing, even for 1 process.
        # if max_processes > 1:
        with multiprocessing.Pool(processes=max_processes) as pool:
            for annotation_csv_path in annotation_csv_list:
                pool.apply_async(self.stitch_batch, args=(annotation_csv_path, stitch_threshold, eight_bit,
                                                          show_arrow, enhance_contrast, True, ))

            pool.close()
            pool.join()
        # else:
        #     for annotation_csv_path in annotation_csv_list:
        #         self.stitch_batch(annotation_csv_path, stitch_threshold, eight_bit, show_arrow,
        #                           enhance_contrast, False)

    def combine_csvs(self, delete_batches: bool = False, to_excel: bool = True):
        """Combines batch csv output files into the final csv file and optionally an excel file

        Args:
            delete_batches (bool): Whether the batch csv files should be deleted after stitching them to the combined
                csv file. Defaults to False (not deleting the batch csv files)
            to_excel (bool): Whether the csv file should also be saved as an excel file. Defaults to True (creating the
                Excel file)

        """
        logger = sip.MapsXmlParser.create_logger(self.log_file_path)

        items = os.listdir(self.csv_base_path)
        stitched_csvs = []
        for name in items:
            if name.endswith('_stitched.csv'):
                stitched_csvs.append(name)

        stitched_csvs.sort()
        annotation_tiles = {}
        for csv in stitched_csvs:
            current_tiles = sip.MapsXmlParser.load_annotations_from_csv(self.base_header, self.csv_base_path / csv)
            for key in current_tiles:
                annotation_tiles[key] = current_tiles[key]
        csv_output_path = self.csv_base_path / (self.project_name + '_fused' + '.csv')
        sip.MapsXmlParser.save_annotation_tiles_to_csv(annotation_tiles, self.base_header, csv_output_path)

        # Delete all the batch files if the option is set for it
        if delete_batches:
            for name in items:
                os.remove(self.csv_base_path / name)

        if to_excel:
            logger.info('Saving the annotations csv as an excel file')
            data_frame = pd.read_csv(csv_output_path)
            excel_output_path = self.csv_base_path / (self.project_name + '_fused' + '.xlsx')

            # Create a list of headers whose column should be expanded to fit the content
            fitting_headers = list(data_frame.columns.values)
            non_fitting_headers = ['img_path', 'surrounding_tile_names', 'surrounding_tile_exists']
            for header in non_fitting_headers:
                if header in fitting_headers:
                    fitting_headers.remove(header)

            no_wrap_text_style = Styler(wrap_text=False, shrink_to_fit=False)
            excel_writer = StyleFrame.ExcelWriter(excel_output_path)
            styled_df = StyleFrame(data_frame, styler_obj=no_wrap_text_style)
            styled_df.to_excel(excel_writer, 'MapsAnnotations', index=False, columns_and_rows_to_freeze='A1',
                               best_fit=fitting_headers)
            excel_writer.save()
