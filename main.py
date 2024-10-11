# Import the required pacakage
import json
import streamlit
import requests
from funtion import *

# Create a df using function
ToDataFrame('Inventory sheet v1 - Grain.xlsx')

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
response = requests.post(url=API_url, 
                        headers=Headers,
                        data=datas,
                        cert=cert)