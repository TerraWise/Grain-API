import csv
import pandas as pd
import numpy as np
from datetime import datetime as dt
import os
import geopandas as gpd
import tempfile
import shutil
import glob

# Extract follow up question
def FollowUp(df: pd.DataFrame, dir):
    # Extract from csv
    info = {}
    # A fall back Attribute error
    try:
        info['Enterprises'] = df['Please select the following that best apply to your operation'].iloc[0].split('\n')
    except AttributeError:
        info['Enterprises'] = "Haven't selected business's enterprises"
    try:
        info['List of on-farm machinery'] = df['If you have a list of all on-farm machinery and equipment, please upload it here. Alternatively, please email it to toby@terrawise.au'].iloc[0].split('\n')
    except AttributeError:
        info['List of on-farm machinery'] = "Don't have attachment, please follow up"
    try:
        info['Farm management software'] = df['Please select the applications you use below'].iloc[0].split('\n')
    except AttributeError:
        info['Farm management software'] = "Didn't select software"
    try:    
        info['Variable rate'] = df['Do you utilise Variable Rate Technology (VRT) across your property? Or do you apply differing rates of fertiliser within paddock zones and/or crop types?'].iloc[0]
    except AttributeError:
        info['Variable rate'] = "Don't know. Need to ask again."    
    try:
        info['Access to software & \n record of variable rate'] = df['Are you happy to provide us with access to these applications, records and/or service providers to conduct your carbon account? If so, provide details via toby@terrawise.au or call 0488173271 for clarification'].iloc[0]
    except AttributeError:
        info['Access to software & \n record of variable rate'] = "Either no or hasn't been answered. Please follow up"
    # Write out the follow up question
    with open(os.path.join(dir, 'follow_up.csv'), 'w', newline='') as out:
        csv_out = csv.DictWriter(out, info.keys())
        csv_out.writeheader()
        csv_out.writerow(info)

def SpecCrop(df: pd.DataFrame, crops: list, dir):
    # Loops for crop specific info
    # based on the number of crops
    # Number of crop in the questionnaire
    for crop in crops:
        crop_info = {}
        for label, content in df.items():
            if crop.lower() in label:
                # Land management
                if 'land management' in label:
                    try:
                        crop_info[f'Land management practices - {crop}'] = content.iloc[0].split('\n')
                    except AttributeError:
                        crop_info[f'{crop}'] = "Wasn't answered in the form"
                # Contractors
                if 'contractor' in label:
                    try:
                        crop_info[f'{label}'] = content.iloc[0].split('\n')
                    except AttributeError:
                        crop_info[f'{label}'] = "Wasn't answered in the form"
        try:
            out = pd.DataFrame(dict([(key, pd.Series(value)) for key, value 
                                     in crop_info.items()]))
        except ValueError:
            out = pd.DataFrame(dict([(key, pd.Series(value)) for key, value 
                                     in crop_info.items()]), index=[0])
        out.to_csv(os.path.join(dir, f'{crop}_follow_up.csv'))

# Fertilser info from questionnaire
def ListFertChem(df: pd.DataFrame, crops: list, a: int) -> list:
    products_applied = []
    for crop in crops:
        products = {}
        names = []
        rates = []
        forms = []
        # area = [] 
        for label, content in df.items():
            if a == 1: # To choose fert
                cond = crop.lower() in label.lower() and 'fertiliser' in label.lower()
                if cond and 'npk' in label.lower():
                    try:
                        if not np.isnan(float(content.iloc[0])):
                            if cond and 'other' in label.lower():
                                names.append(content.iloc[0])
                    except ValueError:
                        names.append(content.iloc[0])
                if cond and 'rate' in label.lower():
                    rates.append(content.iloc[0])
                if cond and 'liquid' in label.lower():
                    forms.append(content.iloc[0])
                # if cond and 'hectares' in label.lower():
                #     area.append(content.iloc[0])
            else: # for chemical
                cond = crop.lower() in label.lower() and 'chemical' in label.lower()
                if cond and 'select' in label.lower():
                    try:
                        if not np.isnan(float(content.iloc[0])):
                            if crop.lower() in label and 'other' in label.lower() and 'chemical' in label.lower():
                                names.append(content.iloc[0])
                    except ValueError:
                        names.append(content.iloc[0])
                if cond and 'rate' in label.lower():
                    rates.append(content.iloc[0])
                if cond and 'liquid' in label.lower():
                    forms.append(content.iloc[0])
                # if cond and 'hectares' in label.lower():
                #     area.append(content.iloc[0])
        i = 0
        while i < len(names):
            products[f'product_{i}'] = {
                'name': names[i],
                'rate': rates[i],
                'form': forms[i]
            }
            i += 1
        products_applied.append(products)
    return products_applied

# Soil amelioration
def ToSoilAme(df: pd.DataFrame, crops: list) -> dict:
    # List of soil amelioration
    soil_amelioration = ['lime', 'dolomite']
    # Empty dict to store result
    products_applied = {}
    # Iterate over different crop types
    for crop in crops:
        products_applied[crop] = {}
        for ame in soil_amelioration: 
            for label, content in df.items():
                cond = crop.lower() in label.lower() and ame in label.lower()
                if  cond and 'hectares' in label.lower():
                    ha = content.iloc[0]
                if cond and 'rate' in label.lower():
                    rate = content.iloc[0]
            if not np.isnan(ha) or not np.isnan(rate):
                products_applied[crop][ame] = {
                    'rate': rate,
                    'area': ha
                }
    
    return products_applied

# Get the total number of products applied
def get_num_applied(crops: list, products_applied: dict):
    if len(crops) == 0:
        return 0
    return len(products_applied[crops[0]]) + get_num_applied(crops[1:], products_applied)

# Vegetation
def ToVeg(df: pd.DataFrame) -> dict:
    pre_year = dt.now().year

    vegetation = {}
    # Set the evaluate to 'Yes' or 'No' based on the questionnaire
    eva = df['Have you planted any vegetation (trees) on-farm since 1990?'].iloc[0]

    for label, content in df.items():
        cond = 'veg' in label.lower()
        if eva == 'Yes':
            if cond and 'describes' in label.lower():
                vegetation['species'] = content.iloc[0]
            if cond and 'hectares' in label.lower():
                vegetation['ha'] = content.iloc[0]
            if cond and 'year' in label.lower():
                planted_year = content.iloc[0]
                vegetation['age'] = pre_year - planted_year
            if cond and 'soil' in label.lower():
                vegetation['soil type'] = content.iloc[0]

    return vegetation

# Get the lat, lon of the shapefile
def GetXY(shapes):
    with tempfile.TemporaryDirectory() as td:
        # Iterate over the uploaded file to get the filename
        for shape in shapes:
            path = os.path.join(td, shape.name)
            with open(path, 'wb') as f:
                f.write(shape.getbuffer().tobytes())
        shape_paths = glob.glob(os.path.join(td, "*.shp"))
        gdfs = []
        # Read and store the require file in the cluster of shapefile
        for path in shape_paths:
            gdf = gpd.read_file(path)
            gdfs.append(gdf)
        # Group all the separate geo df into one complete geo df
        gdf = gpd.GeoDataFrame(pd.concat(gdfs))
        centroid = gdf.dissolve().centroid
        lon = centroid.x[0]
        lat = centroid.y[0]
        shutil.rmtree(td)
    return lon, lat
