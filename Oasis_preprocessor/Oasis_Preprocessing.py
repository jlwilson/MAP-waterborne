
# coding: utf-8

# """
# Last Revised 11/20/2017
# Jordan Wilson
# USGS
# Missouri Water Science Center
# jlwilson@usgs.gov
# 
# Combines multiple resistivity and water-quality profiles in the form of semicolon and comma delimited .txt files into .csv files for import into Oasis. 
# 
# Tkinter code was modified from DSWallace integrateGeophysicsQW.py script. 
# """
#%%
from Tkinter import *
import pandas as pd
from Tkinter import Tk
from tkFileDialog import asksaveasfilename
from tkFileDialog import askdirectory
from tkFileDialog import askopenfilename
import tkMessageBox
import os
from shapely.geometry import Point
import geopandas as gp
import numpy as np
import shutil, glob
import fiona
from math import radians, cos, sin, asin, sqrt
from shutil import copyfile

#%%
# Defining bandpass filter to filter resistivity data channels
def band_pass(df,column, min, max):
    df[column+'_bandpass']=df[column]
    df[column+'_bandpass'][df[column]<min] = np.nan
    df[column+'_bandpass'][df[column]>max] = np.nan

#%%
# Defining depth filter
def depth_filt(df, column, offset, factor):
    df[column+'_filt']=df[column]
    df[column+'_filt'][df[column]<offset+factor]=np.nan
    
#%%
# Defining rolling average filter
def rolling_avg(df, column1, column2, width):
    df[column1+'_rollavg']=df[column2]
    df[column1+'_rollavg']= pd.rolling_mean(df[column1+'_rollavg'],window=width)

def haversine(lon1, lat1, lon2, lat2):
    """
    Calculate the great circle distance between two points
    on the earth (specified in decimal degrees)
    """
    # convert decimal degrees to radians
    lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])

    # haversine formula
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a))
    r = 6371  # Radius of earth in kilometers. Use 3956 for miles
    return c * r
    
#%%
Tk().withdraw() 
tkMessageBox.showinfo("Directions", "For this script to work, you must have all resistivity .txt files that you want to combine in one folder. All QW .csv files must also be in one folder. It may be the same folder.")

# Hard-coded for now, tired of selecting.  Will remove when finalized
res_folder = "D:\\Mississippi Alluvial Plain\\2018\\Waterborne Resistivity Scripts\\TestFiles\\FromWilson\\Pre_Oasis\\Resistivity"
wq_folder = "D:\\Mississippi Alluvial Plain\\2018\\Waterborne Resistivity Scripts\\TestFiles\\FromWilson\\Pre_Oasis\\QW"
ini_file = "D:\\Mississippi Alluvial Plain\\2018\\Waterborne Resistivity Scripts\\TestFiles\\FromWilson\\Pre_Oasis\\Resistivity\\Floodway_Inflatable_10m_extension_06142017.ini"
directory = "D:\\Mississippi Alluvial Plain\\2018\\Waterborne Resistivity Scripts\\TestFiles\\FromWilson\\Pre_Oasis\\TestOutput"

"""
# Resistivity files
res_folder = askdirectory(title="Select folder that contains all raw resistivity files for processing...")  # show an "Open" dialog box and return the path to the selected file
if not glob.glob('{}/*.txt'.format(res_folder)):
    tkMessageBox.showerror("FILE ERROR", "No resistivity files contained within folder or incorrect format")
    exit()

# Water Quality Files
wq_folder = askdirectory(title="Select folder that contains all raw water-quality data for processing...")
if not glob.glob('{}/*.csv'.format(wq_folder)):
    tkMessageBox.showerror("FILE ERROR", "No water quality files contained within folder or incorrect format")
    exit()

# Initialization File
ini_file = askopenfilename(title="Select ini file used to collect the resistivity data",
                           filetypes=[("INI Files", "*.ini")])
if not ini_file:
    tkMessageBox.showerror("FILE ERROR", "No INI file selected")
    exit()

# Save File Location
directory = askdirectory(title="Select directory to save the reordered resistivity and water-quality data")
"""
"""
# %% NHD geodatabase Location
gdb_dir = askdirectory(title="Select directory where NHD geodatabase is located")
try:
    streams = gp.read_file(gdb_dir)
except:
    tkMessageBox.showerror("FILE ERROR", "No NHD geodatabase selected")
    exit()
stream_df=pd.DataFrame(streams)
#%%
str(stream_df.ix[3,'geometry'])
#%%
for x in range(0,len(stream_df.FCode)):
    stream_df.ix[x,'geo']=str(stream_df.ix[x,'geometry'])
#%%

#Rename files from upstream to downstream with indicator of direction '_up' and '_down'

#Ideas: tkinter prompt to select if files are upstream or downstream 
#%%

"""
#%%

# Create crosstab table and export as a .txt file showing old and new names

#%%
path = directory + r'/Raw_Data_Renamed'

try:
    os.makedirs(os.path.join(path))
    print('Raw data folder created')
except:
    pass  # This makes me nervous- what errors are you avoiding? dsw 20171128

#%%
# Export renamed files to 'Raw_Data_Renamed' directory
print("Verifying continuity of surveys")
# Correct names of columns in resistivity raw data files
colNames = ["Distance", "Depth", "Rho 1", "Rho 2", "Rho 3", "Rho 4", "Rho 5", "Rho 6", "Rho 7", "Rho 8", "Rho 9",
            "Rho 10", "C1", "C2", "P1", "P2", "P3", "P4", "P5", "P6", "P7", "P8", "P9", "P10", "P11", "Latitude",
            "Longitude", "In_p", "In_n", "V1_p", "V1_n", "V2_p", "V2_n", "V3_p", "V3_n", "V4_p", "V4_n", "V5_p", "V5_n",
            "V6_p", "V6_n", "V7_p", "V7_n", "V8_p", "V8_n", "V9_p", "V9_n", "V10_p", "V10_n", "GPSString", "HDOP",
            "EXTRANEOUS"]
outfilename = "{}\\all.txt".format(res_folder)
# Grab starting and ending points of each survey to reorder
# NOTE: THIS ASSUMES CONTINUITY WITHIN SURVEY - NO TURNING BOAT AROUND WITHIN SURVEY LINE
subset = pd.DataFrame(columns=["StartLat", "EndLat", "StartLong", "EndLong", "Filename"])
excludeSurveys = pd.DataFrame(columns=["Filename", "Number_of_Data_Points"])
for filename in glob.glob('{}/*.txt'.format(res_folder)):
    if filename == outfilename:
        continue
    # print(filename)
    temp = pd.read_csv(filename, sep=';').reset_index()
    temp.columns = colNames

    # Check if survey is bad (500m or 100 point threshold)
    if len(temp) < 100:
        excludeSurveys = excludeSurveys.append(pd.DataFrame([[filename, str(len(temp))]],
                                                            columns=["Filename",
                                                                     "Number_of_Data_Points"])).reset_index(drop=True)
        continue

    # Convert the starting and ending coordinates of the survey from degrees decimal minutes to decimal degrees
    try:
        startLat = float(str(temp.loc[0, "Latitude"])[0:2]) + float(str(temp.loc[0, "Latitude"])[2:]) / 60
        endLat = float(str(temp.loc[len(temp)-1, "Latitude"])[0:2]) + float(str(temp.loc[len(temp)-1, "Latitude"])[2:]) / 60
        startLong = float(str(temp.loc[0, "Longitude"])[0:3]) - float(str(temp.loc[0, "Longitude"])[3:]) / 60
        endLong = float(str(temp.loc[len(temp)-1, "Longitude"])[0:3]) - float(str(temp.loc[len(temp)-1, "Longitude"])[3:]) / 60
    except ValueError:
        tkMessageBox.showerror("FORMATTING ERROR",
                               "Value Error: could not convert latitude or longitude in " + filename)
        exit()
    # Check to see if Longitude is formatted like we want it to
    if startLong > 0 or endLong > 0:
        tkMessageBox.showerror("FORMATTING ERROR",
                               "Error: please format longitude with negative sign for file " + filename)
        exit()
    subset = subset.append(pd.DataFrame([[startLat, endLat, startLong, endLong, filename]],
                                        columns=["StartLat", "EndLat", "StartLong", "EndLong", "Filename"])).reset_index(drop=True)

# Track files that were removed due to their length
excludeSurveys.to_csv(path + "\\EXCLUDED_SURVEYS.txt", index=False)

# Reorganize files based upon their location to one another
reorderedSubset = pd.DataFrame(columns=["StartLat", "EndLat", "StartLong", "EndLong", "Filename", "Distance", "Reverse"])
# Pick starting survey as one where start is farthest away from finish
subset["Distance"] = 0.00
for i, f in enumerate(subset.Filename):
    startLat = subset.loc[i, "StartLat"]
    startLong = subset.loc[i, "StartLong"]
    dist = 0
    # Find the greatest distance between all lines
    for i2, f2 in enumerate(subset.Filename):
        endLat = subset.loc[i2, "EndLat"]
        endLong = subset.loc[i2, "EndLong"]
        dist = max(dist, haversine(startLong, startLat, endLong, endLat))
    subset.at[i, "Distance"] = dist
# Start survey is one with greatest starting distance from any survey
reorderedSubset = reorderedSubset.append(subset.loc[subset["Distance"].idxmax(), :]).reset_index(drop=True)
reorderedSubset.loc[len(reorderedSubset) - 1, "Reverse"] = False  # First line shouldn't need reversal
subset.drop([subset["Distance"].idxmax()], inplace=True)
subset.reset_index(drop=True, inplace=True)

# Reorder remaining surveys based on distance from the end of previous survey
while len(subset) > 0:
    endLat = reorderedSubset.loc[len(reorderedSubset)-1, "EndLat"]
    endLong = reorderedSubset.loc[len(reorderedSubset)-1, "EndLong"]
    subset["Distance"] = 999999999.00
    subset["ReverseDistance"] = 999999999.00
    # The next line "starts" closest to the "end" of the previous line
    for i2, f2 in enumerate(subset.Filename):
        startLat = subset.loc[i2, "StartLat"]
        startLong = subset.loc[i2, "StartLong"]
        subset.at[i2, "Distance"] = haversine(startLong, startLat, endLong, endLat)
        subset.at[i2, "ReverseDistance"] = haversine(subset.loc[i2, "EndLong"], subset.loc[i2, "EndLat"], endLong, endLat)

    # Check to see if next survey section is reversed
    if min(subset["Distance"]) <= min(subset["ReverseDistance"]):
        reorderedSubset = reorderedSubset.append(subset.loc[subset["Distance"].idxmin(), :]).reset_index(drop=True)
        reorderedSubset.loc[len(reorderedSubset) - 1, "Reverse"] = False
    else:
        reorderedSubset = reorderedSubset.append(subset.loc[subset["ReverseDistance"].idxmin(), :]).reset_index(drop=True)
        reorderedSubset.loc[len(reorderedSubset)-1, "Reverse"] = True
    subset.drop([subset["Distance"].idxmin()], inplace=True)
    subset.reset_index(drop=True, inplace=True)

# Create new filenames for surveys based on their order and export directory to csv file
riverName = "Floodway"  # ------------------------------------------------------------> HARDCODED, NEED TO UPDATE
reorderedSubset.drop(["StartLat", "EndLat", "StartLong", "EndLong", "Distance", "ReverseDistance"], axis=1, inplace=True)
reorderedSubset["NewFilename"] = reorderedSubset.index + 1
reorderedSubset["NewFilename"] = directory + "\\" + riverName + "_" + reorderedSubset["NewFilename"].apply(lambda k: str(k).zfill(3)) + ".txt"
reorderedSubset.to_csv(path + "\\RENAMED_RESISTIVITY_FILE_DIRECTORY.txt", index=False)

# Rename the actual files in the renamed directory
for i, fOld in enumerate(reorderedSubset["Filename"]):
    fNew = path + "\\" + reorderedSubset.loc[i, "NewFilename"].replace('/', '\\').split('\\')[-1]
    copyfile(fOld, fNew)
    
#%%
# Preprocessing Resistivity Data
print('Aggregating raw data files')

# Copy resistivity data into a single file
colNames = ["Distance", "Depth", "Rho 1", "Rho 2", "Rho 3", "Rho 4", "Rho 5", "Rho 6", "Rho 7", "Rho 8", "Rho 9",
            "Rho 10", "C1", "C2", "P1", "P2", "P3", "P4", "P5", "P6", "P7", "P8", "P9", "P10", "P11", "Latitude",
            "Longitude", "In_p", "In_n", "V1_p", "V1_n", "V2_p", "V2_n", "V3_p", "V3_n", "V4_p", "V4_n", "V5_p", "V5_n",
            "V6_p", "V6_n", "V7_p", "V7_n", "V8_p", "V8_n", "V9_p", "V9_n", "V10_p", "V10_n", "GPSString", "UTC",
            "Latitude2", "D1", "Longitude2", "D2", "Fix Quality", "Satellites", "HDOP", "Altitude", "D3",
            "Height of Geoid", "E1", "E2", "E3", "E4", "E5", "E6", "E7", "E8", "E9", "E10", "E11"]
importfile = pd.DataFrame(columns=colNames)
for i, filename in enumerate(reorderedSubset["Filename"]):
    # If file flagged for reversal, reverse
    if reorderedSubset.loc[i, "Reverse"]:
        temp = pd.read_csv(filename, sep=';|,', engine='python').reset_index()
        temp.columns = colNames
        temp = temp.iloc[::-1]  # Reversal line
        temp["Filename"] = reorderedSubset.loc[i, "NewFilename"]
        importfile = importfile.append(temp)
    # Otherwise, write file to master file normally
    else:
        temp = pd.read_csv(filename, sep=';|,', engine='python').reset_index()
        temp.columns = colNames
        temp["Filename"] = reorderedSubset.loc[i, "NewFilename"]
        importfile = importfile.append(temp)
importfile.reset_index(drop=True, inplace=True)

# Write combined file
importfile.to_csv(outfilename, index=False)

print('Processing resistivity data')
data_cols = ('Ohm_m',
             'Cor_Dist',
             'Cor_Depth',
             'Final_Rho_1',
             'Final_Rho_2',
             'Final_Rho_3',
             'Final_Rho_4',
             'Final_Rho_5',
             'Final_Rho_6',
             'Final_Rho_7',
             'Final_Rho_8',
             'Final_Rho_9',
             'Final_Rho_10',
             'Lat',
             'Lon',
             'Final_Altitude')
# Add additional data columns listed above and remove unwanted data columns
for x in data_cols:
    importfile[x]=np.nan
importfile.drop(['D1', 'D2', 'D3', "E1", "E2", "E3", "E4", "E5", "E6", "E7", "E8", "E9", "E10", "E11"],
                inplace=True, axis=1)

importfile.set_index([range(0,len(importfile.Distance))], inplace=True)
importfile["Latitude"] = importfile["Latitude"].astype(str)
importfile["Longitude"] = importfile["Longitude"].astype(str)
# Reformat Latitude and Longitude to decimal degrees
importfile['Lat1'] = importfile['Latitude'].str[0:2]
importfile['Lat2'] = importfile['Latitude'].str[2:]
importfile['Lat2'] = importfile['Lat2'].astype(float)
importfile['Lat1'] = importfile['Lat1'].astype(float)
importfile['Lat'] = importfile.Lat1+importfile.Lat2/60

importfile['Lon1'] = importfile['Longitude'].str[0:3]
importfile['Lon2'] = importfile['Longitude'].str[3:]
importfile['Lon2'] = importfile['Lon2'].astype(float)
importfile['Lon1'] = importfile['Lon1'].astype(float)
importfile['Lon'] = importfile.Lon1-importfile.Lon2/60

importfile.drop(['Lat1','Lat2','Lon1','Lon2'], axis=1, inplace=True)
# importfile.drop('Counter', axis=1, inplace=True)  # Propose dropping this code

# Reformat numbers in the file to float
for col in importfile.columns[1:]: 
    try:
        importfile[col] = importfile[col].astype(float)
    except:
        pass

# Import INI file
try:
    ini = pd.read_csv(ini_file, index_col=None, sep='=')
    depthoffset = float(ini.ix['DepthOffset', '[SwitchPro]'])
    if depthoffset > 0:
        tkMessageBox.showwarning("WARNING", "Positive value for depth offset from INI file")
except:
    tkMessageBox.showerror("FILE ERROR", "No INI file selected or incorrect file format...")
    exit()

#%%
# Applying the bandpass filter and rolling average
for x in range(1,11):
    band_pass(importfile,'Rho {}'.format(x),0,250)
    rolling_avg(importfile, 'Rho {}'.format(x), 'Rho {}_bandpass'.format(x), 20)

#%%
# Applying the depth filter
depth_filt(importfile, 'Depth', depthoffset, 0.01)
rolling_avg(importfile, 'Depth', 'Depth_filt'.format(x), 20)

#%%
# Filtering Altitude via rolling median filter
importfile['Altitude_filt'] = pd.rolling_median(importfile['Altitude'],window=10)
rolling_avg(importfile, 'Altitude', 'Altitude_filt', 20)
importfile['Altitude_rollavg']=importfile['Altitude_rollavg'].round(1)

#%%
# Converting WGS 84 coordinates to UTM 15N coordiantes
geometry = [Point(xy) for xy in zip(importfile.Lon, importfile.Lat)]
crs=None
importfile = gp.GeoDataFrame(importfile, crs=crs, geometry=geometry)
importfile.crs = {'init' :'epsg:4326'}
importfile = importfile.to_crs({'init': 'epsg:32615'})

def getXY(pt):
    return (pt.x, pt.y)
centroidseries = importfile['geometry'].centroid
x,y = [list(t) for t in zip(*map(getXY, centroidseries))]

importfile['X_UTM']=x
importfile['Y_UTM']=y

#%%
# Calculating the distance from UTM coordinates
print("Calculating distance from UTM coordinates")
importfile['Cum_dist']=0

for i in range(1,len(importfile['Distance'])):
    importfile.ix[i,'Cor_Dist']=np.sqrt(np.square(importfile.ix[i,'X_UTM']-importfile.ix[i-1,'X_UTM'])+np.square(importfile.ix[i,'Y_UTM']-importfile.ix[i-1,'Y_UTM']))
    importfile.ix[i,'Cum_dist']=importfile.ix[i-1,'Cum_dist']+importfile.ix[i,'Cor_Dist']

# Here is where we might search for gaps in the data...

#%%

#%%
#Replacing all NaNs with "*" and dropping geometry column
importfile.fillna('*', inplace=True)
importfile.drop('geometry', axis=1, inplace=True)

#%%

saveRes = asksaveasfilename(defaultextension='.csv',title="Designate resitivity csv name and location", filetypes=[('csv file', '*.csv')])
importfile.to_csv(saveRes, index=False)
print('Resistivity data exported')




#%%
# Preprocessing QW Data

from os import listdir
from os.path import isfile, join

mypath=wq_folder

qwfiles = [f for f in listdir(mypath) if isfile(join(mypath, f))]

j=qwfiles[0]

print('Importing water quality data')
data = pd.read_csv('{}/{}'.format(wq_folder,j),sep=',',skiprows=12,index_col=False,engine='python',encoding='utf-16',
                   names=["Date","Time","°C","mmHg","DO %","SPC-uS/cm","C-uS/cm","ohm-cm","pH","NH4-N mg/L",
                          "NO3-N mg/L","Cl mg/L","FNU","TSS mg/L","DEP m","ALT m","Lat","Lon"])

qwdata=data
qwdata['File']=1
z=2
try:
    for x in qwfiles[1:]:
        data = pd.read_csv('{}/{}'.format(wq_folder,x),sep=',',skiprows=12,index_col=False,engine='python',
                           encoding='utf-16', names=["Date","Time","°C","mmHg","DO %","SPC-uS/cm","C-uS/cm",
                                                     "ohm-cm","pH","NH4-N mg/L","NO3-N mg/L","Cl mg/L","FNU",
                                                     "TSS mg/L","DEP m","ALT m","Lat","Lon"])
        qwdata['File']=z
        z+=1
        qwdata=qwdata.append(data)

    print('Water quality data imported')
except:
    pass
print('Processing water quality data')
qwdata.dropna(axis=1, how='all', inplace=True)

qwdata.rename(columns={'°C':'Temp_C', 'SPC-uS/cm': 'SPC_mscm','C-uS/cm':'Cond_mscm','ohm-cm':'Res_ocm','ALT m':'Alt_m'}, inplace=True)
try:
    qwdata = qwdata.loc[qwdata.Res_ocm!="    +++++",:]
except:
    pass
qwdata['Res_ocm'] = qwdata['Res_ocm'].astype('float')
qwdata['Ohm_m']=qwdata['Res_ocm']/100

#%%
# Applying a rolling average on resistivity
rolling_avg(qwdata, 'Ohm_m', 'Ohm_m', 20)

#%%
for col in qwdata.columns[1:]:                  
    try:
        qwdata[col] = qwdata[col].astype(float)
    except:
        pass

#%%
# Converting WGS 84 coordinates to UTM 15N coordiantes
geometry = [Point(xy) for xy in zip(qwdata.Lon, qwdata.Lat)]
crs=None
qwdata = gp.GeoDataFrame(qwdata, crs=crs, geometry=geometry)
qwdata.crs = {'init' :'epsg:4326'}
qwdata = qwdata.to_crs({'init': 'epsg:32615'})

def getXY(pt):
    return (pt.x, pt.y)
centroidseries = qwdata['geometry'].centroid
x,y = [list(t) for t in zip(*map(getXY, centroidseries))]

qwdata['X_UTM']=x
qwdata['Y_UTM']=y

#%%
# Filling all NaNs with '*'
qwdata.drop('geometry',axis=1,inplace=True)
qwdata.fillna('*', inplace=True)

#%%
saveQW = asksaveasfilename(defaultextension='.csv',title="Designate water quality csv name and location", filetypes=[('csv file', '*.csv')])
qwdata.to_csv(saveQW, index=False)
print('Water quality data exported!')
