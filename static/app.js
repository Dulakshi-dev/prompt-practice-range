const chatLog = document.getElementById("chat-log");
const chatInput = document.getElementById("chat-input");
const sendBtn = document.getElementById("send-btn");
const turnsUsedEl = document.getElementById("turns-used");
const turnsMaxEl = document.getElementById("turns-max");
const finalEmailEl = document.getElementById("final-email");
const gradeBtn = document.getElementById("grade-btn");
const resultPanel = document.getElementById("result-panel");
const restartBtn = document.getElementById("restart-btn");

let history = [];
let scenario = null;

function addMessage(role, content) {
  const div = document.createElement("div");
  div.className = `msg ${role}`;
  div.textContent = content;
  chatLog.appendChild(div);
  chatLog.scrollTop = chatLog.scrollHeight;
}

function addSystemNote(text) {
  const div = document.createElement("div");
  div.className = "msg system-note";
  div.textContent = text;
  chatLog.appendChild(div);
  chatLog.scrollTop = chatLog.scrollHeight;
}

function showError(msg) {
  const div = document.createElement("div");
  div.className = "error-banner";
  div.textContent = msg;
  chatLog.appendChild(div);
  chatLog.scrollTop = chatLog.scrollHeight;
}

async function loadScenario() {
  const res = await fetch("/api/scenario");
  scenario = await res.json();
  document.getElementById("scenario-title").textContent = scenario.title;
  document.getElementById("scenario-brief").textContent = scenario.brief;
  turnsMaxEl.textContent = scenario.max_turns;
}

async function sendMessage() {
  const text = chatInput.value.trim();
  if (!text) return;

  const userTurns = history.filter((h) => h.role === "user").length;
  if (userTurns >= scenario.max_turns) {
    addSystemNote("Turn limit reached — paste your final email below.");
    return;
  }

  history.push({ role: "user", content: text });
  addMessage("user", text);
  chatInput.value = "";
  sendBtn.disabled = true;

  try {
    const res = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ history }),
    });
    if (!res.ok) {
      const err = await res.json();
      showError(err.detail || "Something went wrong.");
      return;
    }
    const data = await res.json();
    history.push({ role: "assistant", content: data.reply });
    addMessage("assistant", data.reply);
    turnsUsedEl.textContent = data.turns_used;
    if (data.turns_remaining === 0) {
      addSystemNote("Turn limit reached — paste your final email below when ready.");
    }
  } catch (e) {
    showError("Network error — check the backend is running and reachable.");
  } finally {
    sendBtn.disabled = false;
  }
}

function scoreRow(label, value) {
  const row = document.createElement("div");
  row.className = "score-row";
  row.innerHTML = `
    <div class="score-label">${label}</div>
    <div class="score-track"><div class="score-fill" style="width:${value * 10}%"></div></div>
    <div class="score-value">${value}</div>
  `;
  return row;
}

async function submitForGrading() {
  const finalEmail = finalEmailEl.value.trim();
  if (!finalEmail) {
    alert("Paste your final email first.");
    return;
  }
  gradeBtn.disabled = true;
  gradeBtn.textContent = "Grading…";

  try {
    const res = await fetch("/api/grade", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ history, final_email: finalEmail }),
    });
    if (!res.ok) {
      const err = await res.json();
      alert("Grading failed: " + (err.detail || res.statusText));
      return;
    }
    const data = await res.json();

    const bars = document.getElementById("score-bars");
    bars.innerHTML = "";
    bars.appendChild(scoreRow("Specificity", data.specificity));
    bars.appendChild(scoreRow("Iteration quality", data.iteration_quality));
    bars.appendChild(scoreRow("Verification habit", data.verification_habit));
    bars.appendChild(scoreRow("Efficiency", data.efficiency));

    document.getElementById("overall-score").textContent = `${data.overall} / 10`;
    document.getElementById("verdict").textContent = data.one_line_verdict;
    document.getElementById("strength").textContent = data.strength;
    document.getElementById("improve").textContent = data.improve;

    resultPanel.classList.remove("hidden");
    resultPanel.scrollIntoView({ behavior: "smooth" });
  } catch (e) {
    alert("Network error while grading.");
  } finally {
    gradeBtn.disabled = false;
    gradeBtn.textContent = "Submit for grading";
  }
}

sendBtn.addEventListener("click", sendMessage);
chatInput.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    sendMessage();
  }
});
gradeBtn.addEventListener("click", submitForGrading);
restartBtn.addEventListener("click", () => window.location.reload());

loadScenario();
