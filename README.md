# Data sources


## Landsat 8
- Landsat 8 from earthexplorer https://earthexplorer.usgs.gov
- Alternatively, download from stac: https://collections.eurodatacube.com/landsat-8-l2/
- Or maybe from here: https://radiantearth.github.io/stac-browser/#/search/external/landsatlook.usgs.gov/stac-server/

My suspicion is that landsat only has L2 onver the US.
Indeed, over Europe I can only find L1 data.


## Copernicus
Alternatively use copernicus data:
https://land.copernicus.eu/global/products/lst
Provides LST, but only at 5km resolution.


## NYC
Maybe I can calibrate my approach on NYC data: https://qsel.columbia.edu/nycenergy/
https://www.sciencedirect.com/science/article/abs/pii/S037877881100524X


## Eu government buildings
The EU also publishes some of their government building stock: https://data.europa.eu/data/datasets/building1?locale=en


## US building data
https://trynthink.github.io/buildingsdatasets/


## Ireland Ber
- BER from https://ndber.seai.ie/BERResearchTool/ber/search.aspx
    - see also https://gis.seai.ie/ber/


## Buildings in relation to local weather
https://www.kaggle.com/datasets/arashnic/building-sites-power-consumption-dataset



# Analysis

## LS8 processing
To calculate LST is a bit complicated - see https://custom-scripts.sentinel-hub.com/landsat-8/land_surface_temperature_mapping/
This seems to be a good source for calculations:
https://custom-scripts.sentinel-hub.com/landsat-8/land_surface_temperature_mapping/



## Energy consumption estimates
- https://www.sciencedirect.com/science/article/abs/pii/S0306261920314616
- http://cs231n.stanford.edu/reports/2022/pdfs/165.pdf
- https://www.scopus.com/record/display.uri?origin=recordpage&zone=relatedDocuments&eid=2-s2.0-85139879311&noHighlight=false&relpos=2

