# Import the required pacakage
import json
import openpyxl.cell
import streamlit
import requests
import openpyxl
import openpyxl.utils.dataframe
import openpyxl.cell.cell as Cell
import pandas as pd
from Extract_params import GenInfo, ToDataFrame, ByCropType
from From_q import FollowUp, SpecCrop
import requests

# Read in the form as csv
df = pd.read_csv('source_2.csv')

# Number of crop in the questionnaire
crops = df['What crops did you grow last year?'].iloc[0].split('\n')

# Write out the general info
FollowUp(df)

# Crop specific info
SpecCrop(df)

# Write into the inventory sheet
wb = openpyxl.load_workbook("Inventory sheet v1 - Grain.xlsx")
# Fill in general info
ws = wb['General information']

## Business name or client name
ws.cell(1,2).value = df['Property name and location'].iloc[0]
ws.cell(2,2).value = df['Property name and location'].iloc[0]

## Rainfall & request ETo from DPIRD
if df['Property average annual rainfall (mm)'].iloc[0] > 0:
    ws.cell(1, 11).value = df['Property average annual rainfall (mm)'].iloc[0]
else:
    # Request both rainfall and Eto from DPIRD
    pass

CropType = Cell.Cell(ws, 9, 1)

for i in range(12):
    CC = CropType.offset(i + 1)
    for crop in crops:
        if crop == CC.value:
            # Area sown
            CC.offset(column=2).value = df[f'What area was sown to {crop.lower()} last year? (Ha)'].iloc[0]
            # Last year yield
            CC.offset(column=3).value = df[f'What did your {crop.lower()} crop yield on average last year? (t/ha)'].iloc[0]
            # Fraction of crop burnt
            CC.offset(column=4).value = df[f'Was any land burned to prepare for {crop.lower()} crops last year? If so, how much? (Ha)'].iloc[0]

## Electricity
ws.cell(22, 5).value = df['Annual electricity usage last year (kwh)'].iloc[0]
ws.cell(22, 6).value = df['Annual renewable electricity usage last year (kwh)'].iloc[0]

ws = wb['Fertiliser Applied - Input']

# Fertiliser applied
# i = 0
# while i <= len()

fert_applied = []

for crop in crops:
    fert = {}
    for label, content in df.items():
        if crop.lower() in label and 'npk' in label.lower():
            product = content.iloc[0]
        if crop.lower() in label and 'rate' in label.lower():
            rate = content.iloc[0]
        fert[f'{product}'] = rate
    fert_applied.append(fert)

wb.save('test.xlsx')

# General info
loc, rain_over, prod_sys = GenInfo('Inventory sheet v1 - Grain.xlsx')

# Create a df using function
df = ToDataFrame('Inventory sheet v1 - Grain.xlsx')

# Separate it by crop type
Crop = ByCropType(df)

# Selected crop
# 0: Wheat
# 1: Barley
# 2: Canola
# 3: Lupins
# 4: Oats
# 5: Hay
# 6: Triticale
# 7: Field Peas
# 8: Chick Peas
# 9: Faba Beans
# 10: Lentils
# 11: Other Grains
selected_crop = 0

# url and key
API_url = 'https://emissionscalculator-mtls.production.aiaapi.com/calculator/v1/grains'
# Add in the key and perm file when AIA gets back to us
cert = ('something.key', 'something.perm')

# Set the header
Headers = {
    'Authorisation': 'Bearer <token>',
    'Content-type': 'application/json',
    'User-Agent': 'Chrome/120.0.0.0',
    "Accept": "application/json"
}

# params for the API
datas = {
    'state': loc,
    'crops': [
        {
            'type': Crop[selected_crop]['Crop type'],
            'state': loc,
            'productionSystem': prod_sys,
            'averageGrainYield': Crop[selected_crop]['Average grain yield (t/ha)'],
            'areaSown': Crop[selected_crop]['Area sown (ha)'],
            'nonUreaNitrogen': Crop[selected_crop]['Non-Yrea Nitrogen Applied (kg N/ha)'],
            'ureaApplication': Crop[selected_crop]['Urea Applied (kg Urea/ha)'],
            'ureaAmmoniumNitrate': Crop[selected_crop]['Urea-Ammonium Nitrate (UAN) (kg product/ha)'],
            'phosphorusApplication': Crop[selected_crop]['Phosphorus Applied (kg P/ha)'],
            'potassiumApplication': Crop[selected_crop]['Potassium Applied (kg K/ha)'],
            'sulfurApplication': Crop[selected_crop]['Sulfur Applied (kg S/ha)'],
            'rainfallAbove600': rain_over,
            'fractionOfAnnualCropBurnt': Crop[selected_crop]['Fraction of the annual production of crop that is burnt (ha/total crop ha)'],
            'herbicideUse': Crop[selected_crop]['General Herbicide/Pesticide use (kg a.i. per crop)'],
            'glyphosateOtherHerbicideUse': Crop[selected_crop]['Herbicide (Paraquat, Diquat, Glyphosate) (kg a.i. per crop)'],
            'electricityAllocation': Crop[selected_crop]['electricityAllocation'],
            'limestone': Crop[selected_crop]['Mass of Lime Applied (total tonnes)'],
            'limestoneFraction': Crop[selected_crop]['Fraction of Lime/Dolomite'],
            'dieselUse': Crop[selected_crop]['Annual Diesel Consumption (litres/year)'],
            'petrolUse': Crop[selected_crop]['Annual Petrol Use (litres/year)'],
            'lpg': Crop[selected_crop]['lpg']
        }
    ],
    'electricityRenewable': Crop[selected_crop]['% of electricity from renewable source'],
    'electricityUse': Crop[selected_crop]['Annual Electricity Use (state Grid) (kWh/crop)'],
    'vegetation': [
        {
            'vegetation': {
                'region': Crop[selected_crop]['region'],
                'treeSpecies': Crop[selected_crop]['treeSpecies'],
                'soil': Crop[selected_crop]['soil'],
                'area': Crop[selected_crop]['area'],
                'age': Crop[selected_crop]['age']
            },
            'allocationToCrops': Crop[selected_crop]['allocationToCrops']
        }
    ]
}

# GET request for the API Grains only
# response = requests.post(url=API_url, 
#                         headers=Headers,
#                         data=datas,
#                         cert=cert)