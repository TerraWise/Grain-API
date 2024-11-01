import csv
import pandas as pd
import math

# Extract follow up question
def FollowUp(df: pd.DataFrame):
    # Extract from csv
    info = {}
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
    with open("follow_up.csv", 'w', newline='') as out:
        csv_out = csv.DictWriter(out, info.keys())
        csv_out.writeheader()
        csv_out.writerow(info)

def SpecCrop(df: pd.DataFrame, crops: list):
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
        out.to_csv(f'{crop}_follow_up.csv')

# Fertilser info from questionnaire
def ListFert(df: pd.DataFrame, crops: list) -> list:
    fert_applied = []
    for crop in crops:
        fert = {}
        products = []
        rates = []
        forms = []
        for label, content in df.items():
            if crop.lower() in label and 'npk' in label.lower():
                try:
                    if not math.isnan(float(content.iloc[0])):
                        if crop.lower() in label and 'other' in label.lower() and 'fertiliser' in label.lower():
                            products.append(content.iloc[0])
                except ValueError:
                    products.append(content.iloc[0])
            elif crop.lower() in label and 'rate' in label.lower() and 'fertiliser' in label.lower():
                rates.append(content.iloc[0])
            elif crop.lower() in label.lower() and 'liquid' in label.lower() and 'fertiliser' in label.lower():
                forms.append(content.iloc[0])
        i = 0
        while i < len(products):
            if not math.isnan(rates[i]):
                fert[products[i]] = [rates[i], forms[i]]
            i += 1
        fert_applied.append(fert)
    return fert_applied

# Chemical info from questionnaire
def ListChem(df: pd.DataFrame, crops: list) -> list:
    chem_applied = []
    for crop in crops:
        chem = {}
        products = []
        rates = []
        forms = []
        for label, content in df.items():
            if crop.lower() in label and 'chemical' in label.lower() and 'select' in label.lower():
                try:
                    if not math.isnan(float(content.iloc[0])):
                        if crop.lower() in label and 'other' in label.lower() and 'chemical' in label.lower():
                            products.append(content.iloc[0])
                except ValueError:
                    products.append(content.iloc[0])
            elif crop.lower() in label and 'rate' in label.lower() and 'chemical' in label.lower():
                rates.append(content.iloc[0])
            elif crop.lower() in label.lower() and 'liquid' in label.lower() and 'chemical' in label.lower():
                forms.append(content.iloc[0])
        i = 0
        while i < len(products):
            if not math.isnan(rates[i]):
                chem[products[i]] = [rates[i], forms[i]]
            i += 1
        chem_applied.append(chem)
    return chem_applied