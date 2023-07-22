import numpy as np
import json
import fiona
from utils.raster import readTif, tifGetBbox
from shapely.geometry import shape, box


def loadGeoJson(path):
    fh = fiona.open(path, driver="GeoJSON")
    return fh


def getClass(jsn, bbox):
    
    bboxTuple = (bbox["lonMin"], bbox["latMin"], bbox["lonMax"], bbox["latMax"])
    bboxShape = box(*bboxTuple).buffer(0.01)
    bboxBuffered = bboxShape.bounds
    featuresIntersectingWithBbox = [f for f in jsn.filter(bbox=bboxBuffered)]

    data = []
    for feature in featuresIntersectingWithBbox:
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
        intersection = featureShape.intersection(bboxShape)
        overlapDegree = intersection.area / bboxShape.area

        meanBer = 15 * berCountA1 + 14 * berCountA2 + 13 * berCountA3 + 12 * berCountB1 + 11 * berCountB2 + 10 * berCountB3 + 9 * berCountC1 + 8 * berCountC2 + 7 * berCountC3 + 6 * berCountD1 + 5 * berCountD2 + 4 * berCountE1 + 3 * berCountE2 + 2 * berCountF + 1 * berCountG
        meanBer /= berCount

        data.append({
            "weight": overlapDegree * berCoverage,
            "meanBer": meanBer
        })

    if len(data) <= 0:
        return -9999

    weightSum = 0
    estimate = 0
    for datum in data:
        weight = datum["weight"]
        meanBer = datum["meanBer"]
        estimate += weight * meanBer
        weightSum += weight
    if weightSum <= 0:
        return -9999
    estimate /= weightSum

    return np.round(estimate)


def getBbox(jsn):
    lonMin, latMin, lonMax, latMax = jsn.bounds
    return {"lonMin": lonMin, "latMin": latMin, "lonMax": lonMax, "latMax": latMax}


def loadLs8(path, fileBaseName, bbox, bands, maskClouds=True):

    fhs = [readTif(path + fileBaseName + band + ".TIF") for band in bands]
    data = np.array([tifGetBbox(fh, bbox)[0] for fh in fhs])

    if maskClouds:
        qa = readTif(path + fileBaseName + "QA_PIXEL.tif")
        qaData = tifGetBbox(qa, bbox)
        data = np.where(qaData == 21824, data, -9999)

    return data


def calcBbox(bboxGlobal, shapeGlobal, index):
    nrRows, nrCols = shapeGlobal
    row, col = index
    width = bboxGlobal["lonMax"] - bboxGlobal["lonMin"]
    lonPerCol = width / nrCols
    height = bboxGlobal["latMax"] - bboxGlobal["latMin"]
    latPerRow = height / nrRows

    lonMin = bboxGlobal["lonMin"] + col * lonPerCol
    lonMax = lonMin + lonPerCol
    latMax = bboxGlobal["latMax"] - row * latPerRow
    latMin = latMax - latPerRow
    
    return {"lonMin": lonMin, "latMin": latMin, "lonMax": lonMax, "latMax": latMax}


def loadData(nrSamples):
    yRaw = loadGeoJson("data/ber/BERPublicSearch/features.geojson")
    bbox = getBbox(yRaw)
    bands = ["B1", "B2", "B3", "B4", "B5", "B6", "B7", "B9", "B10", "B11"]   # not reading B8 - has twice the resolution
    xRaw = loadLs8("data/ls8/", "LC09_L1TP_206023_20230113_20230314_02_T1_", bbox, bands, maskClouds=True)
    nrBands, nrRows, nrCols = xRaw.shape

    X = np.zeros((nrSamples, nrBands))
    Y = np.zeros((nrSamples,))

    s = 0
    while s < nrSamples:
        if s % 10 == 0:
            print(f"... {100 * s/nrSamples}%")
        row = np.random.randint(nrRows)
        col = np.random.randint(nrCols)
        x = xRaw[:, row, col]
        if x[0] == -9999:
            print("hit clouds")
            continue
        xBbox = calcBbox(bbox, (nrRows, nrCols), (row, col))
        y = getClass(yRaw, xBbox)
        if y != -9999:
            X[s, :] = x
            Y[s] = y
            s += 1
        else:
            print("No data: ", xBbox)

    return X, Y