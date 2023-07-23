import numpy as np
import json
import fiona
from utils.raster import readTif, tifLonLatToPixel, tifGetPixelOutline
from shapely.geometry import shape, box
import os


def loadGeoJson(path: str):
    fh = fiona.open(path, driver="GeoJSON")
    return fh


def getClass(jsn, shp: shape):
    
    bboxBuffered = shp.bounds
    featuresIntersectingWithBbox = [f for f in jsn.filter(bbox=bboxBuffered)]

    featureIds = []
    data = []
    for feature in featuresIntersectingWithBbox:
        featureIds.append(feature.id)
        berCount = feature.properties["BER_COUNT"]

        if berCount is None or berCount <= 0:
            continue

        berCoverage = feature.properties["ESTIMATED_BER_COVERAGE"]
        berCountA1 = feature.properties["A1"]   if feature.properties["A1"] else 0
        berCountA2 = feature.properties["A2"]   if feature.properties["A2"] else 0
        berCountA3 = feature.properties["A3"]   if feature.properties["A3"] else 0
        berCountB1 = feature.properties["B1"]   if feature.properties["B1"] else 0
        berCountB2 = feature.properties["B2"]   if feature.properties["B2"] else 0
        berCountB3 = feature.properties["B3"]   if feature.properties["B3"] else 0
        berCountC1 = feature.properties["C1"]   if feature.properties["C1"] else 0
        berCountC2 = feature.properties["C2"]   if feature.properties["C2"] else 0
        berCountC3 = feature.properties["C3"]   if feature.properties["C3"] else 0
        berCountD1 = feature.properties["D1"]   if feature.properties["D1"] else 0
        berCountD2 = feature.properties["D2"]   if feature.properties["D2"] else 0
        berCountE1 = feature.properties["E1"]   if feature.properties["E1"] else 0
        berCountE2 = feature.properties["E2"]   if feature.properties["E2"] else 0
        berCountF  = feature.properties["F"]    if feature.properties["F"]  else 0
        berCountG  = feature.properties["G"]    if feature.properties["G"]  else 0

        featureShape = shape(feature.geometry)
        intersection = featureShape.intersection(shp)
        overlapDegree = intersection.area / shp.area

        meanBer = 15 * berCountA1 + 14 * berCountA2 + 13 * berCountA3 + 12 * berCountB1 + 11 * berCountB2 + 10 * berCountB3 + 9 * berCountC1 + 8 * berCountC2 + 7 * berCountC3 + 6 * berCountD1 + 5 * berCountD2 + 4 * berCountE1 + 3 * berCountE2 + 2 * berCountF + 1 * berCountG
        meanBer /= berCount

        data.append({
            "weight": overlapDegree * berCoverage,
            "meanBer": meanBer
        })

    if len(data) <= 0:
        return -9999, featureIds

    weightSum = 0
    estimate = 0
    for datum in data:
        weight = datum["weight"]
        meanBer = datum["meanBer"]
        estimate += weight * meanBer
        weightSum += weight
    if weightSum <= 0:
        return -9999, featureIds
    estimate /= weightSum

    return estimate, featureIds


class Ls8:
    def __init__(self, bands) -> None:
        path = "data/ls8/"
        baseFileName = "LC09_L1TP_206023_20230113_20230314_02_T1_"
        self.fhs = [readTif(path + baseFileName + band + ".TIF") for band in bands]
        self.bandData = [fh.read(1) for fh in self.fhs]
        self.qa = readTif(path + baseFileName + "QA_PIXEL.TIF")
        self.qaData = self.qa.read(1)


    def getRandomData(self, bbox):
        row, col = self.__getRandomCoordsWithData(bbox)
        xs = []
        for band in self.bandData:
            x = band[row, col]
            xs.append(x)
        shape = tifGetPixelOutline(self.qa, row, col)
        return xs, shape

    def __getRandomCoordsWithData(self, bbox):
        hasData = False
        while not hasData:
            lon = bbox["lonMin"] + np.random.random() * (bbox["lonMax"] - bbox["lonMin"])
            lat = bbox["latMin"] + np.random.random() * (bbox["latMax"] - bbox["latMin"])
            row, col = tifLonLatToPixel(self.qa, lon, lat)
            qaData = self.qaData[row, col]
            if qaData == 21824:
                hasData = True
        return row, col

    


def loadData(nrSamples):
    yRaw = loadGeoJson("data/ber/BERPublicSearch/features.geojson")
    lonMin, latMin, lonMax, latMax = box(*yRaw.bounds).buffer(-0.06).bounds  # insetting a little so that we don't hit that many no-data values
    bbox = {"lonMin": lonMin, "latMin": latMin, "lonMax": lonMax, "latMax": latMax}

    bands = ["B1", "B2", "B3", "B4", "B5", "B6", "B7", "B8", "B9", "B10", "B11"]
    ls8 = Ls8(bands)

    X = np.zeros((nrSamples, len(bands)))
    Y = np.zeros((nrSamples,))

    s = 0
    while s < nrSamples:
        print(f"... {100 * s/nrSamples}%")

        x, shp = ls8.getRandomData(bbox)
        y, featureIds = getClass(yRaw, shp)
        
        if y != -9999:
            X[s, :] = x
            Y[s] = y
            s += 1
        else:
            print("No data: ", shp)

    return X, Y



def testLs8():
    yRaw = loadGeoJson("data/ber/BERPublicSearch/features.geojson")
    lonMin, latMin, lonMax, latMax = box(*yRaw.bounds).buffer(-0.06).bounds  # insetting a little so that we don't hit that many no-data values
    bbox = {"lonMin": lonMin, "latMin": latMin, "lonMax": lonMax, "latMax": latMax}

    bands = ["B1", "B2", "B3", "B4", "B5", "B6", "B7", "B8", "B9", "B10", "B11"]
    ls8 = Ls8(bands)

    x, shp = ls8.getRandomData(bbox)

    coll = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {
                    "x": [int(v) for v in x]
                },
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [
                        [c for c in shp.exterior.coords]
                    ]
                }
            }
        ]
    }

    fh = open("testfile.geojson", "w")
    json.dump(coll, fh)
