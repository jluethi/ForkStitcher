from pathlib import Path
import tkinter as tk
import tkinter.messagebox
import tkinter.filedialog
from tkinter.scrolledtext import ScrolledText
import _tkinter
import time
import logging
import threading
import queue
import tkinter.font as font

from stitch_MAPS_annotations import Stitcher
from sites_of_interest_parser import MapsXmlParser

# TODO: Figure out how to run pyimagej and tkinter at the same time on Macs, see suggestions here:
#  https://github.com/imagej/pyimagej/issues/39
# import imagej
# ij = imagej.init('/Applications/Fiji.app')


class QueueHandler(logging.Handler):
    """Class that accepts logs and adds them to a queue
    """
    # Based on: https://github.com/beenje/tkinter-logging-text-widget

    def __init__(self, logging_queue):
        super().__init__()
        self.logging_queue = logging_queue

    def emit(self, log_statement):
        self.logging_queue.put(log_statement)


class LoggingWindow:
    # Based on: https://github.com/beenje/tkinter-logging-text-widget
    def __init__(self, master):
        self.master = master
        self.scrolled_text = ScrolledText(master=master, state='disabled', height=15)
        self.scrolled_text.grid(row=0, column=0)
        self.scrolled_text.configure(font='TkFixedFont')
        self.scrolled_text.tag_config('INFO', foreground='black')
        self.scrolled_text.tag_config('DEBUG', foreground='gray')
        self.scrolled_text.tag_config('WARNING', foreground='orange')
        self.scrolled_text.tag_config('ERROR', foreground='red')

        # Get the logger
        self.logger = logging.getLogger()

        self.log_queue = queue.Queue()
        self.queue_handler = QueueHandler(self.log_queue)
        formatter = logging.Formatter('%(asctime)s : %(levelname)s : %(message)s')
        self.queue_handler.setFormatter(formatter)
        self.logger.addHandler(self.queue_handler)
        # Start polling messages from the queue
        self.master.after(100, self.poll_log_queue)

        self.autoscroll = tk.BooleanVar()
        tk.Checkbutton(master, text='Autoscroll Log', variable=self.autoscroll).\
            grid(row=1, column=0, sticky=tk.W)
        self.autoscroll.set(True)

    def display(self, record):
        msg = self.queue_handler.format(record)
        self.scrolled_text.configure(state='normal')
        self.scrolled_text.insert(tk.END, msg + '\n', record.levelname)
        self.scrolled_text.configure(state='disabled')
        # Autoscroll to the bottom
        if self.autoscroll.get():
            self.scrolled_text.yview(tk.END)

    def poll_log_queue(self):
        # Check every 100ms if there is a new message in the queue to display
        while True:
            try:
                record = self.log_queue.get(block=False)
            except queue.Empty:
                break
            else:
                self.display(record)
        self.master.after(100, self.poll_log_queue)


class Gui:

    def __init__(self, master):

        self.master = master
        frame = tk.Frame(master)

        self.font = font.Font()

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

        # ***** User Inputs *****
        file_picker_label = tk.Label(master, text='Project folder:')
        self.project_path = tk.StringVar()
        self.file_picker_entry = tk.Entry(master, textvariable=self.project_path, width=30)
        file_picker_button = tk.Button(master, text='Choose Directory', command=self.ask_for_path)

        file_picker_label.grid(row=0, column=0, sticky=tk.E, pady=(10, 0), padx=5)
        self.file_picker_entry.grid(row=0, column=1, sticky=tk.W, pady=(10, 0))
        file_picker_button.grid(row=0, column=2, sticky=tk.W, pady=(10, 0))

        self.classifier_input = tk.BooleanVar()
        tk.Checkbutton(master, text='Load input from classifier', variable=self.classifier_input,
                       command=self.display_csv_picker).grid(row=1, column=1, pady=(6, 0), sticky=tk.W)

        self.csv_picker_label = tk.Label(master, text='Classifier CSV file:')
        self.csv_path = tk.StringVar()
        self.csv_picker_entry = tk.Entry(master, textvariable=self.csv_path, width=30)
        self.csv_picker_button = tk.Button(master, text='Choose CSV file', command=self.ask_for_file)

        grid_pos = 4
        tk.Label(master, text='Advanced Options', font=(self.font, 14, 'bold')).grid(row=grid_pos, column=1,
                                                                                     pady=(20, 0), sticky=tk.W)

        # TODO: Find out how to hide advanced options by default
        self.output_folder = tk.StringVar()
        tk.Label(master, text='Output folder name images:').grid(row=grid_pos + 1, column=0, sticky=tk.E, padx=5)
        tk.Entry(master, textvariable=self.output_folder).grid(row=grid_pos + 1, column=1, sticky=tk.W)

        self.csv_folder_name = tk.StringVar()
        tk.Label(master, text='Output folder name CSVs:').grid(row=grid_pos + 2, column=0, sticky=tk.E, padx=5)
        tk.Entry(master, textvariable=self.csv_folder_name).grid(row=grid_pos + 2, column=1, sticky=tk.W)

        self.max_processes = tk.IntVar()
        tk.Label(master, text='Number of parallel processes:').grid(row=grid_pos + 3, column=0, sticky=tk.E, padx=5)
        tk.Entry(master, textvariable=self.max_processes).grid(row=grid_pos + 3, column=1, sticky=tk.W)

        self.batch_size = tk.IntVar()
        tk.Label(master, text='Batch size:').grid(row=grid_pos + 4, column=0, sticky=tk.E, padx=5)
        tk.Entry(master, textvariable=self.batch_size).grid(row=grid_pos + 4, column=1, sticky=tk.W)

        self.highmag_layer = tk.StringVar()
        tk.Label(master, text='MAPS high magnification layer:').grid(row=grid_pos + 5, column=0, sticky=tk.E, padx=5)
        tk.Entry(master, textvariable=self.highmag_layer).grid(row=grid_pos + 5, column=1, sticky=tk.W)

        self.stitch_threshold = tk.IntVar()
        tk.Label(master, text='Stitch threshold:').grid(row=grid_pos + 6, column=0, sticky=tk.E, padx=5)
        tk.Entry(master, textvariable=self.stitch_threshold).grid(row=grid_pos + 6, column=1, sticky=tk.W)

        self.eight_bit = tk.BooleanVar()
        tk.Checkbutton(master, text='8 bit output', variable=self.eight_bit).grid(row=grid_pos + 7, column=1, sticky=tk.W)

        self.arrow_overlay = tk.BooleanVar()
        tk.Checkbutton(master, text='Add an arrow overlay that points to the fork', variable=self.arrow_overlay). \
            grid(row=grid_pos + 8, column=1, sticky=tk.W)

        self.contrast_enhance = tk.BooleanVar()
        tk.Checkbutton(master, text='Produce contrast enhanced images', variable=self.contrast_enhance). \
            grid(row=grid_pos + 9, column=1, sticky=tk.W)

        self.continue_processing = tk.BooleanVar()
        tk.Checkbutton(master, text='Continue processing an experiment', variable=self.continue_processing).\
            grid(row=grid_pos + 10, column=1, sticky=tk.W)

        # Run button
        self.run_button_text = tk.StringVar()
        self.run_button = tk.Button(master, textvariable=self.run_button_text, width=10)
        self.run_button_ready()
        self.run_button.grid(row=15, column=2, sticky=tk.W, pady=10, padx=10)

        # Reset button
        self.reset_button = tk.Button(master, text='Reset Parameters', width=20, command=self.reset_parameters)
        self.reset_button.grid(row=15, column=0, sticky=tk.E, pady=10, padx=10)

        # Stop button (available during run)
        self.reset_parameters()

    def reset_parameters(self):
        self.project_path.set('')
        self.max_processes.set(5)
        self.eight_bit.set(True)
        self.batch_size.set(5)
        self.output_folder.set('stitchedForks')
        self.csv_folder_name.set('annotations')
        self.highmag_layer.set('highmag')
        self.stitch_threshold.set(1000)
        self.arrow_overlay.set(True)
        self.contrast_enhance.set(True)
        self.continue_processing.set(False)
        self.classifier_input.set(False)
        self.csv_path.set('')

    def run(self):
        project_dir = Path(self.project_path.get())
        base_path = project_dir.parent
        project_name = project_dir.name

        params_set = self.check_all_parameters_set()
        if params_set and not self.continue_processing.get() and not self.classifier_input.get():
            self.create_logging_window()
            self.run_button_to_running()
            log_file_path = str(Path(project_dir) / (project_name + '.log'))
            logger = MapsXmlParser.create_logger(log_file_path)
            logger.info('Process experiment {}'.format(project_name))

            # thread = threading.Thread(target=self.dummy, args=(10, ))
            # thread.daemon = True
            # thread.start()
            thread = threading.Thread(target=self.run_from_beginning, args=(base_path, project_name,))
            thread.daemon = True
            thread.start()

        elif params_set and self.continue_processing.get():
            self.create_logging_window()
            self.run_button_to_running()
            logging.info('Continuing to process experiment {}'.format(project_name))
            thread = threading.Thread(target=self.continue_run, args=(base_path, project_name,))
            thread.daemon = True
            thread.start()

        elif params_set and self.classifier_input.get():
            self.create_logging_window()
            self.run_button_to_running()
            logging.info('Load classifier output for experiment {} from the csv file: {}'.format(project_name,
                                                                                                 self.csv_path.get()))
            thread = threading.Thread(target=self.classifier_input_run, args=(base_path, project_name,
                                                                              self.csv_path.get(),))
            thread.daemon = True
            thread.start()

        else:
            tkinter.messagebox.showwarning(title='Warning: parameters missing',
                                           message='You need to enter the correct kind of parameters in all the '
                                                   'required fields and then try again')

    def run_button_to_running(self):
        self.run_button_text.set('Running...')
        self.run_button.config(height=2, fg='gray', command=self.nothing)

    def run_button_ready(self):
        self.run_button_text.set('Run')
        self.run_button.config(height=2, fg='green', command=self.run, font=(self.font, 24, 'bold'))

    def run_from_beginning(self, base_path, project_name):
        # TODO: Catch issues when wrong path is provided or another error/warning occurs in the stitcher => catch my custom Exception, display it to the user
        stitcher = Stitcher(base_path, project_name, self.csv_folder_name.get(), self.output_folder.get())
        stitcher.parse_create_csv_batches(batch_size=self.batch_size.get(), highmag_layer=self.highmag_layer.get())
        stitcher.manage_batches(self.stitch_threshold.get(), self.eight_bit.get(), show_arrow=self.arrow_overlay.get(),
                                max_processes=self.max_processes.get(), enhance_contrast=self.contrast_enhance.get())
        stitcher.combine_csvs(delete_batches=True)
        logging.info('Finished processing the experiment')
        self.run_button_ready()


    def continue_run(self, base_path, project_name):
        stitcher = Stitcher(base_path, project_name, self.csv_folder_name.get(), self.output_folder.get())
        stitcher.manage_batches(self.stitch_threshold.get(), self.eight_bit.get(), show_arrow=self.arrow_overlay.get(),
                                max_processes=self.max_processes.get(), enhance_contrast=self.contrast_enhance.get())
        stitcher.combine_csvs(delete_batches=True)
        logging.info('Finished processing the experiment')
        self.run_button_ready()

    def classifier_input_run(self, base_path, project_name, csv_path):
        stitcher = Stitcher(base_path, project_name, self.csv_folder_name.get(), self.output_folder.get())
        stitcher.parse_create_classifier_csv_batches(batch_size=self.batch_size.get(), classifier_csv_path=csv_path,
                                                     highmag_layer=self.highmag_layer.get())
        stitcher.manage_batches(self.stitch_threshold.get(), self.eight_bit.get(), show_arrow=self.arrow_overlay.get(),
                                max_processes=self.max_processes.get(), enhance_contrast=self.contrast_enhance.get())
        stitcher.combine_csvs(delete_batches=True)
        logging.info('Finished processing the experiment')
        self.run_button_ready()

    def create_logging_window(self):
        # TODO: Check if the window already exists. Only make a new window if it doesn't exist yet
        log_window = tk.Toplevel(self.master)
        log_window.title('Log')
        LoggingWindow(log_window)

    def dummy(self, iterations):
        """Dummy run function to test the interface, e.g. locally on my Mac

        Function just does some logging so that the interface can be tested.

        Args:
            iterations (int): Number of log messages to be produced

        """
        logger = logging.getLogger(__name__)
        for i in range(iterations):
            logger.info('Running Dummy')
            time.sleep(1)

        for i in range(iterations):
            logger.info('Running Dummy 2! =D')
            time.sleep(1)

        self.run_button_ready()

    @staticmethod
    def nothing():
        """If the run button has already been pressed, just do nothing on future presses until the function finishes

        """
        pass

    def ask_for_path(self):
        path = tkinter.filedialog.askdirectory(title='Select folder containing the MapsProject.xml file')
        self.project_path.set(path)

    def ask_for_file(self):
        path = tkinter.filedialog.askopenfilename(title='Select the classifier output',
                                                  filetypes=(("csv files", "*.csv"), ("all files", "*.*")))
        self.csv_path.set(path)

    def display_csv_picker(self):
        if self.classifier_input.get():
            self.csv_picker_label.grid(row=2, column=0, sticky=tk.E)
            self.csv_picker_entry.grid(row=2, column=1, sticky=tk.W)
            self.csv_picker_button.grid(row=2, column=2, sticky=tk.W)
        else:
            self.csv_picker_label.grid_remove()
            self.csv_picker_entry.grid_remove()
            self.csv_picker_button.grid_remove()

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

            if self.classifier_input.get():
                params_set = params_set and len(self.csv_path.get()) > 0
                params_set = params_set and self.csv_path.get().endswith('.csv')

        except _tkinter.TclError:
            params_set = False

        return params_set

    def shutdown(self):
        # Helper function to shut down all stitching processes when the interface is quit
        if tk.messagebox.askokcancel("Quit", "Do you want to stop processing the experiment?"):
            self.master.destroy()
