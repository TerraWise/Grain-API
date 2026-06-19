import os
import pandas as pd
import requests


def remove_insert(lst: list, index: int, value) -> list:
    del lst[index]
    lst.insert(index, value)
    return lst


def find_selected_indices(desired_crop: list, Crop: list) -> list:
    selected = []
    i, j = 0, 0
    while i < len(desired_crop) and j < len(Crop):
        if desired_crop[i] == Crop[j]["Crop type"]:
            selected.append(j)
            if desired_crop[i] == "Canola":
                Crop[j].replace("Canola", "Oilseeds", inplace=True)
            j = 0
            i += 1
        else:
            j += 1
    return selected


def build_aia_payload(Crop: list, selected_indices: list, rain_over: bool) -> dict:
    prod_sys = "Non-irrigated crop"
    datas = {
        "state": "wa_sw",
        "crops": [],
        "electricityRenewable": float(
            Crop[0]["% of electricity from renewable source"]
        ),
        "electricityUse": float(Crop[0]["Annual Electricity Use (state Grid) (KWh)"]),
        "vegetation": [],
    }
    for i in selected_indices:
        datas["crops"].append(
            {
                "type": Crop[i]["Crop type"],
                "state": "wa_sw",
                "productionSystem": prod_sys,
                "averageGrainYield": float(Crop[i]["Average grain yield (t/ha)"]),
                "areaSown": float(Crop[i]["Area sown (ha)"]),
                "nonUreaNitrogen": float(
                    Crop[i]["Non-Urea Nitrogen Applied (kg N/ha)"]
                ),
                "ureaApplication": float(Crop[i]["Urea Applied (kg Urea/ha)"]),
                "ureaAmmoniumNitrate": float(
                    Crop[i]["Urea-Ammonium Nitrate (UAN) (kg product/ha)"]
                ),
                "phosphorusApplication": float(Crop[i]["Phosphorus Applied (kg P/ha)"]),
                "potassiumApplication": float(Crop[i]["Potassium Applied (kg K/ha)"]),
                "sulfurApplication": float(Crop[i]["Sulfur Applied (kg S/ha)"]),
                "rainfallAbove600": bool(rain_over),
                "fractionOfAnnualCropBurnt": float(
                    Crop[i][
                        "Fraction of the annual production of crop that is burnt (%)"
                    ]
                ),
                "herbicideUse": float(
                    Crop[i]["Other chemicals applied (kg a.i. per crop)"]
                ),
                "glyphosateOtherHerbicideUse": float(
                    Crop[i]["Glyphosate (or equivalent) applied (kg a.i. per crop)"]
                ),
                "electricityAllocation": float(Crop[i]["electricityAllocation"]),
                "limestone": float(Crop[i]["Mass of Lime Applied (total tonnes)"]),
                "limestoneFraction": float(Crop[i]["Fraction of Lime/Dolomite"]),
                "dieselUse": float(Crop[i]["Annual Diesel Consumption (litres/year)"]),
                "petrolUse": float(Crop[i]["Annual Pertol Consumption (litres/year)"]),
                "lpg": float(Crop[i]["Annual LPG Consumption (litres/year)"]),
                "id": Crop[i]["Crop type"],
            }
        )
        if pd.isna(Crop[i]["Vegetation area (ha)"]):
            datas["vegetation"].append(
                {
                    "vegetation": {
                        "region": "South Coastal",
                        "treeSpecies": "Mixed species (Environmental Plantings)",
                        "soil": "Loams & Clays",
                        "area": 0,
                        "age": 0,
                    },
                    "allocationToCrops": [0],
                }
            )
        else:
            datas["vegetation"].append(
                {
                    "vegetation": {
                        "region": Crop[i]["Region"],
                        "treeSpecies": Crop[i]["Vegetation species"],
                        "soil": Crop[i]["Vegetation Soil type"],
                        "area": float(Crop[i]["Vegetation area (ha)"]),
                        "age": float(Crop[i]["Average Vegetation age (yrs)"]),
                    },
                    "allocationToCrops": [0] * len(selected_indices),
                }
            )
            datas["vegetation"][i]["allocationToCrops"] = remove_insert(
                datas["vegetation"][i]["allocationToCrops"],
                i,
                float(Crop[i]["Allocation"]),
            )
    return datas


def call_aia_api(payload: dict) -> requests.Response:
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "User-Agent": "terrawise",
    }
    url = (
        "https://emissionscalculator-mtls.production.aiaapi.com/calculator/3.0.0/grains"
    )
    key = os.path.join("credential", "carbon-calculator-integration.key")
    pem = os.path.join("credential", "aiaghg-terrawise.pem")
    return requests.post(url=url, headers=headers, json=payload, cert=(pem, key))
