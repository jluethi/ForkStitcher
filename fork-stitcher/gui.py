from pathlib import Path
import tkinter as tk
import tkinter.messagebox
import tkinter.filedialog
import _tkinter
import time
import logging
import threading

# from stitch_MAPS_annotations import Stitcher

# TODO: Figure out how to run pyimagej and tkinter at the same time on Macs, see suggestions here:
#  https://github.com/imagej/pyimagej/issues/39
# import imagej
# ij = imagej.init('/Applications/Fiji.app')


class Gui:

    def __init__(self, master):

        frame = tk.Frame(master)
        # ***** Menu *****
        menu = tk.Menu(master)
        master.config(menu=menu)
        file_menu = tk.Menu(menu)
        edit_menu = tk.Menu(menu)
        menu.add_cascade(label='File', menu=file_menu)
        # file_menu.add_separator()
        file_menu.add_command(label='Quit', command=frame.quit)
        menu.add_cascade(label='Edit', menu=edit_menu)
        edit_menu.add_command(label='Reset to default', command=self.reset_parameters)

        file_picker_label = tk.Label(master, text='Project Folder')
        self.project_path = tk.StringVar()
        self.file_picker_entry = tk.Entry(master, textvariable=self.project_path, width=30)
        file_picker_button = tk.Button(master, text='Choose Directory', command=self.ask_for_path)

        file_picker_label.grid(row=0, column=0, sticky=tk.E)
        self.file_picker_entry.grid(row=0, column=1, sticky=tk.W)
        file_picker_button.grid(row=0, column=2, sticky=tk.W)

        # Advanced options in a dropdown
        self.max_processes = tk.IntVar()
        tk.Label(master, text='Number of parallel processes').grid(row=1, column=0, sticky=tk.E)
        tk.Entry(master, textvariable=self.max_processes).grid(row=1, column=1, sticky=tk.W)

        # TODO: Find out how to hide some options by default
        # Advanced options in a dropdown
        self.batch_size = tk.IntVar()
        tk.Label(master, text='Batch size').grid(row=2, column=0, sticky=tk.E)
        tk.Entry(master, textvariable=self.batch_size).grid(row=2, column=1, sticky=tk.W)

        self.csv_folder_name = tk.StringVar()
        tk.Label(master, text='CSV folder name').grid(row=3, column=0, sticky=tk.E)
        tk.Entry(master, textvariable=self.csv_folder_name).grid(row=3, column=1, sticky=tk.W)

        self.output_folder = tk.StringVar()
        tk.Label(master, text='Stitched images folder name').grid(row=4, column=0, sticky=tk.E)
        tk.Entry(master, textvariable=self.output_folder).grid(row=4, column=1, sticky=tk.W)

        self.highmag_layer = tk.StringVar()
        tk.Label(master, text='High magnification layer').grid(row=5, column=0, sticky=tk.E)
        tk.Entry(master, textvariable=self.highmag_layer).grid(row=5, column=1, sticky=tk.W)

        self.stitch_threshold = tk.IntVar()
        tk.Label(master, text='Stitch Threshold').grid(row=6, column=0, sticky=tk.E)
        tk.Entry(master, textvariable=self.stitch_threshold).grid(row=6, column=1, sticky=tk.W)

        self.eight_bit = tk.BooleanVar()
        tk.Checkbutton(master, text='8 bit output', variable=self.eight_bit).grid(row=7, column=1, sticky=tk.W)

        self.arrow_overlay = tk.BooleanVar()
        tk.Checkbutton(master, text='Add an arrow overlay that points to the fork', variable=self.arrow_overlay). \
            grid(row=8, column=1, sticky=tk.W)

        self.contrast_enhance = tk.BooleanVar()
        tk.Checkbutton(master, text='Produce contrast enhanced images', variable=self.contrast_enhance). \
            grid(row=9, column=1, sticky=tk.W)

        self.continue_processing = tk.BooleanVar()
        tk.Checkbutton(master, text='Continue Processing an Experiment', variable=self.continue_processing).\
            grid(row=10, column=1, sticky=tk.W)

        # Add a "continue existing processing" Button

        # Run button
        self.run_button = tk.Button(master, text='Run', fg='red', command=self.run, width=20)
        self.run_button.grid(row=11, column=2, sticky=tk.W)

        # Stop button (available during run)
        self.reset_parameters()

    def reset_parameters(self):
        self.project_path.set('')
        self.max_processes.set(4)
        self.eight_bit.set(True)
        self.batch_size.set(5)
        self.output_folder.set('stitchedForks_test')
        self.csv_folder_name.set('annotation_csv_tests')
        self.highmag_layer.set('highmag')
        self.stitch_threshold.set(1000)
        self.arrow_overlay.set(True)
        self.contrast_enhance.set(True)
        self.continue_processing.set(False)

    def run(self):
        project_dir = Path(self.project_path.get())
        base_path = project_dir.parent
        project_name = project_dir.name

        params_set = self.check_all_parameters_set()
        if params_set and not self.continue_processing.get():
            logging.info('Process experiment {}'.format(project_name))

            # TODO: Catch the quitting of the window to shut down the thread
            thread = threading.Thread(target=self.dummy, args=(10, ))
            thread.start()
            # thread = threading.Thread(target=self.run_from_beginning, args=(base_path, project_name,))
            # thread.start()

        elif params_set and self.continue_processing.get():
            logging.info('Continuing to process experiment {}'.format(project_name))
            # thread = threading.Thread(target=self.continue_run, args=(base_path, project_name,))
            # thread.start()

        else:
            tkinter.messagebox.showwarning(title='Warning: parameters missing',
                                           message='You need to enter the correct kind of parameters in all the '
                                                   'required fields and then try again')

        # TODO: Show all warnings to the user

    # def run_from_beginning(self, base_path, project_name):
    #     # TODO: Catch issues when wrong path is provided or another error/warning occurs in the stitcher => catch my custom Exception, display it to the user
    #     stitcher = Stitcher(base_path, project_name, self.csv_folder_name.get(), self.output_folder.get())
    #     stitcher.parse_create_csv_batches(batch_size=self.batch_size.get(), highmag_layer=self.highmag_layer.get())
    #     stitcher.manage_batches(self.stitch_threshold.get(), self.eight_bit.get(), show_arrow=self.arrow_overlay.get(),
    #                             max_processes=self.max_processes.get(), enhance_contrast=self.contrast_enhance.get())
    #     stitcher.combine_csvs(delete_batches=True)
    #
    # def continue_run(self, base_path, project_name):
    #     stitcher = Stitcher(base_path, project_name, self.csv_folder_name.get(), self.output_folder.get())
    #     stitcher.manage_batches(self.stitch_threshold.get(), self.eight_bit.get(), show_arrow=self.arrow_overlay.get(),
    #                             max_processes=self.max_processes.get(), enhance_contrast=self.contrast_enhance.get())
    #     stitcher.combine_csvs(delete_batches=True)

    def dummy(self, iterations):
        # while True:
        for i in range(iterations):
            print('Running Dummy')
            time.sleep(1)

        for i in range(iterations):
            print('Running Dummy 2! =D')
            time.sleep(1)


    def ask_for_path(self):
        path = tkinter.filedialog.askdirectory()
        self.project_path.set(path)
        # self.file_picker_entry.delete(0, tk.END)
        # self.file_picker_entry.insert(0, path)

    def check_all_parameters_set(self):
        try:
            params_set = len(self.project_path.get()) > 0
            params_set = params_set and type(self.max_processes.get()) == int
            params_set = params_set and type(self.eight_bit.get()) == bool
            params_set = params_set and type(self.batch_size.get()) == int
            params_set = params_set and len(self.output_folder.get()) > 0
            params_set = params_set and len(self.csv_folder_name.get()) > 0
            params_set = params_set and len(self.highmag_layer.get()) > 0
            params_set = params_set and type(self.stitch_threshold.get()) == int

        except _tkinter.TclError:
            params_set = False

        return params_set


def main():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s')
    root = tk.Tk()
    root.title('Fork Stitcher')

    root.geometry("+2000+0")

    p = Gui(root)

    root.mainloop()


if __name__ == "__main__":
    main()

# # ***** Toolbar *****
# toolbar = tk.Frame(master, bg='blue')
# reset_button = tk.Button(toolbar, text='Reset Parameters', command=self.reset_parameters)
# reset_button.pack(side=tk.LEFT, dadx=2, pady=2)
# toolbar.grid()

# # ***** Status Bar *****
# status = tk.Label(master, text='Fill in Options', bd=1, relief=tk.SUNKEN, anchor=tk.W)
# status.grid(row=3, columnspan=2)
