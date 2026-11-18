// The model menu in the top bar: the server's model, the offline demo, or the visitor's own key.
// The choice is kept in this tab only (sessionStorage), so closing the tab forgets the key.

const STORAGE_NAME = "teller-model";

const modelButton = document.getElementById("model-button");
const modelName = document.getElementById("model-name");
const modelPanel = document.getElementById("model-panel");
const serverTitle = document.getElementById("server-title");
const serverNote = document.getElementById("server-note");
const offlineOption = document.getElementById("offline-option");
const keyFields = document.getElementById("key-fields");
const keyProvider = document.getElementById("key-provider");
const keyModel = document.getElementById("key-model");
const keyValue = document.getElementById("key-value");
const modelError = document.getElementById("model-error");
const modelCancel = document.getElementById("model-cancel");
const modelApply = document.getElementById("model-apply");

let serverStatus = null;
let modelChoice = { source: "server", provider: "gemini", model: "", key: "" };

function loadSavedChoice() {
  // Storage can be blocked, for example in a private window, so every use is wrapped
  try {
    const saved = sessionStorage.getItem(STORAGE_NAME);
    if (saved) {
      modelChoice = JSON.parse(saved);
    }
  } catch (error) {
    modelChoice = { source: "server", provider: "gemini", model: "", key: "" };
  }
}

function saveChoice() {
  try {
    sessionStorage.setItem(STORAGE_NAME, JSON.stringify(modelChoice));
  } catch (error) {
    // The choice still works for this page, it is only not remembered
  }
}

function getSelectedSource() {
  const selected = document.querySelector('input[name="model-source"]:checked');
  return selected.value;
}

function selectSource(source) {
  const radio = document.querySelector('input[name="model-source"][value="' + source + '"]');
  if (radio) {
    radio.checked = true;
  }
  keyFields.hidden = source !== "own";
}

function showDefaultModel() {
  // The model box shows the provider's usual model until the visitor types another one
  if (serverStatus) {
    keyModel.placeholder = serverStatus.default_models[keyProvider.value];
  }
}

function getModelRequest() {
  // What desk.js sends when it opens a case
  if (modelChoice.source === "own") {
    return {
      provider: modelChoice.provider,
      model: modelChoice.model,
      api_key: modelChoice.key,
    };
  }
  if (modelChoice.source === "offline") {
    return { provider: "offline" };
  }
  return { provider: "server" };
}

function showModelName(label) {
  modelName.textContent = formatModel(label);
}

function openModelPanel() {
  selectSource(modelChoice.source);
  keyProvider.value = modelChoice.provider;
  keyModel.value = modelChoice.model;
  keyValue.value = modelChoice.key;
  modelError.textContent = "";
  showDefaultModel();

  modelPanel.hidden = false;
  modelButton.setAttribute("aria-expanded", "true");
}

function closeModelPanel() {
  modelPanel.hidden = true;
  modelButton.setAttribute("aria-expanded", "false");
}

function toggleModelPanel() {
  if (modelPanel.hidden) {
    openModelPanel();
  } else {
    closeModelPanel();
  }
}

function applyModelChoice() {
  const source = getSelectedSource();
  const key = keyValue.value.trim();

  if (source === "own" && key.length < 10) {
    modelError.textContent = "Paste a full API key first";
    keyValue.focus();
    return;
  }

  modelChoice = {
    source: source,
    provider: keyProvider.value,
    model: keyModel.value.trim(),
    key: "",
  };
  if (source === "own") {
    modelChoice.key = key;
  }

  saveChoice();
  closeModelPanel();
  openNewCase();
}

function handleOutsideClick(event) {
  if (modelPanel.hidden) {
    return;
  }
  if (modelPanel.contains(event.target) || modelButton.contains(event.target)) {
    return;
  }
  closeModelPanel();
}

function handleEscape(event) {
  if (event.key === "Escape" && !modelPanel.hidden) {
    closeModelPanel();
    modelButton.focus();
  }
}

async function loadServerStatus() {
  try {
    serverStatus = await getJson("/api/status");
  } catch (error) {
    serverNote.textContent = "Not available";
    return;
  }

  // With no model on the server, the server option is the offline demo itself
  if (serverStatus.offline) {
    serverTitle.textContent = "Offline demo";
    serverNote.textContent = "No key needed. A script plays the model.";
    offlineOption.hidden = true;
  } else {
    serverNote.textContent = formatModel(serverStatus.label);
  }
  showDefaultModel();
}

function startModelMenu() {
  loadSavedChoice();

  modelButton.addEventListener("click", toggleModelPanel);
  modelCancel.addEventListener("click", closeModelPanel);
  modelApply.addEventListener("click", applyModelChoice);
  keyProvider.addEventListener("change", showDefaultModel);
  document.addEventListener("click", handleOutsideClick);
  document.addEventListener("keydown", handleEscape);

  const radios = document.querySelectorAll('input[name="model-source"]');
  for (const radio of radios) {
    radio.addEventListener("change", function () {
      selectSource(radio.value);
    });
  }

  loadServerStatus();
}

startModelMenu();
