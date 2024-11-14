# Import the required pacakage
import openpyxl.cell
import openpyxl
import openpyxl.utils.dataframe
import openpyxl.cell.cell as Cell
import pandas as pd
from Extract_params import GenInfo, ToDataFrame, ByCropType
from From_q import FollowUp, ListFertChem, ToSoilAme, ToVeg, SpecCrop, get_num_applied
import requests as rq
import streamlit as st
import shutil, os, tempfile
from datetime import datetime as dt
import numpy as np

# Get current path
cwd = os.getcwd()

st.title("Carbon accounting")

tool = st.radio("Select which tools you want to run:", ['Extraction', 'API'])
if tool == 'Extraction':
    st.header("Questionnaire extraction")

    in_q = st.file_uploader("Upload your questionnaire form as a csv format:", 'csv')

    try:
        df = pd.read_csv(in_q)
        crops = df['What crops did you grow last year?'].iloc[0].split('\n')
    except ValueError:
        st.write("Don't have an input")

    # Number of crop in the questionnaire
    if st.button("Get your crop types", "CropType"):
        # Read in the form as csv

        st.write(crops)

    if st.toggle("Do you want to check you questionnaire?"):
        df_t = {}
        for label, content in df.items():
            df_t[label] = content.iloc[0]
        st.dataframe(df_t)    

    config = {}
    config['filename'] = st.text_input("Name your file (client, location, etc.):")

    if st.button("Run"):
        # Temp output folder
        tmp_out = tempfile.mkdtemp(dir=cwd)
        # Write out the general info
        FollowUp(df, tmp_out)

        # Crop specific info
        SpecCrop(df, crops, tmp_out)
        # Write into the inventory sheet
        wb = openpyxl.load_workbook("Inventory sheet v1 - Grain.xlsx")
        # Fill in general info
        ws = wb['General information']

        ## Business name & location & rf
        ws.cell(1, 2).value = df['Property name '].iloc[0]
        ws.cell(2, 2).value = df['Property location'].iloc[0]
        ws.cell(1, 11).value = df['Property average annual rainfall (mm)'].iloc[0]
        for i in range(2, 3):
            ws.cell(1, i + 1).value = df[f'Property {i} name '].iloc[0]
            ws.cell(2, i + 1).value = df[f'Property {i} location'].iloc[0]
            ws.cell(1, i + 10).value = df[f'Property {i} average annual rainfall (mm)'].iloc[0]

        ## Rainfall & request ETo from DPIRD
        # if df['Property average annual rainfall (mm)'].iloc[0] > 0:
        #     ws.cell(1, 11).value = df['Property average annual rainfall (mm)'].iloc[0]
        # else:
        #     # Request both rainfall and Eto from DPIRD
        #     pass

        CropType = Cell.Cell(ws, 9, 1)

        for i in range(12):
            CC = CropType.offset(i + 1)
            for crop in crops:
                if crop == CC.value:
                    # Area sown
                    CC.offset(column=1).value = df[f'What area was sown to {crop.lower()} last year? (Ha)'].iloc[0]
                    # Last year yield
                    CC.offset(column=2).value = df[f'What did your {crop.lower()} crop yield on average last year? (t/ha)'].iloc[0]
                    # Fraction of crop burnt
                    CC.offset(column=3).value = df[f'Was any land burned to prepare for {crop.lower()} crops last year? If so, how much? (Ha)'].iloc[0] / df[f'What area was sown to {crop.lower()} last year? (Ha)'].iloc[0]

        ## Electricity
        ws.cell(22, 5).value = df['Annual electricity usage last year (kwh)'].iloc[0]
        try:
            ws.cell(22, 6).value = float(df['Percentage of annual renewable electricity usage last year '].iloc[0].rstrip('%'))
        except AttributeError:
            ws.cell(22, 6).value = float(df['Percentage of annual renewable electricity usage last year '].iloc[0])

        # Fertiliser
        ws = wb['Fertiliser Applied - Input']

        fert_applied = ListFertChem(df, crops, 1)

        for i, crop in enumerate(crops):
            ferts = fert_applied[i]
            space = 0
            if i == 0:
                row = 2
            if i > 0:
                row += len(fert_applied[i-1])
            for fert in ferts:
                # Product name
                ws.cell(row + space, 1).value = ferts[fert]['name']
                # # Rate
                ws.cell(row + space, 6).value = ferts[fert]['rate']
                # # Forms
                ws.cell(row + space, 2).value = ferts[fert]['form']
                # # Crop
                ws.cell(row + space, 4).value = crop 
                space += 1

        # Chemical
        ws = wb['Chemical Applied - Input']

        chem_applied = ListFertChem(df, crops, 2)

        for i, crop in enumerate(crops):
            chems = chem_applied[i]
            space = 0
            if i == 0:
                row = 2
            if i > 0:
                row += len(chem_applied[i-1])
            for chem in chems:
                # Product name
                ws.cell(row + space, 1).value = chems[chem]['name']
                # # Rate
                ws.cell(row + space, 17).value = chems[chem]['rate']
                # # Forms
                ws.cell(row + space, 2).value = chems[chem]['form']
                # # Crop
                ws.cell(row + space, 16).value = crop
                space += 1

        # Lime/gypsum
        ws = wb['Lime Product - Input']

        products_applied = ToSoilAme(df, crops)

        num_prod_applied = get_num_applied(crops, products_applied)

        i = 0
        while i < num_prod_applied:
            for crop in crops:
                for product in products_applied[crop]:
                    # Product
                    ws.cell(2 + i, 1).value = product
                    # Crop
                    ws.cell(2 + i, 3).value = crop
                    # Area
                    ws.cell(2 + i, 5).value = products_applied[crop][product]['area']
                    # Rate
                    ws.cell(2 + i, 4).value = products_applied[crop][product]['rate']
                    i += 1

        #  Fuel usage
        ws = wb['Fuel Usage - Input']

        # Vegetation
        ws = wb['Vegetation - Input']

        vegetation = ToVeg(df)

        try:
            ws.cell(2, 2).value = vegetation['species']
            ws.cell(2, 3).value = vegetation['soil type']
            ws.cell(2, 4).value = vegetation['ha']
            ws.cell(2, 5).value = vegetation['age']
        except KeyError:
            pass

        wb.save(os.path.join(tmp_out, 'Inventory_Sheet.xlsx'))

        shutil.make_archive("Question_Extract", "zip", tmp_out)

        zip_name = config['filename'] + str(dt.today().strftime('%d-%m-%Y'))

        with open("Question_Extract.zip", "rb") as f:
            st.download_button('Download the extracted info', f, file_name=zip_name+".zip")

        shutil.rmtree(tmp_out)
else:
    st.header("Send to AIA")

    st.subheader("Disclaimer")
    st.text(
        "Before uploading the excel file, please open and save it so the data can be \nupdated accordingly"
    )

    ex_file = st.file_uploader("Upload your inventory sheet:",'xlsx')

    try:
        # Create a df using function
        df = ToDataFrame(ex_file)

        # Separate it by crop type
        Crop = ByCropType(df)
        # Display the dataframe for checking
        if st.toggle("Do you want to check your input data frame?"):
            st.dataframe(Crop, hide_index=True)
            st.write("If there are no data, please refer to the text above")
        # Choose the desired crop to send a request
        desired_crop = st.radio('Choose which crop to send your request:', df['Crop type'].loc[df['Area sown (ha)']>0])
    except TypeError:
        st.write("Don't have an excel file to read")

    if st.button('Run'):

        # General info
        loc, rain_over, prod_sys = GenInfo(ex_file)

        # To get the selected crop index
        for i, crop in enumerate(Crop):
            if desired_crop == Crop[i]['Crop type']:
                selected_crop = i

        if prod_sys == None:
            prod_sys = 'Non-irrigated crop'

        # params for the API
        datas = {
            'state': 'wa_sw',
            'crops': [
                {
                    'type': Crop[selected_crop]['Crop type'],
                    'state': 'wa_sw',
                    'productionSystem': prod_sys,
                    'averageGrainYield': float(Crop[selected_crop]['Average grain yield (t/ha)']),
                    'areaSown': float(Crop[selected_crop]['Area sown (ha)']),
                    'nonUreaNitrogen': float(Crop[selected_crop]['Non-Urea Nitrogen Applied (kg N/ha)']),
                    'ureaApplication': float(Crop[selected_crop]['Urea Applied (kg Urea/ha)']),
                    'ureaAmmoniumNitrate': float(Crop[selected_crop]['Urea-Ammonium Nitrate (UAN) (kg product/ha)']),
                    'phosphorusApplication': float(Crop[selected_crop]['Phosphorus Applied (kg P/ha)']),
                    'potassiumApplication': float(Crop[selected_crop]['Potassium Applied (kg K/ha)']),
                    'sulfurApplication': float(Crop[selected_crop]['Sulfur Applied (kg S/ha)']),
                    'rainfallAbove600': bool(rain_over),
                    'fractionOfAnnualCropBurnt': float(Crop[selected_crop]['Fraction of the annual production of crop that is burnt (%)']),
                    'herbicideUse': float(Crop[selected_crop]['General Herbicide/Pesticide use (kg a.i. per crop)']),
                    'glyphosateOtherHerbicideUse': float(Crop[selected_crop]['Herbicide (Paraquat, Diquat, Glyphoste) (kg a.i. per crop)']),
                    'electricityAllocation': float(Crop[selected_crop]['electricityAllocation']),
                    'limestone': float(Crop[selected_crop]['Mass of Lime Applied (total tonnes)']),
                    'limestoneFraction': float(Crop[selected_crop]['Fraction of Lime/Dolomite']),
                    'dieselUse': float(Crop[selected_crop]['Annual Diesel Consumption (litres/year)']),
                    'petrolUse': float(Crop[selected_crop]['Annual Pertol Use (litres/year)']),
                    'lpg': 0
                }
            ],
            'electricityRenewable': float(Crop[selected_crop]['% of electricity from renewable source']),
            'electricityUse': float(Crop[selected_crop]['Annual Electricity Use (state Grid) (KWh)']),
        }

        if np.isnan(Crop[selected_crop]['Area (ha)']):
            datas['vegetation'] = [
                {
                    'vegetation': {
                        'region': 'South Coastal',
                        'treeSpecies': 'No tree data available',
                        'soil': 'No Soil / Tree data available',
                        'area': 0,
                        'age': 0
                    },
                    'allocationToCrops': [0]
                }
            ]
        else:
            datas['vegetation'] = [
                {
                    'vegetation': {
                        'region': Crop[selected_crop]['Region'],
                        'treeSpecies': Crop[selected_crop]['Tree Species'],
                        'soil': Crop[selected_crop]['Soil'],
                        'area': float(Crop[selected_crop]['Area (ha)']),
                        'age': float(Crop[selected_crop]['Age (yrs)'])
                    },
                    'allocationToCrops': [
                        float(Crop[selected_crop]['Allocation to crop'])
                        ]
                }
            ]

        # Set the header
        Headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "terrawise"
        }

        # url and key
        API_url = 'https://emissionscalculator-mtls.production.aiaapi.com/calculator/v1/grains'
        # Add in the key and perm file when AIA gets back to us
        key = 'carbon-calculator-integration.key'
        pem = 'aiaghg-terrawise.pem'

        # POST request for the API Grains only
        response = rq.post(url=API_url, headers=Headers, json=datas, cert=(pem, key))

        st.write(response.status_code)

        response_dict = response.json()

        scopes = ['scope1', 'scope2', 'scope3']

        metrics_list = []

        for scope in scopes:
            for metric in response_dict[scope]:
                metrics_list.append(
                    {
                        'scope': scope,
                        'metric': metric,
                        'value': response_dict[scope][metric]
                    }
                )

        metrics_list.append(
            {
                'scope': 'carbonSequestration',
                'metric': 'total',
                'value': response_dict['carbonSequestration']['total']  
            }
        )
        metrics_list.append(
            {
                'scope': 'carbonSequestration',
                'metric': 'intermediate',
                'value': response_dict['carbonSequestration']['intermediate'][0]
            }
        )
        metrics_list.append(
            {
                'scope': 'net',
                'metric': 'crop',
                'value': response_dict['net']['crops'][0]
            }
        )
        metrics_list.append(
            {
                'scope': 'net',
                'metric': 'total',
                'value': response_dict['net']['total']
            }
        )
        metrics_list.append(
            {
                'scope': 'intensities',
                'metric': 'intensities',
                'value': response_dict['intensities'][0]
            }
        )
        metrics_list.append(
            {
                'scope': 'intensitiesWithSequestration',
                'metric': 'grainsExcludingSequestraion',
                'value': response_dict['intensitiesWithSequestration'][0]['grainsExcludingSequestration']
            }
        )
        metrics_list.append(
            {
                'scope': 'intensitiesWithSequestration',
                'metric': 'grainsIncludingSequestration',
                'value': response_dict['intensitiesWithSequestration'][0]['grainsIncludingSequestration']
            }
        )

        out = pd.DataFrame(metrics_list)

        out_dir = tempfile.mkdtemp(dir=cwd)

        out.to_csv(os.path.join(out_dir, 'output.csv'), index=False)

        with open(os.path.join(out_dir, 'output.csv'), "rb") as f:
            st.download_button('Download the AIA result', f, file_name='output.csv')

        shutil.rmtree(out_dir)

        
        