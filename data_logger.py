#data_logger.py ver 0.5.0
import os
import csv
from datetime import datetime
import pyqtgraph as pg
from pyqtgraph import exporters

class DataLogger:
    def __init__(self, basepath, metadata_fieldnames, data_fieldnames):
        self.basepath = basepath
        self.metadata_fieldnames = metadata_fieldnames
        self.data_fieldnames = data_fieldnames
        self.metadata_written = False
        self.setup_csv()

    def setup_csv(self):
        mypath = os.path.join(self.basepath, 'Scanning_log_files')
        if not os.path.exists(mypath):
            os.makedirs(mypath)
        os.chdir(mypath)
        with open('data_temp.csv', 'w', encoding='utf-8') as csvfile:
            csvwriter = csv.DictWriter(csvfile, fieldnames=self.data_fieldnames + self.metadata_fieldnames)
            csvwriter.writeheader()

    def write_metadata(self, metadata):
        with open('data_temp.csv', 'a', encoding='utf-8') as csvfile:
            csvwriter = csv.DictWriter(csvfile, fieldnames=self.data_fieldnames + self.metadata_fieldnames)
            if not self.metadata_written:
                csvwriter.writerow(metadata)
                self.metadata_written = True

    def append_data_row(self, data_row):
        with open('data_temp.csv', 'a', encoding='utf-8') as csvfile:
            csvwriter = csv.DictWriter(csvfile, fieldnames=self.data_fieldnames + self.metadata_fieldnames)
            csvwriter.writerow(data_row)
            
    def write_run_notes(self, notes_dict, timestamp):
        notes_path = os.path.join(self.basepath, 'Scanning_log_files', f"{timestamp}_run_notes.csv")

        # Separate Run Method from Other Notes
        other_notes = notes_dict.get("Other_Notes", "")
        run_method = ""
        if "Run Method:" in other_notes:
            parts = other_notes.split("Run Method:", 1)
            notes_dict["Other_Notes"] = parts[0].strip()
            run_method = "Run Method:\n" + parts[1].strip()
        notes_dict["Run_Method"] = run_method

        with open(notes_path, 'w', encoding='utf-8', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(["Field", "Value"])
            for key, value in notes_dict.items():
                writer.writerow([key, value])
                if key == "Other_Notes":
                    writer.writerow([])
        print(f"Run notes written to {notes_path}")

    def save_final_csv_and_plot(self, plot_widget, timestamp):
        if os.path.exists('data_temp.csv'):
            #fileDateTime = datetime.strftime(datetime.now(), "%Y_%B_%d_%H%M%S") + ".csv"
            #plotDateTime = datetime.strftime(datetime.now(), "%Y_%B_%d_%H%M%S") + ".png"        
            
            fileDateTime = timestamp + ".csv"
            plotDateTime = timestamp + ".png"
            
            mypath = os.path.join(self.basepath, 'Scanning_log_files')
            os.rename('data_temp.csv', os.path.join(mypath, fileDateTime))
            print('CSV File saved as', os.path.join(mypath, fileDateTime))
            exporter = pg.exporters.ImageExporter(plot_widget.scene())
            exporter.export(os.path.join(mypath, plotDateTime))
            print(f"Plot saved as {os.path.join(mypath, plotDateTime)}")
        else:
            print("Error: data_temp.csv not found.")

    def clear_data(self):
        self.metadata_written = False
        self.setup_csv()
        print('Data cleared. Ready for next acquisition.')
