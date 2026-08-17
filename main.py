import streamlit as st
import pandas as pd
import os
from functions.Extract_params import gen_info
from functions.aia_api import build_aia_payload, call_aia_api
import json

_CROP_NAME = object()  # sentinel: write crop.capitalize() into this column


def write_products_to_ws(ws, crops, products_by_crop, col_map):
    row = 2
    for i, crop in enumerate(crops):
        if i > 0:
            row += len(products_by_crop[crops[i - 1]])
        for space, product in enumerate(products_by_crop[crop]):
            for col, key in col_map.items():
                ws.cell(row + space, col).value = (
                    crop.capitalize() if key is _CROP_NAME else product[key]
                )


STATE_REMAP = {"nw_western_australia": "wa_nw", "sw_western_australia": "wa_sw"}


# Get current path
cwd = os.getcwd()

st.title("Carbon accounting tool")

st.header("Send to AIA")

st.subheader("Disclaimer")
st.write(
    "Before uploading the excel file, please open and save it so the data can be\nupdated accordingly"
)

ex_file = st.file_uploader("Upload your inventory sheet:", "xlsm")

desired_crop = []
try:
    # Create a df using function
    df = pd.read_excel(ex_file, sheet_name="Farm Data - Grains", index_col=0).T
    st.write(df)
    df["Area sown (ha)"] = df["Area sown (ha)"].apply(lambda x: float(x))

    # Separate it by crop type
    crop_types = df.index

    # Display the dataframe for checking
    if st.toggle("Do you want to check your input data frame?"):
        st.dataframe(crop_types, hide_index=True)
        st.write("If there are no data, please refer to the text above")
    # Choose the desired crop to send a request
    selected_indices = st.multiselect(
        "Choose which crop to send your request:",
        df.loc[df["Area sown (ha)"] > 0].index,
    )
except TypeError:
    st.write("Haven't uploaded an inventory sheet yet")

# Name the file by the first property name
filename = st.text_input("Save the file as:", key="GAFF_file")

if st.button("Run", key="AIA_API"):
    df = df.loc[selected_indices]

    loc, rain_over = gen_info(ex_file)
    payload = build_aia_payload(df, loc, rain_over)
    response = call_aia_api(payload)

    st.write(response.status_code)
    if response.status_code != 200:
        st.write(response.json())
    else:
        json_str = json.dumps(response.json(), indent=4)
        st.download_button(
            "Download the result from AIA's API",
            data=json_str.encode("utf-8"),
            file_name=filename + "_" + "_".join(desired_crop) + ".json",
            mime="application/json",
        )
