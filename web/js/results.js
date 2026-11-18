const PIPELINE_ORDER = ["no_docs", "bm25", "teller_no_checks", "teller", "teller_golden", "golden"];

// The same names as in teller/benchmark/pipelines.py, shown before a pipeline has a run
const PIPELINE_LABELS = {
  no_docs: "No documents",
  bm25: "Plain RAG (BM25 tool)",
  teller_no_checks: "Teller without checks",
  teller: "Teller",
  teller_golden: "Teller, correct documents given",
  golden: "Benchmark agent, correct documents given",
};

const TELLER_SEARCH_METHOD = "Hybrid + reranker";

const pipelineBars = document.getElementById("pipeline-bars");
const runRows = document.getElementById("run-rows");
const runsEmpty = document.getElementById("runs-empty");
const runDetail = document.getElementById("run-detail");
const runName = document.getElementById("run-name");
const taskRows = document.getElementById("task-rows");
const retrievalBars = document.getElementById("retrieval-bars");
const retrievalTable = document.getElementById("retrieval-table");
const retrievalRows = document.getElementById("retrieval-rows");
const retrievalEmpty = document.getElementById("retrieval-empty");
const retrievalLegend = document.getElementById("retrieval-legend");

function makeElement(tag, className, text) {
  const element = document.createElement(tag);
  if (className) {
    element.className = className;
  }
  if (text !== undefined) {
    element.textContent = text;
  }
  return element;
}

function addCell(row, text, className) {
  const cell = makeElement("td", className, text);
  row.append(cell);
  return cell;
}

function formatPercent(value) {
  if (value === null || value === undefined) {
    return "n/a";
  }
  return (value * 100).toFixed(1) + "%";
}

function formatCost(value) {
  if (!value) {
    return "$0";
  }
  return "$" + value.toFixed(4);
}

function formatTaskCount(count) {
  if (count === 1) {
    return "1 task";
  }
  return count + " tasks";
}

function addBar(container, label, sublabel, value, tooltip) {
  // Draws one row of a bar chart and returns it, so the caller can mark it
  const row = makeElement("div", "bar-row");
  row.title = tooltip;

  const labelBox = makeElement("div", "bar-label", label);
  if (sublabel) {
    labelBox.append(makeElement("div", "bar-sublabel", sublabel));
  }

  const track = makeElement("div", "bar-track");
  const fill = makeElement("div", "bar-fill");
  fill.style.width = (value * 100) + "%";
  track.append(fill);

  row.append(labelBox, track, makeElement("div", "bar-value", formatPercent(value)));
  container.append(row);
  return row;
}

function addEmptyBar(container, label) {
  const row = makeElement("div", "bar-row bar-empty");
  row.append(makeElement("div", "bar-label", label));
  row.append(makeElement("div", "bar-track"));
  row.append(makeElement("div", "bar-value", "Not run"));
  container.append(row);
  return row;
}

function addTick(row, value) {
  // A thin mark on the track, used for the best possible score
  const tick = makeElement("span", "bar-tick");
  tick.style.left = (value * 100) + "%";
  row.querySelector(".bar-track").append(tick);
}

function getLatestRuns(runs) {
  // The API lists the newest runs first, so the first one seen for a pipeline is the latest.
  // Runs that tried another search method stay in the table below, out of the chart.
  const latestRuns = {};
  for (const run of runs) {
    if (!run.usual_search) {
      continue;
    }
    if (!latestRuns[run.pipeline]) {
      latestRuns[run.pipeline] = run;
    }
  }
  return latestRuns;
}

function showTiles(latestRuns) {
  const teller = latestRuns.teller;
  if (teller) {
    document.getElementById("tile-teller").textContent = formatPercent(teller.success_rate);
    document.getElementById("tile-teller-note").textContent = teller.passed + " of " + formatTaskCount(teller.tasks_run) + ", " + teller.split;
    document.getElementById("tile-cost").textContent = formatCost(teller.cost_per_task);
  }

  const baseline = latestRuns.bm25;
  if (baseline) {
    document.getElementById("tile-baseline").textContent = formatPercent(baseline.success_rate);
    document.getElementById("tile-baseline-note").textContent = baseline.passed + " of " + formatTaskCount(baseline.tasks_run) + ", " + baseline.split;
  }
}

function showPipelineBars(latestRuns) {
  // Every pipeline gets a row, so the chart shows what is still missing
  for (const pipeline of PIPELINE_ORDER) {
    const run = latestRuns[pipeline];

    let row = null;
    if (run) {
      const sublabel = formatTaskCount(run.tasks_run) + ", " + run.split;
      const tooltip = run.label + ": " + run.passed + " of " + formatTaskCount(run.tasks_run) + " passed on " + run.model;
      row = addBar(pipelineBars, run.label, sublabel, run.success_rate, tooltip);
    } else {
      row = addEmptyBar(pipelineBars, PIPELINE_LABELS[pipeline]);
    }

    if (pipeline === "teller") {
      row.classList.add("bar-main");
    }
  }
}

function addRunRow(run) {
  const row = makeElement("tr");

  const nameCell = addCell(row);
  const button = makeElement("button", "run-button", run.label);
  button.type = "button";
  button.addEventListener("click", function () {
    showRun(run.id);
  });
  nameCell.append(button);

  addCell(row, run.split);
  addCell(row, run.model);
  addCell(row, run.tasks_run, "number");
  addCell(row, formatPercent(run.success_rate), "number");
  addCell(row, formatPercent(run.document_recall), "number");
  addCell(row, formatCost(run.cost_per_task), "number");
  addCell(row, run.seconds_per_task, "number");
  runRows.append(row);
}

function addTaskRow(task) {
  const row = makeElement("tr");
  addCell(row, task.task_id);

  const outcomeCell = addCell(row);
  if (task.reward === 1) {
    outcomeCell.append(makeElement("span", "outcome outcome-passed", "Passed"));
  } else {
    outcomeCell.append(makeElement("span", "outcome outcome-failed", "Failed: " + task.failure));
  }

  addCell(row, task.ending);
  addCell(row, formatPercent(task.document_recall), "number");
  addCell(row, task.messages, "number");
  addCell(row, task.seconds, "number");
  taskRows.append(row);
}

async function showRun(runId) {
  const run = await getJson("/api/runs/" + encodeURIComponent(runId));

  runName.textContent = run.id;
  taskRows.replaceChildren();
  for (const task of run.tasks) {
    addTaskRow(task);
  }

  runDetail.hidden = false;
  runDetail.scrollIntoView({ behavior: "smooth", block: "nearest" });
}

function showRecallTile(report) {
  for (const item of report.table) {
    if (item.method !== TELLER_SEARCH_METHOD) {
      continue;
    }

    document.getElementById("tile-recall").textContent = formatPercent(item.recall_at_10);
    if (report.best_possible) {
      const ceiling = formatPercent(report.best_possible.recall_at_10);
      document.getElementById("tile-recall-note").textContent = "Out of " + ceiling + " possible with one search";
    }
  }
}

function showRetrieval(report) {
  retrievalEmpty.hidden = true;
  retrievalTable.hidden = false;

  if (report.best_possible) {
    retrievalLegend.hidden = false;
  }

  for (const item of report.table) {
    const tooltip = item.method + ": recall at 10 on " + report.tasks + " tasks";
    const bar = addBar(retrievalBars, item.method, "", item.recall_at_10, tooltip);

    if (item.method === TELLER_SEARCH_METHOD) {
      bar.classList.add("bar-main");
    }
    if (report.best_possible) {
      addTick(bar, report.best_possible.recall_at_10);
    }

    const row = makeElement("tr");
    addCell(row, item.method);
    addCell(row, formatPercent(item.recall_at_5), "number");
    addCell(row, formatPercent(item.recall_at_10), "number");
    addCell(row, formatPercent(item.recall_at_20), "number");
    addCell(row, formatPercent(item.tool_name_hit_rate), "number");
    retrievalRows.append(row);
  }

  // A task can need more documents than one search returns, so this is the ceiling
  if (report.best_possible) {
    const row = makeElement("tr", "row-note");
    addCell(row, "Best possible with one search");
    addCell(row, formatPercent(report.best_possible.recall_at_5), "number");
    addCell(row, formatPercent(report.best_possible.recall_at_10), "number");
    addCell(row, formatPercent(report.best_possible.recall_at_20), "number");
    addCell(row, "");
    retrievalRows.append(row);
  }
}

async function start() {
  const results = await getJson("/api/results");

  if (results.runs.length > 0) {
    runsEmpty.hidden = true;
  }

  const latestRuns = getLatestRuns(results.runs);
  showTiles(latestRuns);
  showPipelineBars(latestRuns);

  for (const run of results.runs) {
    addRunRow(run);
  }

  if (results.retrieval) {
    showRecallTile(results.retrieval);
    showRetrieval(results.retrieval);
  }
}

start();
