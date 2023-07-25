import './style.css';
import 'ol/ol.css';
import { Map, MapBrowserEvent, Overlay, View } from 'ol';
import TileLayer from 'ol/layer/Tile';
import WGLTileLayer from 'ol/layer/WebGLTile';
import OSM from 'ol/source/OSM';
import VectorLayer from 'ol/layer/Vector';
import VectorSource from 'ol/source/Vector';
import GeoJSON from 'ol/format/GeoJSON';
import Style from 'ol/style/Style';
import Fill from 'ol/style/Fill';
import Feature, { FeatureLike } from 'ol/Feature';
import { GeoTIFF } from 'ol/source';
import vectorData from './buildings_temperature.geo.json';
import { colorScale } from './graph';
import { Datum, barchart } from './barchart';

// const timeSeries: Datum[] = [
//   { label: 'a', value: -4 },
//   { label: 'b', value: 0.5 },
//   { label: 'c', value: 2 }
// ]
// const pop = document.getElementById('pop') as HTMLDivElement;
// barchart().container(pop).width(400).height(300).data(timeSeries).xlabel('time').ylabel('delta T').hlines([{label: '-2.1', value: -2.1}, {label: 'other', value: 1.0}])();




/**********************************************
 *   STATE
 *********************************************/

interface State {
  mode: 'mean' | 'time',
  currentTime: string,
  availableTimes: string[],
  clickedFeature: FeatureLike | undefined,
  clickLocation: number[] | undefined,
  statistic: "statisticTemp" | "statisticTinMinTout" | "statisticTinMinToutNature"
}

const state: State = {
  mode: 'mean',
  currentTime: '2020-11-17 10:04:26.7534760Z',
  availableTimes: [
    "2020-11-17 10:04:26.7534760Z",
    // "2020-12-03 10:04:30.0526110Z",
    "2020-12-19 10:04:29.0548320Z",
    "2021-01-04 10:04:24.4138260Z",
    // "2021-01-20 10:04:17.4570379Z",
    // "2021-02-05 10:04:15.9847940Z",
    // "2021-02-21 10:03:47.5687389Z",
    "2021-02-21 10:04:11.4555430Z",
    // "2021-11-20 10:04:29.0843560Z",
    // "2021-12-14 10:04:26.7646900Z",
    // "2021-12-22 10:04:03.7751530Z",
    // "2021-12-22 10:04:27.6577210Z",
    // "2022-01-07 10:04:23.4671659Z",
    "2022-01-15 10:04:23.2404300Z",
    // "2022-01-23 10:04:19.2682800Z",
    // "2022-02-24 10:03:46.7479169Z",
    // "2022-02-24 10:04:10.6220130Z",
    // "2022-08-03 10:04:11.7338470Z",
    "2022-08-03 10:04:35.6121790Z",
    "2022-10-06 10:04:44.6235710Z",
  ],
  clickedFeature: undefined,
  clickLocation: undefined,
  statistic: "statisticTemp"
};

/**********************************************
 *   INTERACTIVE COMPONENTS
 *********************************************/


const appDiv                        = document.getElementById("app") as HTMLDivElement;
const popupDiv                      = document.getElementById("popup") as HTMLDivElement;
const meanDiv                       = document.getElementById("modeSelectMean") as HTMLDivElement;
const timeDiv                       = document.getElementById("modeSelectTime") as HTMLDivElement;
const timeControlBackDiv            = document.getElementById("timeControlBack") as HTMLDivElement;
const timeControlCurrentTimeDiv     = document.getElementById("timeControlCurrentTime") as HTMLDivElement;
const timeControlForwardDiv         = document.getElementById("timeControlForward") as HTMLDivElement;
const statisticTempDiv              = document.getElementById("statisticTemp") as HTMLDivElement;
const statisticTinMinToutDiv        = document.getElementById("statisticTinMinTout") as HTMLDivElement;
const statisticTinMinToutNatureDiv  = document.getElementById("statisticTinMinToutNature") as HTMLDivElement;


/**********************************************
 *   SETUP
 *********************************************/


const baseLayer = new TileLayer({
  source: new OSM({
    // url: "https://tile-{a-c}.openstreetmap.fr/hot/{z}/{x}/{y}.png"
  }),
  className: 'bw',
  opacity: 0.7
});

const cogLayer = new WGLTileLayer({
  source: new GeoTIFF({
    sources: [{ url: `/public/lst_${state.currentTime}.tif` }]
  }),
  style: {
    // https://openlayers.org/workshop/en/cog/ndvi.html
    color: [
      'interpolate',
      ['linear'],
      ['band', 1],
      -0.05,  [0, 0, 0],
      0.0,  [125, 125, 125],
      0.05,  [256, 256, 256]
    ]
  },
  opacity: 0.6,
  visible: false
});


const vectorLayer = new VectorLayer({
  source: new VectorSource({
    features: new GeoJSON().readFeatures(vectorData)
  }),
  style: createVectorStyle(state),
  opacity: 0.8
});

const view = new View({
  center: [11.3, 48.08],
  zoom: 14,
  projection: 'EPSG:4326'
});

const popupOverlay = new Overlay({
  element: popupDiv
});

const map = new Map({
  view, layers: [baseLayer, cogLayer, vectorLayer], overlays: [popupOverlay], target: appDiv
});





/**********************************************
 *   EVENTS
 *********************************************/


map.on("click", evt => handleMapClick(evt));
meanDiv.addEventListener('click', activateMeanView);
timeDiv.addEventListener('click', activateTimeView);
timeControlBackDiv.addEventListener('click', timeBack);
timeControlForwardDiv.addEventListener('click', timeForward);
statisticTempDiv.addEventListener('click', () => useStatistic("statisticTemp"));
statisticTinMinToutDiv.addEventListener('click', () => useStatistic("statisticTinMinTout"));
statisticTinMinToutNatureDiv.addEventListener('click', () => useStatistic("statisticTinMinToutNature"));


/**********************************************
 *   ACTIONS -> STATE
 *********************************************/


function handleMapClick(evt: MapBrowserEvent<any>) {
  const location = evt.coordinate;
  const features = vectorLayer.getSource()?.getFeaturesAtCoordinate(location);
  if (features && features?.length > 0) {
    state.clickedFeature = features[0];
    state.clickLocation = location;
  } else {
    state.clickedFeature = undefined;
    state.clickLocation = undefined;
  }

  updatePopup(state);
}

function useStatistic(statistic: State["statistic"]) {
  state.statistic = statistic;

  updateStatsSelector(state);
  updatePopup(state);
  updateMap(state);
}


function timeBack() {
  if (state.mode === "mean") return;
  const indexCurrent = state.availableTimes.indexOf(state.currentTime);
  if (indexCurrent <= 0) return;
  const newTime = state.availableTimes[indexCurrent - 1];
  state.currentTime = newTime;

  updateTimeButtons(state);
  updatePopup(state);
  updateMap(state);
}

function timeForward() {
  if (state.mode === "mean") return;
  const indexCurrent = state.availableTimes.indexOf(state.currentTime);
  if (indexCurrent >= state.availableTimes.length - 1) return;
  const newTime = state.availableTimes[indexCurrent + 1];
  state.currentTime = newTime;

  updateTimeButtons(state);
  updatePopup(state);
  updateMap(state);
}

function activateTimeView() {
  state.mode = "time";

  updateModeSelector(state);
  updatePopup(state);
  updateMap(state);
}

function activateMeanView() {
  state.mode = "mean";

  updateModeSelector(state);
  updatePopup(state);
  updateMap(state);
}

/**********************************************
 *   STATE -> UI
 *********************************************/

function updateMap(state: State) {
  if (state.mode === "mean") {
    const style = createVectorStyle(state);
    vectorLayer.setStyle(style);
    cogLayer.setVisible(false);
  }
  else if (state.mode === "time") {
    const style = createVectorStyle(state);
    vectorLayer.setStyle(style);
    cogLayer.setVisible(true);
    cogLayer.setSource(new GeoTIFF({
      sources: [{ url: `/public/lst_${state.currentTime}.tif` }]
    }));
  }

}

function updateModeSelector(state: State) {
  if (state.mode === "mean") {
    meanDiv.classList.replace('inactive', 'active');
    timeDiv.classList.replace('active', 'inactive');
    timeControlCurrentTimeDiv.innerHTML = "time";
  } else if (state.mode === "time") {
    meanDiv.classList.replace('active', 'inactive');
    timeDiv.classList.replace('inactive', 'active');
    timeControlCurrentTimeDiv.innerHTML = state.currentTime.slice(0, 10);
  }
}

function updateStatsSelector(state: State) {
  if (state.statistic === "statisticTemp") {
    statisticTempDiv.classList.replace("inactive", "active");
    statisticTinMinToutDiv.classList.replace("active", "inactive");
    statisticTinMinToutNatureDiv.classList.replace("active", "inactive");
  }
  else if (state.statistic === "statisticTinMinTout") {
    statisticTempDiv.classList.replace("active", "inactive");
    statisticTinMinToutDiv.classList.replace("inactive", "active");
    statisticTinMinToutNatureDiv.classList.replace("active", "inactive");  
  }
  else if (state.statistic === "statisticTinMinToutNature") {
    statisticTempDiv.classList.replace("active", "inactive");
    statisticTinMinToutDiv.classList.replace("active", "inactive");
    statisticTinMinToutNatureDiv.classList.replace("inactive", "active");  
  }
}

function updatePopup(state: State) {
  if (!state.clickedFeature) {
    popupOverlay.setPosition(undefined);
    return;
  }

  popupDiv.innerHTML = "";

  const timeSeries = getTimeSeries(state.clickedFeature, state.statistic);
  const vMean = timeSeriesMean(timeSeries);
  const vCurrent = timeSeriesValueAt(timeSeries, state.currentTime);
  const ylabel = getLabel(state.statistic);

  barchart()
  .container(popupDiv)
  .width(250).height(250)
  .data(timeSeries)
  .xlabel('time').ylabel(ylabel)
  .margin({ top: 20, left: 50, bottom: 50, right: 10})
  .hlines([{label: "mean", value: vMean}])();
  
  const textDiv = document.createElement('div');
  let popupText = `<p>${ylabel}</p>`;
  popupText += `<p>Mean: ${vMean.toFixed(2)}</p>`;
  if (state.mode === "time" && state.currentTime) popupText += `<p>${state.currentTime.slice(0, 10)}: ${vCurrent ? vCurrent.toFixed(2) : 'NaN'}</p>`;

  textDiv.innerHTML = popupText;
  popupDiv.appendChild(textDiv);

  popupOverlay.setPosition(state.clickLocation);
}

function updateTimeButtons(state: State) {
  const indexCurrent = state.availableTimes.indexOf(state.currentTime);
  if (indexCurrent <= 0) {
    timeControlBackDiv.classList.replace("active", "inactive");
    return;
  } else {
    timeControlBackDiv.classList.replace("inactive", "active");
  }
  if (indexCurrent >= (state.availableTimes.length - 1)) {
    timeControlForwardDiv.classList.replace("active", "inactive");
    return;
  } else {
    timeControlForwardDiv.classList.replace("inactive", "active");
  }
}



/**********************************************
 *   HELPERS
 *********************************************/

function createVectorStyle(state: State) {
  // state.mode, state.statistic, state.currentTime
  if (state.mode === "mean") {

  }
  return (feature: FeatureLike) => {
    const ts = getTimeSeries(feature, state.statistic);
    let value: number | undefined;
    if (state.mode === "mean") value = timeSeriesMean(ts);
    if (state.mode === "time") value = timeSeriesValueAt(ts, state.currentTime);

    if (value === undefined) {
      return new Style({
        fill: new Fill({ color: `rgb(50, 50, 50)` })
      });
    }

    const {maxVal,  minVal} = getMaxAndMin(state.statistic);
    const {r, g, b} = colorScale(value, minVal, maxVal);
  
    return new Style({
      fill: new Fill({
        color: `rgb(${r}, ${g}, ${b})`
      })
    });
  }
}

function timeSeriesValueAt(ts: Datum[], time: string) {
  return ts.find(d => d.label === time)?.value;
}

function timeSeriesMean(ts: Datum[]) {
  const values = ts.map(d => d.value).filter(v => Number.isFinite(v));
  const sum = values.reduce((last, curr) => last + curr, 0);
  return sum / values.length;
}

function getTimeSeries(feature: FeatureLike, stat: State["statistic"]) {
    const props = feature.getProperties();
    const deltaTs = props["temperature"];

    const func = getStatisticFunction(stat);

    const timeSeries: Datum[] = [];
    for (const [time, values] of Object.entries(deltaTs)) {

        const { tMeanInside, tMeanOutside, tMeanOutsideNature } = values as any;
        const val = func(tMeanInside, tMeanOutside, tMeanOutsideNature);
        if (Number.isNaN(val) || !Number.isFinite(val)) continue;
        timeSeries.push({ label: time.slice(0, 10), value: val });

    }

    timeSeries.sort((a, b) => a.label < b.label ? -1 : 1);

    return timeSeries;
}

function getStatisticFunction(stat: State["statistic"]) {
  switch(stat) {
    case "statisticTemp":
      return (tMeanInside: number, tMeanOutside: number, tMeanOutsideNature: number) => tMeanInside;
    case "statisticTinMinTout":
      return (tMeanInside: number, tMeanOutside: number, tMeanOutsideNature: number) => tMeanInside - tMeanOutside;
    case "statisticTinMinToutNature":
      return (tMeanInside: number, tMeanOutside: number, tMeanOutsideNature: number) => tMeanInside - tMeanOutsideNature;
  }
}

function getMaxAndMin(stat: State["statistic"]) {
  switch(stat) {
    case "statisticTemp":
      return {minVal: -5, maxVal: 35};
    case "statisticTinMinTout":
    case "statisticTinMinToutNature":
      return {minVal: -2, maxVal: 2};
  }
}

function getLabel(stat: State["statistic"]) {
  switch (stat) {
    case "statisticTemp":
      return "T [°C]"
    case "statisticTinMinTout":
      return "T_in - T_out [°C]"
    case "statisticTinMinToutNature":
      return "T_in - T_out (no buildings) [°C]"
  }
}




function ___meanLayerStyle(feature: FeatureLike) {
  const mean = featureMeanDeltaT(feature);
  if (Number.isNaN(mean)) return new Style({
    fill: new Fill({
      color: `rgb(125, 125, 125)`
    })
  })

  const maxVal = 2.0;
  const minVal = -2.0;
  const {r, g, b} = colorScale(mean, minVal, maxVal);

  return new Style({
    fill: new Fill({
      color: `rgb(${r}, ${g}, ${b})`
    })
  });
}
