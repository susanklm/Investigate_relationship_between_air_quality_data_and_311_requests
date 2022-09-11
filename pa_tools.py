# -*- coding: utf-8 -*-

import requests
import pandas as pd
import time
import datetime
import json
from io import StringIO
from sqlalchemy import create_engine
import os
import folium
from folium.features import DivIcon
from folium import FeatureGroup
from geopy.distance import geodesic as gd

# Sleep Seconds
#sleep_seconds = 3 # wait sleep_seconds after each query

# Function which input the latitude longitude of a bounding box, location, key_read, desired filename, and return a list of sensor index
def get_sensorslist(nwlng,nwlat,selng,selat,location,key_read, fname):
    # PurpleAir API URL
    root_url = 'https://api.purpleair.com/v1/sensors/'

    # Box domain: lat_lon = [nwlng,, nwlat, selng, selat]
    lat_lon = [nwlng, nwlat, selng, selat]
    for i,l in enumerate(lat_lon):
        if (i == 0):
            ll_api_url = f'&nwlng={l}'
        elif (i == 1):
            ll_api_url += f'&nwlat={l}'
        elif (i == 2):
            ll_api_url += f'&selng={l}'
        elif (i == 3):
            ll_api_url += f'&selat={l}'
        
    # Fields to get
    fields_list = ['sensor_index','name','location_type', 'latitude','longitude'] 
    for i,f in enumerate(fields_list):
        if (i == 0):
            fields_api_url = f'&fields={f}'
        else:
            fields_api_url += f'%2C{f}'

    # Indoor, outdoor or all
    if (location == 'indoor'):
        loc_api = f'&location_type=1'
    elif (location == 'outdoor'):
        loc_api = f'&location_type=0'
    else:
        loc_api = ''
            
    # Final API URL
    api_url = root_url + f'?api_key={key_read}' + fields_api_url + ll_api_url + loc_api

    # Getting data
    response = requests.get(api_url)

    if response.status_code == 200:
        #print(response.text)
        json_data = json.loads(response.content)['data']
        df = pd.DataFrame.from_records(json_data)
        df.columns = fields_list
    else:
        print("Error")
        #raise requests.exceptions.RequestException
    
    # writing to csv file
    folderpath = 'PurpleAir'
    suffix = '.csv'
    #filename = folderpath + '\sensors_list.csv'
    filename = os.path.join(folderpath, fname + suffix)
    df.to_csv(filename, index=False, header=True)
            
    # Creating a Sensors 
    sensorslist = list(df.sensor_index)
    
    return sensorslist

# Function which input the latitude longitude of a bounding box, location, key_read, and return a dataframe which columns consist of 
# sensor index, name, location_type, latitude, longitude
def get_sensors_df(nwlng,nwlat,selng,selat,location,key_read):
    # PurpleAir API URL
    root_url = 'https://api.purpleair.com/v1/sensors/'

    # Box domain: lat_lon = [nwlng,, nwlat, selng, selat]
    lat_lon = [nwlng, nwlat, selng, selat]
    for i,l in enumerate(lat_lon):
        if (i == 0):
            ll_api_url = f'&nwlng={l}'
        elif (i == 1):
            ll_api_url += f'&nwlat={l}'
        elif (i == 2):
            ll_api_url += f'&selng={l}'
        elif (i == 3):
            ll_api_url += f'&selat={l}'
        
    # Fields to get
    fields_list = ['sensor_index','name','location_type', 'latitude','longitude'] 
    for i,f in enumerate(fields_list):
        if (i == 0):
            fields_api_url = f'&fields={f}'
        else:
            fields_api_url += f'%2C{f}'

    # Indoor, outdoor or all
    if (location == 'indoor'):
        loc_api = f'&location_type=1'
    elif (location == 'outdoor'):
        loc_api = f'&location_type=0'
    else:
        loc_api = ''
            
    # Final API URL
    api_url = root_url + f'?api_key={key_read}' + fields_api_url + ll_api_url + loc_api

    # Getting data
    response = requests.get(api_url)

    if response.status_code == 200:
        #print(response.text)
        json_data = json.loads(response.content)['data']
        df = pd.DataFrame.from_records(json_data)
        df.columns = fields_list
    else:
        print("Error")
        #raise requests.exceptions.RequestException
    
    return df

# Function to plot sensors on a folium map from a sensors_list
def plot_sensors(sensors_list):
    latitude = (sensors_list['latitude'].max()+sensors_list['latitude'].min())/2
    longitude = (sensors_list['longitude'].max()+sensors_list['longitude'].min())/2
    
    nc_geo = r'Neighborhood_Councils_(Certified).geojson'
    m5 = folium.Map(location=[latitude, longitude], tiles = 'CartoDB positron', zoom_start=11, min_zoom=8,max_zoom=15)
    cpleth = folium.Choropleth(geo_data = nc_geo,
            name='Choropleth',
            key_on='features.properties.Name',
            fill_opacity=0.1, line_opacity=0.3
            ).add_to(m5) 
    folium.LayerControl().add_to(m5)
    for lat, lng, sensor_name, sensor_index in zip(sensors_list.latitude, sensors_list.longitude, sensors_list.name, sensors_list.sensor_index):
        tooltip_text = sensor_name+", ID: " + str(sensor_index)
        folium.CircleMarker([lat, lng], radius = 5, color = "green", weight=1,
                fill = True, fill_color = "green", fill_opacity = 0.6,
                tooltip=tooltip_text).add_to(m5)
    return m5

# Function which input sensor_index and read_key and output sensor name, index, location_type, latitude, and longitude
def create_s_list(sensor_index, READ_KEY):
    root_url = 'https://api.purpleair.com/v1/sensors/' + str(sensor_index)
    api_url = root_url + f'?api_key={READ_KEY}' 
    results = requests.get(api_url).json()
    s_list = [results['sensor']['name'], results['sensor']['sensor_index'], results['sensor']['location_type'], results['sensor']['latitude'], results['sensor']['longitude']]
    return s_list

###############################################################################################################
# Below, whithin the "###" closure is a set of functions to calculate AQI for PM2.5 and PM10.0

def calcAQI(Cp, Ih, Il, BPh, BPl):
    a = (Ih - Il)
    b = (BPh - BPl)
    c = (Cp - BPl)
    return round((a/b) * c + Il);

#Below is the EPA PM2.5 AQI Breakpoints 
#                                        AQI         RAW PM2.5
#    Good                               0 - 50   |   0.0 – 12.0
#    Moderate                          51 - 100  |  12.1 – 35.4
#    Unhealthy for Sensitive Groups   101 – 150  |  35.5 – 55.4
#    Unhealthy                        151 – 200  |  55.5 – 150.4
#    Very Unhealthy                   201 – 300  |  150.5 – 250.4
#    Hazardous                        301 – 400  |  250.5 – 350.4
#    Hazardous                        401 – 500  |  350.5 – 500.4
#    Hazardous                        501 – 999  |  505.5 – 99999.9
        
# Calculate the AQI of pm2.5_cf_1
def aqiFrom25PM(pm):
    if not pm:
        return "-"
    if pm < 0: 
        return "-"; 
    if pm > 1000: 
        return "-"; 
    
    if pm > 505.0:
        return calcAQI(pm, 999, 501, 99999.0, 505.0) #Hazardous
    elif pm > 350.5:
        return calcAQI(pm, 500, 401, 500.4, 350.5) #Hazardous
    elif pm > 250.5:
        return calcAQI(pm, 400, 301, 350.4, 250.5) #Hazardous
    elif pm > 150.5: 
        return calcAQI(pm, 300, 201, 250.4, 150.5) #Very Unhealthy
    elif pm > 55.5: 
        return calcAQI(pm, 200, 151, 150.4, 55.5) #Unhealthy
    elif pm > 35.5: 
        return calcAQI(pm, 150, 101, 55.4, 35.5) #Unhealthy for Sensitive Groups
    elif pm > 12.1: 
        return calcAQI(pm, 100, 51, 35.4, 12.1) #Moderate
    elif pm >= 0: 
        return calcAQI(pm, 50, 0, 12, 0) #Good
    else: 
        return None
    

# Below is the EPA PM10.0 AQI Breakpoints 
#                                        AQI         RAW PM10.0
#    Good                               0 - 50   |   0.0 – 54.0
#    Moderate                          51 - 100  |  55.0 – 154.0
#    Unhealthy for Sensitive Groups   101 – 150  |  155.0 – 254.0
#    Unhealthy                        151 – 200  |  255.0 – 354.0
#    Very Unhealthy                   201 – 300  |  355.0 – 424.0
#    Hazardous                        301 – 400  |  425.0 – 504.0
#    Hazardous                        401 – 500  |  505.0 – 604.0
#    Hazardous                        501 – 999  |  605.0 – 99999.0
    
# Calculate the AQI of pm10.1_cf_1
def aqiFrom10PM(pm):
    if not pm:
        return "-"
    if pm < 0: 
        return "-"; 
    if pm > 1000: 
        return "-"; 
    
    if pm > 605.0:
        return calcAQI(pm, 999, 501, 99999.0, 605.0) #Hazardous
    elif pm > 505.0:
        return calcAQI(pm, 500, 401, 604.0, 505.0) #Hazardous
    elif pm > 425.0:
        return calcAQI(pm, 400, 301, 504.0, 425.0 ) #Hazardous
    elif pm > 355.0: 
        return calcAQI(pm, 300, 201, 424.0, 355.0 ) #Very Unhealthy
    elif pm > 255.0: 
        return calcAQI(pm, 200, 151, 354.0, 255.0 ) #Unhealthy
    elif pm > 155.0: 
        return calcAQI(pm, 150, 101, 254.0, 155.0) #Unhealthy for Sensitive Groups
    elif pm > 55.0: 
        return calcAQI(pm, 100, 51, 154.0, 55.0) #Moderate
    elif pm >= 0.0: 
        return calcAQI(pm, 50, 0, 54.0, 0.0) #Good
    else: 
        return None
###############################################################################################################

# Create a Dataframe from the API response and return a filename of the created dataframe. It input the response from the API,
# sensor_index, and a dataframe of 10 selected sensors.
def create_df(response, sensor_index, sensors_loc_df):
    column_names = response['fields']
    temp_df = pd.DataFrame(response['data'], columns = column_names)
    temp_date = []
    
    for i in range(len(temp_df['time_stamp'])):
        date_time = datetime.datetime.fromtimestamp(temp_df['time_stamp'][i])
        temp_date.append(date_time.strftime('%Y-%m-%d %H:%M:%S'))
    temp_df['date_local'] = temp_date
    temp_df.sort_values(by=["date_local"], inplace = True)
    temp_df = temp_df.drop(["time_stamp"], axis = 1)
    temp_df = temp_df[["date_local", "pm1.0_cf_1", "pm2.5_cf_1", "pm10.0_cf_1"]]
    temp_df = temp_df.reset_index(drop=True)

    # Calculate the AQI of PM2.5 and PM10.0
    temp_25 = []
    temp_10 = []
    for pm25, pm10 in zip(temp_df["pm2.5_cf_1"],temp_df["pm10.0_cf_1"]):
        temp_25.append(aqiFrom25PM(pm25))
        temp_10.append(aqiFrom10PM(pm10))
    temp_df['pm2.5_aqi'] = temp_25
    temp_df['pm10.0_aqi'] = temp_10

    # Find the max of AQIs
    temp_df['aqi'] = temp_df[['pm2.5_aqi','pm10.0_aqi']].max(axis=1)

    # Add sensor_name  and sensor_index column
    findex = response["sensor_index"]
    temp_df["sensor_index"] = response["sensor_index"]
    temp_df["sensor_name"] = sensors_loc_df[sensors_loc_df["sensor_index"] == findex]['sensor_name'].values[0]

    # Save dataframe to csv
    folderpath = 'PurpleAir/Sensors_Data/pa_API/'
    suffix = '.csv'
    filename = os.path.join(folderpath, f'pa_{findex}' + suffix)
    temp_df.to_csv(filename, index=False, header=True)
    return filename

# Create a Dataframe of 311 Requests surrounding the selected 10 sensors and return a filename of the created dataframe. It input a dataframe of 311 requests, selected 10 sensor locations, and desired filename
def create_request_sensor_df(df21, sensors_loc_df, fname):
    # Create a dataframe which consists of 311 Requests/Services surrounding the 10 Selected Sensors
    column_names = ['CreatedDate', 'RequestType', 'ServiceDate', 'Latitude', 'Longitude', 'DistToSensor', 'SensorName', 'SensorIndex', 'Sensor#']
    temp_list = []
    dist_to_sensor = 0
    for crt_date, request_type, serv_date, lat, lng in zip(df21.CreatedDate, df21.RequestType, df21.ServiceDate, df21.Latitude, df21.Longitude):
        serv_loc = [lat, lng]
        for i, lat_s, lng_s, sensor_name, sensor_index in zip(sensors_loc_df.index.values.tolist(),sensors_loc_df.latitude, sensors_loc_df.longitude, sensors_loc_df.sensor_name, sensors_loc_df.sensor_index):
            sensor_loc = [lat_s, lng_s]
            fields = [crt_date, request_type, serv_date, lat, lng, dist_to_sensor, sensor_name, sensor_index, i]
            if (gd(serv_loc, sensor_loc).miles <= 2):
                dist_to_sensor = gd(serv_loc, sensor_loc).miles
                temp_list.append(fields)
            
    temp_df = pd.DataFrame(temp_list, columns = column_names)
    temp_df = temp_df.sort_values(["Sensor#", "CreatedDate"], ascending=[True, True])
    
    # Save dataframe to csv
    folderpath = 'PurpleAir/Sensors_Data/request_around_sensors/'
    suffix = '.csv'
    filename = os.path.join(folderpath, fname + suffix)
    temp_df.to_csv(filename, index=False)
    return filename