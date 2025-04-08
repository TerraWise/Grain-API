import pandas as pd
import urllib
import io
import geopy.distance
from datetime import datetime as dt
import numpy as np
import streamlit as st

# Calculate the weight of each station based on distance
def calc_weights(distances: list[float]) -> list[float]:
    invs = []
    for el in distances:
        invs.append(1/el**2)

    inv_sum = sum(invs)
    invs_out = [] 
    for el in invs:
        invs_out.append(el/inv_sum)
    return invs_out

# Get a station weather data from SILO's API
def get_station_df(station_code: int, start_Year: int, end_Year: int) -> pd.DataFrame:
    # Specify the full start and end year
    start = str(start_Year) + '0101'
    finish = str(end_Year) + '1231'

    #get API data    
    api_url = 'https://www.longpaddock.qld.gov.au/cgi-bin/silo'
    # Set the params for the GET request
    params = {
        'format': 'csv',
        'start': start,
        'finish': finish,
        'station': station_code,
        'username': 'terrawise@terrawise.au',
        'comment': 'rft'
    }
    # url for the GET request
    url = api_url + '/PatchedPointDataset.php?' + urllib.parse.urlencode(params)

    with urllib.request.urlopen(url) as remote:
        data = remote.read()

    #write API data as file and then as Pd DF
    with io.BytesIO() as f:
        f.write(data)
        f.seek(0)
        df = pd.read_csv(f)
    return df

def get_quality_stations(weather_station: pd.DataFrame) -> list:
    quality_station = weather_station.copy()

    station_df = get_station_df(quality_station.loc["Number"], dt.now().year - 21, dt.now().year - 1)

    rf_count = len(station_df[station_df["daily_rain_source"] == 0])
    rf_frac = rf_count/len(station_df)

    if (round(rf_frac, 1) >= 0.9):
        quality_station.loc["Fraction of ranfall from BOM"] = rf_frac

        return quality_station
    
    return None

# Get the weather data from four nearby stations (NE, NW, SE, SW)
def to_list_dfs(endYear: int, nearest_station: pd.DataFrame) -> list:
    endYear = endYear
    startYear = endYear - 19
    stations_dfs = []
    for i in nearest_station.index:
        stations_dfs.append(get_station_df(nearest_station.loc[i, "Number"], startYear, endYear))

    return stations_dfs

def weighted_ave_col(input_dfs, colname: str, nearest_station_df: pd.DataFrame, selected_stations: list)->pd.Series:
    if isinstance(input_dfs, list):
        weights = []
        for station in selected_stations:
            weights.append(nearest_station_df[nearest_station_df.iloc[:, 0]==station]['weights'].iloc[0])
        out = 0
        for i in range(len(weights)):
            out += input_dfs[i][colname] * weights[i]
    else:
        out = input_dfs[colname]

    return out

def annual_summary(df: pd.DataFrame, assess_year: int) -> tuple:
    rain = df["Rain"].loc[df['Year'].eq(assess_year)].sum()
    eto_short = df["ETShortCrop"].loc[df['Year'].eq(assess_year)].sum()
    eto_tall = df["ETTallCrop"].loc[df['Year'].eq(assess_year)].sum()
    return rain, eto_short, eto_tall

def longTerms_summary(df: pd.DataFrame) -> tuple:
    rain = df["Rain"].sum() / 20
    eto_short = df["ETShortCrop"].sum() / 20
    eto_tall = df["ETTallCrop"].sum() / 20
    return rain, eto_short, eto_tall

def get_nearby_stations(lat: float, long: float, station_df: pd.DataFrame)->pd.DataFrame:
    station_df_copy = station_df.copy()

    distances = list()
    quadrants = list()
    
    for i in station_df_copy.index:
        row_coords = (station_df_copy.loc[i,"Latitude"], station_df_copy.loc[i,"Longitud"],)
        distances.append(geopy.distance.geodesic((lat, long), row_coords).km)
        coord_diff = (row_coords[0] - lat, row_coords[1] - long)
        
        quadrant = ""
        if coord_diff[0] > 0:
            quadrant = quadrant + "N"
        else:
            quadrant = quadrant + "S"
        
        if coord_diff[1] > 0:
            quadrant = quadrant + "E"
        else:
            quadrant = quadrant + "W"
        
        quadrants.append(quadrant)

    station_df_copy.insert(len(station_df_copy.columns), 'distance to polygon', distances)
    station_df_copy.insert(len(station_df_copy.columns), 'quadrant', quadrants)
    
    station_df_copy = station_df_copy.sort_values("distance to polygon")

    select_station_df = pd.DataFrame(columns=station_df_copy.columns.to_list() + ['Fraction of ranfall from BOM'])
    i = 0
    while len(select_station_df) < 8 and i < len(station_df_copy):
        quality_station = get_quality_stations(station_df_copy.iloc[i])
        if quality_station is not None:
            select_station_df = pd.concat([select_station_df, quality_station.to_frame().T], ignore_index=True)
        i += 1

    weights = calc_weights(select_station_df["distance to polygon"].to_list())    

    select_station_df.insert(len(select_station_df.columns), 'weights', weights)
    return select_station_df.drop(['Latitude','Longitud', 'Stat', 'Elevat.', 'Distance (km)'], axis=1)
