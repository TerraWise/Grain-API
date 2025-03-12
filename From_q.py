import os, tempfile, shutil, glob, csv
import pandas as pd
import numpy as np
from datetime import datetime as dt
import geopandas as gpd
from zipfile import ZipFile
import streamlit as st


def FromTheTop(zipfiles: list):
    for zipfile in zipfiles:
        with tempfile.TemporaryDirectory() as td:
            with ZipFile(zipfile) as zObject:
                zObject.extractall(td)
            for csv in os.listdir(td):
                if 'questionnaire' in csv.lower():
                    questionnaire_df = pd.read_csv(
                        os.path.join(td, csv)
                    )
            crops = questionnaire_df['crops_grown'].iloc[0].split(',')
            crop_specific_input = CropAssemble(td, crops)
            veg_df = VegetationDf(td)
    return crops, crop_specific_input, questionnaire_df, veg_df

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
        crop_specific_input[crop] = {}
        for csv in os.listdir(tmp_input_dir):
            input = csv.split('_')
            if input[0] != 'chem' and input[0] != 'machine':
                canola_in_csv = '_'.join(input[1:3])
            else:
                canola_in_csv = '_'.join(input[2:4])
            if canola_in_csv == crop:
                crop_specific_input[crop][input[0]] = (
                    pd.read_csv(os.path.join(tmp_input_dir, csv))
                    .drop(cols_to_drop, axis=1)
                )
            elif not 'gm_canola' in crop and crop in csv:
                crop_specific_input[crop][input[0]] = (
                    pd.read_csv(os.path.join(tmp_input_dir, csv))
                    .drop(cols_to_drop, axis=1)
                )
    return crop_specific_input

def VegetationDf(tmp_input_dir: str) -> pd.DataFrame:
    for csv in os.listdir(tmp_input_dir):
        if 'planting' in csv:
            return pd.read_csv(
                os.path.join(tmp_input_dir, csv)
            )
    return None


# Extract follow up question
def FollowUp(df: pd.DataFrame, dir: str):
    # Extract from csv
    info = {}
    # A fall back Attribute error
    try:
        info['List of on-farm machinery'] = df['If you have a list of all on-farm machinery and equipment, please upload it here. Alternatively, please email it to toby@terrawise.au'].iloc[0].split('\n')
    except KeyError:
        info['List of on-farm machinery'] = "Don't have attachment, please follow up"
    try:
        info['Farm management software'] = df['Please select the applications you use below'].iloc[0].split('\n')
    except AttributeError:
        info['Farm management software'] = "Didn't select software"
    try:
        info['Access to software & \n record of variable rate'] = df['Are you happy to provide us with access to these applications, record and/or service providers to conduct your carbon account?'].iloc[0]
    except AttributeError:
        info['Access to software & \n record of variable rate'] = "Either no or hasn't been answered. Please follow up"
    try:    
        info['Variable rate'] = df['Do you use variable rate technology (VRT) across your property ?'].iloc[0]
    except AttributeError:
        info['Variable rate'] = "Don't know. Need to ask again."
    if df['Do you engage any on-farm contractor services during the year?'].iloc[0] == 'yes':
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
        try:
            land_practices = df[f'alt_land_man_{crop}'].iloc[0].split(',')
            crop_info[f'Land management practices - {crop}'] = ', '.join(land_practices)
        except AttributeError:
            crop_info[f'Land management practices - {crop}'] = "Wasn't answered in the form"
        out = pd.DataFrame(crop_info.values(), index=crop_info.keys())
        out.to_csv(os.path.join(dir, f'LandMangementPractices.csv'))
       

# Fertilser info from questionnaire
def ListFertChem(input_dict: dict, crops: list, questionnaire_df: pd.DataFrame, which: str) -> dict:
    products_applied = {}
    for crop in crops:
        df = input_dict[crop][which]
        products = []
        names = []
        rates = []
        forms = []
        whole_area = questionnaire_df[f'area_sown_{crop.lower()}'].iloc[0]
        area = []
        times = []
        for col in df.columns:
            for i in df.index:
                col_lower = col.lower()
                if which == 'fert':
                    if 'npk' in col_lower:
                        name = df[col].iloc[i].split('_')
                        if name == 'other':
                            name = df[f'specify_fert_{crop.lower()}'].iloc[i].split('_')
                            brand = ' '.join(name)
                            names.append(brand.capitalize())
                        else:
                            brand = ' '.join(name)
                            names.append(brand.capitalize())  
                else:
                    if 'applied' in col_lower:
                        name = df[col].iloc[i].split('_')
                        if name == 'other':
                            name = df[f'specify_{which}_{crop.lower()}'].iloc[i].split('_')
                            brand = ' '.join(name)
                            names.append(brand.capitalize())
                        else:
                            brand = ' '.join(name)
                            names.append(brand.capitalize())  
                if 'form' in col_lower:
                    forms.append(df[col].iloc[i])
                try:
                    if forms[i] == 'liquid':
                        rates.append(df[f'{which}_rate_l_{crop}'].iloc[i])
                except IndexError:
                    continue
                else:
                    rates.append(df[f'{which}_rate_kg_{crop}'].iloc[i])
                if 'hectares' in col_lower and 'spec' not in col_lower:
                    if df[col].iloc[i] == 'whole':
                        area.append(whole_area)
                    elif 'spec' in col_lower:
                        area.append(
                            df[col].iloc[i]
                        )
                if 'times' in col_lower:
                    times.append(df[col].iloc[i])
        j = 0
        while j < len(names):
            st.write(f'Progressing: {j+1} out of {len(names)}')
            st.write(f'Product: {names[j]}\nRate: {rates[j]}\nArea: {area[j]}\nTimes: {times[j]}')
            products.append(
                {
                    'name': names[j],
                    'form': forms[j],
                    'rate': rates[j],
                    'area': area[j],
                    'times': times[j]
                }
            )
            j += 1
        products_applied[crop] = products
    return products_applied

# Soil amelioration
def ToSoilAme(df: pd.DataFrame, crops: list) -> dict:
    # List of soil amelioration
    soil_amelioration = ['lime', 'dolomite', 'gypsum', 'other']
    # Empty dict to store result
    products_applied = {}
    # Iterate over different crop types
    for i, crop in enumerate(crops):
        products_applied[crop] = []
        applied = 'no'
        for ame in soil_amelioration:
            for col in df.columns:
                col_lower = col.lower()
                cond = crop.lower() in col_lower and ame in col_lower
                if cond and 'applied' in col_lower:
                    applied = df[col].iloc[0]
                if applied == 'yes':
                    if ame == 'lime':
                        name = df[f'lime_or_limesand_{crop}'].iloc[0]
                    elif ame == 'other':
                        name = df[f'spec_amel_{crop}'].iloc[0]
                    else:
                        name = ame
                    if cond and 'hectares' in col_lower:
                        ha = df[col].iloc[0]
                    if cond and 'rate' in col_lower:
                        rate = df[col].iloc[0]  
                    if cond and 'location' in col_lower:
                        source = df[col].iloc[0]
                    if cond and 'times' in col_lower:
                        times = df[col].iloc[0]
            products_applied[crop].append(
                {
                    'name': name,
                    'source': source,
                    'rate': rate,
                    'area': ha,
                    'times': times
                }
            )
    return products_applied

# Vegetation
def ToVeg(veg_df, planting_shapes) -> dict:
    current_year = dt.now().year
    vegetation = []
    # Set the evaluate to 'Yes' or 'No' based on the questionnaire
    if veg_df is None:
        return None
    region, area = get_planting_region(planting_shapes)
    for i in veg_df.index:
        species = veg_df['Which species were planted?'].iloc[i]
        planted_year = veg_df['What year were these trees planted?'].iloc[i]
        configuration = veg_df['How were these plantings configured?'].iloc[i]
        soil_type = veg_df['What was the soil type?'].iloc[i]
        vegetation.append(
            {
                'region': region,
                'species': species,
                'soil': soil_type,
                'area': area,
                'planted_year': planted_year,
                'age': current_year - planted_year
            }
        )
    return vegetation

# Helper function for region
def get_planting_region(shapes):
    BOM_rainfall_gdf = gpd.read_file(
        os.path.join('input', 'BOM_RF_Region.zip')
    )
    gdf = read_shapes(shapes)

    BOM_rainfall_gdf = BOM_rainfall_gdf.to_crs('WGS84')
    gdf = gdf.to_crs('WGS84')

    clipped_region = BOM_rainfall_gdf.clip(gdf)

    region = clipped_region['DIST_NAME'].iloc[0]
    area = gdf.to_crs(gdf.estimate_utm_crs()).area.iloc[0]
    
    return region, area


# Get the lat, lon of the shapefile
def read_shapes(shapes):
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
        shutil.rmtree(td)
    return gdf


# Remove multiple files
def RemoveFiles(files: list):
    for file in files:
        os.remove(file)