import * as d3color from 'd3-color';



export function colorScale(value: number, min: number = -10.0, max: number = 50.0): { r: any; g: any; b: any; } {
  const [r, g, b] = blueRedScaleStepwise(min, max, value);
  return { r, g, b };
}

function blueRedScaleStepwise(startVal: number, endVal: number, currentVal: number): [number, number, number] {
  const degree = fraction(currentVal, startVal, endVal);
  const rgb = scaleInterpolation(blueRedScale, degree);
  return rgb;
}


function greenVioletRangeStepwise(startVal: number, endVal: number, currentVal: number): [number, number, number] {
  const degree = fraction(currentVal, startVal, endVal);
  const rgb = scaleInterpolation(violetGreenScale2, 1.0 - degree);
  return rgb;
}

function fraction(val: number, start: number, end: number, minDistance = 0.0000001): number {
  if (Math.abs(end - start) < minDistance) {
    console.warn(`Trying to calculate a fraction with start- and end-point very close to each other: ${end} - ${start} = ${end - start}`);
    return 0.0; // by l'Hospital
  }
  return (val - start) / (end - start);
}

function scaleInterpolation(scale: Scale, value: number, smooth = true): [number, number, number] {
  const keys = Object.keys(scale).map(k => +k).sort();  // js-objects dont keep the ordering of numeric keys as they were entered. instead it goes: integers, strings, decimals, each group sorted by first appearance, not value.
  const colors = keys.map(k => scale[k]);
  const nrKeys = keys.length;
  if (value < keys[0]) {
    return colors[0];
  }
  for (let i = 0; i < nrKeys; i++) {
    const startKey = keys[i];
    const endKey = keys[i + 1];
    if (startKey <= value && value < endKey) {
      if (!smooth) {
        return colors[i];
      }
      const degree = fraction(value, startKey, endKey);
      const startColorRGB = colors[i];
      const endColorRGB = colors[i + 1];
      const startColorHSL = d3color.hsl(d3color.rgb(...startColorRGB));
      const endColorHSL = d3color.hsl(d3color.rgb(...endColorRGB));
      const h = linInterpolate(startColorHSL.h, endColorHSL.h, degree);
      const s = linInterpolate(startColorHSL.s, endColorHSL.s, degree);
      const l = linInterpolate(startColorHSL.l, endColorHSL.l, degree);
      const rgb = d3color.rgb(d3color.hsl(h, s, l));
      return [Math.round(rgb.r), Math.round(rgb.g), Math.round(rgb.b)];
    }
  }
  return colors[nrKeys - 1];
}

function linInterpolate(startVal: number, endVal: number, degree: number): number {
  const degreeClamped = Math.max(Math.min(degree, 1), 0);
  const interpolated = degreeClamped * (endVal - startVal) + startVal;
  return interpolated;
}

interface Scale {
  [key: string]: [number, number, number];
}

const violetGreenScale2: Scale = {
  0.2: [184, 53, 131],
  0.35: [213, 62, 79],
  0.5: [252, 141, 89],
  0.7: [254, 224, 139],
  0.8: [230, 245, 152],
  0.9: [153, 213, 148],
};

const blueRedScale: Scale = {
  0.1: [69,117,180],     // blue
  0.3: [145,191,219],
  0.4: [224,243,248],
  0.5: [254,224,144],
  0.6: [252,141,89],
  0.9: [215,48,39],       // red
}