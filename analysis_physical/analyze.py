#%%
import numpy as np
import json
from raster import readTif, tifGetBbox, saveToTif, makeTransform
from vectorAndRaster import rasterizeGeojson
from rasterio import CRS
from inspect import getsourcefile
from os.path import abspath, dirname
import matplotlib.pyplot as plt



def extractClouds(data, qaPixelData, noDataValue = -9999):
    """
    extracts clouds
    https://www.usgs.gov/landsat-missions/landsat-collection-2-quality-assessment-bands
    https://pages.cms.hu-berlin.de/EOL/gcg_eo/02_data_quality.html
    
    I think I can do this with just the L1 QA_PIXEL bands.
    Only take values where QA_PIXEL == 21824
    There should be more information in L2 QA-layers, but those are not always available
    (My suspicion is that landsat only has L2 onver the US)

    @TODO: get data for all confidence intervals, not only 21824
    ```
        code = 0
        code |= 0 << 0  # image data only
        code |= 0 << 1  # no dilated clouds
        code |= 0 << 2  # no cirrus
        code |= 0 << 3  # no cloud
        code |= 0 << 4  # no cloud shadow
        code |= 0 << 5  # no snow
        code |= 1 << 6  # clear sky
        code |= 0 << 7  # no water
    ```
    """

    dataFiltered = np.zeros(data.shape)
    dataFiltered = np.where(qaPixelData == 21824, data, noDataValue)

    return dataFiltered


def readMetaData(pathToMetadataJsonFile):
    fh = open(pathToMetadataJsonFile)
    metadata = json.load(fh)
    return metadata


def scaleBandData(rawData, bandNr, metaData):
    mult = float(metaData["LANDSAT_METADATA_FILE"]["LEVEL1_RADIOMETRIC_RESCALING"][f"RADIANCE_MULT_BAND_{bandNr}"])
    add = float(metaData["LANDSAT_METADATA_FILE"]["LEVEL1_RADIOMETRIC_RESCALING"][f"RADIANCE_ADD_BAND_{bandNr}"])
    return rawData * mult + add


def radiance2BrightnessTemperature(toaSpectralRadiance, metaData):
    # Brightness Temperature:
    # If the TOA were a black-body, it would have to have this temperature
    # so that the sensor would receive the measured radiance.
    # Obtained using Planck's law, solved for T (see `black_body_temperature`) and calibrated to sensor.

    k1ConstantBand10 = float(metaData["LANDSAT_METADATA_FILE"]["LEVEL1_THERMAL_CONSTANTS"]["K1_CONSTANT_BAND_10"])
    k2ConstantBand10 = float(metaData["LANDSAT_METADATA_FILE"]["LEVEL1_THERMAL_CONSTANTS"]["K2_CONSTANT_BAND_10"])
    toaBrightnessTemperature = k2ConstantBand10 / np.log((k1ConstantBand10 / toaSpectralRadiance) + 1.0)

    return toaBrightnessTemperature


def bt2lstSingleWindow(toaBrightnessTemperatureCelsius, emissivity, emittedRadianceWavelength = 0.000010895):
    rho = 0.01438                               # [mK]; rho = Planck * light-speed / Boltzmann
    scale = 1.0 + emittedRadianceWavelength * toaBrightnessTemperatureCelsius * np.log(emissivity)  / rho
    landSurfaceTemperature = toaBrightnessTemperatureCelsius / scale
    return landSurfaceTemperature


def bt2lstSplitWindow(toaBT10, toaBT11, emissivity10, emissivity11, cwv = None):
    """
        as per "A practical split-window algorithm for estimating LST", 
        by Cen Du, Huazhong Ren, Remote Sens, 2015
        - `cwv`: column water vapor [g/cm^2]
    """

    def getCoeffsForCWV(cwv):
        # See table 1 of paper
        if cwv == None:  # Default values
            return -0.41165, 1.00522, 0.14543, -0.27297, 4.06655, -6.92512, -18.27461, 0.24468
        if 0 <= cwv <=2.25:
            return -2.78009, 1.01408, 0.15833, -0.34991, 4.04487, 3.55414, -8.88394, 0.09152
        elif 2.25 < cwv <= 3.25:
            return 11.00824, 0.95995, 0.17243, -0.28852, 7.11492, 0.42684, -6.62025, -0.06381
        elif 3.25 < cwv <= 4.25:
            return 9.62610, 0.96202, 0.13834, -0.17262, 7.87883, 5.17910, -13.26611, -0.07603
        elif 4.25 < cwv <= 5.25:
            return 0.61258, 0.99124, 0.10051, -0.09664, 7.85758, 6.86626, -15.00742, -0.01185
        elif 5.25 < cwv <= 6.3:
            return -0.34808, 0.98123, 0.05599, -0.03518, 11.96444, 9.06710, -14.74085, -0.20471
        else:
            raise Exception(f"Unknown value for column water vapor: {cwv}")


    emissivityDelta = emissivity10 - emissivity11
    emissivityMean = (emissivity10 + emissivity11) / 2.0
    b0, b1, b2, b3, b4, b5, b6, b7 = getCoeffsForCWV(cwv)

    term0 = b0

    term1 = (
            b1 
          + b2 * (1 - emissivityMean) / emissivityMean 
          + b3 * emissivityDelta / np.power(emissivityMean, 2)
        ) * (toaBT10 + toaBT11) / 2
    
    term2 = (
            b4 
          + b5 * (1 - emissivityMean) / emissivityMean
          + b6 * emissivityDelta / np.power(emissivityMean, 2)
        ) * (toaBT10 - toaBT11) / 2
    
    term3 = b7 * np.power(toaBT10 - toaBT11, 2)
    
    lst = term0 + term1 + term2 + term3
    return lst


def emissivityFromNDVI(valuesNIR, valuesRed):
    # NDVI:
    # -1.0 ... 0.0 :  water
    # -0.1 ... 0.1 :  rock, sand, snow
    #  0.2 ... 0.5 :  grassland, soil, agricultural, light vegetation
    #  0.6 ... 1.0 :  deep vegetation
    # NDBI:
    # -1.0 ... 0.0 : water
    #  0.0 ... 1.0 : built up 

    ndvi = (valuesNIR - valuesRed) / (valuesNIR + valuesRed)


    ## Step 2.2: Vegetation proportion
    ndviVegetation = 0.5
    ndviSoil = 0.2
    vegetationProportion = np.power((ndvi - ndviSoil) / (ndviVegetation - ndviSoil), 2)


    ## Step 2.3: Land-surface emissivity
    
    # Emissivity: fraction of actually emmited radiation relative to a black body. (Black bodies have maximum emissivity.)
    # Water and soil have high emissivity, asphalt has low (0.88). See https://en.wikipedia.org/wiki/Emissivity
    # @TODO: also account for asphalt, then?
    # For that you might want to use NDBI https://pro.arcgis.com/en/pro-app/latest/arcpy/spatial-analyst/ndbi.htm
    # NDBI = (SWIR - NIR) / (SWIR + NIR)
    #
    # Note that this is only thermal radiation - but things are also cooled by convection and conduction.
    # However, we only care about current temperature - and that is not influenced by any of the other heat-flows.
    # But a problem that *does* occur here is this:
    # Real objects are not black bodies - they dont absorb all incident radiation. They also reflect some of it.
    # Soil and vegetation are not very reflective - so that's good. Water is, but we can mask it out.
    # But buildings are, and we're mostly interested in those. So some very reflective buildings will send out a lot of radiation,
    # leading us to overestimate their temperature.
    # We can mitigate this, though: just look for pixels with a high whight-light value and filter those out.
    # Wait! No, we can't! Materials that reflect visible light don't neccessarily reflect thermal.

    soilEmissivity       = 0.996
    waterEmissivity      = 0.991
    vegetationEmissivity = 0.973
    surfaceRoughness     = 0.005
    landSurfaceEmissivity = np.zeros(ndvi.shape)
    # Probably water
    landSurfaceEmissivity += np.where((ndvi <= 0.0), waterEmissivity, 0)
    # Probably soil
    landSurfaceEmissivity += np.where((0.0 < ndvi) & (ndvi <= ndviSoil), soilEmissivity, 0)
    # Soil/vegetation mixture
    weightedEmissivity = vegetationEmissivity * vegetationProportion + soilEmissivity * (1.0 - vegetationProportion) + surfaceRoughness
    landSurfaceEmissivity += np.where((ndviSoil < ndvi) & (ndvi <= ndviVegetation), weightedEmissivity, 0)
    # Vegetation only
    landSurfaceEmissivity += np.where((ndviVegetation < ndvi), vegetationEmissivity, 0)

    return landSurfaceEmissivity


def emissivityFromOSM(band, bbox, shape, osmBuildings, osmVegetation):
    """
        emissivity values as per table 3 of paper
    """
    if band == 10:
        soilEmissivity       = 0.970
        waterEmissivity      = 0.992
        vegetationEmissivity = 0.973
        buildingEmissivity   = 0.973
    elif band == 11:
        soilEmissivity       = 0.971
        waterEmissivity      = 0.998
        vegetationEmissivity = 0.973
        buildingEmissivity   = 0.981
    else:
        raise Exception(f"Invalid band for emissivity: {band}")

    buildingsRaster = rasterizeGeojson(osmBuildings, bbox, shape)
    vegetationRaster = rasterizeGeojson(osmVegetation, bbox, shape)

    emissivity = np.zeros(shape)
    emissivity += soilEmissivity
    emissivity = np.where(vegetationRaster, vegetationEmissivity, emissivity)
    emissivity = np.where(buildingsRaster, buildingEmissivity, emissivity)

    return emissivity


def estimateLSTfromNDVI(valuesRed, valuesNIR, toaSpectralRadiance, metaData, noDataValue = -9999):

    """
    Convert raw data to land-surface-temperature (LST) in celsius
    
    Based on [Avdan & Jovanovska](https://www.researchgate.net/journal/Journal-of-Sensors-1687-7268/publication/296414003_Algorithm_for_Automated_Mapping_of_Land_Surface_Temperature_Using_LANDSAT_8_Satellite_Data/links/618456aca767a03c14f69ab7/Algorithm-for-Automated-Mapping-of-Land-Surface-Temperature-Using-LANDSAT-8-Satellite-Data.pdf?__cf_chl_rt_tk=e64hIdi4FTDBdxR5Fz0aaWift_OPNow89iJrKJxXOpo-1686654949-0-gaNycGzNEZA)
    https://www.youtube.com/watch?v=FDmYCI_xYlA
    https://cimss.ssec.wisc.edu/rss/geoss/source/RS_Fundamentals_Day1.ppt

    Raw data:
    - Band 4: Red
    - Band 5: NIR
    - Band 6: SWIR-1
    - Band 7: SWIR-2
    - Band 10: Thermal radiance
    """

    noDataMask = (toaSpectralRadiance == noDataValue) | (valuesNIR == noDataValue) | (valuesRed == noDataValue)

    # Step 1: radiance to at-sensor temperature (brightness temperature BT)
    toaBrightnessTemperatureCelsius = radiance2BrightnessTemperature(toaSpectralRadiance, metaData)
    toaBrightnessTemperatureCelsius = np.where(noDataMask, noDataValue, toaBrightnessTemperatureCelsius)

    # Step 2: 
    landSurfaceEmissivity = emissivityFromNDVI(valuesNIR, valuesRed)
    landSurfaceEmissivity = np.where(noDataMask, noDataValue, landSurfaceEmissivity)

    # Step 3: land-surface-temperature
    landSurfaceTemperature = bt2lstSingleWindow(toaBrightnessTemperatureCelsius, landSurfaceEmissivity)
    landSurfaceTemperature = np.where(noDataMask, noDataValue, landSurfaceTemperature)

    return landSurfaceTemperature


def estimateLSTfromOSM(toaSpectralRadiance, metaData, osmBuildings, osmVegetation, noDataValue = -9999):
    """
        - toaSpectralRadiance: [W/m² angle]
        - emissivity:        (https://en.wikipedia.org/wiki/Emissivity)
             - soil:        0.996
             - water:       0.991
             - vegetation:  0.973
             - concrete:    0.91
             - brick:       0.90
             - asphalt:     0.88

        Steps:
            1. toaSpectralRadiance to toaBlackbodyTemperature (aka BrightnessTemperature) with Planck's law
            2. estimate emissivity from OSM data
            3. blackBodyTemperature to landSurfaceTemperature

    """

    noDataMask = (toaSpectralRadiance == noDataValue)

    # Step 1: radiance to at-sensor temperature (brightness temperature BT)
    toaBrightnessTemperatureCelsius = radiance2BrightnessTemperature(toaSpectralRadiance, metaData)
    toaBrightnessTemperatureCelsius = np.where(noDataMask, noDataValue, toaBrightnessTemperatureCelsius)

    # Step 2: estimate emissivity from OSM data
    emissivity = emissivityFromOSM(toaSpectralRadiance.shape, osmBuildings, osmVegetation)

    # Step 3: black-body-temperature to land-surface-temperature
    landSurfaceTemperature = bt2lstSingleWindow(toaBrightnessTemperatureCelsius, emissivity)
    landSurfaceTemperature = np.where(noDataMask, noDataValue, landSurfaceTemperature)

    return landSurfaceTemperature



#%%

def lstFromFile_Avdan(pathToFile, fileNameBase, aoi):

    base = f"{pathToFile}/{fileNameBase}"
    # `noDataValue` must not be np.nan, because then `==` doesn't work as expected
    noDataValue = -9999

    metaData                = readMetaData(base + "MTL.json")

    qaPixelFh               = readTif(base + "QA_PIXEL.TIF")
    valuesRedFh             = readTif(base + "B4.TIF")
    valuesNIRFh             = readTif(base + "B5.TIF")
    toaSpectralRadianceFh   = readTif(base + "B10.TIF")

    assert(qaPixelFh.res == valuesRedFh.res)
    assert(valuesRedFh.res == valuesNIRFh.res)
    assert(valuesNIRFh.res == toaSpectralRadianceFh.res)

    qaPixelAOI              = tifGetBbox(qaPixelFh, aoi)[0]
    valuesRedAOI            = tifGetBbox(valuesRedFh, aoi)[0]
    valuesNIRAOI            = tifGetBbox(valuesNIRFh, aoi)[0]
    toaSpectralRadianceAOI  = tifGetBbox(toaSpectralRadianceFh, aoi)[0]

    valuesRedNoClouds           = extractClouds(valuesRedAOI, qaPixelAOI, noDataValue)
    valuesNIRNoClouds           = extractClouds(valuesNIRAOI, qaPixelAOI, noDataValue)
    toaSpectralRadianceNoClouds = extractClouds(toaSpectralRadianceAOI, qaPixelAOI, noDataValue)

    valuesRed = valuesRedNoClouds  # no need to scale these - only used for ndvi
    valuesNIR = valuesNIRNoClouds  # no need to scale these - only used for ndvi
    toaSpectralRadiance = scaleBandData(toaSpectralRadianceNoClouds, 10, metaData)

    lst = estimateLSTfromNDVI(valuesRed, valuesNIR, toaSpectralRadiance, metaData, noDataValue)
    lstWithNan = np.where(lst == noDataValue, np.nan, lst)

    # adding projection metadata
    imgH, imgW = lst.shape
    transform = makeTransform(imgH, imgW, aoi)
    saveToTif(f"{pathToFile}/lst.tif", lst, CRS.from_epsg(4326), transform, noDataValue)
    lstTif = readTif(f"{pathToFile}/lst.tif")

    return lstWithNan, lstTif


def lstFromFile_OSM(pathToFile, fileNameBase, aoi, osmBuildings, osmVegetation):

    base = f"{pathToFile}/{fileNameBase}"
    # `noDataValue` must not be np.nan, because then `==` doesn't work as expected
    noDataValue = -9999

    metaData = readMetaData(base + "MTL.json")

    qaPixelFh               = readTif(base + "QA_PIXEL.TIF")
    toaRadiance10Fh         = readTif(base + "B10.TIF")
    toaRadiance11Fh         = readTif(base + "B11.TIF")
    assert(qaPixelFh.res == toaRadiance10Fh.res)
    assert(toaRadiance10Fh.res == toaRadiance11Fh.res)

    qaPixelAOI        = tifGetBbox(qaPixelFh, aoi)[0]
    toaRadiance10AOI  = tifGetBbox(toaRadiance10Fh, aoi)[0]
    toaRadiance11AOI  = tifGetBbox(toaRadiance11Fh, aoi)[0]

    toaRadiance10NoClouds = extractClouds(toaRadiance10AOI, qaPixelAOI, noDataValue)
    toaRadiance11NoClouds = extractClouds(toaRadiance11AOI, qaPixelAOI, noDataValue)

    # Converting raw scaled sensor-data to spectral radiance [W/m²]
    toaRadiance10 = scaleBandData(toaRadiance10NoClouds, 10, metaData)
    toaRadiance11 = scaleBandData(toaRadiance11NoClouds, 11, metaData)

    noDataMask = (toaRadiance10 == noDataValue) | (toaRadiance11 == noDataValue)

    # Step 1: radiance to at-sensor temperature (brightness temperature BT)
    toaBT10 = radiance2BrightnessTemperature(toaRadiance10, metaData)
    toaBT11 = radiance2BrightnessTemperature(toaRadiance11, metaData)
    toaBT10 = np.where(noDataMask, noDataValue, toaBT10)
    toaBT11 = np.where(noDataMask, noDataValue, toaBT11)

    # Step 2: estimate emissivity from OSM data
    emissivity10 = emissivityFromOSM(10, aoi, toaRadiance10.shape, osmBuildings, osmVegetation)
    emissivity11 = emissivityFromOSM(11, aoi, toaRadiance10.shape, osmBuildings, osmVegetation)

    # Step 3: black-body-temperature to land-surface-temperature
    landSurfaceTemperature = bt2lstSplitWindow(toaBT10, toaBT11, emissivity10, emissivity11)
    landSurfaceTemperature = np.where(noDataMask, np.nan, landSurfaceTemperature)

    # adding projection metadata
    imgH, imgW = landSurfaceTemperature.shape
    transform = makeTransform(imgH, imgW, aoi)
    saveToTif(f"{pathToFile}/lst.tif", landSurfaceTemperature, CRS.from_epsg(4326), transform, noDataValue)
    lstTif = readTif(f"{pathToFile}/lst.tif")

    return landSurfaceTemperature, lstTif



# execute

if __name__ == "__main__":
    thisFilePath = dirname(abspath(getsourcefile(lambda:0)))
    pathToFile = f"{thisFilePath}/ls8/LC08_L1TP_193026_20220803_20220806_02_T1"
    fileNameBase = "LC08_L1TP_193026_20220803_20220806_02_T1_"
    
    aoi = { "lonMin": 11.214, "latMin": 48.064, "lonMax": 11.338, "latMax": 48.117 }
    
    fh = open("./osm/buildings.geo.json")
    osmBuildings = json.load(fh)
    osmVegetation = { "type": "FeatureCollection", "features": [] }

    lst, lstFile = lstFromFile_OSM(pathToFile, fileNameBase, aoi, osmBuildings, osmVegetation)

    fig, axes = plt.subplots(1, 2)
    axes[0].imshow(lst)
    axes[1].hist(lst.flatten() - 273)
    

# %%
