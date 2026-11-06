const SUGGESTIONS = [
  "I want the credit card with the most cash back. I earn $100,000 a year.",
  "I need to change the email address on my account.",
  "There is a charge on my credit card that I do not recognise.",
  "Can I open another personal checking account?",
];

const PROFILE_FIELDS = [
  { key: "user_id", label: "Customer ID" },
  { key: "date_of_birth", label: "Date of birth" },
  { key: "email", label: "Email" },
  { key: "phone_number", label: "Phone" },
  { key: "address", label: "Address" },
];

const ICONS = {
  search: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"><circle cx="11" cy="11" r="7"/><path d="m20 20-4-4"/></svg>',
  done: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><path d="m5 13 4 4L19 7"/></svg>',
  blocked: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round"><path d="M6 6l12 12M18 6 6 18"/></svg>',
};

const customerCount = document.getElementById("customer-count");
const customerSearch = document.getElementById("customer-search");
const customerList = document.getElementById("customer-list");
const currentAvatar = document.getElementById("current-avatar");
const currentName = document.getElementById("current-name");
const caseNumber = document.getElementById("case-number");
const newCaseButton = document.getElementById("new-case-button");
const messages = document.getElementById("messages");
const welcome = document.getElementById("welcome");
const suggestions = document.getElementById("suggestions");
const messageForm = document.getElementById("message-form");
const messageInput = document.getElementById("message-input");
const sendButton = document.getElementById("send-button");
const formError = document.getElementById("form-error");
const activityTab = document.getElementById("activity-tab");
const profileTab = document.getElementById("profile-tab");
const activityPanel = document.getElementById("activity-panel");
const profilePanel = document.getElementById("profile-panel");
const activityEmpty = document.getElementById("activity-empty");
const timeline = document.getElementById("timeline");
const profile = document.getElementById("profile");
const statDocuments = document.getElementById("stat-documents");
const statActions = document.getElementById("stat-actions");
const statCost = document.getElementById("stat-cost");

let customers = [];
let selectedCustomer = null;
let currentCaseId = null;
let actionCount = 0;
let totalCost = 0;

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

function getInitials(name) {
  const words = name.split(" ");
  const first = words[0][0];
  const last = words[words.length - 1][0];
  return (first + last).toUpperCase();
}

function showCustomerList() {
  customerList.replaceChildren();
  const searchText = customerSearch.value.trim().toLowerCase();

  for (const customer of customers) {
    if (!customer.name.toLowerCase().includes(searchText)) {
      continue;
    }

    const button = makeElement("button", "customer-button");
    button.type = "button";
    if (customer === selectedCustomer) {
      button.classList.add("customer-active");
    }

    button.append(makeElement("span", "avatar", getInitials(customer.name)));
    button.append(makeElement("span", "customer-name", customer.name));
    button.addEventListener("click", function () {
      selectCustomer(customer);
    });

    const item = makeElement("li");
    item.append(button);
    customerList.append(item);
  }
}

function showProfile() {
  profile.replaceChildren();
  for (const field of PROFILE_FIELDS) {
    profile.append(makeElement("dt", "", field.label));
    profile.append(makeElement("dd", "", selectedCustomer[field.key]));
  }
}

function selectCustomer(customer) {
  selectedCustomer = customer;
  currentAvatar.textContent = getInitials(customer.name);
  currentName.textContent = customer.name;
  showCustomerList();
  showProfile();
  openNewCase();
}

function showSuggestions() {
  for (const text of SUGGESTIONS) {
    const button = makeElement("button", "suggestion", text);
    button.type = "button";
    button.addEventListener("click", function () {
      messageInput.value = text;
      messageInput.focus();
    });
    suggestions.append(button);
  }
}

function addMessage(author, text, className) {
  welcome.hidden = true;

  const message = makeElement("div", "message " + className);
  message.append(makeElement("p", "message-author", author));
  message.append(makeElement("p", "message-text", text));
  messages.append(message);
  messages.scrollTop = messages.scrollHeight;
  return message;
}

function addTypingMessage() {
  const message = addMessage("Teller", "", "message-teller");
  const typing = makeElement("div", "typing");
  typing.append(makeElement("span"), makeElement("span"), makeElement("span"));
  message.querySelector(".message-text").append(typing);
  messages.scrollTop = messages.scrollHeight;
  return message;
}

function addTimelineItem(iconName, label, title) {
  activityEmpty.hidden = true;

  const item = makeElement("li", "timeline-item");
  const icon = makeElement("span", "timeline-icon icon-" + iconName);
  icon.innerHTML = ICONS[iconName];

  const body = makeElement("div");
  body.append(makeElement("p", "timeline-label", label));
  body.append(makeElement("p", "timeline-title", title));

  item.append(icon, body);
  timeline.prepend(item);
  return body;
}

function addStep(step) {
  if (step.kind === "search") {
    const body = addTimelineItem("search", "Searched policies", step.text);
    const titles = step.details || [];

    if (titles.length === 0) {
      body.append(makeElement("p", "timeline-note", "No new documents"));
      return;
    }

    const list = makeElement("ul", "timeline-list");
    for (const title of titles) {
      list.append(makeElement("li", "", title));
    }
    body.append(list);
    return;
  }

  if (step.kind === "blocked") {
    const body = addTimelineItem("blocked", "Blocked by check", step.text);
    body.append(makeElement("p", "timeline-note", step.details[0]));
  }
}

function addAction(action) {
  let iconName = "done";
  let label = "Bank action";
  if (action.failed) {
    iconName = "blocked";
    label = "Bank action failed";
  }

  const body = addTimelineItem(iconName, label, action.text);
  const code = JSON.stringify(action.arguments, null, 1);
  body.append(makeElement("pre", "timeline-code", code));

  actionCount += 1;
  statActions.textContent = actionCount;
}

function showActivityTab() {
  activityTab.classList.add("tab-active");
  profileTab.classList.remove("tab-active");
  activityPanel.hidden = false;
  profilePanel.hidden = true;
}

function showProfileTab() {
  profileTab.classList.add("tab-active");
  activityTab.classList.remove("tab-active");
  profilePanel.hidden = false;
  activityPanel.hidden = true;
}

function clearCaseView() {
  const oldMessages = messages.querySelectorAll(".message");
  for (const message of oldMessages) {
    message.remove();
  }

  timeline.replaceChildren();
  welcome.hidden = false;
  activityEmpty.hidden = false;
  formError.textContent = "";
  actionCount = 0;
  totalCost = 0;
  statDocuments.textContent = "0";
  statActions.textContent = "0";
  statCost.textContent = "$0.00";
}

async function openNewCase() {
  clearCaseView();
  caseNumber.textContent = "opening";

  try {
    const newCase = await postJson("/api/cases", {});
    currentCaseId = newCase.id;
    caseNumber.textContent = newCase.id;
  } catch (error) {
    caseNumber.textContent = "not opened";
    formError.textContent = error.message;
  }
}

async function handleSubmit(event) {
  event.preventDefault();

  const text = messageInput.value.trim();
  if (!text || !currentCaseId) {
    return;
  }

  formError.textContent = "";
  sendButton.disabled = true;
  messageInput.value = "";
  addMessage("Customer", text, "message-customer");
  const typingMessage = addTypingMessage();

  try {
    const path = "/api/cases/" + currentCaseId + "/messages";
    const result = await postJson(path, { text: text });

    typingMessage.remove();
    for (const step of result.steps) {
      addStep(step);
    }
    for (const action of result.actions) {
      addAction(action);
    }
    addMessage("Teller", result.reply, "message-teller");

    totalCost += result.cost;
    statDocuments.textContent = result.documents_found;
    statCost.textContent = "$" + totalCost.toFixed(4);
  } catch (error) {
    typingMessage.remove();
    formError.textContent = error.message;
    messageInput.value = text;
  }

  sendButton.disabled = false;
  messageInput.focus();
}

async function start() {
  showSuggestions();
  customerSearch.addEventListener("input", showCustomerList);
  messageForm.addEventListener("submit", handleSubmit);
  newCaseButton.addEventListener("click", openNewCase);
  activityTab.addEventListener("click", showActivityTab);
  profileTab.addEventListener("click", showProfileTab);

  try {
    customers = await getJson("/api/customers");
    customerCount.textContent = customers.length;
    selectCustomer(customers[0]);
  } catch (error) {
    formError.textContent = error.message;
  }
}

start();
