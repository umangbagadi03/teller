// Light or dark theme. Loaded in <head>, so the page never flashes the wrong colours.
// The visitor's choice is remembered in this browser. Without one, the system setting decides.

const THEME_STORAGE = "teller-theme";

function getSavedTheme() {
  // Storage can be blocked, for example in a private window
  try {
    return localStorage.getItem(THEME_STORAGE);
  } catch (error) {
    return null;
  }
}

function saveTheme(theme) {
  try {
    localStorage.setItem(THEME_STORAGE, theme);
  } catch (error) {
    // The theme still changes, it is only not remembered
  }
}

function getStartTheme() {
  const saved = getSavedTheme();
  if (saved === "light" || saved === "dark") {
    return saved;
  }

  if (window.matchMedia("(prefers-color-scheme: dark)").matches) {
    return "dark";
  }
  return "light";
}

function applyTheme(theme) {
  document.documentElement.dataset.theme = theme;
}

function updateThemeButton(button) {
  if (document.documentElement.dataset.theme === "dark") {
    button.setAttribute("aria-label", "Switch to light mode");
  } else {
    button.setAttribute("aria-label", "Switch to dark mode");
  }
  button.title = button.getAttribute("aria-label");
}

function toggleTheme() {
  let next = "dark";
  if (document.documentElement.dataset.theme === "dark") {
    next = "light";
  }

  applyTheme(next);
  saveTheme(next);
  updateThemeButton(document.getElementById("theme-button"));
}

function startThemeButton() {
  const button = document.getElementById("theme-button");
  button.addEventListener("click", toggleTheme);
  updateThemeButton(button);
}

applyTheme(getStartTheme());
document.addEventListener("DOMContentLoaded", startThemeButton);
