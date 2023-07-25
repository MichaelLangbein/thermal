# Data

## Input

- Landsat 8 from earthexplorer https://earthexplorer.usgs.gov

## Labels 

- BER from https://ndber.seai.ie/BERResearchTool/ber/search.aspx
    - see also https://gis.seai.ie/ber/



# Python

Libraries used:

 - fiona: reads geojson with index
 - shapely: for geometry operations
 - rasterio: for raster handling
 - pyproj: projections