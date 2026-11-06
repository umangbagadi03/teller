async function readJson(response) {
  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.detail || "The request failed.");
  }
  return data;
}

async function getJson(path) {
  const response = await fetch(path);
  return readJson(response);
}

async function postJson(path, body) {
  const response = await fetch(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  return readJson(response);
}

async function showModelLine() {
  const line = document.getElementById("model-line");
  try {
    const status = await getJson("/api/status");
    const modelName = status.model.split("/").slice(1).join("/");
    line.textContent = status.provider + " · " + modelName;
  } catch (error) {
    line.textContent = "Model not available";
  }
}

showModelLine();
