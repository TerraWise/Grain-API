import csv
import pandas as pd

def follow_up(df: pd.DataFrame):
    # Extract from csv
    info = {}
    info['List of on-farm machinery'] = df['If you have a list of all on-farm machinery and equipment, please upload it here. Alternatively, please email it to toby@terrawise.au'].iloc[0].split('\n')
    info['Farm management software'] = df['Please list the applications you use below'].iloc[0].split('\n')
    info['Variable rate'] = df['Do you utilise Variable Rate Technology (VRT) across your property? Or do you apply differing rates of fertiliser within paddock zones and/or crop types?'].iloc[0]
    info['Access to software & \n record of variable rate'] = df['Are you happy to provide us with access to these applications, records and/or service providers to conduct your carbon account? If so, provide details via toby@terrawise.au or call 0488173271 for clarification'].iloc[0]
    # Write out the follow up question
    with open("follow_up.csv", 'w', newline='') as out:
        csv_out = csv.DictWriter(out, info.keys())
        csv_out.writeheader()
        csv_out.writerow(info)

def SpecCrop(df: pd.DataFrame):
    # Number of crop in the questionnaire
    crops = df['What crops did you grow last year?'].iloc[0].split('\n')
    # Loops for crop specific info
    # based on the number of crops
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