# Import the required pacakage
import pandas as pd
import json
import streamlit
import requests

# Read in the csv
test = pd.read_csv('dummy_grains.csv')

# url and key
API_url = 'https://emissionscalculator-mtls.production.aiaapi.com/calculator/v1/grains'
API_key = 'random bull craps go'

# Set the header
Headers = {
    'Authorisation': f'Bearer {API_key}',
    'Content-type': 'application/json',
    'User-Agent': 'Chrome/120.0.0.0',
    "Accept": "application/json"
}

# params for the API
params = {
    'state': test['state'],
    'crops': [
        {
            'type': test['type'],
            'state': test['state'],
            'productionSystem': test['productionSystem'],
            'averageGrainYield': test['averageGrainYield'],
            'areaSown': test['areaSown'],
            'nonUreaNitrogen': test['nonUreaNitrogen'],
            'ureaApplication': test['ureaApplication'],
            'ureaAmmoniumNitrate': test['ureaAmmoniumNitrate'],
            'phosphorusApplication': test['phosphorusApplication'],
            'potassiumApplication': test['potassiumApplication'],
            'sulfurApplication': test['sulfurApplication'],
            'rainfallAbove600': test['rainfallAbove600'],
            'fractionOfAnnualCropBurnt': test['fractionOfAnnualCropBurnt'],
            'herbicideUse': test['herbicideUse'],
            'glyphosateOtherHerbicideUse': test['glyphosateOtherHerbicideUse'],
            'electricityAllocation': test['electricityAllocation'],
            'limestone': test['limestone'],
            'limestoneFraction': test['limestoneFraction'],
            'dieselUse': test['dieselUse'],
            'petrolUse': test['pertolUse'],
            'lpg': test['lpg']
        }
    ],
    'electricityRenewable': test['electricityRenewable'],
    'electricityUse': test['electricityUse'],
    'vegetation': [
        {
            'vegetation': {
                'region': test['region'],
                'treeSpecies': test['treeSpecies'],
                'soil': test['soil'],
                'area': test['area'],
                'age': test['age']
            },
            'allocationToCrops': test['allocationToCrops']
        }
    ]
}

# GET request for the API Grains only
response = requests.get(url=API_url, 
                        headers=Headers,
                        params=params)