"use strict";

const bank = globalThis.QUIZ_BANK;
const rules = globalThis.QuizRules;
const screen = document.querySelector("#app-screen");
const device = document.querySelector("#device");
const deviceArea = document.querySelector("#device-area");
const deviceFit = document.querySelector("#device-fit");
const dimensions = document.querySelector("#dimensions");
const deviceSize = document.querySelector("#device-size");
const resumeGame = document.querySelector("#resume-game");
const duration = 10_000;
const storageKey = "stats-quiz-phone-preview-v1";
const players = ["Player 1", "Player 2"];
const bonuses = ["AI/ML", "Pro"];

const setup = { mode: "solo", level: "100", count: 10 };
let phase = "home";
let session = null;
let inspection = null;
let formulaChoice;
let best = readBest();

function readBest() {
  try {
    const stored = JSON.parse(localStorage.getItem(storageKey) ?? "{}");
    return Object.fromEntries(Object.entries(stored).filter(([, value]) =>
      typeof value === "number" && value >= 0 && value <= 1
    ));
  } catch {
    return {};
  }
}

function remember(level, outcomes) {
  best[level] = Math.max(best[level] ?? 0, correctCount(outcomes) / outcomes.length);
  try {
    localStorage.setItem(storageKey, JSON.stringify(best));
  } catch {
    // The active preview still keeps progress if this browser blocks local storage.
  }
}

function el(tag, className = "", text = "") {
  const node = document.createElement(tag);
  node.className = className;
  node.textContent = text;
  return node;
}

function levelName(level) {
  return {
    "100": "Level 100", "200": "Level 200", "300": "Level 300", "400": "Level 400",
    "AI/ML": "AI/ML Bonus", Pro: "Pro · Bring It All",
  }[level] ?? level;
}

function modeName() {
  return setup.mode === "solo" ? "Solo" : "Pass-and-play";
}

function correctCount(outcomes) {
  return outcomes.filter(outcome => outcome.correct).length;
}

function unlocked(level) {
  return bonuses.includes(level) ||
    rules.LEVELS.slice(0, rules.LEVELS.indexOf(level)).every(prior => best[prior] >= .6);
}

function icon() {
  const sigma = device.dataset.icon === "sigma";
  const mark = el("span", sigma ? "app-icon sigma" : "app-icon", sigma ? "Σ" : "");
  mark.setAttribute("aria-hidden", "true");
  if (!sigma) for (let i = 0; i < 5; i++) mark.append(el("i"));
  return mark;
}

function gameButton(label, action, { primary = false, note = "", disabled = false } = {}) {
  const button = el("button", primary ? "game-button primary" : "game-button");
  button.type = "button";
  button.disabled = disabled;
  const words = el("span", "", label);
  if (note) words.append(el("small", "button-note", note));
  const arrow = el("span", "", "→");
  arrow.setAttribute("aria-hidden", "true");
  button.append(words, arrow);
  button.addEventListener("click", action);
  return button;
}

function go(next) {
  phase = next;
  if (inspection === null) render();
}

function backBar(label, onBack, detail = "") {
  const bar = el("div", "screen-top");
  const back = el("button", "back", "‹ " + label);
  back.type = "button";
  back.addEventListener("click", onBack);
  bar.append(back, el("span", "", detail));
  return bar;
}

function renderHome() {
  const home = el("div", "home");
  const hero = el("div", "home-hero");
  const heading = el("h2");
  for (const word of ["Games", "Statisticians", "Play"]) heading.append(el("span", "", word + " "));
  hero.append(icon(), heading, el("p", "", "Name the concept in 10 seconds."));
  const actions = el("div", "home-actions");
  actions.append(
    gameButton("Solo", () => { setup.mode = "solo"; go("levels"); },
      { primary: true, note: "Unlock levels as you play" }),
    gameButton("Pass-and-play", () => { setup.mode = "match"; go("levels"); },
      { note: "Two players · One phone" }),
  );
  home.append(hero, actions);
  screen.append(home);
}

function renderLevels() {
  const list = el("div", "level-list");
  for (const level of [...rules.LEVELS, ...bonuses]) {
    if (level === bonuses[0]) list.append(el("p", "levels-subtitle", "Optional play"));
    const locked = setup.mode === "solo" && !unlocked(level);
    const note = locked ? "Locked" : setup.mode === "solo" && level in best
      ? "Best " + Math.round(best[level] * 100) + "%"
      : "";
    list.append(gameButton(levelName(level), () => { setup.level = level; go("length"); }, { note, disabled: locked }));
  }
  screen.append(backBar("Home", () => go("home"), modeName()), el("h2", "", "Choose a level"), list);
}

function renderLength() {
  const form = el("form", "length-form");
  const label = el("label", "", setup.mode === "solo" ? "Questions · 1 to 20" : "Questions per player · 1 to 20");
  label.htmlFor = "round-count";
  const input = el("input");
  Object.assign(input, { id: "round-count", type: "number", min: "1", max: "20", step: "1", required: true, value: setup.count });
  input.inputMode = "numeric";
  const submit = el("button", "game-button primary", setup.mode === "solo" ? "Start round" : "Start match");
  submit.type = "submit";
  form.append(label, input, submit);
  form.addEventListener("submit", event => {
    event.preventDefault();
    setup.count = input.valueAsNumber;
    start();
  });
  screen.append(backBar("Levels", () => go("levels"), modeName()), el("h2", "", levelName(setup.level)));
  if (setup.level === "Pro") screen.append(el("p", "muted", "Mostly higher years, with AI/ML and earlier years mixed in."));
  screen.append(form);
}

function start() {
  const solo = setup.mode === "solo";
  session = {
    index: 0,
    solo: solo ? rules.drawSolo(bank, setup.level, setup.count) : null,
    pairs: solo ? null : rules.drawPairs(bank, setup.level, setup.count),
    outcomes: solo ? [[]] : [[], []],
    turn: null,
    winner: null,
  };
  if (solo) startTurn();
  else go("ready");
}

function startTurn() {
  const question = session.solo
    ? session.solo[session.index]
    : session.pairs[Math.floor(session.index / 2)][session.index % 2];
  session.turn = { question, choices: rules.shuffle(question.choices), started: performance.now() };
  go("question");
}

function renderReady() {
  const player = players[session.index % 2];
  const handover = el("div", "handover");
  const ready = gameButton("Ready", startTurn, { primary: true });
  handover.append(
    el("p", "muted", "Pass the phone"), el("h2", "", player + ", your turn"),
    el("p", "", "The countdown starts when you tap Ready."), ready,
  );
  screen.append(handover);
}

function renderOptions(question, choices, onChoice) {
  const options = el("div", "options");
  choices.forEach((choice, index) => {
    const button = el("button", "game-button");
    button.type = "button";
    const letter = el("span", "option-letter", String.fromCharCode(65 + index));
    letter.setAttribute("aria-hidden", "true");
    button.append(letter, el("span", "", choice));
    button.addEventListener("click", () => onChoice(choice));
    options.append(button);
  });
  screen.append(el("h2", "quiz-heading", "Name the concept"), el("p", "clue", question.clue), options);
}

function renderQuestion() {
  const turn = session.turn;
  const header = el("div", "screen-top");
  let description = levelName(setup.level) + " · " + (session.index + 1) + "/" + setup.count;
  if (session.pairs) {
    const pair = Math.floor(session.index / 2);
    description = players[session.index % 2] + " · " + (pair >= setup.count ? "Sudden death" : (pair + 1) + "/" + setup.count);
  }
  const timer = el("span", "countdown", "10s");
  timer.id = "countdown";
  const track = el("div", "timer-track");
  track.setAttribute("aria-hidden", "true");
  const fill = el("div");
  fill.id = "timer-fill";
  track.append(fill);
  header.append(el("span", "", description), timer);
  screen.append(header, track);
  renderOptions(turn.question, turn.choices, choice => submitTurn(choice, turn));
}

function submitTurn(choice, turn) {
  if (phase !== "question" || session.turn !== turn) return;
  const elapsed = Math.min(duration, Math.floor(performance.now() - turn.started));
  const result = { question: turn.question, choice: elapsed >= duration ? null : choice, elapsed };
  result.correct = result.choice === result.question.answer;
  session.turn = null;
  if (session.solo) {
    session.outcomes[0].push(result);
    if (session.outcomes[0].length === setup.count) remember(setup.level, session.outcomes[0]);
    go("feedback");
  } else {
    session.outcomes[session.index % 2].push(result);
    session.index++;
    session.winner = rules.matchWinner(session.outcomes, setup.count);
    go(session.winner === null ? "ready" : "results");
  }
}

function tick() {
  const turn = session?.turn;
  if (!turn) return;
  const remaining = Math.max(0, duration - (performance.now() - turn.started));
  if (remaining === 0) {
    submitTurn(null, turn);
    return;
  }
  const timer = document.querySelector("#countdown");
  if (timer) {
    const reading = Math.ceil(remaining / 1000) + "s";
    if (timer.textContent !== reading) timer.textContent = reading;
    document.querySelector("#timer-fill").style.transform = "scaleX(" + remaining / duration + ")";
  }
}

function renderFeedback() {
  const result = session.outcomes[0].at(-1);
  const status = result.correct ? "Correct" : result.choice === null ? "Time’s up" : "Incorrect";
  const note = el("div", "outcome-note");
  note.append(
    el("p", "", "Answer · " + result.question.answer),
    el("p", "muted", result.question.explanation),
  );
  screen.append(
    el("h2", "", status), note,
    gameButton("Next", () => {
      session.index++;
      if (session.index === setup.count) go("results");
      else startTurn();
    }, { primary: true }),
  );
}

function renderResults() {
  if (session.solo) {
    screen.append(
      el("h2", "", "Round complete"),
      el("div", "score", correctCount(session.outcomes[0]) + "/" + setup.count),
      el("p", "muted", "Best " + Math.round(best[setup.level] * 100) + "%"),
    );
    const after = rules.LEVELS[rules.LEVELS.indexOf(setup.level) + 1];
    if (rules.LEVELS.includes(setup.level) && after && unlocked(after)) {
      screen.append(el("p", "", levelName(after) + " is available."));
    }
  } else {
    const title = session.winner === "draw" ? "Draw" : players[session.winner] + " wins";
    screen.append(el("h2", "", title));
    for (const [player, outcomes] of session.outcomes.entries()) {
      const regulation = outcomes.slice(0, setup.count);
      screen.append(el("p", "", players[player] + " · " + correctCount(regulation) + "/" + setup.count + " correct"));
      const review = el("details", "review-list");
      review.append(el("summary", "", "Review " + players[player] + "’s answers"));
      for (const result of outcomes) {
        review.append(el("p", "", result.question.answer + " · " + result.question.explanation));
      }
      screen.append(review);
    }
  }
  const actions = el("div", "result-actions");
  actions.append(
    gameButton("Play again", start, { primary: true }),
    gameButton("Choose a level", () => { session = null; go("levels"); }),
    gameButton("Home", () => { session = null; go("home"); }),
  );
  screen.append(actions);
}

function renderFormula() {
  const sample = bank.find(item => item.id === "aiml-046") ?? bank.find(item => item.clue_type === "formula");
  screen.append(backBar("Game", leaveInspection, "Untimed preview"));
  renderOptions(sample, sample.choices, choice => {
    formulaChoice = choice;
    render();
    screen.querySelector(".outcome-note").focus({ preventScroll: true });
    screen.querySelector(".outcome-note").scrollIntoView({ block: "nearest" });
  });
  if (formulaChoice !== undefined) {
    const note = el("p", "outcome-note", (formulaChoice === sample.answer ? "Correct. " : "") + sample.answer + " · " + sample.explanation);
    note.tabIndex = -1;
    screen.append(note);
  }
}

function renderLauncher() {
  const launcher = el("div", "launcher");
  launcher.append(el("h2", "", "App launcher"));
  const tile = el("button", "launcher-tile");
  tile.type = "button";
  tile.append(icon(), el("span", "", "Games Statisticians Play"));
  tile.addEventListener("click", leaveInspection);
  launcher.append(tile);
  screen.append(launcher);
}

const views = {
  home: renderHome, levels: renderLevels, length: renderLength, ready: renderReady,
  question: renderQuestion, feedback: renderFeedback, results: renderResults,
  formula: renderFormula, launcher: renderLauncher,
};

function render(focus = true) {
  screen.replaceChildren();
  const view = inspection ?? phase;
  views[view]();
  screen.scrollTop = 0;
  resumeGame.hidden = inspection === null;
  const title = screen.querySelector("h2");
  if (title && focus) {
    title.tabIndex = -1;
    title.focus({ preventScroll: true });
  }
}

function leaveInspection() {
  inspection = null;
  render();
  tick();
}

function fitDevice() {
  const landscape = document.querySelector('[name="orientation"]:checked').value === "landscape";
  const [portraitWidth, portraitHeight] = deviceSize.value.split(",").map(Number);
  const width = landscape ? portraitHeight : portraitWidth;
  const height = landscape ? portraitWidth : portraitHeight;
  const top = deviceArea.getBoundingClientRect().top + window.scrollY;
  const verticalRoom = window.innerWidth > 760 ? Math.max(510, window.innerHeight - top - 36) : Infinity;
  const scale = Math.min(1, deviceArea.clientWidth / (width + 18), verticalRoom / (height + 18));
  device.style.setProperty("--screen-w", width + "px");
  device.style.setProperty("--screen-h", height + "px");
  device.style.setProperty("--device-scale", scale);
  deviceFit.style.width = (width + 18) * scale + "px";
  deviceFit.style.height = (height + 18) * scale + "px";
  dimensions.textContent = width + " × " + height + (scale < 0.995 ? " · " + Math.round(scale * 100) + "% view" : "");
}

deviceSize.addEventListener("change", fitDevice);
document.querySelectorAll('[name="orientation"]').forEach(input => input.addEventListener("change", fitDevice));
document.querySelectorAll('[name="text-size"]').forEach(input => input.addEventListener("change", () => {
  device.style.setProperty("--text-scale", input.value);
}));
document.querySelectorAll('[name="theme"]').forEach(input => input.addEventListener("change", () => {
  device.dataset.theme = input.value;
}));
document.querySelectorAll('[name="icon"]').forEach(input => input.addEventListener("change", () => {
  device.dataset.icon = input.value;
  if (inspection === "launcher" || (inspection === null && phase === "home")) render(false);
}));
document.querySelector("#inspect-formula").addEventListener("click", () => {
  if (!bank?.length || !rules) return;
  formulaChoice = undefined;
  inspection = "formula";
  render();
});
document.querySelector("#inspect-launcher").addEventListener("click", () => {
  if (!bank?.length || !rules) return;
  inspection = "launcher";
  render();
});
resumeGame.addEventListener("click", leaveInspection);
new ResizeObserver(fitDevice).observe(deviceArea);
window.addEventListener("resize", fitDevice);
fitDevice();

if (bank?.length && rules) {
  render(false);
  setInterval(tick, 100);
  document.addEventListener("visibilitychange", tick);
} else {
  screen.replaceChildren(el("p", "", "Couldn’t load the game. Keep this HTML file with the other preview files."));
}
