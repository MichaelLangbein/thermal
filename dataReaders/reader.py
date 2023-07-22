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
    bboxShape = box(*bboxTuple)
    featuresIntersectingWithBbox = jsn.filter(bbox=bboxTuple)
    for feature in featuresIntersectingWithBbox:
        berCount = feature.properties["BER_COUNT"]
        berCoverage = feature.properties["ESTIMATED_BER_COVERAGE"]
        berCountA1 = feature.properties["A1"]
        berCountA2 = feature.properties["A2"]
        berCountA3 = feature.properties["A3"]
        berCountB1 = feature.properties["B1"]
        berCountB2 = feature.properties["B2"]
        berCountB3 = feature.properties["B3"]
        berCountC1 = feature.properties["C1"]
        berCountC2 = feature.properties["C2"]
        berCountC3 = feature.properties["C3"]
        berCountD1 = feature.properties["D1"]
        berCountD2 = feature.properties["D2"]
        berCountE1 = feature.properties["E1"]
        berCountE2 = feature.properties["E2"]
        berCountF = feature.properties["F"]
        berCountG = feature.properties["G"]

        featureShape = shape(feature.geometry)
        intersection = featureShape.intersection(bboxShape)
        overlapDegree = intersection.area / bboxShape.area

        


def getBbox(jsn):
    lonMin, latMin, lonMax, latMax = jsn.bounds()
    return {"lonMin": lonMin, "latMin": latMin, "lonMax": lonMax, "latMax": latMax}


def loadLs8(path, bbox, bands, maskClouds=True):
    fileBaseName = "LC09_L1TP_206023_20230113_20230314_02_T1_"

    fhs = [readTif(path + fileBaseName + band + ".TIF") for band in bands]
    data = np.array([tifGetBbox(fh, bbox) for fh in fhs])

    qa = readTif(path + fileBaseName + "QA_PIXEL.tif")
    qaData = tifGetBbox(qa, bbox)

    dataFiltered = np.where(qaData == 21824, data, -9999)

    return dataFiltered



def calcBbox(bboxGlobal, shapeGlobal, index):
    nrRows, nrCols = shapeGlobal
    row, col = index
    width = bboxGlobal["lonMax"] - bboxGlobal["lonMin"]
    lonPerCol = width / nrCols
    height = bboxGlobal["latMax"] - bboxGlobal["latMin"]
    latPerRow = height / nrRows

    lonStart = col * lonPerCol + bboxGlobal["lonMin"]
    lonEnd = lonStart + lonPerCol
    latStart = row * latPerRow + bboxGlobal["latMin"]
    latEnd = latStart + latPerRow
    
    return {"lonMin": lonStart, "lonMax": lonEnd, "latMin": latStart, "latMax": latEnd}


def loadData(nrSamples):
    yRaw = loadGeoJson("data/ber/features.geojson")
    bbox = getBbox(yRaw)
    bands = ["B1", "B2", "B3", "B4", "B5", "B6", "B7", "B8", "B9", "B10", "B11"]
    xRaw = loadLs8("data/ls8/", bbox, bands, maskClouds=True)
    nrBands, nrRows, nrCols = xRaw.shape

    X = np.zeros((nrSamples, nrBands))
    Y = np.zeros((nrSamples,))

    for s in range(nrSamples):
        row = np.random.randint(nrRows)
        col = np.random.randint(nrCols)
        x = xRaw[:, row, col]
        xBbox = calcBbox(bbox, (nrRows, nrCols), (row, col))
        y = getClass(yRaw, xBbox)
        X[s, :] = x
        Y[s] = y

    return X, Y