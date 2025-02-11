# Import the required pacakage
import openpyxl.cell
import openpyxl
import openpyxl.utils.dataframe
import openpyxl.cell.cell as Cell
import pandas as pd
from Extract_params import *
from From_q import *
import requests as rq
import streamlit as st
import shutil, os, tempfile
from datetime import datetime as dt
import numpy as np
import datetime as dt
from weather_stations import *
from zipfile import ZipFile

# Get current path
cwd = os.getcwd()

st.title("Carbon accounting tool")

tool = st.sidebar.radio("Select which tools you want to run:", ['Extraction', 'API'])

if tool == "Extraction":
    st.header("Questionnaire extraction")

    zipfile = st.file_uploader("Upload your questionnaire form as a csv format:", 'csv')

    tmp_input_dir = tempfile.mkdtemp()

    with ZipFile(zipfile) as zObject:
        zObject.extractall(tmp_input_dir)
    for csv in os.listdir(
        os.path.join(os.curdir, tmp_input_dir)
    ):
        if 'questionnaire' in csv:
            questionnaire_df = pd.read_csv(csv)

    cols_to_drop = [
        'ObjectID', 
        'GlobalID',
        'CreationDate', 
        'Creator', 
        'EditDate', 
        'Editor',
        'x',
        'y'
    ]

    questionnaire_df = questionnaire_df.drop(cols_to_drop, axis=1)

    production_year = dt.strptime(questionnaire_df['Production Year'].iloc[0]).year

    questionnaire_df['Production Year'].iloc[0] = production_year

    try:
        crops = questionnaire_df['What crops did you grow last year?'].iloc[0].split(',')
        crop_specific_input = CropAssemble(tmp_input_dir, crops)
    except ValueError:
        st.write("Don't have an input")

    # Number of crop in the questionnaire
    if st.button("Get your crop types", "CropType"):
        # Read in the form as csv

        st.write(crops)

    tab1, tab2, tab3 = st.tabs(['Check questionnaire', 'Check fert/chem input', "Get weather from DPIRD's API"])

    with tab1:
        try:
            df_t = {}
            for label, content in questionnaire_df.items():
                df_t[label] = content.iloc[0]
            # Transform the questionnaire into a df for first pass
            st.dataframe(df_t)
        except NameError:
            st.write("Nothing to see here!")

    with tab2:
        try:
            crop = st.radio('Choose the crop to view', crops)
            st.write(crop_specific_input[crop])
        except Exception as e:
            st.write(e)

    with tab3:
        # Upload shapefile for SILO's API (weather data)
        shapes = st.file_uploader("Upload all of your shapefile for weather data or the compressed file:", accept_multiple_files=True)

        try: # Incase there are no files (don't want to scare people away)
            # Get the coordinate from the shapefile
            lon, lat = GetXY(shapes)

            # A df of nearest station
            nearest_station = get_nearby_stations(lat, lon)

            # To show four nearest weather station with the
            # fraction of data from BOM
            st.write(percentage_from_BOM(nearest_station.index.to_list(), nearest_station))

            endYear = int(st.text_input("Input the end year (YYYY):", "2023"))

            # Get a list of weather data from all four weather station
            weather_dfs = to_list_dfs(endYear, nearest_station)

            # Choose the data from a weather station or
            # a weighted average of multiple stations
            selected_stations = st.multiselect("Select your weather station (one or multiples):", nearest_station.iloc[:,0].to_list())
        except ValueError:
            st.write("Haven't upload a bunch of shapefiles yet")

        if st.button("Retrive your data from SILO Long Paddock"):
            # Indexes to go through the list of selected
            # station and list of all weather station's df
            i, j = 0, 0
            # If multiples stations are selected create a
            # list
            if len(selected_stations) > 1:
                extracted_df = []
            if len(selected_stations) == 0:
                raise Exception("Haven't selected a weather station")
            
            # Append the selected stations into the extracted list
            while i < len(selected_stations) and j < len(weather_dfs):
                if weather_dfs[j].iloc[0, 0] == selected_stations[i]:
                    try:
                        extracted_df.append(weather_dfs[j])
                    except NameError:
                        extracted_df = weather_dfs[j]
                    j = 0
                    i += 1
                else:
                    j += 1

            # Create an empty df for extracted data or
            # weighted average if multiple stations
            daily_df = pd.DataFrame()
            try: 
                daily_df['Date'] = extracted_df[0]["YYYY-MM-DD"]
            except KeyError:
                daily_df['Date'] = extracted_df["YYYY-MM-DD"]
            daily_df["Year"] = [int(i[0:4]) for i in daily_df['Date']]
            daily_df["Rain"] = weighted_ave_col(extracted_df, "daily_rain", nearest_station, selected_stations)
            daily_df["ETShortCrop"] = weighted_ave_col(extracted_df, "et_short_crop", nearest_station, selected_stations)
            daily_df["ETTallCrop"] = weighted_ave_col(extracted_df, "et_tall_crop", nearest_station, selected_stations)

            # Create a folder for saving and linkage
            # to the excel writing
            try:
                os.mkdir(os.path.join(cwd, 'weather_output'))
            except FileExistsError:
                pass

            daily_df.to_csv(os.path.join(cwd, 'weather_output', f'{'+'.join(str(station) for station in selected_stations)}_daily_df.csv'))

            rain, eto_short, eto_tall = annual_summary(daily_df)

            # Save the annual weather data as csv without indexes
            pd.DataFrame(
                {"Rainfall_2yr_ave_mm": rain, "ETo_Short_2yr_ave_mm": eto_short, "ETo_Tall_2yr_ave_mm": eto_tall}, index=[0]
                ).to_csv(
                    os.path.join(cwd, 'weather_output', f'{'+'.join(str(station) for station in selected_stations)}_annual_ave_df.csv'), index=False
                    )
            
            # Put everything into a zip file
            shutil.make_archive("Weather_data", "zip", os.path.join(cwd, 'weather_output'))

            zip_name = f'{'+'.join(str(num) for num in selected_stations)}' + str(dt.today().strftime('%d-%m-%Y'))
            # Download the zip file
            with open("Weather_data.zip", "rb") as f:
                st.download_button('Download weather data?', f, file_name=zip_name+".zip")

    if st.button("Start the extraction process", key="Extraction"):
        # A temporary output file
        tmp_out = tempfile.mkdtemp()
        # Write out the general info
        FollowUp(questionnaire_df, tmp_out)

        # Crop specific info
        LandManagement(questionnaire_df, crops, tmp_out)

        # Write into the inventory sheet
        wb = openpyxl.load_workbook("Inventory sheet v2 - Grain.xlsx")

        # Fill in general info
        ws = wb['General information']

        # General information
        # Client name
        ws.cell(2, 2).value = questionnaire_df['Client Name'].iloc[0]
        # Business name
        ws.cell(3, 2).value = questionnaire_df['Business Name'].iloc[0]
        # Client email
        ws.cell(4, 2).value = questionnaire_df['Email Address'].iloc[0]
        # Production year assessed
        ws.cell(5, 2).value = production_year

        # Location
        # Property name
        ws.cell(7, 2).value = questionnaire_df['Property Name'].iloc[0]
        # Property address
        ws.cell(8, 2).value = questionnaire_df['Property Addresss'].iloc[0]
        # State
        ws.cell(9, 2).value = questionnaire_df['State'].iloc[0]
        # Farm map or paddock boundaries
        ws.cell(10, 2).value = questionnaire_df['Farm map or paddock boundaries']

        # Climate
        ## Rainfall & request ETo from DPIRD
        try:
            ws.cell(12, 2).value = questionnaire_df['Property average annual rainfall'].iloc[0]
        except AttributeError:
            ws.cell(12, 2).value = "Didn't provide rainfall data"
        # Data from the weather_output/
        SILO_weather = pd.read_csv(os.path.join(cwd, 'weather_output', f'{'+'.join(str(station) for station in selected_stations)}_annual_ave_df.csv'))
        # Rainfall
        ws.cell(13, 2).value = SILO_weather.loc[0, 'Rainfall_2yr_ave_mm']
        # Evapotranspiration
        ws.cell(16, 2).value = SILO_weather.loc[0, 'ETo_Short_2yr_ave_mm']
        ws.cell(17, 2).value = SILO_weather.loc[0, 'ETo_Tall_2yr_ave_mm']

        # Software
        # Farm management software (Y/N)
        ws.cell(19, 2).value = questionnaire_df[
            'Do you use any Farm Management Practices software applications?'
        ].iloc[0]
        # List
        if np.isnan(questionnaire_df['Please select the applications you use below']):
            ws.cell(20, 2).value = questionnaire_df['Please specify'].iloc[0]
        else:
            ws.cell(20, 2).value = questionnaire_df[
                'Please select the applications you use below'
            ].iloc[0].split(',')
        # Practices
        # VRT
        ws.cell(22, 2).value = questionnaire_df[
            'Do you use variable rate technology (VRT) across your property ?'
        ].iloc[0]

        # Vegetation
        # Planting post_1990 (Y/N)
        ws.cell(25, 2).value = questionnaire_df[
            'Have you planted any vegetation (tress) on-farm since 1990'
        ].iloc[0]
        # Planting mapped (Y/N)?

        # Fuel
        fuels = ['diesel', 'petrol', 'LPG']
        for i, fuel in enumerate(fuels):
            # Begining (L)
            ws.cell(33 + 3 * i, 2).value = questionnaire_df[
                f'How much {fuel} did you have on hand at the start of the last calendar year?'
            ].iloc[0]
            # Purchased (L)
            ws.cell(34 + 3 * i, 2).value = questionnaire_df[
                f'How much {fuel} did you purchase throughout the year?'
            ].iloc[0]
            # End (l)
            ws.cell(35 + 3 * i, 2).value = questionnaire_df[
                f'How much {fuel} did you have on hand at the end of the last calendar year?'
            ].iloc[0]


        # Set the reference cell for offset below
        CropType = Cell.Cell(ws, 9, 1)
        # Write into cells under corresponding crop types
        # using the refrence cell
        for i in range(12): # Number of crop type
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
        # Percentage of renewable electricity
        try:
            ws.cell(22, 6).value = float(df['Percentage of annual renewable electricity usage last year '].iloc[0].rstrip('%'))
        except AttributeError:
            ws.cell(22, 6).value = float(df['Percentage of annual renewable electricity usage last year '].iloc[0])

        # Fertiliser
        ws = wb['Fertiliser Applied - Input']
        # List of fertiliser applied breaks down by
        # crop type
        fert_applied = ListFertChem(df, crops, 1)
        # Loop to write into the worksheet
        for i, crop in enumerate(crops):
            ferts = fert_applied[i]
            space = 0 # Spacing between products of the same crop
            if i == 0: # Set the starting row
                row = 2
            if i > 0: # Starting row after first crop
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
        # List of chemical applied break downs
        # by crop
        chem_applied = ListFertChem(df, crops, 2)
        # Refer to fertiliser section
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
        # List of products (lime/dolomite and gypsum) applied
        # breaking down by crop type
        products_applied = ToSoilAme(df, crops)
        # Total numbers of product applied
        num_prod_applied = get_num_applied(crops, products_applied)

        i = 0 # Spacing
        # Loop to write into the worksheet
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

        # A dictionary of vegetation planted
        vegetation = ToVeg(df)

        # Write into the worksheet
        try:
            ws.cell(2, 2).value = vegetation['species']
            ws.cell(2, 3).value = vegetation['soil type']
            ws.cell(2, 4).value = vegetation['ha']
            ws.cell(2, 5).value = vegetation['age']
        except KeyError: # If no vegetation planted, pass
            pass
        
        # Save the workbook
        wb.save(os.path.join(tmp_out, 'Inventory_Sheet.xlsx'))
        
        # Create a zip to save follow ups question
        # and workbook
        shutil.make_archive("Question_Extract", "zip", tmp_out)

        # Name the file by the first property name
        zip_name = df.loc[0, 'Property name '] + '_' + str(dt.today().strftime('%d-%m-%Y'))

        with open("Question_Extract.zip", "rb") as f:
            st.download_button('Download the extracted info', f, file_name=zip_name+".zip")
        
        # Remove the unused folder
        shutil.rmtree(tmp_out)
        shutil.rmtree(os.path.join(cwd, 'weather_output'))
else:
    st.header("Send to AIA")

    st.subheader("Disclaimer")
    st.write(
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
        desired_crop = st.multiselect('Choose which crop to send your request:', df['Crop type'].loc[df['Area sown (ha)']>0].to_list())
    except TypeError:
        st.write("Don't have an excel file to read")

    # Name the file by the first property name
    filename = st.text_input('Save the file as:', key='GAFF_file')

    if st.button('Run', key="AIA_API"):

        # General info
        loc, rain_over, prod_sys = GenInfo(ex_file)

        # params json
        datas = {
            'state': 'wa_sw',
            'crops': [],
            'electricityRenewable': float(Crop[0]['% of electricity from renewable source']),
            'electricityUse': float(Crop[0]['Annual Electricity Use (state Grid) (KWh)']),
            'vegetation': []
        }

        # To get the selected crop index
        i = 0
        j = 0
        selected_crop = []
        while i < len(desired_crop) and j < len(Crop):
            if desired_crop[i] == Crop[j]['Crop type']:
                selected_crop.append(j)
                if desired_crop[i] == 'Canola':
                    Crop[j]['Crop type'] = 'Oilseeds'
                j = 0
                i += 1
            else:
                j += 1

        # Default the production system
        # to 'Non-irrigated crop'
        if prod_sys == None:
            prod_sys = 'Non-irrigated crop'

        # params for the API
        for i in range(len(selected_crop)): # For one or multiple crops
            datas['crops'].append({
                'type': Crop[selected_crop[i]]['Crop type'],
                'state': 'wa_sw',
                'productionSystem': prod_sys,
                'averageGrainYield': float(Crop[selected_crop[i]]['Average grain yield (t/ha)']),
                'areaSown': float(Crop[selected_crop[i]]['Area sown (ha)']),
                'nonUreaNitrogen': float(Crop[selected_crop[i]]['Non-Urea Nitrogen Applied (kg N/ha)']),
                'ureaApplication': float(Crop[selected_crop[i]]['Urea Applied (kg Urea/ha)']),
                'ureaAmmoniumNitrate': float(Crop[selected_crop[i]]['Urea-Ammonium Nitrate (UAN) (kg product/ha)']),
                'phosphorusApplication': float(Crop[selected_crop[i]]['Phosphorus Applied (kg P/ha)']),
                'potassiumApplication': float(Crop[selected_crop[i]]['Potassium Applied (kg K/ha)']),
                'sulfurApplication': float(Crop[selected_crop[i]]['Sulfur Applied (kg S/ha)']),
                'rainfallAbove600': bool(rain_over),
                'fractionOfAnnualCropBurnt': float(Crop[selected_crop[i]]['Fraction of the annual production of crop that is burnt (%)']),
                'herbicideUse': float(Crop[selected_crop[i]]['General Herbicide/Pesticide use (kg a.i. per crop)']),
                'glyphosateOtherHerbicideUse': float(Crop[selected_crop[i]]['Herbicide (Paraquat, Diquat, Glyphoste) (kg a.i. per crop)']),
                'electricityAllocation': float(Crop[selected_crop[i]]['electricityAllocation']),
                'limestone': float(Crop[selected_crop[i]]['Mass of Lime Applied (total tonnes)']),
                'limestoneFraction': float(Crop[selected_crop[i]]['Fraction of Lime/Dolomite']),
                'dieselUse': float(Crop[selected_crop[i]]['Annual Diesel Consumption (litres/year)']),
                'petrolUse': float(Crop[selected_crop[i]]['Annual Pertol Use (litres/year)']),
                'lpg': 0
            })
            if np.isnan(Crop[selected_crop[i]]['Area (ha)']):
                datas['vegetation'].append({
                        'vegetation': {
                            'region': 'South Coastal',
                            'treeSpecies': 'No tree data available',
                            'soil': 'No Soil / Tree data available',
                            'area': 0,
                            'age': 0
                        },
                        'allocationToCrops': [0]
                    })
            else:
                datas['vegetation'][i].append({
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
                    })

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

        # Status code to see if it's a
        # successful request
        st.write(response.status_code)

        # Turn the responsed json into python dict
        response_dict = response.json()

        # Empty list to store the scope, metric, 
        # value of the response dict
        metrics_list = []
        by_crop = []

        for keys, values in response_dict.items():
            if keys != 'intermediate' and keys != 'metaData': # Skip intermediate (crop specific) and metaDate
                # Check if the value of the key is a dictionary
                if isinstance(values, dict):
                    for key, value in values.items():
                        # Check if the value is not a list
                        if not isinstance(value, list):
                            metrics_list.append(
                                {
                                    'scope': keys,
                                    'metric': key,
                                    'value': value
                                }
                            )
                        else:
                            for i in range(len(value)):
                                # List type value breaks the result into crop type
                                # Append based on the crop type
                                metrics_list.append(
                                    {
                                    'scope': keys,
                                    'metric': desired_crop[i],
                                    'value': value[i]
                                    }
                                )
                else:
                    # For list type values
                    for i in range(len(values)):
                        if keys == 'intensitiesWithSequestration': # this key has dictionary type value
                            for key, value in values[i].items():
                                metrics_list.append(
                                    {
                                        'scope': keys + '_' + desired_crop[i],
                                        'metric': key,
                                        'value': value
                                    }
                                )
                        else:
                            metrics_list.append(
                            {
                                'scope': keys,
                                'metric': desired_crop[i],
                                'value': values[i]
                            }
                        )
                            
        for dictionary in response_dict['intermediate']:
            df = []
            for scope, dict_within in dictionary.items():
                if isinstance(dict_within, dict):
                    for key, value in dict_within.items():
                        df.append(
                            {
                                'scope': scope,
                                'metric': key,
                                'value': value
                            }
                        )
                else:
                    df.append(
                        {
                            'scope': scope,
                            'metric': "",
                            'value': dict_within
                        }
                    )
            by_crop.append(df)

        # Temp folder to save ouput
        out_dir = tempfile.mkdtemp(dir=cwd)
        
        if len(by_crop) > 1:
            for i in range(len(by_crop)):
                pd.DataFrame(
                    by_crop[i]
                ).to_csv(
                    os.path.join(out_dir, f'{desired_crop[i]}_GAFF.csv'), index=False
                )

        # Create a df to export from the metrics list
        out = pd.DataFrame(metrics_list)

        out.to_csv(os.path.join(out_dir, 'output.csv'), index=False)

        # Create a zip to save follow ups question
        # and workbook
        shutil.make_archive("GAFF_Tool_output", "zip", out_dir)

        zip_name = filename + '_' + str(dt.today().strftime('%d-%m-%Y'))

        with open("GAFF_Tool_output.zip", "rb") as f:
            st.download_button("Download the result from AIA's API", f, file_name=zip_name+".zip")

        # Remove the temp folder
        shutil.rmtree(out_dir)
