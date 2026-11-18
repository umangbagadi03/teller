async function readJson(response) {
  const data = await response.json();
  if (!response.ok) {
    let message = "The request failed";
    if (data.detail) {
      message = data.detail;
    }
    throw new Error(message);
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
  ollama_chat: "Ollama",
};

function formatModel(model) {
  // "gemini/gemini-2.5-flash-lite" becomes "Gemini · gemini-2.5-flash-lite"
  const slash = model.indexOf("/");
  if (slash === -1) {
    return model;
  }

  const provider = model.slice(0, slash);
  const modelName = model.slice(slash + 1);
  let providerName = provider;
  if (PROVIDER_NAMES[provider]) {
    providerName = PROVIDER_NAMES[provider];
  }
  return providerName + " · " + modelName;
}

async function showModelLine() {
  // Only the Results page has this line. The Console has the model menu instead.
  const line = document.getElementById("model-line");
  if (!line) {
    return;
  }

  try {
    const status = await getJson("/api/status");
    line.textContent = formatModel(status.label);
  } catch (error) {
    line.textContent = "Model not available";
  }
}

showModelLine();
