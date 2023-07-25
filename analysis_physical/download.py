from dotenv import dotenv_values
from landsatxplore.api import API
from landsatxplore.earthexplorer import EarthExplorer, EarthExplorerError
import os


datasets = {
    "Landsat 5 TM Collection 2 Level 1":    "landsat_tm_c2_l1",
    "Landsat 5 TM Collection 2 Level 2":    "landsat_tm_c2_l2",
    "Landsat 7 ETM+ Collection 2 Level 1":  "landsat_etm_c2_l1",
    "Landsat 7 ETM+ Collection 2 Level 2":  "landsat_etm_c2_l2",
    "Landsat 8 Collection 2 Level 1":       "landsat_ot_c2_l1",
    "Landsat 8 Collection 2 Level 2":       "landsat_ot_c2_l2",
    "Landsat 9 Collection 2 Level 1":       "landsat_ot_c2_l1",
    "Landsat 9 Collection 2 Level 2":       "landsat_ot_c2_l2"
}

def downloadLandsat(bbox, startDate, endDate, maxResults, outputDir = "./data", maxClouds = 50, dataset = "landsat_ot_c2_l1"):

    config = dotenv_values(".env")

    api = API(config["username"], config["password"])
    ee = EarthExplorer(config["username"], config["password"])

    lonMin = bbox["lonMin"]
    latMin = bbox["latMin"]
    lonMax = bbox["lonMax"]
    latMax = bbox["latMax"]
    bboxArr = [lonMin, latMin, lonMax, latMax]

    scenes = api.search(
        dataset=dataset,
        start_date=startDate,
        end_date=endDate,
        bbox=bboxArr,
        max_cloud_cover=maxClouds,
        max_results=maxResults
    )

    for scene in scenes:
        print(f"Trying to download scene {scene['entity_id']}")
        try:
            ee.download(scene["entity_id"], output_dir=outputDir)
        except EarthExplorerError as e:
            print(e)

    api.logout()
    ee.logout()

    fileNames = os.listdir(outputDir)
    tarFilePaths = [os.path.abspath(os.path.join(outputDir, fileName)) 
                    for fileName in fileNames if fileName.endswith(".tar")]
    return tarFilePaths




if __name__ == "__main__":
    bbox = {"lonMin": 11.214026877579727, "latMin": 48.06498094193711, "lonMax": 11.338031979211422, "latMax": 48.117561211533626}
    clouds = 10
    start = "2022-01-01"
    end = "2023-01-01"
    limit = 10
    outputDir = "./data"
    paths = downloadLandsat(bbox, start, end, limit, outputDir, clouds)
    print(paths)

