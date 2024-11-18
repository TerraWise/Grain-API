import pandas as pd
import urllib
import io
import geopy.distance

def calc_weights(distances: list[float]) -> list[float]:
    invs = []
    for el in distances:
        invs.append(1/el**2)

    inv_sum = sum(invs)
    invs_out = [] 
    for el in invs:
        invs_out.append(el/inv_sum)
    return invs_out

def get_nearby_stations(lat: float, long: float, station_df: pd.DataFrame)->pd.DataFrame:
    
    distances = list()
    quadrants = list()
    #station_nums = list()
    for i in station_df.index:
        row_coords = (station_df.loc[i,"Latitude"],station_df.loc[i,"Longitud"],)
        distances.append(geopy.distance.geodesic((lat,long),row_coords).km)
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
        #station_nums.append(station_df.loc[i,"Number"])
    try:
        del(station_df["Distance (km)"])
    except KeyError:
        pass
    station_df["distance"] = distances
    station_df["quadrant"] = quadrants
    station_df = station_df.sort_values("distance")
    
    select_stations = []
    for quad in ["NE","SE","SW","NW"]:
        select_row = station_df[station_df["quadrant"] == quad].head(1).index
        if len(select_row) > 0:
            select_stations.append(select_row[0])
    
    select_station_df = station_df.loc[select_stations,:]

    weights = calc_weights(select_station_df["distance"].to_list())    

    select_station_df["weight"] = weights
    return select_station_df

def get_station_df(station_code: int, start_year: int, end_year: int) -> pd.DataFrame:

    start = str(start_year) + '0101'
    finish = str(end_year) + '1231'

    #get API data    
    api_url = 'https://www.longpaddock.qld.gov.au/cgi-bin/silo'

    params = {
        'format': 'csv',
        'start': start,
        'finish': finish,
        'station': station_code,
        'username': 'terrawise@terra-wise.com.au',
        'comment': 'rft'
    }
    url = api_url + '/PatchedPointDataset.php?' + urllib.parse.urlencode(params)

    with urllib.request.urlopen(url) as remote:
        data = remote.read()

    #write API data as file and then as Pd DF
    with io.BytesIO() as f:
        f.write(data)
        f.seek(0)
        df = pd.read_csv(f)
    return df


#get API data    
api_url = 'https://www.longpaddock.qld.gov.au/cgi-bin/silo'

params = {
    'format': 'near',
    'station': 10619,
    'radius': 10000
}
url = api_url + '/PatchedPointDataset.php?' + urllib.parse.urlencode(params)

with urllib.request.urlopen(url) as remote:
    data = remote.read()

#write API data as file and then as Pd DF
with io.BytesIO() as f:
    f.write(data)
    f.seek(0)
    weather_stations = pd.read_csv(f,delimiter = "|")
