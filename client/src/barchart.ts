import { select, pointer } from 'd3-selection';
import { scaleBand, scaleLinear, scaleOrdinal } from 'd3-scale';
import { axisBottom, axisLeft } from 'd3-axis';
import { colorScale as gvColorScale } from './graph';



export interface Datum { label: string, value: number };

export function makeBarchart(container: HTMLDivElement, data: Datum[], xLabel: string, yLabel: string, widthTotal: number, heightTotal: number, hlines: Datum[], margin = { top: 10, right: 10, bottom: 30, left: 30 }) {

    /**
     *   -------------------------svg-----------------  widthTotal * heightTotal
     *   |    -----------------graph---------------  | width * height
     *   |    | y  |--------center---------------| | | (width - margins) * (height - margins)
     *   | y  | a  |                             | | |    
     *   | l  | x  |                             | | |  
     *   | a  | i  |                             | | |  
     *   | b  | s  |                             | | | 
     *   | e  |    |-----------------------------| | | 
     *   | l  |           x-axis                   | | 
     *   |    -------------------------------------  |
     *   |          x-label                          |
     *   ---------------------------------------------
     */

    const letterSize = 10;


    const width = widthTotal - margin.left - margin.right;
    const height = heightTotal - margin.top - margin.bottom;

    const base = select(container);
    const svg = base
        .append('svg')
        .attr('width', widthTotal)
        .attr('height', heightTotal)
        .attr('viewport', `0, 0, ${widthTotal}, ${heightTotal}`);

    // x-label
    const xLabelContainer = svg.append('text')
        .attr('class', 'xLabel')
        .style('text-anchor', 'middle')
        .attr('transform', `translate(${3 * letterSize}, ${heightTotal - margin.bottom * 0.3})`)
        .text(xLabel);

    // y-label
    const yLabelContainer = svg.append('text')
        .attr('class', 'yLabel')
        .attr('transform', `translate(${margin.left * 0.75}, ${1.5 * letterSize})`) //  rotate(-90)`)
        .style('text-anchor', 'middle')
        .text(yLabel);


    // central canvas including axes, but without x- and y-label
    const graph = svg
        .append('g')
        .attr('class', 'graph')
        .attr('width', width)
        .attr('height', height)
        .attr('transform', `translate(${margin.left}, ${margin.top})`);



    // x-axis
    const barNames = data.map(d => d.label);
    const xScale = scaleBand()
        .domain(barNames)
        .range([0, width - 40]) // should be `- yAxis.width`, but we don't know that yet.
        .padding(0.2);
    const xAxisGenerator = axisBottom(xScale);
    graph.append('g')
        .attr('class', 'xAxis')
        .call(xAxisGenerator);
    // rotating x-labels
    const maxLabelSize = barNames.reduce((c, n) => n.length > c ? n.length : c, 0) * letterSize;
    const tickSize = xAxisGenerator.tickSize();
    if (maxLabelSize > tickSize) {
        graph.select('.xAxis').selectAll('.tick').selectAll('text')
            .attr('text-anchor', 'start')
            .attr('transform', () => {
                const rotation = 45;
                const transform = `translate(${letterSize / 2}, ${letterSize / 2}) rotate(${rotation})`;
                return transform;
            })
    }
    const xAxis = graph.select<SVGGElement>('.xAxis');
    const xAxisSize = xAxis.node()!.getBBox();


    // y-axis
    let minVal = data.reduce((c, v) => Math.min(c, v.value), Infinity);
    let maxVal = data.reduce((c, v) => Math.max(c, v.value), -Infinity);
    minVal = Math.min(minVal, 0);
    maxVal = Math.max(maxVal, 0);
    const padding = 0.1 * (maxVal - minVal);
    const startVal = minVal === 0.0 ? minVal : minVal - padding;
    const endVal = maxVal + padding;
    const yScale = scaleLinear()
        .domain([startVal, endVal])
        .range([height - xAxisSize.height, 0]);
    const yAxisGenerator = axisLeft(yScale);
    graph.append('g')
        .attr('class', 'yAxis')
        .call(yAxisGenerator);
    const yAxis = graph.select<SVGGElement>('.yAxis');
    const yAxisSize = yAxis.node()!.getBBox();

    xAxis.attr('transform', `translate(${yAxisSize.width}, ${height - xAxisSize.height})`);
    yAxis.attr('transform', `translate(${yAxisSize.width}, 0)`);



    // center: actual plot without x- and y-axis
    const centerLeft = yAxisSize.width;
    const centerHeight = height - xAxisSize.height;
    const centerWidth = width - yAxisSize.width;
    const center = graph
        .append('g')
        .attr('class', 'center')
        .attr('transform', `translate(${centerLeft}, 0)`)
        .attr('width', centerWidth)
        .attr('height', centerHeight);


    // bars
    const bars = center.selectAll('.bar')
        .data(data)
        .enter()
        .append('g')
        .attr('class', 'bar')
        .attr('transform', (d: any) => `translate(${xScale(d.label)}, 0)`);

    // bars: append rect
    bars.append('rect')
        .attr('width', xScale.step())
        .attr('height', (d: Datum) => d.value < 0 ? yScale(d.value) - yScale(0) : yScale(0) - yScale(d.value))
        .attr('y', (d: Datum) => d.value > 0 ? yScale(d.value) : yScale(0))
        .attr('fill', (d: Datum) => {
            const v = gvColorScale(d.value, -2, 2);
            return `rgb(${v.r}, ${v.g}, ${v.b})`;
        });



    const hlineGroups = center.selectAll('.hline')
        .data(hlines)
        .enter()
        .append('g')
        .attr('class', 'hline')
        .attr('transform', (d: Datum) => `translate(0, ${yScale(d.value)})`);
    hlineGroups.append('line')
        .attr('stroke', 'grey')
        .attr('stroke-dasharray', 4)
        .attr('x1', centerLeft).attr('x2', centerLeft + centerWidth);
    hlineGroups.append('text')
        .attr('transform', d => `translate(${centerWidth - letterSize * (d.label.length + 1)}, -4)`)
        .text(d => d.label);


    // bars: hover-effect
    const maxWidthHoverText = 200;
    const infobox = base.append('div')
        .style('max-width', `${maxWidthHoverText}px`)
        .style('visibility', 'hidden')
        .style('position', 'absolute')
        .style('display', 'block')
        .style('z-index', 1000)
        .style("background-color", "white")
        .style("border", "solid")
        .style("border-width", "1px")
        .style("border-radius", "3px")
        .style('padding', '3px');
    const infoboxP = infobox.append('p');

    bars.on('mouseenter', (evt: any, datum: Datum) => {
        infobox.style('visibility', 'visible');
        const text = `${yLabel}: ${datum.value}`;
        infoboxP.html(text);
        const positionInsideSvg = pointer(evt, svg.node());  // doesn't seem to work in popup
        const positionInLayer = [evt.layerX, evt.layerY];    // doesn't seem to work in raw html
        let x = Math.min(positionInsideSvg[0], positionInLayer[0]);
        if (x > centerWidth / 2) {
            x -= maxWidthHoverText;
            x -= 20;  // safety-distance so popup doesn't touch mouse (which would trigger a `mouseout` event)
        } else {
            x += 20; // safety-distance so popup doesn't touch mouse (which would trigger a `mouseout` event)
        }
        const y = Math.min(positionInsideSvg[1], positionInLayer[1]);
        infobox
            .style('left', `${x}px`)
            .style('top', `${y}px`);

        const rgb = gvColorScale(datum.value, -2, 2);
        const fillColor = `rgb(${rgb.r}, ${rgb.g}, ${rgb.b})`;
        bars.select('rect').attr('fill', 'lightgray');
        select(evt.target).select('rect').attr('fill', fillColor);
        xAxis.selectAll('text').attr('color', 'lightgray');
        const n = xAxis.selectAll('text').nodes()!.find((n: any) => n.innerHTML === datum.label)!;
        select(n).attr('color', 'black');
    })
    .on('mouseleave', (evt: any, datum: Datum) => {
        infobox.style('visibility', 'hidden');
        bars.selectAll('rect').attr('fill', (d: any) => {
            const v = gvColorScale(d.value, -2, 2);
            return `rgb(${v.r}, ${v.g}, ${v.b})`;
        });
        xAxis.selectAll('text').attr('color', 'currentColor');
    });
}


export function barchart() {
    let _data: Datum[] = [];
    let _xlabel: string = "";
    let _ylabel: string = "";
    let _width = 300;
    let _height = 250;
    let _hlines: Datum[] = [];
    let _margin = { top: 10, right: 10, bottom: 30, left: 30 };
    let _container: HTMLDivElement = document.createElement('div');
    _container.setAttribute('width', `${_width}px`);
    _container.setAttribute('height', `${_height}px`);
    function bc() {
        makeBarchart(_container, _data, _xlabel, _ylabel, _width, _height, _hlines, _margin);
    }

    bc.data = (data: Datum[]) => {_data = data; return bc; }
    bc.xlabel = (xlabel: string) => {_xlabel = xlabel; return bc; }
    bc.ylabel = (ylabel: string) => {_ylabel = ylabel; return bc; }
    bc.width = (width: number) => {_width = width; return bc; }
    bc.height = (height: number) => {_height = height; return bc; }
    bc.hlines = (hlines: Datum[]) => {_hlines = hlines; return bc; }
    bc.margin = (margin: {top: number, bottom: number, left: number, right: number}) => {_margin = margin; return bc; }
    bc.container = (container: HTMLDivElement) => {
        _container = container;
        _width = container.clientWidth;
        _height = container.clientHeight;
        return bc;
    }
    
    return bc;
}


const ts: Datum[] = [{label: "a", value: 1}, {label: "b", value: 2}];
barchart().width(400).height(300).data(ts)();