import os
import sys
import multiprocessing
import tkinter as tk
import logging
import tkinter.font as font

# If everything is run from a frozen .exe package, set the path variables accordingly. See here for details:
# https://stackoverflow.com/questions/404744/determining-application-path-in-a-python-exe-generated-by-pyinstaller
if getattr(sys, 'frozen', False):
    os.environ['JAVA_HOME'] = os.path.join(os.getcwd(), 'share\\jdk8')
    os.environ['PATH'] = os.path.join(os.getcwd(), 'share\\jdk8\\jre\\bin') + os.pathsep + \
                         os.path.join(os.getcwd(), 'share\\jdk8\\jre\\bin\\server') + os.pathsep + \
                         os.path.join(os.getcwd(), 'share\\maven\\bin') + os.pathsep + os.environ['PATH']


def main():
    root = tk.Tk()
    loading_message = tk.Label(root, text='Loading ... Please wait.')
    loading_message.config(height=2, font=(font.Font(), 24, 'bold'))
    loading_message.grid(row=0, column=0, sticky=tk.E, pady=10, padx=10)
    loading_details = tk.Label(root, text='Loading takes ~ 30s on normal runs and a few minutes on the first run')
    loading_details.grid(row=1, column=0, sticky=tk.E, pady=10, padx=10)
    root.update()

    root.title('Fork Stitcher')

    windowWidth = root.winfo_reqwidth()
    windowHeight = root.winfo_reqheight()
    positionRight = int(root.winfo_screenwidth() / 2 - windowWidth / 2)
    positionDown = int(root.winfo_screenheight() / 2 - windowHeight / 2)

    root.geometry("+{}+{}".format(positionRight, positionDown))

    # This import takes time and needs to happen after the paths are set correctly and the loading window is running
    from gui import Gui
    loading_message.grid_remove()
    loading_details.grid_remove()
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
