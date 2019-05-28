# Selection of code fragments that have become superfluous but may still be relevant in the future

# stich_MAPS_annotations.py
# Use python for set bit depth, pixel size & saving the image
# Downside: Have not found a way to set pixel size. OpenCV doesn't touch metadata. py3exiv2
# or GExiv2 may get that job done, but I can't figure out how
# Load an image into python
# from jnius import autoclass
# WindowManager = autoclass('ij.WindowManager')
# stitched_img = WindowManager.getCurrentImage()
# stitched_img_python = ij.py.from_java(stitched_img)
#
# output_filename = annotation_name + '.png'
#
# # Save the image
# if eight_bit:
#     eight_bit_img = (stitched_img_python - np.min(stitched_img_python)) / \
#                     (np.max(stitched_img_python) - np.min(stitched_img_python)) * 256
#     cv2.imwrite(str(output_path / output_filename), eight_bit_img.astype('uint8'))
# else:
#     cv2.imwrite(str(output_path / output_filename), stitched_img_python.astype('uint16'))


# @staticmethod
# def fuse_and_save_to_csv(annotation_tiles_1, annotation_tiles_2, base_header, csv_path):
#     """Fuses the dataframes made from 2 annotation_tiles dictionaries, saves the result to a csv file
#
#     Goes through the self.annotation_tiles dictionary and saves it to a csv file. Overwrites any existing file in
#     the same location.
#
#     Args:
#         base_header (list): list of strings that will be headers but will not contain any content
#         csv_path (Path): pathlib Path to the csv file that will be created. Must end in .csv
#
#     """
#     assert (str(csv_path).endswith('.csv'))
#     # Initialize empty csv file (or csv files if batch mode is used)
#     base_header_2 = ['Image'] + base_header
#     header_addition = list(list(annotation_tiles.values())[0].keys())
#     # csv_header = pd.DataFrame(columns=base_header_2 + header_addition)
#     # csv_header.to_csv(csv_path, index=False)
#
#     for i, annotation_name in enumerate(annotation_tiles):
#         current_annotation = {'Image': annotation_name}
#         # for header in base_header:
#         #     current_annotation[header] = ''
#
#         for info_key in annotation_tiles[annotation_name]:
#             current_annotation[info_key] = annotation_tiles[annotation_name][info_key]
#             if type(current_annotation[info_key]) == list:
#                 current_annotation[info_key] = '[' + ','.join(map(str, current_annotation[info_key])) + ']'
#
#         current_annotation_pd = pd.DataFrame(current_annotation, index=[0])
#
#         with open(str(csv_path), 'a') as f:
#             current_annotation_pd.to_csv(f, header=False, index=False)

# #### Listen to Java print / console statements
# # Initialize ImageJ.
# import imagej
# ij = imagej.init('/Applications/Fiji.app')
#
# # Define an OutputListener.
# from jnius import PythonJavaClass, java_method
# class MyOutputListener(PythonJavaClass):
#     __javainterfaces__ = ['org/scijava/console/OutputListener']
#
#     @java_method('(Lorg/scijava/console/OutputEvent;)V')
#     def outputOccurred(self, e):
#         source = e.getSource().toString()
#         output = e.getOutput()
#         print('\n[OUTPUT]\n\tsource = {}\n\toutput = {}'.format(source, output))
#
# # Instantiate our OutputListener.
# l = MyOutputListener()
#
# # Register it with ImageJ.
# ij.console().addOutputListener(l)
#
# # Test it!
# from jnius import autoclass
# System = autoclass('java.lang.System')
# System.out.println('Hello world')


######### Stitching via ImageJ1 plugin call
# center_filename = annotation_tiles[annotation_name]['filename']
# plugin = 'Grid/Collection stitching'
# index_x = int(center_filename[9:12]) - stitch_radius
# index_y = int(center_filename[5:8]) - stitch_radius
# args = {'type': '[Filename defined position]', 'order': '[Defined by filename         ]',
#         'grid_size_x': '3', 'grid_size_y': '3', 'tile_overlap': '8', 'first_file_index_x': str(index_x),
#         'first_file_index_y': str(index_y), 'directory': img_path,
#         'file_names': 'Tile_{yyy}-{xxx}-000000_0-000.tif', 'output_textfile_name': 'TileConfiguration.txt',
#         'fusion_method': '[Intensity of random input tile]', 'regression_threshold': '0.15',
#         'max/avg_displacement_threshold': '0.20', 'absolute_displacement_threshold': '0.30',
#         'compute_overlap': True, 'computation_parameters': '[Save memory (but be slower)]',
#         'image_output': '[Fuse and display]'}
# ij.py.run_plugin(plugin, args)
#
# # Use imageJ to set bit depth, pixel size & save the image.
# from jnius import autoclass
# IJ = autoclass('ij.IJ')
#
# # Get the open window with the stitched image
# WindowManager = autoclass('ij.WindowManager')
# stitched_img = WindowManager.getCurrentImage()







