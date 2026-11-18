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

const PROVIDER_NAMES = {
  gemini: "Gemini",
  anthropic: "Anthropic",
  openai: "OpenAI",
  ollama: "Ollama",
};

async function showModelLine() {
  const line = document.getElementById("model-line");
  try {
    const status = await getJson("/api/status");

    // The model looks like "gemini/gemini-2.5-flash-lite". Keep what is after the first slash.
    const slash = status.model.indexOf("/");
    const modelName = status.model.slice(slash + 1);

    line.textContent = PROVIDER_NAMES[status.provider] + " · " + modelName;
  } catch (error) {
    line.textContent = "Model not available";
  }
}

showModelLine();
