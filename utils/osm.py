import os
import json
import requests as req


# Tested with http://overpass-turbo.eu/#

def nodeToPoint(node):
    coordinates = [node["lon"], node["lat"]]
    properties = {key: val for key, val in node.items() if key not in ["type", "lon", "lat"]}
    point =  {
        "type": "Feature",
        "geometry" : {
            "type": "Point",
            "coordinates": coordinates,
            },
        "properties" : properties,
    }
    return point

def nodeToPoly(node):
    coordinates = [[[e["lon"], e["lat"]] for e in node["geometry"]]]
    properties = node["tags"] if "tags" in node else {}
    properties["id"] = node["id"]
    return {
        "type": "Feature",
        "geometry" : {
            "type": "Polygon",
            "coordinates": coordinates,
            },
        "properties" : properties,
    }

def nodeToLineString(way):
    coordinates = [[e["lon"], e["lat"]] for e in way["geometry"]]
    properties = way["tags"] if "tags" in way else {}
    properties["id"] = way["id"]
    return {
        "type": "Feature",
        "geometry" : {
            "type": "LineString",
            "coordinates": coordinates,
            },
        "properties" : properties,
    }


def osmToGeojson(data, format="polygon", saveFreeNodes=False):
    elements = data["elements"]

    try: 
        ways =  [e for e in elements if e["type"] == "way"]
        if format == "polygon":
            polygons = [nodeToPoly(way) for way in ways]
            features = polygons
        elif format == "linestring":
            lineStrings = [nodeToLineString(way) for way in ways]
            features = lineStrings
        else:
            raise Exception(f"Unknown format: {format}")
    except Exception as e:
        print(e)

    if saveFreeNodes:
        nodes = [e for e in elements if e["type"] == "node"]
        freeNodes = []
        for node in nodes:
            isFreeNode = True
            for way in ways:
                if node["id"] in way["nodes"]:
                    isFreeNode = False
                    break
            if isFreeNode:
                freeNodes.append(node) 
        freePoints = [nodeToPoint(n) for n in freeNodes]
        features += freePoints

    json = {
        "type": "FeatureCollection",
        "features": features
    }
    return json


def downloadAndSaveOSM(bbox, saveToDirPath=None, getBuildings=True, getTrees=True, getWater=True, getRoads=True):
    overpass_url = "http://overpass-api.de/api/interpreter"

    lonMin = bbox["lonMin"]
    latMin = bbox["latMin"]
    lonMax = bbox["lonMax"]
    latMax = bbox["latMax"]
    stringifiedBbox = f"{latMin},{lonMin},{latMax},{lonMax}"

    buildingQuery = f"""
        [out:json];     /* output in json format */
        way[building]( {stringifiedBbox} );
        (._;>;);        /* get the nodes that make up the ways  */
        out geom;
    """

    treesQuery = f"""
        [out:json];
        (
            way[landuse=forest]( {stringifiedBbox} );
            way[landuse=meadow]( {stringifiedBbox} );
            way[landuse=orchard]( {stringifiedBbox} );
            relation[landuse=forest]( {stringifiedBbox} );  /* also including multi-polyons */
            relation[landuse=meadow]( {stringifiedBbox} );  /* also including multi-polyons */
            relation[landuse=orchard]( {stringifiedBbox} );  /* also including multi-polyons */
        );              /* union of the above statements */
        (._;>;);
        out geom;
    """

    waterQuery = f"""
        [out:json];
        (
            way[natural=water]( {stringifiedBbox} );
            relation[natural=water]( {stringifiedBbox} );
        );
        (._;>;);
        out geom;
    """

    roadQuery = f"""
        [out:json];
        way["highway"]( {stringifiedBbox} );
        out geom;
    """

    fullData = {}

    if saveToDirPath is not None:
        os.makedirs(saveToDirPath, exist_ok=True)

    if getBuildings:
        response = req.get(overpass_url, params={'data': buildingQuery})
        data = response.json()
        geojson = osmToGeojson(data)
        fullData["buildings"] = geojson

        if saveToDirPath is not None:
            filePath = os.path.join(saveToDirPath, 'buildings.geo.json')
            with open(filePath, 'w') as fh:
                json.dump(geojson, fh, indent=4)

    if getTrees:
        response = req.get(overpass_url, params={'data': treesQuery})
        data = response.json()
        geojson = osmToGeojson(data)
        fullData["trees"] = geojson

        if saveToDirPath is not None:
            filePath = os.path.join(saveToDirPath, 'trees.geo.json')
            with open(filePath, 'w') as fh:
                json.dump(geojson, fh, indent=4)

    if getWater:
        response = req.get(overpass_url, params={'data': waterQuery})
        data = response.json()
        geojson = osmToGeojson(data)
        fullData["water"] = geojson

        if saveToDirPath is not None:
            filePath = os.path.join(saveToDirPath, 'water.geo.json')
            with open(filePath, 'w') as fh:
                json.dump(geojson, fh, indent=4)

    if getRoads:
        response = req.get(overpass_url, params={'data': roadQuery})
        data = response.json()
        geojson = osmToGeojson(data, "linestring")
        fullData["roads"] = geojson

        if saveToDirPath is not None:
            filePath = os.path.join(saveToDirPath, 'roads.geo.json')
            with open(filePath, 'w') as fh:
                json.dump(geojson, fh, indent=4)

    return fullData


# osmData = downloadAndSaveOSM(osmDir, bbox)



if __name__ == "__main__":
    bbox = { "lonMin": 11.214, "latMin": 48.064, "lonMax": 11.338, "latMax": 48.117 }
    data = downloadAndSaveOSM(bbox, saveToDirPath="./", getBuildings=False, getTrees=False, getWater=False, getRoads=True)
