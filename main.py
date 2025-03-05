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
import geopandas as gpd
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

    zipfiles = st.file_uploader("Upload your questionnaire form as a csv format:", 'zip', accept_multiple_files=True)

    try:
        crops, crop_specific_input, questionnaire_df, veg_df = FromTheTop(zipfiles)

        print(crops)
        
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

        try:
            production_year = dt.strptime(questionnaire_df['production_year'].iloc[0], '%d/%m/%Y %I:%M:%S %p').year
        except TypeError:
            production_year = dt(questionnaire_df['production_year'].iloc[0], 1, 1).year

    except AttributeError:
        st.write("Haven't uploaded a zip of Survey123 production data!")
    except UnboundLocalError:
        st.write("Haven't uploaded a zip of Survey123 production data!")

    planting_shapes = st.file_uploader('Upload your planting shapefile (zip or all of it)', accept_multiple_files=True, key='PlantingShape')

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
            input = st.radio('Choose an input to review', [
                    'fert', 'fungicide', 'herbicide', 'insecticide', 'chem'
                ]
            )
            st.dataframe(crop_specific_input[crop][input], hide_index=True)
        except NameError:
            st.markdown(':woman-gesturing-no:!:man-gesturing-no:!\
                        Quickly upload files to discover the secret lies here')

    with tab3:
        # Upload shapefile for SILO's API (weather data)
        shapes = st.file_uploader("Upload all of your shapefile for weather data or the compressed file:", accept_multiple_files=True)

        try: # Incase there are no files (don't want to scare people away)
            # Get the coordinate from the shapefile

            gdf = read_shapes(shapes)

            centroid = gdf.dissolve().centroid
            lon = centroid.x[0]
            lat = centroid.y[0]

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
        with tempfile.TemporaryDirectory() as tmp_out:


            # Write out the general info
            FollowUp(questionnaire_df, tmp_out)


            # Crop specific info
            LandManagement(questionnaire_df, crops, tmp_out)


            # Write into the inventory sheet
            wb = openpyxl.load_workbook(
                os.path.join('input', "Inventory sheet v2 - Grain.xlsx")
            )

            # Fill in general info
            ws = wb['General information']

            # General information
            # Client name
            ws.cell(2, 2).value = questionnaire_df['client_name'].iloc[0]
            # Business name
            ws.cell(3, 2).value = questionnaire_df['business_name'].iloc[0]
            # Client email
            ws.cell(4, 2).value = questionnaire_df['email'].iloc[0]
            # Production year assessed
            ws.cell(5, 2).value = production_year

            # Location
            # Property name
            ws.cell(7, 2).value = questionnaire_df['property_name'].iloc[0]
            # Property address
            ws.cell(8, 2).value = questionnaire_df['property_address'].iloc[0]
            # State
            if questionnaire_df['state'].iloc[0] == 'nw_western_australia':
                ws.cell(9, 2).value = 'wa_nw'
            elif questionnaire_df['state'].iloc[0] == 'sw_western_australia':
                ws.cell(9, 2).value = 'wa_sw'
            else:
                ws.cell(9, 2).value = questionnaire_df['state'].iloc[0]
            # Farm map or paddock boundaries
            ws.cell(10, 2).value = questionnaire_df['upload_email_draw'].iloc[0]

            # Climate
            ## Rainfall & request ETo from DPIRD
            try:
                ws.cell(12, 2).value = questionnaire_df['property_av_annual_rainfall'].iloc[0]
            except AttributeError:
                ws.cell(12, 2).value = "Didn't provide rainfall data"
            # Data from the weather_output/
            SILO_weather = pd.read_csv(os.path.join(cwd, 'weather_output', f'{'+'.join(str(station) for station in selected_stations)}_annual_ave_df.csv'))
            # Rainfall
            ws.cell(13, 2).value = SILO_weather.loc[0, 'Rainfall_2yr_ave_mm']
            # Evapotranspiration
            ws.cell(16, 2).value = SILO_weather.loc[0, 'ETo_Short_2yr_ave_mm']
            ws.cell(16, 3).value = SILO_weather.loc[0, 'ETo_Tall_2yr_ave_mm']

            # Software
            # Farm management software (Y/N)
            ws.cell(19, 2).value = questionnaire_df[
                'Do you use any Farm Management Practices software applications?'
            ].iloc[0]
            # List
            if isinstance(
                questionnaire_df['Please select the applications you use below'].iloc[0],
                str
            ):
                ws.cell(20, 2).value = questionnaire_df['Please specify'].iloc[0]
            else:
                ws.cell(20, 2).value = questionnaire_df[
                    'Please select the applications you use below'
                ].iloc[0].split(',')
            # Practices
            # VRT
            strings = questionnaire_df[
                'Do you use variable rate technology (VRT) across your property ?'
            ].iloc[0].split('_')
            ws.cell(22, 2).value = ' '.join(strings)

            # Vegetation
            # Planting post_1990 (Y/N)
            try:
                ws.cell(26, 2).value = veg_df[' Location of plantings'].iloc[0]
                ws.cell(25, 2).value = "Y"
            except TypeError:
                ws.cell(25, 2).value = 'N'
                ws.cell(26, 2).value = 'N'

            # Electricity
            # Annual electricity use (KWh)
            ws.cell(28, 2).value = questionnaire_df[
                'What was your annual electricity consumption?'
            ].iloc[0]
            # Renewable (Y/N)
            ws.cell(29, 2).value = questionnaire_df[
                'Did you use renewable energy?'
            ].iloc[0]
            # Renewable source
            ws.cell(30, 2).value = questionnaire_df[
                'What was the source(s) of this renewable energy?'
            ].iloc[0]
            # % renewable
            ws.cell(31, 2).value = questionnaire_df[
                'What percentage of the total electricity consumption came from this source?'
            ].iloc[0]

            # Fuel
            fuels = ['diesel', 'petrol', 'LPG']
            for i, fuel in enumerate(fuels):
                # Begining (L)
                ws.cell(33 + 3 * i, 2).value = questionnaire_df[
                    f'How much {fuel} did you have on hand at the start of the last calender year?'
                ].iloc[0]
                # Purchased (L)
                ws.cell(34 + 3 * i, 2).value = questionnaire_df[
                    f'How much {fuel} did you purchase throughout the year?'
                ].iloc[0]
                # End (l)
                ws.cell(35 + 3 * i, 2).value = questionnaire_df[
                    f'How much {fuel} did you have on hand at the end of the last calender year?'
                ].iloc[0]

            # Set the reference cell for offset below
            CropType_Header = Cell.Cell(ws, 46, 1)
            # Write into cells under corresponding crop types
            # using the refrence cell
            for i in range(12): # Number of crop type
                croptype = CropType_Header.offset(i + 1)
                for crop in crops:
                    if crop == croptype.value.lower():
                        # Area sown
                        croptype.offset(column=1).value = questionnaire_df[f'area_sown_{crop.lower()}'].iloc[0]
                        # Last year yield
                        croptype.offset(column=2).value = questionnaire_df[f'av_yield_{crop.lower()}'].iloc[0]
                        # Burn (Y/N)
                        croptype.offset(column=5).value = questionnaire_df[f'paddocks_burnt_{crop.lower()}'].iloc[0]
                        # Area burnt
                        if croptype.offset(column=5).value == 'yes':
                            croptype.offset(column=6).value = questionnaire_df[
                                f'windrow_burnt_{crop.lower()}'
                            ].iloc[0] + questionnaire_df[
                                f'area_burnt_{crop.lower()}'
                            ].iloc[0] # Need update to specific crop type
                        else:
                            croptype.offset(column=6).value = 0


            # Fertiliser
            ws = wb['Fertiliser Applied - Input']
            # List of fertiliser applied breaks down by
            # crop type
            ferts = ListFertChem(crop_specific_input, crops, questionnaire_df, 'fert')
            st.write(ferts)
            # Loop to write into the worksheet
            for i, crop in enumerate(crops):
                crop_ferts = ferts[crop]
                space = 0 # Spacing between products of the same crop
                if i == 0: # Set the starting row
                    row = 2
                if i > 0: # Starting row after first crop
                    previous_crop = crops[i-1]
                    row += len(ferts[previous_crop])
                for fert in crop_ferts:
                    # Product name
                    ws.cell(row + space, 1).value = fert['name']
                    # Forms
                    ws.cell(row + space, 2).value = fert['form']
                    # Crop
                    ws.cell(row + space, 4).value = crop
                    # Rate
                    ws.cell(row + space, 6).value = fert['rate']
                    # Area
                    ws.cell(row + space, 7).value = fert['area']
                    # Times
                    ws.cell(row + space, 8).value = fert['times']
                    space += 1


            # Chemical
            ws = wb['Chemical Applied - Input']
            # List of chemical applied break downs
            # by crop
            chemicals = ['fungicide', 'herbicide', 'insecticide', 'chem']
            chems = {}
            for chem in chemicals:
                chems[chem] = ListFertChem(crop_specific_input, crops, questionnaire_df, chem)
            # Refer to fertiliser section
            for chem in chemicals:
                chemical = chems[chem]
                for i, crop in enumerate(crops):
                    crop_chems = chemical[crop]
                    space = 0
                    if i == 0:
                        row = 2
                    if i > 0:
                        previous_crop = crops[i-1]
                        row += len(chemical[previous_crop])
                    for chem in crop_chems:
                        # Product name
                        ws.cell(row + space, 1).value = chem['name']
                        # Forms
                        ws.cell(row + space, 2).value = chem['form']
                        # Crop
                        ws.cell(row + space, 16).value = crop
                        # Rate
                        ws.cell(row + space, 17).value = chem['rate']
                        # Area
                        ws.cell(row + space, 18).value = chem['area']
                        # Times
                        ws.cell(row + space, 19).value = chem['times']
                        space += 1


            # Lime/gypsum
            ws = wb['Lime Product - Input']
            # List of products (lime/dolomite and gypsum) applied
            # breaking down by crop type
            products_applied = ToSoilAme(questionnaire_df, crops)
            # Loop to write into the worksheet
            for i, crop in enumerate(crops):
                crop_products = products_applied[crop]
                space = 0
                if i == 0:
                    row = 2
                if i > 0:
                    previous_crop = crops[i-1]
                    row += len(products_applied[previous_crop])
                for product in crop_products:
                    # Soil amelioration
                    ws.cell(row + space, 1).value = product['name']
                    # Source
                    ws.cell(row + space, 2).value = product['source']
                    # Crop
                    ws.cell(row + space, 4).value = crop
                    # Rate
                    ws.cell(row + space, 5).value = product['rate']
                    # Area
                    ws.cell(row + space, 6).value = product['area']

            #  Fuel usage - PW pathway will be in the future
            ws = wb['Fuel Usage - Input']

            # Vegetation
            ws = wb['Vegetation - Input']
            # A dictionary of vegetation planted
            vegetation = ToVeg(veg_df, planting_shapes)
            # Write into the worksheet
            try:
                for i in range(len(vegetation)):
                    # Region
                    ws.cell(2 + i, 1).value = vegetation[i]['region']
                    # Species
                    ws.cell(2 + i, 2).value = vegetation[i]['species']
                    # Soil
                    ws.cell(2 + i, 4).value = vegetation[i]['soil']
                    # Area
                    ws.cell(2 + i, 5).value = vegetation[i]['area']
                    # Planted year
                    ws.cell(2 + i, 6).value = vegetation[i]['planted_year']
                    # Age
                    ws.cell(2 + i, 7).value = vegetation[i]['age']
            except TypeError:
                ws.cell(2, 1).value = 'No planting'
                ws.cell(2, 2).value = 'No planting'
                ws.cell(2, 4).value = 'No planting'
                ws.cell(2, 5).value = 'No planting'
                ws.cell(2, 6).value = 'No planting'
                ws.cell(2, 7).value = 'No planting'
            
            # Save the workbook
            wb.save(os.path.join(tmp_out, 'Inventory_Sheet.xlsx'))
            
            # Create a zip to save follow ups question
            # and workbook
            shutil.make_archive("Question_Extract", "zip", tmp_out)

            # Name the file by the first property name
            zip_name = questionnaire_df.loc[0, 'property_name'] + '_' + str(dt.today().strftime('%d-%m-%Y'))

            with open("Question_Extract.zip", "rb") as f:
                st.download_button('Download the extracted info', f, file_name=zip_name+".zip")
        
        # Remove the unused folder
        shutil.rmtree(os.path.join(cwd, 'weather_output'))
        files = [
            os.path.join(cwd, 'Question_Extract.zip'),
            os.path.join(cwd, 'Weather_data.zip')
        ]
        RemoveFiles(files)
else:
    st.header("Send to AIA")

    st.subheader("Disclaimer")
    st.write(
        "Before uploading the excel file, please open and save it so the data can be\nupdated accordingly"
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
        loc, rain_over = GenInfo(ex_file)

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
        prod_sys = 'Non-irrigated crop'

        # params for the API
        for i in selected_crop: # For one or multiple crops
            datas['crops'].append(
                {
                    'type': Crop[i]['Crop type'],
                    'state': 'wa_sw',
                    'productionSystem': prod_sys,
                    'averageGrainYield': float(Crop[i]['Average grain yield (t/ha)']),
                    'areaSown': float(Crop[i]['Area sown (ha)']),
                    'nonUreaNitrogen': float(Crop[i]['Non-Urea Nitrogen Applied (kg N/ha)']),
                    'ureaApplication': float(Crop[i]['Urea Applied (kg Urea/ha)']),
                    'ureaAmmoniumNitrate': float(Crop[i]['Urea-Ammonium Nitrate (UAN) (kg product/ha)']),
                    'phosphorusApplication': float(Crop[i]['Phosphorus Applied (kg P/ha)']),
                    'potassiumApplication': float(Crop[i]['Potassium Applied (kg K/ha)']),
                    'sulfurApplication': float(Crop[i]['Sulfur Applied (kg S/ha)']),
                    'rainfallAbove600': bool(rain_over),
                    'fractionOfAnnualCropBurnt': float(Crop[i]['Fraction of the annual production of crop that is burnt (%)']),
                    'herbicideUse': float(Crop[i]['General Herbicide/Pesticide use (kg a.i. per crop)']),
                    'glyphosateOtherHerbicideUse': float(Crop[i]['Herbicide (Paraquat, Diquat, Glyphoste) (kg a.i. per crop)']),
                    'electricityAllocation': float(Crop[i]['electricityAllocation']),
                    'limestone': float(Crop[i]['Mass of Lime Applied (total tonnes)']),
                    'limestoneFraction': float(Crop[i]['Fraction of Lime/Dolomite']),
                    'dieselUse': float(Crop[i]['Annual Diesel Consumption (litres/year)']),
                    'petrolUse': float(Crop[i]['Annual Pertol Use (litres/year)']),
                    'lpg': 0
                }
            )
            if np.isnan(Crop[i]['Area (ha)']):
                datas['vegetation'].append(
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
                )
            else:
                datas['vegetation'].append(
                    {
                        'vegetation': {
                            'region': Crop[i]['Region'],
                            'treeSpecies': Crop[i]['Tree Species'],
                            'soil': Crop[i]['Soil'],
                            'area': float(Crop[i]['Area (ha)']),
                            'age': float(Crop[i]['Age (yrs)'])
                        },
                        'allocationToCrops': [0]*(len(selected_crop)-1) + [float(Crop[i]['Allocation to crop'])]
                    }
                )

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
        with tempfile.TemporaryDirectory() as out_dir:
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