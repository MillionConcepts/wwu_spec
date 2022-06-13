// lines themselves, i.e., scaled reflectance data

let lines = {};

// indicators as to line activity & status

let activeLines = {};

// line colors

let linePalette = [
    '#FF3500',
    '#FF8900',
    '#0CB0FF',
    '#00e102',
    '#FF00FF',
    '#1DCEA8',
    '#7847e7',
    '#ffb600',
    '#a54262',
    '#4df8ce',
];

let lineColors = {};

// size, margin, various ratios for page elements

let containerWidth = gid("graphJtron").offsetWidth;

const margin = {
    top: 20,
    right: 120,
    bottom: 50,
    left: 120,
}

const graphAspect = 0.5
const maxHeight = 475

let vh = Math.max(document.documentElement.clientHeight, window.innerHeight);
let vw = Math.max(document.documentElement.clientWidth, window.innerWidth);

let width = Math.floor(containerWidth) - margin.right;
let height = (
    Math.min(
        maxHeight, vw * graphAspect
    ) -
    margin.top - margin.bottom
);

// variables for range/domain of graph, along with desired max offset
let minX, minY, maxX, maxY, xOff, yOff

// x and y scales used to convert position of svg elements
// into position relative to graph data
// very important
let xScale = d3.scaleLinear();
let yScale = d3.scaleLinear();
// toggle between mouse zoom and widget zoom
// a fundamental design problem here, I think,
// is too many separate handlers
let activeXScale = xScale
let activeYScale = yScale

// slider widgets
const xSlider = gid('x-slider');
const ySlider = gid('y-slider');

// other widgets

const xAxis = d3.axisBottom(xScale).tickFormat(d3.format("d"));
const yAxis = d3.axisLeft(yScale);
let scaleWidgets = [];
const minXInput = gid('min-x-input');
const maxXInput = gid('max-x-input');
const minYInput = gid('min-y-input');
const maxYInput = gid('max-y-input');
const waveNormInput = gid('wavenormal-wavelength-input')

d3.select("#x-slider").style("width", width);
d3.select("#y-slider").style("height", height);

// maybe should be several separate functions
// sloppy signature because 'samples' can be the
// entire 'graph' context object or just the dict of line data
const updateGraphBounds = function (samples, useLines) {
    let graphXValues = [];
    let graphYValues = [];
    // are we setting graph bounds based on currently-rendered lines?
    if (useLines === true) {
        if (Object.values(activeLines).includes(true) === false) {
            return
        }
        Object.keys(samples).forEach(function (line) {
            if (activeLines[line] === true) {
                graphXValues.push(hStack(samples[line])[0])
                graphYValues.push(hStack(samples[line])[1])
            }
        })

        // or are we setting graph bounds simply based on the received data (as on page load)?

    } else {
        samples.forEach(function (sample) {
            graphXValues.push(Object.keys(sample['reflectance']))
            graphYValues.push(Object.values(sample['reflectance']))
        })
    }
    graphXValues = graphXValues[0]
        .map(Number)
        .concat.apply([], graphXValues)
    graphYValues = graphYValues[0]
        .map(Number)
        .concat.apply([], graphYValues)

    minX = Math.min.apply(null, graphXValues)
    maxX = Math.max.apply(null, graphXValues)
    minY = Math.min.apply(null, graphYValues)
    maxY = Math.max.apply(null, graphYValues)
    xOff = (maxX - minX) * .05
    yOff = (maxY - minY) * .05
    if (Object.values(xSlider.classList).includes("noUi-target")) {
        xSlider.noUiSlider.destroy()
        ySlider.noUiSlider.destroy()
        makeSliders()
    }
    maxXInput.setAttribute('max', maxX.toString())
    minXInput.setAttribute('max', (maxX - minX).toString())
    maxYInput.setAttribute('max', maxY.toString())
    minXInput.setAttribute('max', (maxX - minX).toString())
    maxXInput.setAttribute('min', "0")
    minXInput.setAttribute('min', minX.toString())
    maxYInput.setAttribute('min', "0")
    minXInput.setAttribute('min', minY.toString())
    waveNormInput.setAttribute('min', minX.toString())
    waveNormInput.setAttribute('max', maxX.toString())

};

// set bounds  ASAP on page load
updateGraphBounds(graph)

// utility function. converts N 2-item [string, number] arrays to
// 2 N-item [number, .... ] arrays
// similar to np.hstack
/**
 *
 * @param {Array.<Array.<string, number>>} line
 * @returns {[number[], number[]]}
 */
const hStack = function (line) {
    let waveArray = [];
    let reflArray = [];
    line.map(point => {
        waveArray.push(point[0])
        reflArray.push(point[1])
    })
    return [waveArray.map(Number), reflArray]
};

// Array.indexOf but with optional min/max constraints
const getIndex = function (array, target, constraints = null) {
    if (constraints != null) {
        array = array.slice(constraints[0], constraints[1])
    }
    let i = 0
    while (i < array.length) {
        if (array[i] === target) {
            return i
        }
        i++
    }
    return null
};


let yLabelOffset = -50
let xLabelOffset = 40

let normTextX = 0.02
let normTextY = 0.02
let calcTextX = 15
let calcTextY = 15


const makeSliders = function () {
    noUiSlider.create(xSlider, {
        start: [minX - xOff, maxX + xOff],
        behaviour: 'tap-drag',
        connect: true,
        range: {
            'min': minX - xOff,
            'max': maxX + xOff
        },
        margin: (maxX - minX) / 10,
        animate: false
    });
    noUiSlider.create(ySlider, {
        start: [minY - yOff, maxY + yOff],
        behaviour: 'tap-drag',
        orientation: 'vertical',
        connect: true,
        range: {
            'min': minY - yOff,
            'max': maxY + yOff
        },
        margin: (maxY - minY) / 10,
        animate: false,
        direction: 'rtl',
        format: wNumb({
            decimals: 4,
        })

    });
    xSlider.noUiSlider.on('slide', function () {
        updateWindow(
            parseFloat(this.get()[0]),
            parseFloat(this.get()[1]),
            activeYScale.domain()[1],
            activeYScale.domain()[0],
            xSlider
        )
    });

    ySlider.noUiSlider.on('slide', function () {
        updateWindow(
            activeXScale.domain()[0],
            activeXScale.domain()[1],
            parseFloat(this.get()[0]),
            parseFloat(this.get()[1]),
            ySlider
        )
    });
};

makeSliders()


// background svg container

const svg = d3.select(".chart-container").append("svg")
    .attr("width", width + margin.left + margin.right)
    .attr("height", height + margin.top + margin.bottom)
    .on("mouseleave", function () {
        pointerFocus.style("display", "none");
        trackingVertLine.style("display", "none")
    });

// chart area drawn in container

const chart = svg.append("g")
    .attr("transform", "translate(" + margin.left + "," + margin.top + ")");
let xScaleZoom = xScale;
let yScaleZoom = yScale;
let lastCaller;

const constrainZoom = function (zoom) {
    let xProportion = (maxX - minX) / (xScale.domain()[1] - xScale.domain()[0])
    let yProportion = (minY - maxY) / (yScale.domain()[1] - yScale.domain()[0])
    zoom.extent([[0, 0], [width, height]])
        .translateExtent([
            [width * -0.5 * xProportion, height * -0.5 * yProportion],
            [width * 1.5 * xProportion, height * 1.5 * yProportion]
        ])
        .scaleExtent([0.5 / (xProportion + yProportion), 20 * (xProportion + yProportion)])
}

// let lastCall = performance.now()
const zooming = function (event) {
    // console.log( performance.now() - lastCall)
    // lastCall = performance.now();
    if (lastCaller !== event.target) {
        constrainZoom(event.target)
    }
    xScaleZoom = event.transform.rescaleX(xScale);
    yScaleZoom = event.transform.rescaleY(yScale);
    updateWindow(
        xScaleZoom.domain()[0],
        xScaleZoom.domain()[1],
        yScaleZoom.domain()[1],
        yScaleZoom.domain()[0],
        mouseZoom
    )
}

let mouseZoom = d3.zoom()
chart.call(mouseZoom.on("zoom", zooming))

// mask that keeps points from appearing outside the chart
const clip = chart
    .append("defs")
    .append("svg:clipPath").attr("id", "clip")
    .append("svg:rect").attr("id", "clip-rect").attr("x", "0").attr("y", "0").attr("width", width).attr("height", height);

// elements within container
const chartBody = chart.append("g")
    .attr("clip-path", "url(#clip)");

const rect = chartBody.append('svg:rect')
    .attr("id", "rectangle")
    .attr("pointer-events", "all")
    .attr('width', width)
    .attr('height', height)
    .attr('fill', 'white');

// X Axis
const xSVG = chart.append("svg:g")
    .attr("class", "x axis")
    .attr("transform", "translate(0," + height + ")")
    .call(xAxis);

// Y Axis
const ySVG = chart.append("svg:g")
    .attr("class", "y axis")
    .call(yAxis);


// X Axis label
const xlabel = chart.append("text")
    .attr("class", "x label")
    .style("text-anchor", "end")
    .attr("x", width / 2 + margin.left)
    .attr("y", height + 50)
    .text("Wavelength (nm)")
    .style("font-size", "12pt");

// Y Axis label
const ylabel = chart.append("text")
    .attr("class", "y label")
    .style("text-anchor", "end")
    .attr("x", -height / 2 - margin.top + margin.bottom)
    .attr("y", -50)
    .attr("transform", "rotate(-90)")
    .text("Reflectance")
    .style("font-size", "12pt");

let rectBounds = [
    d3.select("#rectangle").node().width.animVal.value,
    d3.select("#rectangle").node().height.animVal.value
];

let trackingVertLine;
const pointerFocus = chart.append("g")
    .attr("class", "focus")
    .style("display", "null");

const makeTextDisplay = function (idRoot, attachmentPoint) {
    const display = attachmentPoint.append("foreignObject")
        .attr("id", idRoot + "-text-holder")
        .attr("class", "svg-text-holder")
    display.append("xhtml:div")
        .attr("id", idRoot + "-text-div")
        .attr("class", "svg-text-div")
    return display
}

const calcTextDisplay = makeTextDisplay('calc', chart)
const normTextDisplay = makeTextDisplay('norm', chart)
    .style("font-size", "22px")

let calcFoci = {};
let focusedLineID = 'none';
let activeFoci = [false, false, false]
let fociWavelengths = [null, null, null]

const createCalcFoci = function (line_id) {
    calcFoci[line_id] = {}
    for (const ix of Array(3).keys()) {
        calcFoci[line_id][ix] = chartBody.append("g")
            .attr("class", "focus")
            .attr("class", "calc-focus")
    }
}

//remove calc foci; clear calc text
const removeCalcFoci = function () {
    /**
     * @type: {}
     * this declaration is just to provide a type hint
     */
    let thisLine;
    for (thisLine of Object.values(calcFoci)) {
        for (let focus of Object.values(thisLine)) {
            focus.remove()
        }
    }
    calcFoci = {};
    activeFoci = [false, false, false];
    fociWavelengths = [null, null, null];
    d3.selectAll('.calc-content').remove()
}

const drawCalcFoci = function (focus_ix) {
    /**
     * @type: {}
     * this declaration is just to provide a type hint
     */
    let thisLine;
    for (thisLine of Object.values(calcFoci)) {
        if (focus_ix === 2) {
            thisLine[focus_ix].append("circle")
                .attr("r", 7)
                .attr("fill", "#cccccc")
                .attr("stroke-width", 3)
                .attr("stroke", "#1c2023")
        } else {
            thisLine[focus_ix].append("circle")
                .attr("r", 7)
                .attr("fill", "#ffffff")
                .attr("stroke-width", 3)
                .attr("stroke", "#1c2023");
        }
    }
}

const showCalcFoci = function (focusIx) {
    for (let thisLine of Object.entries(calcFoci)) {
        thisLine[1][focusIx].style("display", "block")

    }
}

const hideCalcFoci = function (focusIx) {
    for (let thisLine of Object.entries(calcFoci)) {
        thisLine[1][focusIx].style("display", "none")
    }
}


// vertical locator lines
// const vertPalette = [
//     '#d73fff', '#43ce8a', '#3d4911', '#ff7e7e',
//     '#8f8eac', '#3d728f', '#0021ff'
// ];
// const vertPaletteStart = Math.round((Math.random() * vertPalette.length - 1));
let vertCount = 0;
// commenting out all color stuff for now but we may want it back someday

// the line that follows the mouse

const drawVert = function (xPosition) {
    vertCount++
    // let activeColor = vertPalette[(vertCount + vertPaletteStart) % vertPalette.length];
    chart.append("line")
        .attr("x1", 0)
        .attr("y1", 0)
        .attr("x2", 0)
        .attr("y2", height)
        .attr("id", 'verticalLine' + vertCount)
        .attr('class', 'verticalLine')
        .attr('x-position', xPosition)
        .attr('transform', "translate(" + activeXScale(xPosition) + ",0)")
        .style("stroke-width", 2)
        .style("stroke", 'black')
        .style('opacity', 0.4)
        .style("fill", "none")
        .style("display", null);
};

drawVert(xScale.invert(0))
trackingVertLine = d3.select('line#verticalLine1');

const drawLocator = function (coord) {
    chart.append("text")
        .attr("color", '#1c2023')
        .attr("transform", "translate(" + activeXScale(coord[0]) + "," + activeYScale(coord[1]) + ")")
        .attr("dy", "2em")
        .attr("class", "locator")
        .attr("id", 'locator' + vertCount)
        .attr("x-position", coord[0])
        .attr("y-position", coord[1])
        .style("font-family", "Fira Mono")
        .style("font-size", "12px")
        .text(coord[0] + ', ' + coord[1].toFixed(3))
};


const eraseVerts = function () {
    d3.selectAll('.locator').remove()
    d3.selectAll('.verticalLine').remove()
    vertCount = 0
    drawVert(activeXScale.invert(0))
    trackingVertLine = d3.select('line#verticalLine1')
};


// erase every path associated with a line. use
// during redraws and such.
const eraseLine = function (lineID) {
    d3.select("#line" + lineID).remove()
    d3.select("#line" + lineID + "_r").remove()
    d3.select("#points" + lineID).remove()
    d3.select("#points" + lineID + "_r").remove()
};

// toggle whether or not to draw instrument / lab points / lines
let labLinesVisible = true
let instrumentLinesVisible = false
let labPointsVisible = false
let instrumentPointsVisible = false

// further functions for restricting interaction based on visibility
const isLabVisible = function () {
    return labLinesVisible || labPointsVisible
}

const isInstrumentVisible = function () {
    return instrumentLinesVisible || instrumentPointsVisible
}

const areLinesVisible = function () {
    return instrumentLinesVisible || labLinesVisible
}


// function that's called to initially graph spectra (not to scale them, that's in zoomGraphElements)
// decides whether to draw points or lines or neither. also removes as appropriate.
const drawLine = function (lineID) {
    const line = lines[lineID];
    const instrumentLine = lines[lineID + "_r"]
    if (labLinesVisible) {
        chartBody.append('svg:path')
            .attr('d', scaleLine(line))
            .attr('class', 'lab-line')
            .attr('stroke', lineColors[lineID])
            .attr('stroke-width', 2)
            .attr('id', 'line' + lineID)
            .style("fill", "none")
            .style("opacity", 0.8)
            .attr('fill', 'none')
    }
    if (instrumentLinesVisible) {
        chartBody.append('svg:path')
            .attr('d', scaleLine(instrumentLine))
            .attr('class', 'instrument-line')
            .attr('stroke', lineColors[lineID + "_r"])
            .attr('stroke-width', 3)
            .attr('id', 'line' + lineID + "_r")
            .attr("fill", "none")
            .style("stroke-dasharray", ("3, 3"))
    }
    if (labPointsVisible) {
        chartBody.append('svg:path')
            .attr('d', tickMark(line))
            .attr('stroke', lineColors[lineID])
            .attr('stroke-width', 5)
            .attr('stroke-linecap', 'round')
            .attr('class', 'lab-point')
            .attr('id', 'points' + lineID)
            .style("fill", "none")
            .attr('fill', 'none')
            .style("opacity", 0.6)
    }
    if (instrumentPointsVisible) {
        chartBody.append('svg:path')
            .attr('d', tickMark(instrumentLine))
            .attr('stroke', lineColors[lineID + "_r"])
            .attr('stroke-width', 9)
            .attr('class', 'instrument-point')
            .attr('stroke-linecap', 'square')
            .attr('id', 'points' + lineID + "_r")
            .style("fill", "none")
            .attr('fill', 'none')
            .style("opacity", 0.95)
    }
}

let normalized = false;
let waveNormalized = false;
let normWavelength = null;

const pickLineColor = function (sampleID) {
    const colorSpin = Math.round((Math.random() * (linePalette.length - 1)));
    let activeColor = linePalette[colorSpin];
    linePalette.splice(colorSpin, 1)
    if (activeColor === 'undefined') {
        activeColor = "#000000"
    }
    lineColors[sampleID] = activeColor
    //make the rover color complementary
    const roverColor = tinycolor(activeColor);
    if (roverColor.isDark()) {
        roverColor.lighten(25)
    }
    roverColor.spin(180)

    lineColors[sampleID + '_r'] = roverColor.toHexString()
    gid('rect-' + sampleID).style.backgroundColor = activeColor
}

let firstMaxWave;
const findAutoNormWavelength = function () {
    let firstSample = hStack(Object.entries(graph[0]['reflectance']))
    let firstMaxReflectance = Math.max.apply(null, firstSample[1])
    firstMaxWave = firstSample[0][firstSample[1].indexOf(firstMaxReflectance)]
}
findAutoNormWavelength()

const applyNormOffset = function (reflectanceKV, offset, scale) {
    // look at key-value pairs from samples, scale and offset as appropriate
    if (scale !== 1) {
        Object.keys(reflectanceKV).forEach(function (i) {
            reflectanceKV[i][1] *= scale
        })
    }
    if (offset !== 0) {
        Object.keys(reflectanceKV).forEach(function (i) {
            reflectanceKV[i][1] += offset
        })
    }
    return reflectanceKV
}

const generateLine = function (sample) {
    // go over both lab and instrument line associated
    // with a particular sample, make sure they're in order,
    // and trigger draws as necessary.

    // make sure a color is defined for the line.
    // usually this will happen on page load.
    if (!Object.keys(lineColors).includes(sample.id.toString())) {
        pickLineColor(sample.id)
    }
    const active = activeLines[sample.id];

    // decline to do anything at all if the spectrum isn't active,
    // and indeed ensure the line is erased
    if (!active) {
        eraseLine(sample.id)
        eraseLine(sample.id + '_r')
        return;
    }
    let filterSet = filterPicker.value
    let labReflectance = Object.entries(sample["reflectance"])
    let instReflectance = Object.entries(sample[filterSet])
    const offset = parseFloat(
        gid('offset-dialog' + sample.id).value
    )
    let scale = 1
    if (normalized) {
        scale = normLineToWavelength(labReflectance, firstMaxWave)
    } else if (waveNormalized && (normWavelength != null)) {
        scale = normLineToWavelength(labReflectance, normWavelength)
    }
    lines[sample.id] = applyNormOffset(
        labReflectance, offset, scale
    )
    lines[sample.id + '_r'] = applyNormOffset(
        instReflectance, offset, scale
    )
    drawLine(sample.id)
    updateGraphBounds(lines, true)
};


const makeNormText = function () {
    const normDiv = d3.select('#norm-text-div')
    if (normalized) {
        normDiv.append("p")
            .attr('class', 'svg-text-content norm-content')
            .html("normalized to 1.0 @ " + firstMaxWave + "nm")
    } else if (waveNormalized && !(normWavelength === null)) {
        normDiv.append("p")
            .attr('class', 'svg-text-content norm-content')
            .html("normalized to 1.0 @" + normWavelength + "nm")
    } else {
        d3.selectAll('.norm-content').remove()
    }

}

const deWaveNormalize = function () {
    waveNormalized = false
    gid('wavenormal-switch').checked = false
    // gid("arm-div").style.display = "none"
    makeNormText()
    removeCalcFoci()
    resetZoom()
};

const deNormalize = function () {
    normalized = false
    gid('normal-switch').checked = false
    makeNormText()
    removeCalcFoci()
    resetZoom()
};


//Toggle the line based on the checkbox
const toggleSpectrum = function (boxID, index) {
    activeLines[boxID.id.slice(6)] = !!boxID.checked
    activeLines[boxID.id.slice(6) + "_r"] = !!boxID.checked
    // deWaveNormalize()
    // deNormalize()
    generateLine(graph[index])
};

const filterPicker = gid('filter-picker');

filterPicker.addEventListener('change', function () {
    graph.forEach(function (sample) {
            eraseLine(sample.id)
            eraseLine(sample.id + '_r')
            generateLine(sample)
        })
    },
    {passive: true}
)

const updateDataVisibility = function () {
    labPointsVisible = gid('point-switch').checked
    instrumentPointsVisible = gid('instrument-point-switch').checked
    labLinesVisible = gid('line-switch').checked
    instrumentLinesVisible = gid('instrument-line-switch').checked
    for (let sample of Object.values(graph)) {
        // always erasing everything is lazy but i think loses
        // us almost nothing in performance and gains us a
        // great deal of fault-tolerance
        eraseLine(sample.id)
        generateLine(sample)
    }
    if (gid('calc-all-switch').checked) {
        updateMaxCalc()
    }
    // set hidden inputs used to control which simulated values are included in exported csv
    if (instrumentPointsVisible || instrumentLinesVisible) {
        gid('do-we-export-sim').value = 'True'
    }
    else {
        gid('do-we-export-sim').value = 'False'
    }
    gid('sim-instrument-for-export').value = filterPicker.value
    redraw();
}

/**
 *
 * @param lineID {string}
 * @returns {boolean}
 */
const isLineClickable = function (lineID) {
    if (!activeLines[lineID]) {
        return false;
    }
    if (lineID.endsWith('_r') && !isInstrumentVisible()) {
        return false;
    }
    return lineID.endsWith('_r') || isLabVisible();
}


const calcSlope = function (calcFocusEntry) {
    const x1 = calcFocusEntry[1][0].coord[0];
    const y1 = calcFocusEntry[1][0].coord[1];
    const x2 = calcFocusEntry[1][1].coord[0];
    const y2 = calcFocusEntry[1][1].coord[1];
    const slope = (y2 - y1) / (x2 - x1);
    return slope.toExponential(3)
};

const simpleBandDepthCustom = function (calcFocusEntry) {
    const x1 = calcFocusEntry[1][0].coord[0];
    const y1 = calcFocusEntry[1][0].coord[1];
    const x2 = calcFocusEntry[1][1].coord[0];
    const y2 = calcFocusEntry[1][1].coord[1];
    const x3 = calcFocusEntry[1][2].coord[0];
    const y3 = calcFocusEntry[1][2].coord[1];

    // literally just draw a triangle
    const continuumSlope = (y2 - y1) / (x2 - x1);
    const flatLength = (x3 - x1);
    const continuumReflectance = y1 + continuumSlope * flatLength;
    return (1 - y3 / continuumReflectance).toFixed(3)
};

const calcRatio = function (calcFocusEntry) {
    const y1 = calcFocusEntry[1][0].coord[1];
    const y2 = calcFocusEntry[1][1].coord[1];
    if (y1 < y2) {
        return (y1 / y2).toFixed(3)
    } else {
        return (y2 / y1).toFixed(3)
    }
};

// this potentially gives unwanted results if there are multiple minima (with the same value) in the selected range. not sure about the desired behavior in those cases.
const simpleBandDepthMin = function (calcFocusEntry) {
    let lineID = calcFocusEntry[0]
    // we are only using two of them but there _are_ three potentially
    let fociTrio = calcFocusEntry[1]
    let [xLine, yLine] = hStack(lines[lineID])

    // find minimum reflectance in the selected region

    let indexOne = interpWavelength(
        fociTrio[0].coord[0],
        xLine
    )
    let indexTwo = interpWavelength(
        fociTrio[1].coord[0],
        xLine
    )
    let indices
    if (indexOne > indexTwo) {
        indices = [indexTwo, indexOne]
    } else {
        indices = [indexOne, indexTwo]
    }

    // literally just draw a triangle
    // we do not compound interpolation issues
    // because projection of continuum
    // onto reflectance curve occurs exactly at a sample

    const localMinReflectance = Math.min.apply(null, yLine.slice(indices[0] + 1, indices[1]));
    let minIndex = getIndex(yLine, localMinReflectance, indices);

    minIndex = minIndex + indices[0]

    const x1 = fociTrio[0].coord[0];
    const y1 = fociTrio[0].coord[1];
    const x2 = fociTrio[1].coord[0];
    const y2 = fociTrio[1].coord[1];
    const x3 = xLine[minIndex];

    const continuumSlope = (y2 - y1) / (x2 - x1);
    const flatLength = (x3 - x1);

    const continuumReflectance = y1 + continuumSlope * flatLength;

    // the second element of the returned array
    // is simply coordinates for placing calcFocus.third

    return [
        (1 - (localMinReflectance / continuumReflectance))
            .toFixed(3)
        + " @ " + x3.toFixed(0) + "nm",
        [xLine[minIndex], yLine[minIndex]]
    ]
};


const shouldNotBeCalculated = function (thing) {
    if (thing === undefined) {
        return true
    }
    return thing.filter(isNaN).length > 0;
}

// set a new focused line and create calcFoci for one or all lines as appropriate
const setCalcFoci = function (newLineID) {
    const calcAll = gid('calc-all-switch').checked
    // handle single-spectra-calculations cases
    if (!calcAll) {
        if ((focusedLineID !== 'none') && (newLineID !== focusedLineID)) {
            // refuse to set calculation focus on separate spectrum
            return null;
        }
        focusedLineID = newLineID
        if (Object.keys(calcFoci).length === 0) {
            createCalcFoci(newLineID)
        }
        return focusedLineID;
    }

    // handle all-spectra-calculations cases
    if ((Object.keys(calcFoci).length !== 0) && (focusedLineID === "none")) {
        return newLineID
    }
    if ((Object.keys(calcFoci).length !== 0) && (focusedLineID !== "none")) {
        // make matching calcFoci for all lines if a focus is
        // already set, draw them, and bug out
        for (let otherLineID of Object.keys(lines)) {
            if (otherLineID === focusedLineID) {
                continue;
            }
            if (!isLineClickable(otherLineID)) {
                continue;
            }
            createCalcFoci(otherLineID)
        }
        for (const entry of Object.entries(calcFoci[focusedLineID])) {
            let focusIx = entry[0]
            let focus = entry[1]
            if (shouldNotBeCalculated(focus.coord)) {
                continue
            }
            moveCalcFoci(focusIx, focus.coord[0])
            drawCalcFoci(focusIx)
        }
        focusedLineID = "none";
        return newLineID;
    }
    // or if no calc foci are presently created and 'calculate all' is checked:
    for (let lineID of Object.keys(lines)) {
        if (!isLineClickable(lineID)) {
            continue;
        }
        createCalcFoci(lineID)
    }
    focusedLineID = "none";
    return newLineID;
}


// move just a single calcFocus
const moveCalcFocus = function (lineID, focusIx, wavelength) {
    /**
     * @type: {}
     * this declaration is just to provide a type hint
     */
    let focus = calcFoci[lineID][focusIx]
    let interpolatedReflectance = interpRefAtWavelength(lines[lineID], wavelength)
    if (interpolatedReflectance === "out of bounds") {
        focus.coord = [NaN, NaN];
        focus.style("display", "none")
    } else {
        focus.coord = [wavelength, interpolatedReflectance]
        focus.attr(
            "transform",
            "translate(" + activeXScale(focus.coord[0]) + "," + activeYScale(focus.coord[1]) + ")"
        )
    }
}

// move all calcFoci of an individual index
const moveCalcFoci = function (focusIx, wavelength) {
    for (let lineID of Object.keys(calcFoci)) {
        moveCalcFocus(lineID, focusIx, wavelength)
    }
}


const getMaxFoci = function () {
    let maxFoci;
    if (gid('band-custom-calc').checked) {
        maxFoci = 2
    } else {
        maxFoci = 1
    }
    return maxFoci
}

// functions called when you switch calc functions, etc.

const updateMaxCalc = function () {
    if (!gid('calc-all-switch').checked) {
        removeCalcFoci();
        return;
    }
    setCalcFoci(-1);
    let maxFoci = getMaxFoci()
    if (activeFoci[maxFoci] === true) {
        triggerCalculations();
    }
}

const updateCalc = function (thing) {
    if (thing.id.startsWith('band-')) {
        showCalcFoci(0)
        showCalcFoci(1)
        showCalcFoci(2)
    } else if (thing.id === 'no-calc') {
        hideCalcFoci(0)
        hideCalcFoci(1)
        hideCalcFoci(2)
    } else {
        showCalcFoci(0)
        showCalcFoci(1)
        hideCalcFoci(2)
    }
    let maxFoci = getMaxFoci()
    if (activeFoci[maxFoci] === true) {
        triggerCalculations();
    }
}

// function called when you click on the graph with the calculator active
const stepCalcFoci = function (wavelength, line) {
    // ignore input if calculator is off
    if (gid('no-calc').checked) {
        return;
    }
    // check to see if all the foci are in place; if so,
    // clear them
    let maxFoci = getMaxFoci()
    if (activeFoci[maxFoci] === true) {
        focusedLineID = 'none';
        removeCalcFoci();
        return;
    }
    let setter = setCalcFoci(line)
    // refuse to move anything if the wrong line
    // is clicked
    if (setter === null) {
        return;
    }
    let focusIx = null
    // render the next set of foci
    if (!(activeFoci.includes(true))) {
        focusIx = 0
    } else if (!activeFoci[1]) {
        focusIx = 1
    } else if (!(activeFoci[2]) && (maxFoci === 2)) {
        focusIx = 2
    }
    if (focusIx !== null) {
        moveCalcFoci(focusIx, wavelength)
        activeFoci[focusIx] = true
        drawCalcFoci(focusIx)
        fociWavelengths[focusIx] = wavelength
    }
    // do calculations if we have all the sets of foci
    if (activeFoci[maxFoci] === false) {
        // NOTE: this may be overkill. evaluate.
        d3.selectAll('.calc-content').remove()
        renderCalcFocusText()
        return;
    }
    triggerCalculations();
}

let calcResults = {}

// TODO: cruft?
const getSampleName = function (sampleID) {
    let sampleName
    for (let sample of Object.values(graph)) {
        if (!sampleID.startsWith(sample.id.toString())) {
            continue;
        }
        sampleName = sample['sample_name']
    }
    if (sampleID.endsWith('_r')) {
        let instrumentName = " (" + filterPicker.value + ")";
        sampleName += instrumentName
    }
    return sampleName

}

const resizeCalcText = function () {
    d3.selectAll('.calc-content')
        .style(
            'font-size',
            Math.max(rect.attr('height') / 18, 17)
        )
        .style(
            'line-height',
            Math.max(rect.attr('height') / 300, 1.1)
        )
}


//TODO: determine what actual desired behavior for handedness is
const renderCalcFocusText = function () {
    const ctDiv = d3.select('#calc-text-div')
    // this shouldn't be getting called in this case,
    // but just gracefully ignore it
    if (fociWavelengths[0] === null) {
        return
    }
    let minWave, maxWave
    if (fociWavelengths[1] === null) {
        minWave = fociWavelengths[0]
        maxWave = null
    } else {
        minWave = fociWavelengths[0]
        maxWave = fociWavelengths[1]
    }
    ctDiv.append("p")
        .attr('class', 'svg-text-content calc-content')
        .html("L shoulder: " + minWave + "nm")
    if (maxWave !== null) {
        ctDiv.append("p")
            .attr('class', 'svg-text-content calc-content')
            .html("R shoulder: " + maxWave + "nm")
    }
    resizeCalcText()
}

const makeCalcText = function () {
    const results = Object.entries(calcResults)
    const ctDiv = d3.select('#calc-text-div')
    let trailingText = ": "
    // TODO: again, this could probably use error-checking
    if (results[0][1][1] === "band depth @") {
        trailingText = " " + fociWavelengths[2] + "nm: "
    }
    if (results.length > 3) {
        trailingText += "<br>"
    }
    const resultLine = ctDiv.append("p")
        .attr('class', 'svg-text-content calc-content')
        .html("<br>" + results[0][1][1] + trailingText)
    for (const entry of results) {
        const lineColor = lineColors[entry[0]]
        const result = entry[1][0]
        resultLine.append("span")
            .attr('class', 'svg-text-content calc-content')
            .style('color', lineColor)
            .html(result + " ")
    }
    resizeCalcText()
}


// read state from all calcFoci sets and generate appropriate calc results
const triggerCalculations = function () {
    // just gracefully-ish return nothing if we're in some weird
    // DOM state
    let calcFunction = function (anything) {
    }
    let result, calcType;
    if (gid('slope-calc').checked) {
        calcFunction = calcSlope
        calcType = "slope"
    } else if (gid('band-min-calc').checked) {
        calcFunction = simpleBandDepthMin
        calcType = "band depth"
    }
    if (gid('band-custom-calc').checked) {
        calcFunction = simpleBandDepthCustom
        calcType = "band depth @"
    }
    if (gid('ratio-calc').checked) {
        calcFunction = calcRatio
        calcType = "ratio"
    }
    calcResults = {}
    for (let entry of Object.entries(calcFoci)) {
        let stopCalc = false
        let lineFoci = entry[1]
        if (shouldNotBeCalculated(lineFoci[0].coord)) {
            stopCalc = true
        }
        if (shouldNotBeCalculated(lineFoci[1].coord)) {
            stopCalc = true
        }
        if (stopCalc) {
            continue
        }
        if (calcFunction === simpleBandDepthMin) {
            let response = calcFunction(entry)
            result = response[0]
            if (!(response[1][0] === undefined)) {
                moveCalcFocus(entry[0], 2, response[1][0])
                drawCalcFoci(2)
            }
        } else {
            result = calcFunction(entry);
        }
        calcResults[entry[0]] = [result, calcType]
    }
    d3.selectAll('.calc-content').remove()
    renderCalcFocusText()
    makeCalcText()
}

//TODO: maybe yuck? rewrite?
const findClosestPoint = function (line, mouseX) {
    let min = 0;
    let max = line.length;
    let mid = Math.floor((max + min) / 2);
    let nearestX = line[mid][0];
    let nearestY = line[mid][1];
    let dx = Math.abs(mouseX - nearestX);
    let diff = dx;
    let index = mid;
    do {
        if (line[mid][0] > mouseX) {
            max = mid;
        } else {
            min = mid;
        }

        mid = Math.floor((max + min) / 2);
        diff = (Math.abs(line[mid][0] - mouseX));
        if (diff <= dx) {
            dx = diff;
            nearestX = line[mid][0];
            nearestY = line[mid][1];
            index = mid
        }
    } while (diff !== 0 && (max - min) > 1)
    return [parseFloat(nearestX), nearestY, index];
};

const l2Norm = function (x1, y1, x2, y2) {
    return Math.sqrt(Math.pow((x1 - x2), 2) + Math.pow((y1 - y2), 2));
};

//Given a line, find the closest x point to your mouse
//and return the x,y coordinate
const findClosestLinePoint = function (lineObject, mouseX, mouseY) {
    let closestDistance = Number.MAX_VALUE;
    let closestLineID, closestPoint;
    for (let lineID of Object.keys((lineObject))) {
        if (!isLineClickable(lineID)) {
            continue;
        }
        const point = findClosestPoint(lineObject[lineID], mouseX);
        const visibleDistance = l2Norm(
            activeXScale(mouseX), activeYScale(mouseY),
            activeXScale(point[0]), activeYScale(point[1])
        );
        if (visibleDistance < closestDistance) {
            closestPoint = point;
            closestDistance = visibleDistance;
            closestLineID = lineID
        }
    }
    return [closestPoint, closestLineID];
};

// all the primary mouse interactions are in this block
chartBody.on("click", function (event) {
    let mouseX = activeXScale.invert(d3.pointer(event, this)[0]);
    let mouseY = activeYScale.invert(d3.pointer(event, this)[1]);
    let closest = findClosestLinePoint(lines, mouseX, mouseY);
    let line = closest[1];
    let coord = closest[0];
    stepCalcFoci(coord[0], line)
    if (gid("drop-switch").checked) {
        drawVert(coord[0]);
        drawLocator(coord);
    }
})
    .on("mousemove", function (event) {
        let mouseX = activeXScale.invert(d3.pointer(event, this)[0])
        let mouseY = activeYScale.invert(d3.pointer(event, this)[1])
        let closest = findClosestLinePoint(lines, mouseX, mouseY);
        let coord = closest[0];
        pointerFocus.attr("transform", "translate(" + activeXScale(coord[0]) +
            "," + activeYScale(coord[1]) + ")");

        pointerFocus.select("text")
            .text(Math.round(coord[0]) + ", " + parseFloat(coord[1]).toFixed(3));
        trackingVertLine.attr("x1", activeXScale(coord[0]))
            .attr("x2", activeXScale(coord[0]));

        pointerFocus.style("display", null);
        if (gid('vertical-line-switch').checked) {
            trackingVertLine.style("display", null);
        }
    })

// Function for drawing tick marks
// the shape is now all controlled by the stroke-linecap
// property set in drawLine()
const tickMark = function (d) {
    const pathArray = [];
    for (let i = 0; i < d.length; i++) {
        const x = activeXScale(d[i][0]);
        const y = activeYScale(d[i][1]);
        pathArray.push([
            "M", [x, y],
            "L", [x, y],
            "Z"
        ].join(" "));
    }
    return pathArray.join(" ");
}


// scaling function for reflectance values

const scaleLine = d3.line()
    .x(function (dataPoint) {
        return activeXScale(dataPoint[0]);
    })
    .y(function (dataPoint) {
        return activeYScale(dataPoint[1]);
    })

pointerFocus.append("circle")
    .attr("r", 5)
    .attr("fill", "none")
    .attr("stroke-width", 1.5)
    .attr("stroke", "#667986");

pointerFocus.append("text")
    .attr("opacity", 1)
    .attr("color", '#1c2023')
    .attr("dx", 8)
    .attr("dy", "2em")
    .style("font-family", "Fira Mono")
    .style("font-size", "12px");


const normalizeSpectra = function () {
    if (normalized) {
        normalized = false
    } else {
        deWaveNormalize()
        normalized = true
    }
    graph.forEach(function (sample) {
        eraseLine(sample.id)
        eraseLine(sample.id + '_r')
        generateLine(sample)
    })
    makeNormText()
    removeCalcFoci()
    resetZoom()
};

const waveNormalizeSpectra = function () {
    let swap = false;
    if (waveNormalized) {
        deWaveNormalize()
    } else {
        deNormalize()
        waveNormalized = true
        swap = true
        // gid("arm-div").style.display = "block"
    }
    if (normWavelength || swap) {
        graph.forEach(function (sample) {
            eraseLine(sample.id)
            eraseLine(sample.id + "_r")
            generateLine(sample)
        })
    }
    makeNormText()
    removeCalcFoci()
    resetZoom()
};

// right-hand nearest-neighbor 1D interpolation, sort of.
// returns index of nearest neighbor.
const interpWavelength = function (wavelength, waveArray) {
    // check to see if the exact frequency bin is in the array
    let waveIndex = 0
    const bin = waveArray.indexOf(wavelength);
    if (bin !== -1) {
        return bin
    }
    let rightHand = null;
    let leftHand = null;
    while (rightHand - wavelength <= 0) {
        leftHand = rightHand
        rightHand = waveArray[waveIndex]
        waveIndex++
    }
    // waveIndex gets incremented an extra time at end so step back 1
    waveIndex -= 1
    return waveIndex
}

const interpRefAtWavelength = function (reflectanceKV, wavelength) {
    const checkArray = hStack(reflectanceKV)

    // don't try any funny business with scaling nonexistent wavelengths
    const outOfBounds = (Math.max.apply(null, checkArray[0]) < wavelength)
        | (Math.min.apply(null, checkArray[0]) > wavelength);
    if (outOfBounds) {
        return "out of bounds"
    }

    let waveIndex = interpWavelength(wavelength, checkArray[0])
    if (waveIndex === 0) {
        return checkArray[1][0]
    }
    let rightHand = checkArray[0][waveIndex]
    let leftHand = checkArray[0][waveIndex - 1]
    // note that leftHand is always one index back from rightHand.
    // this is just a simpleminded linear interpolation.
    // reflectance is always positive.
    const leftWeight = Math.abs(rightHand - wavelength) / Math.abs(rightHand - leftHand);
    const rightWeight = 1 - leftWeight;
    return checkArray[1][waveIndex] * rightWeight + checkArray[1][waveIndex - 1] * leftWeight;
}

const normLineToWavelength = function (reflectanceKV, wavelength) {
    let interpolatedReflectance = interpRefAtWavelength(reflectanceKV, wavelength)
    if (interpolatedReflectance === "out of bounds") {
        let differences = hStack(reflectanceKV)[0].map(
            function (number) {
                return Math.abs(number - wavelength)
            }
        )
        let closestWave = Math.min(...differences)
        interpolatedReflectance = reflectanceKV[differences.indexOf(closestWave)][1]
    }
    return 1 / interpolatedReflectance
};

// keep track of who called an update last --
// this is so we can reset the mouseZoom transform
// _just once_ during any set of widget operations
// (not sure why it chugs so much but it does, maybe
// selections propagate downward or something)

const updateWindow = function (updateMinX, updateMaxX, updateMinY, updateMaxY, caller) {

    updateMinY = Math.max(0, updateMinY)
    updateMinX = Math.max(0, updateMinX)

    if (caller === "redraw") {
    } else if (caller !== mouseZoom) {
        xScale.domain([updateMinX, updateMaxX]);
        yScale.domain([updateMaxY, updateMinY]);
        xScaleZoom = xScale;
        yScaleZoom = yScale;
        activeXScale = xScale;
        activeYScale = yScale;
        // in some cases we might use the pattern:
        // chart.call(mouseZoom.transform, d3.zoomIdentity)
        // for some reason this incurs a whole bunch of overhead
        // -- perhaps because we are usually rendering > 10k vertices?
        // -- or maybe just interrupts the beginning of our scroll?
        // either way it is absolutely not worth it when we are just using
        // that property as a container -- i.e., it is exactly the ability
        // of d3.zoom to set that property with low overhead that we like!
        // so we just set the private property directly
        if (lastCaller === mouseZoom) {
            chart.node().__zoom = d3.zoomIdentity
        }
    } else {
        activeXScale = xScaleZoom;
        activeYScale = yScaleZoom;
        if (lastCaller !== mouseZoom) {
            constrainZoom(mouseZoom)
        }
    }

    scaleWidgets = [minXInput, maxXInput, minYInput, maxYInput, ySlider, xSlider, mouseZoom]
    for (const item of scaleWidgets) {
        if (item !== caller) { // let no cat chase its own tail
            if (item === minXInput) {
                minXInput.value = updateMinX.toFixed(0);
            }
            if (item === maxXInput) {
                maxXInput.value = updateMaxX.toFixed(0)
            }
            if (item === minYInput) {
                minYInput.value = updateMinY.toFixed(2)
            }
            if (item === maxYInput) {
                maxYInput.value = updateMaxY.toFixed(2)
            }
            if (item === ySlider) {
                ySlider.noUiSlider.set([updateMinY, updateMaxY])
            }
            if (item === xSlider) {
                xSlider.noUiSlider.set([updateMinX, updateMaxX])
            }
        }
    }
    lastCaller = caller;
    zoomGraphElements();
}


const zoomAxes = function () {
    chart.select(".x.axis").call(xAxis.scale(activeXScale));
    chart.select(".y.axis").call(yAxis.scale(activeYScale));
}

const zoomSpectra = function () {
    for (const sample of graph) {
        const lineID = sample.id
        const active = activeLines[sample.id]
        if (!active) {
            continue;
        }
        const line = lines[lineID];
        const instrumentLine = lines[lineID + "_r"]
        if (labLinesVisible) {
            d3.select("#line" + lineID)
                .attr('d', scaleLine(line));
        }
        if (instrumentLinesVisible) {
            d3.select("#line" + lineID + "_r")
                .attr('d', scaleLine(instrumentLine));
        }
        if (labPointsVisible) {
            d3.select("#points" + lineID)
                .attr('d', tickMark(line));
        }
        if (instrumentPointsVisible) {
            d3.select("#points" + lineID + "_r")
                .attr('d', tickMark(instrumentLine));
        }
    }
}

const zoomVerts = function () {
    for (const item of d3.selectAll('.verticalLine').nodes()) {
        const line = d3.select(item)
        if (line.attr("id") !== trackingVertLine.attr("id")) {
            line.attr(
                "transform",
                "translate(" +
                activeXScale(line.attr("x-position"))
                + ",0)"
            )
        }
    }
}

const zoomLocators = function () {
    for (const item of d3.selectAll('.locator').nodes()) {
        locator = d3.select(item)
        locator.attr("transform",
            "translate(" +
            activeXScale(locator.attr("x-position")) +
            "," +
            activeYScale(locator.attr("y-position")) +
            ")")
    }
}

const zoomCalcFoci = function () {
    /**
     * @type: {}
     * this declaration is just to provide a type hint
     */
    let thisLine;
    for (thisLine of Object.values(calcFoci)) {
        for (let focus of Object.values(thisLine)) {
            if (shouldNotBeCalculated(focus.coord)) {
                continue;
            }
            focus.attr(
                "transform",
                "translate(" + activeXScale(focus.coord[0])
                + "," + activeYScale(focus.coord[1]) + ")");
        }
    }
}

function zoomGraphElements() {
    pointerFocus.style("display", "none");
    trackingVertLine.style("display", "none")
    zoomAxes();
    zoomSpectra();
    zoomVerts();
    zoomLocators();
    zoomCalcFoci();
}


// add zooming functionality for range / domain widgets

minXInput.addEventListener(
    'change',
    function () {
        updateWindow(
            parseFloat(this.value),
            xScale.domain()[1],
            yScale.domain()[1],
            yScale.domain()[0],
            minXInput
        )
    },
    {passive: true}
)

maxXInput.addEventListener('change', function () {
        updateWindow(
            xScale.domain()[0],
            parseFloat(this.value),
            yScale.domain()[1],
            yScale.domain()[0],
            maxXInput
        )
    },
    {passive: true}
);

minYInput.addEventListener('change', function () {
        updateWindow(
            xScale.domain()[0],
            xScale.domain()[1],
            parseFloat(this.value),
            yScale.domain()[0],
            minYInput
        )
    },
    {passive: true}
);

maxYInput.addEventListener('change', function () {
        updateWindow(
            xScale.domain()[0],
            xScale.domain()[1],
            yScale.domain()[1],
            parseFloat(this.value),
            maxYInput)
    },
    {passive: true}
);


const resetZoom = function () {
    updateWindow(
        minX - xOff,
        maxX + xOff,
        minY - yOff,
        maxY + yOff)
};


const makeOffsetListeners = function () {
    graph.forEach(function (sample) {
            const offsetDialog = gid('offset-dialog' + sample.id);
            offsetDialog.addEventListener(
                'change',
                function () {
                    eraseLine(sample.id)
                    generateLine(sample)
                })
        },
        {passive: true}
    )
};

makeOffsetListeners()

// normalizer
waveNormInput.addEventListener(
    'change',
    function () {
        normWavelength = this.value;
        graph.forEach(function (sample) {
            eraseLine(sample.id)
            eraseLine(sample.id + "_r")
            generateLine(sample)
        })
        makeNormText()
        resetZoom()
    },
    {passive: true}
)


let shrink = 1;

const shrinkGraph = function () {
    if (shrink === 1) {
        shrink = 2
        gid("shrink-button").innerHTML = "Grow Graph"
    } else {
        shrink = 1
        gid("shrink-button").innerHTML = "Shrink Graph"
    }
    redraw()
};

function redraw() {
    vh = Math.max(document.documentElement.clientHeight, window.innerHeight)
    vw = Math.max(document.documentElement.clientWidth, window.innerWidth)
    containerWidth = gid("graphJtron").offsetWidth;
    width = Math.floor(containerWidth) - margin.right;
    height = (
        Math.min(
            maxHeight, vw * graphAspect
        ) -
        margin.top - margin.bottom
    )
    height = height / shrink
    svg.attr("width", width + margin.left).attr("height", height + margin.top + margin.bottom)
    chart.attr("width", width).attr("height", height).attr("transform", "translate(" + margin.left + "," + margin.top + ")");
    rect.attr("width", width).attr("height", height);
    clip.attr("width", width).attr("height", height);
    calcTextDisplay.attr("width", width / (1.3)).attr("height", height / 2)
    normTextDisplay.attr("width", "40rem").attr("height", "2rem")
    xScale.range([0, width]);
    yScale.range([0, height]);

    d3.selectAll('.verticalLine')
        .attr("y1", 0)
        .attr("y2", height)

    // X Axis label
    xlabel.attr("class", "x label")
        .style("text-anchor", "end")
        .attr("x", width / 2)
        .attr("y", height + xLabelOffset)
        .text("Wavelength (nm)");

    // Y Axis label
    ylabel.attr("class", "y label")
        .style("text-anchor", "end")
        .attr("x", -height / 2 - margin.top + margin.bottom)
        .attr("y", yLabelOffset)
        .attr("transform", "rotate(-90)")
        .text("Reflectance");

    d3.select("#x-slider").style("width", width);
    d3.select("#y-slider").style("height", height);

    rectBounds = [
        d3.select("#rectangle").node().width.animVal.value,
        d3.select("#rectangle").node().height.animVal.value
    ]

    // X Axis
    xSVG.attr("class", "x axis")
        .attr("transform", "translate(0," + height + ")")
        .call(xAxis);

    // Y Axis
    ySVG.attr("class", "y axis")
        .call(yAxis);

    // calculation text


    calcTextDisplay
        .attr("transform",
            "translate(" +
            (calcTextX).toString() +
            "," +
            (rectBounds[1] * 0.5 - calcTextY).toString() +
            ")"
        )

    resizeCalcText()

    normTextDisplay
        .attr("transform",
            "translate(" +
            rectBounds[0] * normTextX +
            "," +
            rectBounds[1] * normTextY +
            ")"
        )
    updateWindow(
        activeXScale.domain()[0],
        activeXScale.domain()[1],
        activeYScale.domain()[1],
        activeYScale.domain()[0],
        "redraw"
    )
}

for (const sample of graph) {
    activeLines[sample.id] = true
    activeLines[sample.id + "_r"] = true
}

updateDataVisibility()
resetZoom()
constrainZoom(mouseZoom)
