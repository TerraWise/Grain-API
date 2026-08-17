import os
import pandas as pd
import requests

from functions.constant import PROD_SYS, STATE_MAP, CROP_TYPES


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


def build_aia_payload(
    crop_df: pd.DataFrame,
    loc: str,
    rain_over: bool,
) -> dict:

    payload = {
        "state": "wa_sw",
        "crops": [],
        "electricityRenewable": crop_df["% of electricity from renewable source"].iloc[
            0
        ],
        "electricityUse": crop_df["Annual Electricity Use (state Grid) (KWh)"].iloc[0],
        "vegetation": [],
    }

    for _, r in crop_df.iterrows():
        payload["crops"].append(extract_crop_production(r, loc, rain_over))

    veg = crop_df.iloc[:, 19:]

    if pd.isna(veg).all(axis=None):
        payload["vegetation"].append(
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
        return payload

    r = veg.iloc[0]
    if pd.isna(r).any():
        raise Exception(f"the vegetation data is invalid")
    regions = r["Region"].split(", ")
    species = r["Vegetation species"].split(", ")
    soil_types = r["Vegetation Soil type"].split(", ")
    areas = r["Vegetation area (ha)"].split(", ")
    ages = r["Average Vegetation age (yrs)"].split(", ")
    allocs = [float(1)] * len(regions)

    i = 0
    while i < len(regions):
        payload["vegetation"].append(
            {
                "vegetation": {
                    "region": regions[i],
                    "treeSpecies": species[i],
                    "soil": soil_types[i],
                    "area": float(areas[i]),
                    "age": int(ages[i]),
                },
                "allocationToCrops": [allocs[i]],
            }
        )
        i += 1

    return payload


def extract_crop_production(crop_record: pd.Series, loc: str, rain_over: bool) -> dict:
    crop_type, id = split_crop_name(str(crop_record.name))

    crop_json = {
        "id": id,
        "type": crop_type.capitalize(),
        "state": STATE_MAP[loc] if loc is not None else "wa_sw",
        "productionSystem": PROD_SYS,
        "rainfallAbove600": rain_over,
    }

    # yield and area sown
    extract_yield(
        crop_json,
        crop_record["Area sown (ha)"],
        crop_record["Average grain yield (t/ha)"],
    )
    # fert application
    kwargs = {
        "non_urea_N": crop_record["Non-Urea Nitrogen Applied (kg N/ha)"],
        "urea": crop_record["Urea Applied (kg Urea/ha)"],
        "uan": crop_record["Urea-Ammonium Nitrate (UAN) (kg product/ha)"],
        "p": crop_record["Phosphorus Applied (kg P/ha)"],
        "k": crop_record["Potassium Applied (kg K/ha)"],
        "s": crop_record["Sulfur Applied (kg S/ha)"],
    }
    extract_fertiliser(crop_json, **kwargs)
    # crop burnt
    extract_pct_crop_burnt(
        crop_json,
        crop_record["Fraction of the annual production of crop that is burnt (%)"],
    )
    # chemical application
    extract_chemical(
        crop_json,
        crop_record["Other chemicals applied (kg a.i. per crop)"],
        crop_record["Glyphosate (or equivalent) applied (kg a.i. per crop)"],
    )
    # electricity allocation
    extract_elec_alloc(crop_json, crop_record["electricityAllocation"])
    # limestone application
    extract_limestone(
        crop_json,
        crop_record["Mass of Lime Applied (total tonnes)"],
        crop_record["Fraction of Lime/Dolomite"],
    )
    # fuel usage
    extract_fuel(
        crop_json,
        crop_record["Annual Diesel Consumption (litres/year)"],
        crop_record["Annual Petrol Consumption (litres/year)"],
        crop_record["Annual LPG Consumption (litres/year)"],
    )

    return crop_json


def split_crop_name(name: str) -> tuple[str, str]:
    for crop_type in sorted(CROP_TYPES, key=len, reverse=True):
        if name == crop_type:
            return crop_type, crop_type
        if name.startswith(crop_type + " "):
            return crop_type, name[len(crop_type) :].strip()
    raise ValueError(f"Unrecognized crop type in {name!r}")


def extract_yield(
    crop_json: dict[str, str | float], area_sown: float, avg_yield: float
):
    crop_json.update(
        {
            "areaSown": area_sown,
            "averageGrainYield": avg_yield,
        }
    )


def extract_fertiliser(
    crop_json: dict[str, str | float],
    non_urea_N: float,
    urea: float,
    uan: float,
    p: float,
    k: float,
    s: float,
):
    crop_json.update(
        {
            "nonUreaNitrogen": non_urea_N,
            "ureaApplication": urea,
            "ureaAmmoniumNitrate": uan,
            "phosphorusApplication": p,
            "potassiumApplication": k,
            "sulfurApplication": s,
        }
    )


def extract_pct_crop_burnt(crop_json: dict[str, str | float], burnt_pct: float):
    crop_json.update({"fractionOfAnnualCropBurnt": burnt_pct})


def extract_chemical(
    crop_json: dict[str, str | float], herbi: float, glyphosate: float
):
    crop_json.update(
        {
            "herbicideUse": herbi,
            "glyphosateOtherHerbicideUse": glyphosate,
        }
    )


def extract_elec_alloc(crop_json: dict[str, str | float], alloc_pct: float):
    crop_json.update({"electricityAllocation": alloc_pct})


def extract_limestone(
    crop_json: dict[str, str | float], limestone: float, limestone_frac: float
):
    crop_json.update({"limestone": limestone, "limestoneFraction": limestone_frac})


def extract_fuel(
    crop_json: dict[str, str | float], diesel: float, petrol: float, lpg: float = 0
):
    crop_json.update({"dieselUse": diesel, "petrolUse": petrol, "lpg": lpg})
