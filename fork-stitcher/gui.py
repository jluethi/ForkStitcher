from pathlib import Path
import tkinter as tk
import tkinter.messagebox
import tkinter.filedialog

# from stitch_MAPS_annotations import Stitcher


class Gui:

    def __init__(self, master):


        frame = tk.Frame(master)
        # ***** Menu *****
        menu = tk.Menu(master)
        master.config(menu=menu)
        file_menu = tk.Menu(menu)
        edit_menu = tk.Menu(menu)
        menu.add_cascade(label='File', menu=file_menu)
        file_menu.add_command(label='Save', command=self.print_text)
        file_menu.add_separator()
        file_menu.add_command(label='Quit', command=frame.quit)
        menu.add_cascade(label='Edit', menu=edit_menu)
        edit_menu.add_command(label='Reset to default', command=self.reset_parameters)

        # # ***** Toolbar *****
        # toolbar = tk.Frame(master, bg='blue')
        # reset_button = tk.Button(toolbar, text='Reset Parameters', command=self.reset_parameters)
        # reset_button.pack(side=tk.LEFT, dadx=2, pady=2)
        # toolbar.grid()

        # # ***** Status Bar *****
        # status = tk.Label(master, text='Fill in Options', bd=1, relief=tk.SUNKEN, anchor=tk.W)
        # status.grid(row=3, columnspan=2)


        file_picker_label = tk.Label(master, text='Project Folder')
        self.file_picker_entry = tk.Entry(master)
        file_picker_button = tk.Button(master, text='Choose Directory', command=self.ask_for_path)


        file_picker_label.grid(row=0, column=0)
        self.file_picker_entry.grid(row=0, column=1)
        file_picker_button.grid(row=0, column=2)

        # Boolean for whether multiple batches should be run
        self.run_batch = tk.BooleanVar()
        batch_processing = tk.Checkbutton(master, text='Process in multiple batches', variable=self.run_batch)
        batch_processing.grid(row=1, columnspan=2)
        # self.run_batch.set(True)

        # TODO: Find out how to hide some options by default
        # Advanced options in a dropdown

        # Run button
        self.run_button = tk.Button(master, text='Run', fg='red', command=self.run)
        self.run_button.grid(row=2, column=1)

        # Stop button (available during run)






    def print_text(self):
        print('Hello World')

    def reset_parameters(self):
        print('Resetting parameters')

    def run(self):
        project_dir = Path(self.file_picker_entry.get())
        base_path = project_dir.parent
        project_name = project_dir.name

        batch = self.run_batch.get()
        if batch:
            batchsize = 4
        else:
            batchsize = 1


        # stitcher = Stitcher(base_path, project_name, csv_folder, output_folder)
        # stitcher.parse_create_csv_batches(batch_size=batch_size, highmag_layer=highmag_layer)
        # stitcher.manage_batches(stitch_threshold, eight_bit, max_processes=max_processes)
        # stitcher.combine_csvs()
        # tkinter.messagebox.showwarning(title='Warning: parameters missing',
        #                                message='You need to enter the parameters in all the required fields')

    def ask_for_path(self):
        path = tkinter.filedialog.askdirectory()
        self.file_picker_entry.delete(0, tk.END)
        self.file_picker_entry.insert(0, path)

def main():
    root = tk.Tk()

    root.geometry("+2000+0")

    p = Gui(root)

    root.mainloop()

if __name__ == "__main__":
    main()