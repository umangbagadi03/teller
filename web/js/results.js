const PIPELINE_ORDER = ["no_docs", "bm25", "teller_no_checks", "teller", "teller_golden", "golden"];

const pipelineBars = document.getElementById("pipeline-bars");
const pipelineEmpty = document.getElementById("pipeline-empty");
const runRows = document.getElementById("run-rows");
const runsEmpty = document.getElementById("runs-empty");
const runDetail = document.getElementById("run-detail");
const runName = document.getElementById("run-name");
const taskRows = document.getElementById("task-rows");
const retrievalBars = document.getElementById("retrieval-bars");
const retrievalTable = document.getElementById("retrieval-table");
const retrievalRows = document.getElementById("retrieval-rows");
const retrievalEmpty = document.getElementById("retrieval-empty");

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
}

function getLatestRuns(runs) {
  // The API lists the newest runs first, so the first one seen for a pipeline is the latest
  const latestRuns = {};
  for (const run of runs) {
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
  for (const pipeline of PIPELINE_ORDER) {
    const run = latestRuns[pipeline];
    if (!run) {
      continue;
    }

    pipelineEmpty.hidden = true;
    const sublabel = formatTaskCount(run.tasks_run) + ", " + run.split;
    const tooltip = run.label + ": " + run.passed + " of " + formatTaskCount(run.tasks_run) + " passed on " + run.model;
    addBar(pipelineBars, run.label, sublabel, run.success_rate, tooltip);
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

function showRetrieval(report) {
  retrievalEmpty.hidden = true;
  retrievalTable.hidden = false;

  for (const item of report.table) {
    const tooltip = item.method + ": recall at 10 on " + report.tasks + " tasks";
    addBar(retrievalBars, item.method, "", item.recall_at_10, tooltip);

    const row = makeElement("tr");
    addCell(row, item.method);
    addCell(row, formatPercent(item.recall_at_5), "number");
    addCell(row, formatPercent(item.recall_at_10), "number");
    addCell(row, formatPercent(item.recall_at_20), "number");
    addCell(row, formatPercent(item.tool_name_hit_rate), "number");
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
    showRetrieval(results.retrieval);
  }
}

start();
