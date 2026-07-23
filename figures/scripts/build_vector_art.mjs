import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const figureRoot = path.basename(here) === "scripts" ? path.dirname(here) : here;
const masterDir = path.join(figureRoot, "masters");
fs.mkdirSync(masterDir, { recursive: true });

const sourceCandidates = [
  path.join(figureRoot, "source_data"),
  path.join(figureRoot, "..", "paper_ready_v3", "generated", "figures", "source_data"),
];
const sourceDir = sourceCandidates.find((candidate) => fs.existsSync(candidate));
if (!sourceDir) throw new Error(`Figure source data not found: ${sourceCandidates.join(", ")}`);

const C = {
  ink: "#111111",
  muted: "#555555",
  rule: "#B7B7B7",
  grid: "#DDDDDD",
  pale: "#F3F3F3",
  teal: "#007C91",
  tealLight: "#DCECEF",
  blueGray: "#627D8C",
  rust: "#A34A2A",
  gray: "#9B9B9B",
  darkGray: "#5F5F5F",
  white: "#FFFFFF",
};

const esc = (value) =>
  String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");

function parseCsv(raw) {
  const rows = [];
  let row = [];
  let cell = "";
  let quoted = false;
  for (let index = 0; index < raw.length; index += 1) {
    const char = raw[index];
    if (char === '"') {
      if (quoted && raw[index + 1] === '"') {
        cell += '"';
        index += 1;
      } else {
        quoted = !quoted;
      }
    } else if (char === "," && !quoted) {
      row.push(cell);
      cell = "";
    } else if ((char === "\n" || char === "\r") && !quoted) {
      if (char === "\r" && raw[index + 1] === "\n") index += 1;
      row.push(cell);
      if (row.some((value) => value !== "")) rows.push(row);
      row = [];
      cell = "";
    } else {
      cell += char;
    }
  }
  if (cell || row.length) {
    row.push(cell);
    rows.push(row);
  }
  const headers = rows.shift();
  return rows.map((values) => Object.fromEntries(headers.map((header, index) => [header, values[index] ?? ""])));
}

const csv = (name) => parseCsv(fs.readFileSync(path.join(sourceDir, name), "utf8"));
const n = (value) => Number(value);
const score = (value) => n(value).toFixed(2);
const pValue = (value) => {
  if (value === "" || value === undefined || value === null) return "—";
  const number = n(value);
  return number < 0.001 ? "<0.001" : number.toFixed(3);
};
const minus = (value) => String(value).replaceAll("-", "−");

const svgStart = (width, height, title, description) => `<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="${height}" viewBox="0 0 ${width} ${height}" role="img" aria-labelledby="title desc">
<title id="title">${esc(title)}</title>
<desc id="desc">${esc(description)}</desc>
<rect width="${width}" height="${height}" fill="white"/>
<style>
text { font-family: Arial, Helvetica, sans-serif; fill: ${C.ink}; }
.label { font-size: 12px; }
.small { font-size: 10.5px; }
</style>`;

const text = (x, y, value, size = 14, options = {}) => {
  const { weight = 400, fill = C.ink, anchor = "start", rotate, italic = false } = options;
  const transform = rotate === undefined ? "" : ` transform="rotate(${rotate} ${x} ${y})"`;
  return `<text x="${x}" y="${y}" font-size="${size}" font-weight="${weight}" fill="${fill}" text-anchor="${anchor}" font-style="${italic ? "italic" : "normal"}"${transform}>${esc(value)}</text>`;
};

const multiline = (x, y, lines, size = 12, options = {}) => {
  const { weight = 400, fill = C.ink, anchor = "start", lineHeight = 1.2 } = options;
  const spans = lines.map((value, index) => `<tspan x="${x}" dy="${index === 0 ? 0 : size * lineHeight}">${esc(value)}</tspan>`).join("");
  return `<text x="${x}" y="${y}" font-size="${size}" font-weight="${weight}" fill="${fill}" text-anchor="${anchor}">${spans}</text>`;
};

const line = (x1, y1, x2, y2, stroke = C.rule, width = 1, dash = "") =>
  `<line x1="${x1}" y1="${y1}" x2="${x2}" y2="${y2}" stroke="${stroke}" stroke-width="${width}"${dash ? ` stroke-dasharray="${dash}"` : ""}/>`;
const rect = (x, y, width, height, fill = C.white, stroke = "none", strokeWidth = 0) =>
  `<rect x="${x}" y="${y}" width="${width}" height="${height}" fill="${fill}" stroke="${stroke}" stroke-width="${strokeWidth}"/>`;
const circle = (cx, cy, radius, fill, stroke = C.white, strokeWidth = 1.2) =>
  `<circle cx="${cx}" cy="${cy}" r="${radius}" fill="${fill}" stroke="${stroke}" stroke-width="${strokeWidth}"/>`;

function panelHeader(parts, x, width, letter, titleValue) {
  parts.push(text(x, 42, letter, 24, { weight: 700 }));
  parts.push(text(x + 38, 40, titleValue, 17, { weight: 700 }));
  parts.push(line(x, 57, x + width, 57, C.ink, 1.1));
}

function modelColor(condition) {
  if (condition.startsWith("Qwen")) return C.teal;
  if (condition.startsWith("Gemma")) return C.blueGray;
  return C.rust;
}

function figure1() {
  const composition = csv("figure1a_scenario_composition.csv");
  const conditions = csv("figure1b_conditions.csv");
  const s = [svgStart(1200, 690, "Integrated benchmark design and analysis workflow", "Benchmark population, evaluated model configurations, and evidence-verified scoring workflow.")];
  panelHeader(s, 32, 350, "A", "Benchmark population");
  panelHeader(s, 418, 350, "B", "Model configurations");
  panelHeader(s, 804, 364, "C", "Evidence-verified scoring");
  s.push(line(400, 24, 400, 660, C.grid, 1));
  s.push(line(786, 24, 786, 660, C.grid, 1));

  const stats = [["60", "scenarios"], ["30", "families"], ["5", "repetitions"], ["3,000", "cells"]];
  stats.forEach(([value, label], index) => {
    const x = 42 + (index % 2) * 168;
    const y = 102 + Math.floor(index / 2) * 72;
    s.push(text(x, y, value, 26, { weight: 700, fill: index === 3 ? C.teal : C.ink }));
    s.push(text(x, y + 22, label, 11.5, { fill: C.muted }));
  });
  s.push(text(42, 246, "Scenario composition", 12.5, { weight: 700 }));
  s.push(line(42, 256, 368, 256, C.grid, 0.8));
  const maxScenarios = Math.max(...composition.map((row) => n(row.scenarios)));
  composition.forEach((row, index) => {
    const y = 292 + index * 54;
    const label = row.stratum.replace("Recent KEV, ", "Recent KEV ").replace("Synthetic misconfiguration", "Synthetic misconfiguration");
    const width = 88 * n(row.scenarios) / maxScenarios;
    const fill = row.stratum === "Clean control" ? C.gray : row.stratum === "Synthetic misconfiguration" ? C.darkGray : C.teal;
    s.push(text(42, y, label, 11.5));
    s.push(rect(250, y - 11, width, 11, fill));
    s.push(text(365, y, row.scenarios, 11.5, { weight: 700, anchor: "end" }));
  });
  s.push(line(42, 622, 368, 622, C.grid, 0.8));
  s.push(text(42, 646, "25 positive · 25 paired negative · 10 clean", 11, { fill: C.muted }));

  const grouped = new Map();
  for (const row of conditions) {
    if (!grouped.has(row.backbone)) grouped.set(row.backbone, []);
    grouped.get(row.backbone).push(row);
  }
  s.push(text(428, 89, "Backbone", 10.5, { weight: 700, fill: C.muted }));
  [["Single-RAG", 564], ["Fixed team", 628], ["Autonomous", 690], ["Ablation", 748]].forEach(([label, x]) => {
    s.push(multiline(x, 83, label === "Fixed team" ? ["Fixed", "team"] : [label], 10, { weight: 700, fill: C.muted, anchor: "middle" }));
  });
  s.push(line(428, 108, 758, 108, C.rule, 0.9));
  const rows = [
    ["Qwen 3.5 27B", 6],
    ["Gemma 3 27B", 2],
    ["gpt-oss 20B", 2],
  ];
  rows.forEach(([backbone, count], index) => {
    const y = 154 + index * 82;
    const values = grouped.get(backbone) ?? [];
    const hasSingle = values.some((row) => row.architecture.startsWith("Single-agent"));
    const hasFixed = values.some((row) => row.architecture === "Fixed specialist team");
    const hasAutonomous = values.some((row) => row.architecture.startsWith("Model-planned"));
    const ablations = values.filter((row) => row.architecture.includes("ablation")).length;
    s.push(text(428, y, backbone, 13, { weight: 700 }));
    s.push(text(428, y + 20, `${count} configurations`, 10.5, { fill: C.muted }));
    [[564, hasSingle], [628, hasFixed], [690, hasAutonomous]].forEach(([x, present]) => {
      s.push(present ? circle(x, y - 4, 5.5, C.teal, C.teal, 1) : text(x, y, "—", 12, { fill: C.gray, anchor: "middle" }));
    });
    s.push(ablations ? text(748, y, String(ablations), 12, { weight: 700, fill: C.teal, anchor: "middle" }) : text(748, y, "—", 12, { fill: C.gray, anchor: "middle" }));
    s.push(line(428, y + 37, 758, y + 37, C.grid, 0.8));
  });
  s.push(text(428, 418, "Common controls", 12.5, { weight: 700 }));
  const controls = [
    ["Temperature", "0"], ["Seed", "paired"], ["Concurrency", "1"],
    ["Runtime egress", "0 bytes"], ["Model commands", "disabled"],
  ];
  controls.forEach(([label, value], index) => {
    const y = 451 + index * 36;
    s.push(text(428, y, label, 11.5, { fill: C.muted }));
    s.push(text(758, y, value, 11.5, { weight: 700, anchor: "end" }));
    s.push(line(428, y + 10, 758, y + 10, C.grid, 0.7));
  });

  const workflow = [
    ["Structured finding", "target · candidate · evidence"],
    ["Asset applicability", "product · version · configuration"],
    ["Source support", "frozen advisory and retrieval record"],
    ["Execution validation", "rule checks in the synthetic range"],
  ];
  workflow.forEach(([label, detail], index) => {
    const y = 82 + index * 104;
    s.push(rect(824, y, 324, 60, C.white, C.rule, 1));
    s.push(rect(824, y, 5, 60, index === 3 ? C.darkGray : C.teal));
    s.push(text(846, y + 25, label, 13, { weight: 700 }));
    s.push(text(846, y + 45, detail, 10.5, { fill: C.muted }));
    if (index < workflow.length - 1) {
      s.push(line(986, y + 60, 986, y + 88, C.rule, 1));
      s.push(`<path d="M981 ${y + 83} L986 ${y + 89} L991 ${y + 83}" fill="none" stroke="${C.rule}" stroke-width="1"/>`);
    }
  });
  s.push(line(824, 512, 1148, 512, C.ink, 1.1));
  s.push(text(824, 544, "TP · FP · FN", 14, { weight: 700 }));
  s.push(text(1148, 544, "failure-inclusive", 10.5, { fill: C.muted, anchor: "end" }));
  s.push(text(824, 584, "Evidence-verified detection F1", 13, { weight: 700 }));
  s.push(text(824, 615, "2TP", 12, { weight: 700, anchor: "middle" }));
  s.push(line(805, 621, 843, 621, C.ink, 1));
  s.push(text(824, 639, "2TP + FP + FN", 10.5, { anchor: "middle" }));
  s.push(text(1148, 625, "paired family-level inference", 10.5, { fill: C.muted, anchor: "end" }));
  s.push("</svg>");
  return s.join("\n");
}

function figure2() {
  const performance = csv("figure2_condition_performance.csv");
  const s = [svgStart(1200, 720, "Evidence-verified detection performance and execution reliability", "Mean-run F1, precision-recall trade-offs, and execution status across ten local configurations.")];
  panelHeader(s, 32, 358, "A", "Mean-run F1");
  panelHeader(s, 420, 356, "B", "Precision and recall");
  panelHeader(s, 806, 362, "C", "Execution status");
  s.push(line(405, 24, 405, 690, C.grid, 1));
  s.push(line(791, 24, 791, 690, C.grid, 1));

  const sorted = [...performance].sort((a, b) => n(b.mean_run_f1) - n(a.mean_run_f1));
  const ax0 = 221;
  const aw = 146;
  [0, 0.2, 0.4, 0.6].forEach((value) => {
    const x = ax0 + aw * value / 0.7;
    s.push(line(x, 87, x, 616, C.grid, 0.7));
    s.push(text(x, 640, value.toFixed(1), 10.5, { fill: C.muted, anchor: "middle" }));
  });
  sorted.forEach((row, index) => {
    const y = 101 + index * 51;
    const label = row.condition
      .replace("Qwen without evidence checking", "Qwen − evidence checking")
      .replace("Qwen without clinical-context agent", "Qwen − clinical-context")
      .replace("Qwen without retrieval", "Qwen − retrieval");
    const x = ax0 + aw * n(row.mean_run_f1) / 0.7;
    s.push(text(42, y + 4, label, 11.2, { weight: index < 3 ? 700 : 400 }));
    s.push(line(ax0, y, x, y, C.rule, 1.2));
    s.push(circle(x, y, 5.4, modelColor(row.condition), C.white, 1));
    s.push(text(Math.min(x + 10, 377), y + 4, score(row.mean_run_f1), 11, { weight: 700 }));
  });
  s.push(text(42, 674, "Five run-specific micro-F1 estimates averaged", 10.5, { fill: C.muted }));

  const bx = 478;
  const by = 598;
  const bw = 258;
  const bh = 492;
  for (let index = 0; index <= 5; index += 1) {
    const value = index / 5;
    const x = bx + bw * value;
    const y = by - bh * value;
    s.push(line(bx, y, bx + bw, y, C.grid, 0.7));
    s.push(text(bx - 10, y + 4, value.toFixed(1), 10.5, { fill: C.muted, anchor: "end" }));
    s.push(text(x, 620, value.toFixed(1), 10.5, { fill: C.muted, anchor: "middle" }));
  }
  s.push(text(607, 652, "Recall", 11.5, { weight: 700, anchor: "middle" }));
  s.push(text(444, 352, "Precision", 11.5, { weight: 700, anchor: "middle", rotate: -90 }));
  const offsets = {
    qwen_single_rag: [10, 4, "start", "Qwen single"],
    qwen_autonomous_team: [-10, -16, "end", "Qwen autonomous"],
    qwen_fixed_team: [-12, 24, "end", "Qwen fixed / ablations"],
    qwen_without_evidence_check: [0, 0, "start", ""],
    qwen_without_context_role: [0, 0, "start", ""],
    qwen_without_retrieval: [0, 0, "start", ""],
    gemma_single_rag: [10, 4, "start", "Gemma single"],
    gemma_fixed_team: [10, 4, "start", "Gemma fixed"],
    gpt_oss_single_rag: [10, 4, "start", "gpt-oss single"],
    gpt_oss_fixed_team: [10, 4, "start", "gpt-oss fixed"],
  };
  performance.forEach((row) => {
    if (row.precision === "") return;
    const x = bx + bw * n(row.recall);
    const y = by - bh * n(row.precision);
    s.push(circle(x, y, row.condition_id.includes("without") ? 3.8 : 5.7, modelColor(row.condition), C.white, 1));
    const [dx, dy, anchor, label] = offsets[row.condition_id];
    if (label) s.push(text(x + dx, y + dy, label, 10.5, { weight: 700, anchor }));
  });
  s.push(text(430, 681, "No retrieval: no positive predictions; precision not estimable", 10, { fill: C.muted }));

  const sx = 929;
  const sw = 211;
  performance.forEach((row, index) => {
    const y = 100 + index * 51;
    const label = row.condition
      .replace("Qwen without evidence checking", "− evidence checking")
      .replace("Qwen without clinical-context agent", "− clinical-context")
      .replace("Qwen without retrieval", "− retrieval")
      .replace(" team", "");
    s.push(text(816, y + 4, label, 10.7, { weight: index < 3 ? 700 : 400 }));
    const complete = n(row.complete);
    const failed = n(row.failed);
    const refused = n(row.refused);
    const completeWidth = sw * complete / 300;
    const failedWidth = sw * failed / 300;
    const refusedWidth = sw * refused / 300;
    s.push(rect(sx, y - 7, sw, 14, C.white, C.rule, 0.7));
    s.push(rect(sx, y - 7, completeWidth, 14, C.teal));
    if (failedWidth) s.push(rect(sx + completeWidth, y - 7, failedWidth, 14, C.gray));
    if (refusedWidth) s.push(rect(sx + completeWidth + failedWidth, y - 7, refusedWidth, 14, C.rust));
    s.push(text(1164, y + 4, String(complete), 10.5, { weight: 700, anchor: "end" }));
  });
  s.push(text(sx, 630, "0", 10.5, { fill: C.muted }));
  s.push(text(sx + sw, 630, "300 cells", 10.5, { fill: C.muted, anchor: "end" }));
  [[C.teal, "Complete"], [C.gray, "Failed"], [C.rust, "Refused"]].forEach(([color, label], index) => {
    const x = 820 + index * 112;
    s.push(rect(x, 658, 11, 11, color));
    s.push(text(x + 17, 668, label, 10.5, { fill: C.muted }));
  });
  s.push("</svg>");
  return s.join("\n");
}

function figure3() {
  const effects = csv("figure3a_f1_effects.csv");
  const retrieval = csv("figure3b_retrieval_window_recall.csv");
  const subgroup = csv("figure3c_qwen_stratum_f1.csv");
  const s = [svgStart(1200, 740, "Architecture effects, retrieval ablation, and scenario-specific performance", "Paired F1 effects with confidence intervals and P values, recall with and without retrieval, and Qwen subgroup F1.")];
  panelHeader(s, 30, 620, "A", "Paired F1 effects");
  panelHeader(s, 674, 238, "B", "Retrieval ablation");
  panelHeader(s, 936, 234, "C", "F1 by scenario stratum");
  s.push(line(662, 24, 662, 710, C.grid, 1));
  s.push(line(924, 24, 924, 710, C.grid, 1));

  const labels = {
    "Qwen fixed team − single-RAG": "Qwen fixed − single",
    "Evidence checking retained − removed": "Evidence check retained − removed",
    "Clinical-context agent retained − removed": "Clinical-context retained − removed",
    "Gemma fixed team − single-RAG": "Gemma fixed − single",
    "gpt-oss fixed team − single-RAG": "gpt-oss fixed − single",
    "Worst-case fixed-team effect across backbones": "Worst-case fixed-team effect",
    "Qwen fixed team − Gemma fixed team": "Qwen fixed − Gemma fixed",
    "Qwen fixed team − gpt-oss fixed team": "Qwen fixed − gpt-oss fixed",
    "Qwen autonomous team − fixed team": "Qwen autonomous − fixed",
    "Qwen autonomous team − single-RAG": "Qwen autonomous − single",
  };
  const orderedNames = [
    "Qwen autonomous team − fixed team",
    "Qwen autonomous team − single-RAG",
    "Qwen fixed team − single-RAG",
    "Gemma fixed team − single-RAG",
    "gpt-oss fixed team − single-RAG",
    "Worst-case fixed-team effect across backbones",
    "Evidence checking retained − removed",
    "Clinical-context agent retained − removed",
    "Qwen fixed team − Gemma fixed team",
    "Qwen fixed team − gpt-oss fixed team",
  ];
  const byName = new Map(effects.map((row) => [row.comparison, row]));
  const ordered = orderedNames.map((name) => byName.get(name));
  const fx = 270;
  const fw = 158;
  const min = -0.25;
  const max = 0.60;
  const mapEffect = (value) => fx + fw * (value - min) / (max - min);
  s.push(text(456, 82, "Difference (95% CI)", 10.5, { weight: 700, fill: C.muted }));
  s.push(text(638, 82, "P value", 10.5, { weight: 700, fill: C.muted, anchor: "end" }));
  s.push(line(mapEffect(0), 91, mapEffect(0), 619, C.gray, 1));
  ordered.forEach((row, index) => {
    const y = 108 + index * 51;
    const isEmphasized = ["Confirmatory", "Multiplicity-adjusted"].includes(row.analysis_status);
    const effect = n(row.effect);
    const lower = n(row.ci_lower);
    const upper = n(row.ci_upper);
    s.push(text(40, y + 4, labels[row.comparison], 10.7, { weight: isEmphasized ? 700 : 400 }));
    s.push(line(mapEffect(lower), y, mapEffect(upper), y, C.ink, 1.5));
    s.push(circle(mapEffect(effect), y, 5.2, isEmphasized ? C.teal : C.white, C.teal, 1.5));
    s.push(text(456, y + 4, `${minus(score(effect))} (${minus(score(lower))} to ${minus(score(upper))})`, 10.2));
    const reportP = row.adjusted_p || row.raw_p;
    s.push(text(638, y + 4, pValue(reportP), 10.2, { anchor: "end" }));
  });
  [-0.2, 0, 0.2, 0.4, 0.6].forEach((value) => {
    const x = mapEffect(value);
    s.push(line(x, 618, x, 624, C.ink, 0.8));
    s.push(text(x, 642, minus(value.toFixed(1)), 10, { fill: C.muted, anchor: "middle" }));
  });
  s.push(text((fx + fx + fw) / 2, 667, "Intervention minus comparator", 10.5, { fill: C.muted, anchor: "middle" }));
  s.push(circle(43, 694, 4.5, C.teal, C.teal, 1));
  s.push(text(54, 698, "confirmatory or adjusted", 10, { fill: C.muted }));
  s.push(circle(210, 694, 4.5, C.white, C.teal, 1.2));
  s.push(text(221, 698, "descriptive or component", 10, { fill: C.muted }));

  const windows = ["0–30 days", "31–60 days", "61–90 days"];
  const ry = [156, 298, 440];
  windows.forEach((window, index) => {
    const withRow = retrieval.find((row) => row.window === window && row.condition_id === "qwen_fixed_team");
    const withoutRow = retrieval.find((row) => row.window === window && row.condition_id === "qwen_without_retrieval");
    const y = ry[index];
    const x0 = 704;
    const x1 = 882;
    const withX = x0 + (x1 - x0) * n(withRow.affected_target_recall);
    const withoutX = x0 + (x1 - x0) * n(withoutRow.affected_target_recall);
    s.push(text(688, y - 38, window, 11.5, { weight: 700 }));
    s.push(line(x0, y, x1, y, C.grid, 1));
    s.push(line(withoutX, y, withX, y, C.teal, 2.5));
    s.push(circle(withoutX, y, 5.5, C.white, C.gray, 1.7));
    s.push(circle(withX, y, 6, C.teal, C.teal, 1));
    s.push(text(withX, y - 15, score(withRow.affected_target_recall), 10.5, { weight: 700, anchor: "middle" }));
  });
  [0, 0.5, 1].forEach((value) => s.push(text(704 + 178 * value, 505, value.toFixed(1), 10, { fill: C.muted, anchor: "middle" })));
  s.push(line(704, 488, 882, 488, C.ink, 0.8));
  s.push(circle(698, 548, 4.5, C.teal, C.teal, 1));
  s.push(text(709, 552, "With retrieval", 10.3));
  s.push(circle(798, 548, 4.5, C.white, C.gray, 1.3));
  s.push(text(809, 552, "Without", 10.3));
  s.push(line(688, 580, 898, 580, C.rule, 0.8));
  s.push(text(688, 609, "Aggregate difference", 10.5, { fill: C.muted }));
  s.push(text(898, 609, "0.75 (0.50 to 0.92)", 11, { weight: 700, anchor: "end" }));
  s.push(text(898, 632, "P<0.001", 10.5, { anchor: "end" }));

  const columns = ["Recent KEV, 0–30 days", "Recent KEV, 31–60 days", "Recent KEV, 61–90 days", "Other CVE", "Synthetic misconfiguration"];
  const columnLabels = [["0–30", "d"], ["31–60", "d"], ["61–90", "d"], ["Other", "CVE"], ["Mis-", "config."]];
  const rowIds = [["qwen_single_rag", "Single"], ["qwen_autonomous_team", "Autonomous"], ["qwen_fixed_team", "Fixed"]];
  const hx = 998;
  const hy = 166;
  const cw = 34;
  const ch = 62;
  columnLabels.forEach((values, index) => s.push(multiline(hx + index * cw + 15, 108, values, 9.5, { weight: 700, fill: C.muted, anchor: "middle" })));
  rowIds.forEach(([id, label], rowIndex) => {
    const y = hy + rowIndex * ch;
    s.push(text(990, y + 32, label, 10.2, { weight: 700, anchor: "end" }));
    columns.forEach((stratum, columnIndex) => {
      const row = subgroup.find((item) => item.condition_id === id && item.stratum === stratum);
      const value = n(row.f1);
      const fill = value === 0 ? C.pale : value >= 0.8 ? C.teal : value >= 0.65 ? "#73AFB8" : "#B4D2D7";
      const x = hx + columnIndex * cw;
      s.push(rect(x, y, cw - 3, ch - 4, fill, C.white, 1));
      s.push(text(x + (cw - 3) / 2, y + 33, score(value), 9.4, { weight: 700, fill: value >= 0.8 ? C.white : C.ink, anchor: "middle" }));
    });
  });
  s.push(line(948, 385, 1166, 385, C.rule, 0.8));
  s.push(text(948, 419, "Clean controls", 10.5, { fill: C.muted }));
  s.push(text(1166, 419, "0 FP / 50 cells each", 10.5, { weight: 700, anchor: "end" }));
  s.push(text(948, 458, "Misconfiguration", 10.5, { fill: C.muted }));
  s.push(text(1166, 458, "F1 0.00", 10.5, { weight: 700, anchor: "end" }));
  s.push(line(948, 477, 1166, 477, C.grid, 0.8));
  s.push(multiline(948, 516, ["All three core Qwen", "configurations showed the", "same rule-based failure."], 10.5, { fill: C.muted, lineHeight: 1.35 }));
  s.push("</svg>");
  return s.join("\n");
}

const outputs = { figure1: figure1(), figure2: figure2(), figure3: figure3() };
for (const [stem, payload] of Object.entries(outputs)) {
  fs.writeFileSync(path.join(masterDir, `${stem}.svg`), payload, "utf8");
}
console.log(JSON.stringify({ output: masterDir, files: Object.keys(outputs).map((stem) => `${stem}.svg`), sourceDir }));
