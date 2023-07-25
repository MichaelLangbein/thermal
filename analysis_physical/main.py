#%%
import os
import json
import numpy as np
import fiona
from shapely.geometry import shape
import matplotlib.pyplot as plt

from raster import readTif, tifGetPixelSizeDegrees, tifGetBbox, saveToCOG, makeTransform, tifGetPixelRowsCols
from vectorAndRaster import rasterizePercentage
from analyze import extractClouds, scaleBandData, radiance2BrightnessTemperature, bt2lstSingleWindow


#%%
np.seterr(all="ignore")


def readJson(path):
    fh = open(path)
    data = json.load(fh)
    return data

def getMaxPixelSize(path):
    tifFile = readTif(path)
    sizeH, sizeW = tifGetPixelSizeDegrees(tifFile)
    return max( sizeH, sizeW)

def getPixelData(tifPath, bbox):
    tifFile = readTif(tifPath)
    return tifGetBbox(tifFile, bbox)

def pixelizeCoverageFraction(geometries, bbox, shape):
    percentage = rasterizePercentage(geometries, bbox, shape)
    return percentage / 100

def estimateLst(b10, qa, meta, buildingFraction, roadsFraction):
    # Emissivity values from https://pure.tudelft.nl/ws/files/95823567/1_s2.0_S221209552100167X_main.pdf
    vegetationEmissivity = 0.973
    roadEmissivity       = 0.945
    buildingEmissivity   = 0.932  
    noDataValue          = -9999

    b10NoClouds = extractClouds(b10, qa, noDataValue)
    toaRadiance = scaleBandData(b10NoClouds, 10, meta)
    noDataMask = (toaRadiance == noDataValue)
    toaBT = radiance2BrightnessTemperature(toaRadiance, meta)
    emissivity = buildingFraction * buildingEmissivity + roadsFraction * roadEmissivity + (1 - buildingFraction - roadsFraction) * vegetationEmissivity
    lst = bt2lstSingleWindow(toaBT - 273, emissivity)
    lst = np.where(noDataMask, np.nan, lst)
    return lst

def saveRaster(path, data, bbox, extraProps):
    rows, cols = data.shape
    transform = makeTransform(rows, cols, bbox)
    saveToCOG(path, data, "EPSG:4326", transform, -9999, "copy", extraProps)
    fh = readTif(path)
    return fh

def getDateTime(meta):
    date = meta["LANDSAT_METADATA_FILE"]["IMAGE_ATTRIBUTES"]["DATE_ACQUIRED"]
    time = meta["LANDSAT_METADATA_FILE"]["IMAGE_ATTRIBUTES"]["SCENE_CENTER_TIME"]
    return f"{date} {time}"

def getLs8Scenes(rootPath, fileDict):
    scenes = []
    for dir in os.listdir(rootPath):
        if dir[-3:] != "tar":
            scene = {}
            for key, ending in fileDict.items():
                scene[key] = f"{rootPath}/{dir}/{dir}_{ending}"
            scenes.append(scene)
    return scenes

def getSceneShape(path, bbox):
    tifFile = readTif(path)
    data = tifGetBbox(tifFile, bbox)
    b, r, c = data.shape
    return r, c


#%%
pathToLs8Data          = "./ls8"
pathToOsmDataBuildings = "./osm/buildings.geo.json"
pathToOsmDataRoads     = "./osm/roads.geo.json"
scenes                 = getLs8Scenes(pathToLs8Data, {"b10": "B10.TIF", "qa": "QA_PIXEL.TIF", "meta": "MTL.json"})
bbox                   = { "lonMin": 11.214, "latMin": 48.064, "lonMax": 11.338, "latMax": 48.117 }


#%%
distance      = 2 * getMaxPixelSize(scenes[0]["b10"])
sceneShape    = getSceneShape(scenes[0]["b10"], bbox)
roadSize      = 0.01 * distance
noDataValue   = -9999


#%%
buildingData       = fiona.open(pathToOsmDataBuildings)
roadData           = fiona.open(pathToOsmDataRoads)
buildingGeometries = [b.geometry for b in buildingData]
roadGeometries     = [shape(r.geometry).buffer(roadSize) for r in roadData]

#%%
if os.path.exists("./results/houses.tif"):
    housesFractionFh = readTif("./results/houses.tif")
    housesFraction   = housesFractionFh.read(1)
else:
    housesFraction   = pixelizeCoverageFraction(buildingGeometries, bbox, sceneShape)
    housesFractionFh = saveRaster("./results/houses.tif", housesFraction, bbox, {})
if os.path.exists("./results/roads.tif"):
    roadsFractionFh = readTif("./results/roads.tif")
    roadsFraction   = housesFractionFh.read(1)
else:
    roadsFraction   = pixelizeCoverageFraction(roadGeometries, bbox, sceneShape)
    roadsFractionFh = saveRaster("./results/roads.tif", roadsFraction, bbox, {})

#%%

sceneNr = 0
buildingTemperatureData = {}
for scene in scenes:
    print(f"Scene {sceneNr} ...")
    sceneNr += 1

    meta      = readJson(scene["meta"])
    dateTime  = getDateTime(meta)
    b10       = getPixelData(scene["b10"], bbox)[0]
    qa        = getPixelData(scene["qa"], bbox)[0]
    lst       = estimateLst(b10, qa, meta, housesFraction, roadsFraction)
    lstTif    = saveRaster(f"./results/lst_{dateTime}.tif", lst, bbox, {"dateTime": dateTime})    

    buildingNr = 0
    for building in buildingData:
        print(f" ... scene {sceneNr}: building {buildingNr} ...")
        buildingNr += 1

        try:    

            buildingId          = building.id
            buildingGeometry    = building["geometry"]
            shp                 = shape(buildingGeometry)
            outline             = shp.exterior
            boutline            = shp.buffer(distance)
            loMn,laMn,loMx,laMx = boutline.bounds
            buildingBbox        = {"lonMin": loMn, "latMin": laMn, "lonMax": loMx, "latMax": laMx}
            lstAroundBuilding   = tifGetBbox(lstTif, buildingBbox)[0]

            # Method 1: temp house - temp surroundings
            # @TODO: there's probably a more efficient thing than `pixelize`
            buildingFraction      = pixelizeCoverageFraction([buildingGeometry], buildingBbox, lstAroundBuilding.shape)
            buildingFractionNorm  = buildingFraction / np.sum(buildingFraction)
            nrHouses              = 1
            nrNonHouses           = buildingFractionNorm.size - nrHouses
            tMeanInside           = np.sum(lstAroundBuilding * buildingFractionNorm) / nrHouses
            tMeanOutside          = np.sum(lstAroundBuilding * (1.0 - buildingFractionNorm)) / nrNonHouses

            # Method 2: temp house - temp (surroundings - buildings)
            buildingsFractionNbh  = tifGetBbox(housesFractionFh, buildingBbox)[0]
            nonHouseFractionNbh   = 1.0 - buildingsFractionNbh
            tMeanOutsideNonHouses = np.sum(lstAroundBuilding * nonHouseFractionNbh / np.sum(nonHouseFractionNbh))
            
            if buildingId not in buildingTemperatureData:
                buildingTemperatureData[buildingId] = {}
            buildingTemperatureData[buildingId][dateTime] = {
                "tMeanInside": tMeanInside,
                "tMeanOutside": tMeanOutside,
                "tMeanOutsideNonHouses": tMeanOutsideNonHouses
            }

        except Exception as e:
            print(e)




#%%
originalBuildings = readJson("./osm/buildings.geo.json")
newDataBuildings = {"type": "FeatureCollection", "features": []}

def find(arr, func):
    for el in arr:
        if func(el):
            return el

for buildingId in buildingTemperatureData:
    originalFeature = find(originalBuildings["features"], lambda f: f["properties"]["id"] == int(buildingId))
    if originalFeature:
        originalFeature["properties"]["temperature"] = buildingTemperatureData[buildingId]
        newDataBuildings["features"].append(originalFeature)


with open("./results/buildings_temperature.geojson", "w") as f:
    json.dump(newDataBuildings, f, indent=4)
# %%
