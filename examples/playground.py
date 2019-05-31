from pathlib import Path

# def convert_string_to_Path_object(string_path):
#     folders = string_path.split('\\')
#     path = Path()
#     for folder in folders:
#         path = path / folder
#
#     return path
#
# print(convert_string_to_Path_object('D:\\8330_siNeg_CPT_3rd\\LayersData\\highmag\\28000 (24)'))

import numpy as np

# example = [1,2,3,4,5,6,1]
#
# print(np.argmin(example))
# import imagej
# ij = imagej.init('/Applications/Fiji.app')
# print(ij.op().help())

# list_str = "[True,True,True,True,True,True,True,True,True]"
# print(list_str)
# lyst = list_str.strip('[]').split(',')
# lyst2 = [bool(i) for i in lyst]
# print(lyst2)

# csv_path = '/Users/Joel/Desktop/test_annotations.csv'
# csv_batch_path = csv_path[:-4] + '_{}.csv'.format(0)
# print(csv_batch_path)

# from multiprocessing import Pool
# import imagej
# ij = imagej.init('sc.fiji:fiji:2.0.0-pre-10')
#
#
# class Test:
#     def f(self, i):
#         print(i)
#
#     def run(self):
#         print('Running')
#         with Pool(processes=4) as pool:
#             for i in range(10):
#                 pool.apply_async(self.f, args=(i, ))
#
#             pool.close()
#             pool.join()
#
# test = Test()
# test.run()


import imagej
import tkinter as tk
ij = imagej.init('sc.fiji:fiji:2.0.0-pre-10')
root = tk.Tk()

root.geometry("+2000+0")

tk.Label(root, text='Test1').grid(row=0, column=0)
tk.Checkbutton(root, text='Test2').grid(row=1, column=0)


root.mainloop()






