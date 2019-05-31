from pathlib import Path
import tkinter as tk
import tkinter.messagebox
import tkinter.filedialog
import _tkinter

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
        self.file_picker_entry = tk.Entry(master, textvariable=self.project_path)
        file_picker_button = tk.Button(master, text='Choose Directory', command=self.ask_for_path)

        file_picker_label.grid(row=0, column=0, sticky=tk.E)
        self.file_picker_entry.grid(row=0, column=1)
        file_picker_button.grid(row=0, column=2)

        # Advanced options in a dropdown
        self.max_processes = tk.IntVar()
        tk.Label(master, text='Number of parallel processes').grid(row=1, column=0, sticky=tk.E)
        tk.Entry(master, textvariable=self.max_processes).grid(row=1, column=1)

        # TODO: Find out how to hide some options by default
        # Advanced options in a dropdown
        # Boolean for whether output should be saved as 8bit images
        self.eight_bit = tk.BooleanVar()
        tk.Checkbutton(master, text='8 bit output', variable=self.eight_bit).grid(row=2, column=1)

        self.batch_size = tk.IntVar()
        tk.Label(master, text='Batch size').grid(row=3, column=0, sticky=tk.E)
        tk.Entry(master, textvariable=self.batch_size).grid(row=3, column=1)

        self.csv_folder_name = tk.StringVar()
        tk.Label(master, text='Csv folder name').grid(row=4, column=0, sticky=tk.E)
        tk.Entry(master, textvariable=self.csv_folder_name).grid(row=4, column=1)

        self.output_folder = tk.StringVar()
        tk.Label(master, text='Stitched images folder name').grid(row=5, column=0, sticky=tk.E)
        tk.Entry(master, textvariable=self.output_folder).grid(row=5, column=1)

        self.highmag_layer = tk.StringVar()
        tk.Label(master, text='High magnification layer').grid(row=6, column=0, sticky=tk.E)
        tk.Entry(master, textvariable=self.highmag_layer).grid(row=6, column=1)

        self.stitch_threshold = tk.IntVar()
        tk.Label(master, text='Stitch Threshold').grid(row=7, column=0, sticky=tk.E)
        tk.Entry(master, textvariable=self.stitch_threshold).grid(row=7, column=1)


        # Add a "continue existing processing" Button

        # Run button
        self.run_button = tk.Button(master, text='Run', fg='red', command=self.run)
        self.run_button.grid(row=10, column=1)

        # Stop button (available during run)
        self.reset_parameters()

    def reset_parameters(self):
        self.project_path.set('')
        self.max_processes.set(1)
        self.eight_bit.set(True)
        self.batch_size.set(5)
        self.output_folder.set('stitchedForks_test')
        self.csv_folder_name.set('annotation_csv_tests')
        self.highmag_layer.set('highmag')
        self.stitch_threshold.set(1000)


    def run(self):
        project_dir = Path(self.project_path.get())
        base_path = project_dir.parent
        project_name = project_dir.name

        # TODO: Check if all parameters are set:
        params_set = self.check_all_parameters_set()
        print(params_set)
        if params_set:
            pass
            # TODO: Catch issues when wrong path is provided or another error/warning occurs in the stitcher
            # stitcher = Stitcher(base_path, project_name, self.csv_folder_name.get(), self.output_folder.get())
            # stitcher.parse_create_csv_batches(batch_size=self.batch_size.get(), highmag_layer=self.highmag_layer.get())
            # stitcher.manage_batches(self.stitch_threshold.get(), self.eight_bit.get(),
            #                         max_processes=self.max_processes.get())
            # stitcher.combine_csvs(delete_batches=False)

        else:
            tkinter.messagebox.showwarning(title='Warning: parameters missing',
                                           message='You need to enter the parameters in all the required fields')

        # TODO: Show all warnings to the user


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
    root = tk.Tk()

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
