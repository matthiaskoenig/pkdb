// Computes reference values (python/tests/studyformat/data/wpd/calibration_oracle.json) with WebPlotDigitizer's own XYAxes code
// (automeris-io/WebPlotDigitizer at 3a3ecb11606945d0701c8a488777e6861be70056).
const fs = require("fs");
// Regenerate: download mathFunctions.js, dateConversion.js, inputParser.js, calibration.js and axes/xy.js
// of that commit from javascript/core into one directory, copy this file there and run `node oracle.cjs`.
// The WebPlotDigitizer sources are AGPL licensed and are not committed here.
const vm = require("vm");
const context = { wpd: {}, console, Math, Date, parseFloat, isNaN };
vm.createContext(context);
for (const file of ["mathFunctions.js", "dateConversion.js", "inputParser.js", "calibration.js", "axes/xy.js"]) {
  vm.runInContext(fs.readFileSync(file.replace("axes/", ""), "utf8"), context, { filename: file });
}
const cases = [
  { name: "linear", isLogX: false, isLogY: false, noRotation: false,
    points: [[105.6686, 528.8291, 0, 0], [716.7337, 528.8291, 20, 0], [105.6686, 528.8291, 0, 0], [105.6686, 138.4325, 0, 8]] },
  { name: "log_y", isLogX: false, isLogY: true, noRotation: false,
    points: [[80, 500, 0, 0.1], [700, 500, 24, 0.1], [80, 500, 0, 0.1], [80, 60, 0, 100]] },
  { name: "log_x_negative", isLogX: true, isLogY: false, noRotation: false,
    points: [[50, 400, -1000, 0], [650, 400, -0.1, 0], [50, 400, -1000, 0], [50, 40, -1000, 50]] },
  { name: "rotated", isLogX: false, isLogY: false, noRotation: false,
    points: [[100, 500, 0, 0], [690, 470, 30, 0], [100, 500, 0, 0], [125, 80, 0, 12]] },
  { name: "no_rotation_snap", isLogX: false, isLogY: false, noRotation: true,
    points: [[100, 500, 0, 0], [690, 497, 30, 0], [100, 500, 0, 0], [103, 80, 0, 12]] },
  { name: "no_rotation_vertical_x", isLogX: false, isLogY: false, noRotation: true,
    points: [[100, 500, 0, 0], [101, 100, 10, 0], [100, 500, 0, 0], [600, 502, 0, 5]] },
  { name: "string_values", isLogX: false, isLogY: false, noRotation: false,
    points: [[105.6686, 528.8291, "0", "0"], [716.7337, 528.8291, "20", "0"], [105.6686, 528.8291, "0", "0"], [105.6686, 138.4325, "0", "8"]] },
];
const pixels = [[105.6686, 528.8291], [400.5, 300.25], [716.7337, 138.4325], [12, 590], [880.75, 22.5]];
const out = [];
for (const c of cases) {
  const cal = new context.wpd.Calibration(2);
  cal.labels = ["X1", "X2", "Y1", "Y2"];
  for (const [px, py, dx, dy] of c.points) cal.addPoint(px, py, String(dx), String(dy));
  const axes = new context.wpd.XYAxes();
  if (!axes.calibrate(cal, c.isLogX, c.isLogY, c.noRotation)) throw new Error("calibration failed: " + c.name);
  const values = pixels.map(([x, y]) => axes.pixelToData(x, y));
  const back = values.map(([x, y]) => { const p = axes.dataToPixel(x, y); return [p.x, p.y]; });
  out.push({
    name: c.name,
    axes: { name: "XY", type: "XYAxes", isLogX: c.isLogX, isLogY: c.isLogY, noRotation: c.noRotation,
      calibrationPoints: c.points.map(([px, py, dx, dy]) => ({ px, py, dx, dy, dz: null })) },
    pixels, values, back,
  });
}
fs.writeFileSync("calibration_oracle.json", JSON.stringify({ source: "WebPlotDigitizer 3a3ecb11606945d0701c8a488777e6861be70056 javascript/core/axes/xy.js", cases: out }, null, 2) + "\n");
console.log("ok", out.length);
