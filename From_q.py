import os, tempfile, shutil, glob, csv
import pandas as pd
import numpy as np
from datetime import datetime as dt
import geopandas as gpd


# Join crop specific dataframe
def CropAssemble(tmp_input_dir: str, crops: list) -> dict:
    cols_to_drop = [
        'ObjectID', 
        'GlobalID', 
        'ParentGlobalID', 
        'CreationDate', 
        'Creator', 
        'EditDate', 
        'Editor'
    ]
    crop_specific_input = {}
    for crop in crops:
        FertChem = []
        for csv in os.listdir(tmp_input_dir):
            if crop in csv:
                FertChem.append(
                    pd.read_csv(os.path.join(tmp_input_dir, csv))
                )
        crop_specific_input[crop] = pd.concat(FertChem, axis=1)
        crop_specific_input[crop] = crop_specific_input[crop].drop(cols_to_drop, axis=1)
    return crop_specific_input


# Extract follow up question
def FollowUp(df: pd.DataFrame, dir: str):
    # Extract from csv
    info = {}
    # A fall back Attribute error
    try:
        info['List of on-farm machinery'] = df['If you have a list of all on-farm machinery and equipment, please upload it here. Alternatively, please email it to toby@terrawise.au'].iloc[0].split('\n')
    except AttributeError:
        info['List of on-farm machinery'] = "Don't have attachment, please follow up"
    try:
        info['Farm management software'] = df['Please select the applications you use below'].iloc[0].split('\n')
    except AttributeError:
        info['Farm management software'] = "Didn't select software"
    try:
        info['Access to software & \n record of variable rate'] = df['Are you happy to provide us with access to these applications, records and/or service providers to conduct your carbon account? If so, provide details via toby@terrawise.au or call 0488173271 for clarification'].iloc[0]
    except AttributeError:
        info['Access to software & \n record of variable rate'] = "Either no or hasn't been answered. Please follow up"
    try:    
        info['Variable rate'] = df['Do you use variable rate technology (VRT) across your property ?'].iloc[0]
    except AttributeError:
        info['Variable rate'] = "Don't know. Need to ask again."
    if df['Do you engage any on-farm contractors used services during the year?'].iloc[0] == 'yes':
        try:
            info['Contractor activities'] = df['Select all that apply']
        except AttributeError:
            info['Contractor activities'] = "Yes engagement with contractor but didn't select the activities"
    else:
        info['Contractor activities'] = "No contractor activites on-farm during preivoues production year"
    # Write out the follow up question
    with open(os.path.join(dir, 'follow_up.csv'), 'w', newline='') as out:
        csv_out = csv.DictWriter(out, info.keys())
        csv_out.writeheader()
        csv_out.writerow(info)

def LandManagement(df: pd.DataFrame, crops: list, dir: str):
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
                        crop_info[f'Land management practices - {crop}'] = content.iloc[0].split(',')
                    except AttributeError:
                        crop_info[f'Land management practices - {crop}'] = "Wasn't answered in the form"
        out = pd.DataFrame(crop_info)
        out.to_csv(os.path.join(dir, f'LandMangementPractices.csv'))
       

# Fertilser info from questionnaire
def ListFertChem(input_dict: dict, crops: list, questionnaire_df: pd.DataFrame, which: str) -> dict:
    products_applied = {}
    for crop in crops:
        df = input_dict[crop]
        products = []
        names = []
        rates = []
        forms = []
        whole_area = questionnaire_df[f'What area was sown to {crop}?'].iloc[0]
        area = []
        for col in df.columns:
            for i in df.index:
                col_lower = col.lower()
                cond = which in col_lower
                if cond and 'select' in col_lower:
                    try:
                        if np.isnan(df[col].iloc[i]):
                            name = df['Please specify'].iloc[i].split('_')
                            names.append(' '.join(name))
                    except TypeError:
                        name = df[col].iloc[i].split('_')
                        names.append(' '.join(name))      
                if cond and 'rate' in col_lower:
                    if np.isnan(df[col].iloc[i]):
                        pass
                    else:
                        rates.append(df[col].iloc[i])
                if cond and 'how' in col_lower and 'hectares' in col_lower:
                    if df[col].iloc[i] == 'whole':
                        area.append(whole_area)
                    else:
                        area.append(
                            df[
                                'Please spcify the total area of your wheat crop this fertiliser was applied to'
                            ].iloc[i]
                        )
                if cond and 'form' in col_lower:
                    forms.append(df[col].iloc[i])
        j = 0
        while j < len(names):
            products.append(
                {
                    'name': names[j],
                    'form': forms[j],
                    'rate': rates[j],
                    'area': area[j]
                }
            )
            j += 1
        products_applied[crop] = products

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
