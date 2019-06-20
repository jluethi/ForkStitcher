import os
import sys
import multiprocessing
import tkinter as tk
import logging

# If everything is run from a frozen .exe package, set the path variables accordingly. See here for details:
# https://stackoverflow.com/questions/404744/determining-application-path-in-a-python-exe-generated-by-pyinstaller
if getattr(sys, 'frozen', False):
    os.environ['JAVA_HOME'] = os.path.join(os.getcwd(), 'share\\jdk8u212-b04')
    os.environ['PATH'] = os.path.join(os.getcwd(), 'share\\jdk8u212-b04\\jre\\bin') + os.pathsep + \
                         os.path.join(os.getcwd(), 'share\\jdk8u212-b04\\jre\\bin\\server') + os.pathsep + \
                         os.path.join(os.getcwd(), 'share\\apache-maven-3.6.1\\bin') + os.pathsep + os.environ['PATH']

# This import needs to happen after the paths are set correctly
from gui import Gui

def main():
    root = tk.Tk()
    root.title('Fork Stitcher')

    root.geometry("+2000+0")

    p = Gui(root)
    root.protocol("WM_DELETE_WINDOW", p.shutdown)

    # Run gui until user terminates the program
    root.mainloop()


if __name__ == "__main__":
    # On Windows calling this function is necessary. See here:
    # https://stackoverflow.com/questions/404744/determining-application-path-in-a-python-exe-generated-by-pyinstaller
    multiprocessing.freeze_support()
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s')
    main()