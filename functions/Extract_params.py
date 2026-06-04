# Import the required function
import pandas as pd
import openpyxl


# Funtion to create a df from excel sheet
def to_data_frame(excel_wb: str):
    wb = openpyxl.load_workbook(excel_wb, data_only=True)
    ws = wb["Farm Data - Grains"]
    headers = [ws.cell(row, 1).value for row in range(1, ws.max_row + 1)]
    rows = [
        [ws.cell(row, col).value for row in range(1, ws.max_row + 1)]
        for col in range(2, ws.max_column + 1)
    ]
    df = pd.DataFrame(rows, columns=headers)
    return df.iloc[0:12]


# Separate the big df into crop type
def by_crop_type(df: pd.DataFrame):
    Crop = []
    for i in df["Crop type"].index:
        Crop.append(df.iloc[i])
    return Crop


# Get the general information
def gen_info(excel_wb: str):
    # Read in the excel wb
    wb = openpyxl.load_workbook(excel_wb, data_only=True)
    # Activate the sheet
    ws = wb["👤 General information"]
    # Get the state loc info (assuming the cell does not change)
    loc = ws.cell(9, 2).value
    # Rainfall > 600mm
    if ws.cell(17, 2).value == "N":
        rain_over = False
    else:
        rain_over = True
    return loc, rain_over
