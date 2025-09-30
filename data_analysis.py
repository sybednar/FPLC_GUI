#data_analysis ver 0.5.0
#09-29-25 enchanced replot_from_csv function to incorporate pumpB% data plotting
import os
import csv
import pandas as pd
from PySide6.QtWidgets import QFileDialog
from scipy.signal import savgol_filter, find_peaks
from pybaselines.whittaker import asls


def extract_metadata_from_csv(csv_path):
    metadata = {
        "Column_type": "Unknown Column",
        "Flowrate (ml/min)": "N/A",
        "Year/Date/Time": "Unknown Time"
    }

    try:
        df = pd.read_csv(csv_path)
        first_valid_row = df[df["Column_type"].notna()].iloc[0]

        metadata["Column_type"] = str(first_valid_row.get("Column_type", "Unknown Column"))
        metadata["Flowrate (ml/min)"] = str(first_valid_row.get("Flowrate (ml/min)", "N/A"))
        metadata["Year/Date/Time"] = str(first_valid_row.get("Year/Date/Time", "Unknown Time"))

    except Exception as e:
        print(f"Error extracting metadata: {e}")

    return metadata

def replot_from_csv(basepath, plot_widget, run_volume, max_y_value, update_plot, csv_path=None):
    """
    Replot data from a user-selected CSV file using the existing plot_widget.
    Plots Eluate_Volume (ml) vs Chan1_AU280 (AU), Chan2, Frac_Mark, and PumpB % if available.
    Sets x-axis range based on RUN_VOLUME (ml) value in the CSV metadata.
    """
    import csv

    if not csv_path:
        file_dialog = QFileDialog()
        file_dialog.setNameFilter("CSV files (*.csv)")
        file_dialog.setDirectory(os.path.join(basepath, 'Scanning_log_files'))
        if file_dialog.exec():
            selected_files = file_dialog.selectedFiles()
            if not selected_files:
                print("No file selected.")
                return
            csv_path = selected_files[0]
        else:
            print("File dialog canceled.")
            return

    eluate_volume_data = []
    chan1_AU280_data = []
    chan2_data = []
    frac_mark_flags = []
    pumpB_percent_data = []
    extracted_run_volume = None
    headers = []

    with open(csv_path, 'r', encoding='utf-8') as file:
        reader = csv.reader(file)
        for row in reader:
            if not headers:
                headers = [h.strip() for h in row]
                continue
            row_dict = dict(zip(headers, row))
            try:
                vol = float(row_dict["Eluate_Volume (ml)"])
                au = float(row_dict["Chan1_AU280 (AU)"])
                chan2 = float(row_dict.get("Chan2", 0.0))
                frac = float(row_dict.get("Frac_Mark", 0))
                pumpB = float(row_dict.get("PumpB_percent", 0.0))

                eluate_volume_data.append(vol)
                chan1_AU280_data.append(au)
                chan2_data.append(chan2)
                frac_mark_flags.append(frac)
                pumpB_percent_data.append(pumpB)

                if extracted_run_volume is None and row_dict.get("RUN_VOLUME (ml)"):
                    extracted_run_volume = float(row_dict["RUN_VOLUME (ml)"])
            except (ValueError, KeyError):
                continue

    max_abs = max(chan1_AU280_data) if chan1_AU280_data else 1.0
    frac_mark_data = [0.1 * max_abs if flag == 1.0 else 0.0 for flag in frac_mark_flags]

    if extracted_run_volume is not None:
        run_volume = extracted_run_volume
        plot_widget.setXRange(0, run_volume, padding=0)

    update_plot(
        plot_widget,
        elapsed_time_data=[],  # Not used
        eluate_volume_data=eluate_volume_data,
        chan1_AU280_data=chan1_AU280_data,
        chan2_data=chan2_data,
        frac_mark_data=frac_mark_data,
        run_volume=run_volume,
        max_y_value=max_y_value,
        pumpB_percent_data=pumpB_percent_data
    )

    
def apply_savgol_smoothing_with_frac_marks(csv_path, window_length=51, polyorder=3):
    """
    Applies Savitzky-Golay smoothing to Chan1_AU280 (AU) and returns a DataFrame
    with smoothed data and scaled Frac_Mark spikes.
    """
    df = pd.read_csv(csv_path)
    if "Chan1_AU280 (AU)" in df.columns and df["Chan1_AU280 (AU)"].notna().sum() >= window_length:
        smoothed = savgol_filter(df["Chan1_AU280 (AU)"].ffill(), window_length, polyorder)
        df["Chan1_AU280_Smoothed (AU)"] = smoothed
        
        max_y = max(df["Chan1_AU280 (AU)"].max(), smoothed.max())
        df["Frac_Mark_Scaled"] = df["Frac_Mark"].apply(lambda x: 0.1 * max_y if x == 1.0 else 0.0)
        
        df.to_csv(csv_path, index=False)
        return df
    else:
        raise ValueError("Insufficient data points or missing column for smoothing.")    

def smooth_and_detect_peaks(csv_path, window_length, polyorder, distance=100, baseline_correction=False, lam=1e5, p=0.01, max_iter=10):
    df = pd.read_csv(csv_path)

    # Apply baseline correction if enabled
    if baseline_correction:
        baseline, _ = asls(df["Chan1_AU280 (AU)"].values, lam=lam, p=p, max_iter=max_iter)
        corrected = df["Chan1_AU280 (AU)"].values - baseline
    else:
        corrected = df["Chan1_AU280 (AU)"].values
    # Apply Savitzky-Golay smoothing
    df["Chan1_AU280_Smoothed (AU)"] = savgol_filter(corrected, window_length, polyorder)

    # Scale fraction marks to 10% of max absorbance
    max_abs = max(df["Chan1_AU280 (AU)"].max(), df["Chan1_AU280_Smoothed (AU)"].max())
    df["Frac_Mark_Scaled"] = df["Frac_Mark"].apply(lambda x: 0.1 * max_abs if x == 1.0 else 0.0)

    # Detect peaks
    peaks, _ = find_peaks(df["Chan1_AU280_Smoothed (AU)"], height=0.05 * max_abs, distance=distance)
    frac_mark_indices = df.index[df["Frac_Mark"] == 1.0].tolist()

    return df, peaks, frac_mark_indices




