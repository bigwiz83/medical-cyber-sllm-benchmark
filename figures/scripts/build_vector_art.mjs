import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const masterDir = path.resolve(here, "..", "masters");
fs.mkdirSync(masterDir, { recursive: true });

const C = {
  ink: "#17212B",
  muted: "#5B6672",
  line: "#D7E0E6",
  pale: "#F3F6F8",
  teal: "#007C91",
  blue: "#2F6B9A",
  orange: "#E69F00",
  red: "#B2332E",
  gray: "#9AA4AD",
  lightGray: "#DBE0E5",
  white: "#FFFFFF",
};

const esc = (value) =>
  String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");

const svgStart = (width, height, title) => `<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="${height}" viewBox="0 0 ${width} ${height}" role="img" aria-labelledby="title desc">
<title id="title">${esc(title)}</title>
<desc id="desc">Publication figure for the synthetic hospital cybersecurity benchmark.</desc>
<rect width="${width}" height="${height}" fill="white"/>
<style>
text { font-family: Arial, Helvetica, sans-serif; fill: ${C.ink}; }
.muted { fill: ${C.muted}; }
.bold { font-weight: 700; }
.semibold { font-weight: 600; }
.panel { fill: white; stroke: ${C.line}; stroke-width: 1; }
</style>`;

const text = (x, y, value, size = 16, options = {}) => {
  const {
    weight = 400,
    fill = C.ink,
    anchor = "start",
    rotate,
    className = "",
  } = options;
  const transform = rotate === undefined ? "" : ` transform="rotate(${rotate} ${x} ${y})"`;
  return `<text x="${x}" y="${y}" font-size="${size}" font-weight="${weight}" fill="${fill}" text-anchor="${anchor}" class="${className}"${transform}>${esc(value)}</text>`;
};

const multiline = (x, y, lines, size = 13, options = {}) => {
  const { weight = 400, fill = C.ink, anchor = "start", lineHeight = 1.25 } = options;
  const tspans = lines
    .map((line, index) => `<tspan x="${x}" dy="${index === 0 ? 0 : size * lineHeight}">${esc(line)}</tspan>`)
    .join("");
  return `<text x="${x}" y="${y}" font-size="${size}" font-weight="${weight}" fill="${fill}" text-anchor="${anchor}">${tspans}</text>`;
};

const rect = (x, y, width, height, fill, options = {}) => {
  const { stroke = "none", strokeWidth = 0, radius = 0 } = options;
  return `<rect x="${x}" y="${y}" width="${width}" height="${height}" rx="${radius}" fill="${fill}" stroke="${stroke}" stroke-width="${strokeWidth}"/>`;
};

const line = (x1, y1, x2, y2, stroke = C.line, width = 1) =>
  `<line x1="${x1}" y1="${y1}" x2="${x2}" y2="${y2}" stroke="${stroke}" stroke-width="${width}"/>`;

const circle = (cx, cy, radius, fill, options = {}) => {
  const { stroke = C.white, strokeWidth = 1.5 } = options;
  return `<circle cx="${cx}" cy="${cy}" r="${radius}" fill="${fill}" stroke="${stroke}" stroke-width="${strokeWidth}"/>`;
};

function figure2() {
  const s = [
    svgStart(1200, 820, "Performance and reliability across local model configurations"),
    text(34, 52, "Performance and reliability across local model configurations", 28, { weight: 700 }),
    text(34, 78, "Failure-inclusive estimates; five repetitions are technical repeats, not independent samples", 16, { fill: C.muted }),
    line(34, 92, 1166, 92, C.ink, 1.5),
    text(34, 141, "A", 28, { weight: 700 }),
    text(76, 138, "Evidence-verified F1", 21, { weight: 600 }),
    rect(34, 154, 380, 616, C.white, { stroke: C.line, strokeWidth: 1, radius: 12 }),
    text(438, 141, "B", 28, { weight: 700 }),
    text(480, 138, "Precision–recall trade-off", 21, { weight: 600 }),
    rect(438, 154, 342, 616, C.white, { stroke: C.line, strokeWidth: 1, radius: 12 }),
    text(804, 141, "C", 28, { weight: 700 }),
    text(846, 138, "Execution status", 21, { weight: 600 }),
    rect(804, 154, 362, 616, C.white, { stroke: C.line, strokeWidth: 1, radius: 12 }),
  ];

  const performance = [
    ["Qwen single-RAG", 0.634, C.teal],
    ["Qwen autonomous team", 0.615, C.teal],
    ["Qwen fixed team", 0.605, C.teal],
    ["Qwen − evidence check", 0.605, C.teal],
    ["Qwen − clinical-context agent", 0.605, C.teal],
    ["Qwen − retrieval", 0, C.teal],
    ["gpt-oss fixed team", 0.261, C.orange],
    ["Gemma single-RAG", 0.242, C.blue],
    ["Gemma fixed team", 0.214, C.blue],
    ["gpt-oss single-RAG", 0.092, C.orange],
  ];
  const ax0 = 196;
  const aw = 184;
  for (let index = 0; index <= 7; index += 1) {
    s.push(text(ax0 + (aw * index) / 7, 735, (index / 10).toFixed(1), 11, { fill: C.muted, anchor: "middle" }));
  }
  performance.forEach(([label, value, color], index) => {
    const y = 210 + index * 49;
    const pointX = ax0 + (aw * value) / 0.7;
    const labelLines = label === "Qwen autonomous team" ? ["Qwen autonomous", "team"] : label === "Qwen − evidence check" ? ["Qwen − evidence", "check"] : [label];
    s.push(multiline(52, y, labelLines, 12.5, { weight: index < 3 ? 600 : 400 }));
    s.push(line(ax0, y, pointX, y, C.lightGray, 2));
    s.push(circle(pointX, y, 6, color));
    s.push(text(pointX + 11, y + 4, value.toFixed(3), 12, { weight: 600 }));
  });
  s.push(text(52, 758, "Mean of five run-specific micro-F1 values", 11.5, { fill: C.muted }));

  const bx = 488;
  const by = 646;
  const bw = 250;
  const bh = 430;
  for (let index = 0; index <= 5; index += 1) {
    const value = index / 5;
    const y = by - (bh * index) / 5;
    s.push(line(bx, y, bx + bw, y, C.line, 0.8));
    s.push(text(482, y + 4, value.toFixed(1), 11, { fill: C.muted, anchor: "end" }));
    s.push(text(bx + (bw * index) / 5, 669, value.toFixed(1), 11, { fill: C.muted, anchor: "middle" }));
  }
  s.push(text(613, 705, "Recall", 13, { weight: 600, fill: C.muted, anchor: "middle" }));
  s.push(text(434, 431, "Precision", 13, { weight: 600, fill: C.muted, anchor: "middle", rotate: -90 }));
  const points = [
    { p: 0.813, r: 0.52, c: C.teal, label: "Qwen single", dx: 9, dy: -14 },
    { p: 0.857, r: 0.48, c: C.teal, label: "Autonomous", dx: -10, dy: -16, anchor: "end" },
    { p: 0.722, r: 0.52, c: C.teal, label: ["Fixed / − evidence /", "− clinical-context"], dx: -12, dy: 26, anchor: "end" },
    { p: 0.5, r: 0.16, c: C.blue, label: "Gemma single", dx: 9, dy: -7 },
    { p: 1.0, r: 0.12, c: C.blue, label: "Gemma fixed", dx: 9, dy: 4 },
    { p: 0.109, r: 0.08, c: C.orange, label: "gpt-oss single", dx: 9, dy: 4 },
    { p: 0.286, r: 0.24, c: C.orange, label: "gpt-oss fixed", dx: 9, dy: 4 },
  ];
  points.forEach((point) => {
    const x = bx + bw * point.r;
    const y = by - bh * point.p;
    s.push(circle(x, y, 7, point.c));
    if (Array.isArray(point.label)) {
      s.push(multiline(x + point.dx, y + point.dy, point.label, 11.5, { weight: 600, anchor: point.anchor }));
    } else {
      s.push(text(x + point.dx, y + point.dy, point.label, 11.5, { weight: 600, anchor: point.anchor }));
    }
  });
  s.push(rect(472, 704, 274, 42, C.pale, { radius: 6 }));
  s.push(multiline(609, 723, ["No retrieval: no positive predictions; precision", "not estimable"], 11, { weight: 600, fill: C.muted, anchor: "middle" }));

  const status = [
    ["Qwen single", 290, 10, 0],
    ["Qwen autonomous", 285, 15, 0],
    ["Qwen fixed", 285, 15, 0],
    ["− evidence", 285, 15, 0],
    ["− clinical-context", 285, 15, 0],
    ["− retrieval", 260, 40, 0],
    ["Gemma single", 235, 65, 0],
    ["Gemma fixed", 250, 50, 0],
    ["gpt-oss single", 300, 0, 0],
    ["gpt-oss fixed", 284, 11, 5],
  ];
  const sx = 920;
  const sw = 214;
  status.forEach(([label, complete, failed, refused], index) => {
    const y = 202 + index * 49;
    if (label === "Qwen autonomous") {
      s.push(multiline(822, y - 3, ["Qwen", "autonomous"], 11.5, { weight: 600, lineHeight: 1.05 }));
    } else if (label === "− clinical-context") {
      s.push(text(822, y + 4, label, 10.5, { weight: 400 }));
    } else {
      s.push(text(822, y + 4, label, 12.2, { weight: index < 3 ? 600 : 400 }));
    }
    const completeWidth = (sw * complete) / 300;
    const failedWidth = (sw * failed) / 300;
    const refusedWidth = (sw * refused) / 300;
    s.push(rect(sx, y - 8, completeWidth, 16, C.teal, { radius: 2 }));
    if (failedWidth > 0) s.push(rect(sx + completeWidth, y - 8, failedWidth, 16, C.gray));
    if (refusedWidth > 0) s.push(rect(sx + completeWidth + failedWidth, y - 8, refusedWidth, 16, C.red));
    s.push(text(1160, y + 4, complete, 11, { weight: 600, anchor: "end" }));
  });
  s.push(text(920, 708, "0", 11, { fill: C.muted }));
  s.push(text(1152, 708, "300 cells", 11, { fill: C.muted, anchor: "end" }));
  [[824, C.teal, "Complete"], [928, C.gray, "Failed"], [1020, C.red, "Refused"]].forEach(([x, color, label]) => {
    s.push(rect(x, 724, 12, 12, color, { radius: 2 }));
    s.push(text(x + 18, 735, label, 11, { fill: C.muted }));
  });
  s.push("</svg>");
  return s.join("\n");
}

function figure3() {
  const s = [
    svgStart(1200, 800, "Architecture effects, ablations, and scenario-specific performance"),
    text(34, 52, "Architecture effects, ablations, and scenario-specific performance", 28, { weight: 700 }),
    text(34, 78, "Paired family-level inference, recent-KEV retrieval dependence, and stratum-specific F1", 16, { fill: C.muted }),
    line(34, 92, 1166, 92, C.ink, 1.5),
    text(34, 141, "A", 28, { weight: 700 }),
    text(76, 138, "F1 effects", 21, { weight: 600 }),
    rect(34, 154, 500, 596, C.white, { stroke: C.line, strokeWidth: 1, radius: 12 }),
    text(558, 141, "B", 28, { weight: 700 }),
    text(600, 138, "Retrieval ablation", 21, { weight: 600 }),
    rect(558, 154, 280, 596, C.white, { stroke: C.line, strokeWidth: 1, radius: 12 }),
    text(862, 141, "C", 28, { weight: 700 }),
    text(904, 138, "Scenario-specific F1", 21, { weight: 600 }),
    rect(862, 154, 304, 596, C.white, { stroke: C.line, strokeWidth: 1, radius: 12 }),
  ];
  const effects = [
    ["Autonomous − fixed", 0.010733, -0.119861, 0.143774, true],
    ["Autonomous − single", -0.018762, -0.121053, 0.065163, false],
    ["Qwen fixed − single", -0.029495, -0.13167, 0.066667, true],
    ["Gemma fixed − single", -0.028139, -0.226852, 0.150878, false],
    ["gpt-oss fixed − single", 0.168673, -0.006807, 0.344814, false],
    ["Worst-case fixed-team effect", -0.029495, -0.226852, 0.035363, false],
    ["Evidence check retained − removed", 0, 0, 0, true],
    ["Clinical-context agent retained − removed", 0, 0, 0, false],
    ["Qwen fixed − Gemma fixed", 0.390365, 0.212121, 0.57424, true],
    ["Qwen fixed − gpt-oss fixed", 0.343782, 0.232146, 0.462412, true],
  ];
  const fx = 292;
  const fw = 220;
  const min = -0.25;
  const max = 0.6;
  const mapEffect = (value) => fx + (fw * (value - min)) / (max - min);
  const zero = mapEffect(0);
  s.push(rect(zero, 190, 1.2, 508, C.gray));
  [-0.2, -0.05, 0.1, 0.25, 0.4, 0.55].forEach((value) => s.push(text(mapEffect(value), 704, value.toFixed(2), 10.5, { fill: C.muted, anchor: "middle" })));
  effects.forEach(([label, value, lower, upper, filled], index) => {
    const y = 200 + index * 49;
    s.push(text(52, y + 2, label, 12.2, { weight: filled ? 600 : 400 }));
    const lowerX = mapEffect(lower);
    const upperX = mapEffect(upper);
    const pointX = mapEffect(value);
    if (Math.abs(upperX - lowerX) < 1) s.push(line(pointX - 5, y, pointX + 5, y, C.ink, 2));
    else s.push(line(lowerX, y, upperX, y, C.ink, 2));
    s.push(circle(pointX, y, 6, filled ? C.teal : C.white, { stroke: C.teal, strokeWidth: 2 }));
  });
  s.push(text(402, 722, "Effect (intervention − comparator)", 11.5, { weight: 600, fill: C.muted, anchor: "middle" }));
  s.push(circle(59, 740, 5, C.teal, { stroke: C.teal, strokeWidth: 1 }));
  s.push(text(70, 744, "confirmatory / adjusted", 10.5, { fill: C.muted }));
  s.push(circle(259, 740, 5, C.white, { stroke: C.teal, strokeWidth: 1.5 }));
  s.push(text(270, 744, "descriptive / component", 10.5, { fill: C.muted }));

  s.push(text(582, 193, "Affected-target recall", 14, { weight: 600, fill: C.muted }));
  const retrieval = [["0–30 days", 1], ["31–60 days", 0.5], ["61–90 days", 0.75]];
  const rx = 596;
  const rw = 204;
  retrieval.forEach(([label, value], index) => {
    const y = 242 + index * 116;
    s.push(text(582, y - 16, label, 13, { weight: 600 }));
    s.push(line(rx, y, rx + rw, y, C.line, 2));
    s.push(circle(rx, y, 7, C.white, { stroke: C.gray, strokeWidth: 2 }));
    const pointX = rx + rw * value;
    s.push(line(rx, y, pointX, y, C.teal, 4));
    s.push(circle(pointX, y, 8, C.teal));
    s.push(text(pointX, y - 24, value.toFixed(2), 12, { weight: 700, fill: C.teal, anchor: "middle" }));
  });
  [0, 0.25, 0.5, 0.75, 1].forEach((value) => s.push(text(rx + rw * value, 602, value.toFixed(2), 10.5, { fill: C.muted, anchor: "middle" })));
  s.push(rect(582, 634, 232, 86, C.pale, { radius: 8 }));
  s.push(text(598, 663, "With retrieval", 12, { weight: 600, fill: C.teal }));
  s.push(text(790, 667, "0.75", 19, { weight: 700, fill: C.teal, anchor: "end" }));
  s.push(text(598, 694, "Without retrieval", 12, { weight: 600, fill: C.muted }));
  s.push(text(790, 698, "0.00", 19, { weight: 700, fill: C.muted, anchor: "end" }));
  s.push(text(698, 735, "Aggregate difference 0.75 (95% CI 0.50–0.92)", 10.5, { fill: C.muted, anchor: "middle" }));

  const heatColumns = ["0–30 d", "31–60 d", "61–90 d", "Other CVE", "Misconfig."];
  const heatRows = [
    ["Single-RAG", [0.857, 0.75, 0.857, 0.667, 0]],
    ["Autonomous", [0.667, 0.75, 0.667, 0.833, 0]],
    ["Fixed team", [0.889, 0.571, 0.857, 0.615, 0]],
  ];
  const hx = 942;
  const hy = 248;
  const cellWidth = 41;
  const cellHeight = 62;
  heatColumns.forEach((label, index) => {
    const x = hx + index * cellWidth + 18;
    if (index < 3) s.push(text(x, 222, label, 10.5, { weight: 600, fill: C.muted, anchor: "middle", rotate: -45 }));
    else if (index === 3) s.push(multiline(x - 3, 190, ["Other", "CVE"], 10.5, { weight: 600, fill: C.muted, anchor: "middle" }));
    else s.push(multiline(x + 3, 190, ["Mis-", "config."], 10.5, { weight: 600, fill: C.muted, anchor: "middle" }));
  });
  heatRows.forEach(([label, values], rowIndex) => {
    const y = hy + rowIndex * cellHeight;
    s.push(text(936, y + 34, label, 10.5, { weight: 600, anchor: "end" }));
    values.forEach((value, columnIndex) => {
      const mix = (a, b) => Math.round(a * (1 - value) + b * value);
      const fill = `rgb(${mix(224, 0)},${mix(240, 124)},${mix(242, 145)})`;
      const x = hx + columnIndex * cellWidth;
      s.push(rect(x, y, cellWidth - 3, cellHeight - 3, fill, { stroke: C.white, strokeWidth: 1, radius: 2 }));
      s.push(text(x + (cellWidth - 3) / 2, y + 34, value.toFixed(3), 10.5, { weight: 700, fill: value > 0.65 ? C.white : C.ink, anchor: "middle" }));
    });
  });
  s.push(text(1000, 461, "Recent KEV", 12, { weight: 600, fill: C.muted, anchor: "middle" }));
  s.push(line(950, 478, 1055, 478, C.teal, 3));
  s.push(text(1084, 461, "Other", 12, { weight: 600, fill: C.muted, anchor: "middle" }));
  s.push(line(1068, 478, 1102, 478, C.blue, 3));
  s.push(multiline(1133, 457, ["Rule-", "based"], 12, { weight: 600, fill: C.muted, anchor: "middle" }));
  s.push(line(1115, 482, 1151, 482, C.orange, 3));
  s.push(rect(886, 510, 256, 86, C.pale, { radius: 8 }));
  s.push(text(1014, 539, "All three core Qwen configurations", 12, { weight: 600, anchor: "middle" }));
  s.push(text(1014, 571, "Clean controls: 0 FP / 50 cells each", 13, { weight: 700, fill: C.teal, anchor: "middle" }));
  s.push(rect(886, 622, 256, 96, "#FFF5DC", { radius: 8 }));
  s.push(text(1014, 651, "Shared limitation", 12, { weight: 700, fill: C.orange, anchor: "middle" }));
  s.push(multiline(1014, 684, ["Synthetic misconfiguration F1 =", "0"], 14, { weight: 700, anchor: "middle" }));
  s.push("</svg>");
  return s.join("\n");
}

fs.writeFileSync(path.join(masterDir, "figure2.svg"), figure2(), "utf8");
fs.writeFileSync(path.join(masterDir, "figure3.svg"), figure3(), "utf8");
console.log(JSON.stringify({ output: masterDir, files: ["figure2.svg", "figure3.svg"] }));
