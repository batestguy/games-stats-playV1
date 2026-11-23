"use strict";

const bank = globalThis.QUIZ_BANK;
const equations = globalThis.QUIZ_EQUATIONS ?? {};
const author = globalThis.QUIZ_AUTHOR;
const rules = globalThis.QuizRules;
const screen = document.querySelector("#app-screen");
const openingScreen = document.querySelector("#opening-screen");
const openingBoard = document.querySelector("#opening-board");
const device = document.querySelector("#device");
const deviceArea = document.querySelector("#device-area");
const deviceFit = document.querySelector("#device-fit");
const dimensions = document.querySelector("#dimensions");
const deviceSize = document.querySelector("#device-size");
const resumeGame = document.querySelector("#resume-game");
const exitDialog = document.querySelector("#exit-dialog");
const exitDescription = document.querySelector("#exit-description");
const durationSeconds = 25;
const duration = durationSeconds * 1000;
const storageKey = "stats-quiz-phone-preview-v1";
const nicknameKey = "stats-quiz-solo-nickname";
const players = ["Player 1", "Player 2"];
const bonuses = ["AI/ML", "Pro"];
const levelSecretaries = {
  "100": ["year100", "Mean Streak"],
  "200": ["year200", "Belle Curve"],
  "300": ["year300", "P. Value"],
  "400": ["year400", "High Leverage"],
  "Final Year": ["final", "Strata Sphere"],
  "Graduate Mix": ["graduate", "Prior Belief"],
  "AI/ML": ["ai", "Madame Overfit"],
  Pro: ["pro", "Mixed Effects"],
};
const introDuration = 10000;
const board = { width: 860, height: 720, rows: 9, center: 430, firstPeg: 107, columnWidth: 72, rowHeight: 53, binHeight: 142, floor: 701 };
const beadRadius = 6.5;
const entryTime = 220;
const bounceTime = 167;
const settleTime = 390;
const systemMotion = matchMedia("(prefers-reduced-motion: reduce)");
const homeSymbols = [
  ["Σ", 67, 20, 4.5, -16, 0],
  ["∇L", 86, 28, 2.3, 13, 2],
  ["p-value", 57, 27, 1.2, -14, 1],
  ["β̂", 76, 39, 3.9, 17, 1],
  ["x̄", 97, 42, 3.4, -12, 0],
  ["ReLU", 85, 49, 1.9, -21, 0],
  ["χ²", 63, 48, 2.7, 15, 2],
  ["σ", 94, 60, 4.9, 12, 1],
  ["argmin", 58, 61, 1.6, -12, 0],
  ["Q·Kᵀ", 73, 58, 1.7, -13, 2],
  ["ŷ", 78, 68, 3.4, 17, 0],
  ["ℓ(θ)", 58, 74, 1.8, -19, 1],
  ["AUC", 93, 76, 1.6, -20, 2],
  ["P(A∣B)", 70, 80, 1.5, 11, 0],
  ["⊗", 91, 89, 2.2, -7, 0],
  ["η", 46, 84, 1.9, 15, 1],
  ["R²", 32, 94, 2.5, -14, 2],
  ["1/n", 15, 88, 1.4, 14, 0],
  ["E[X]", 51, 14, 1.7, 12, 1],
  ["λ", 86, 12, 3.2, -14, 0],
  ["k-NN", 95, 23, 1.3, 17, 2],
  ["≈", 65, 88, 2.1, 6, 1],
  ["μ", 9, 8, 1.8, -17, 1],
  ["∞", 38, 19, 1.8, -13, 2],
  ["eˣ", 86, 69, 1.5, 13, 1],
  ["∫", 97, 10, 3.8, 14, 2],
];

const setup = { mode: "solo", level: "100", count: 10 };
let phase = "home";
let intro = null;
let soloNickname = cleanNickname(readPreference(nicknameKey));
let session = null;
let inspection = null;
let formulaChoice;
let exitPending = false;
let best = readBest();

function readPreference(key) {
  try {
    return localStorage.getItem(key) ?? "";
  } catch {
    return "";
  }
}

function writePreference(key, value) {
  try {
    localStorage.setItem(key, value);
  } catch {
    // Preferences remain available in memory for this visit.
  }
}

function cleanNickname(value) {
  return Array.from(value.trim().replace(/\s+/gu, " ").normalize()).slice(0, 24).join("").trimEnd();
}

function matchNames(values) {
  const names = values.map((value, index) => cleanNickname(value) || players[index]);
  if (names[0].toLowerCase() === names[1].toLowerCase()) {
    return names.map((name, index) => `${name} (${players[index]})`);
  }
  return names;
}

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
    rules.LEVELS.slice(0, rules.LEVELS.indexOf(level)).every(prior => best[prior] === 1);
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

function openIntro(destination) {
  openingScreen.hidden = false;
  document.body.classList.add("opening");
  intro = { destination, started: performance.now(), beads: buildBeads(), frame: 0 };
  intro.timer = setTimeout(finishIntro, introDuration);
  openingScreen.focus({ preventScroll: true });
  fitIntro();
}

function finishIntro() {
  if (!intro) return;
  const remaining = introDuration - (performance.now() - intro.started);
  clearTimeout(intro.timer);
  if (remaining > 0) {
    intro.timer = setTimeout(finishIntro, remaining);
    return;
  }
  const destination = intro.destination;
  cancelAnimationFrame(intro.frame);
  intro = null;
  openingScreen.hidden = true;
  document.body.classList.remove("opening");
  if (phase !== destination) go(destination);
  else requestAnimationFrame(focusScreenTitle);
}

function buildBeads() {
  const binSizes = Array(board.rows + 1).fill(0);
  return Array.from({ length: 58 }, (_, index) => {
    let x = board.center;
    let bin = 0;
    const route = [x];
    for (let row = 0; row < board.rows; row++) {
      const right = Math.random() < .5;
      if (right) bin++;
      x += (right ? .5 : -.5) * board.columnWidth;
      route.push(x);
    }
    return { route, released: index * 128, stack: binSizes[bin]++ };
  });
}

function beadPosition(bead, elapsed, radiusX, radiusY) {
  const firstContact = board.firstPeg - 2.1 * radiusY;
  if (elapsed < entryTime) {
    return [board.center, 25 + (firstContact - 25) * (elapsed / entryTime) ** 2];
  }
  const crossing = (elapsed - entryTime) / bounceTime;
  const row = Math.floor(crossing);
  if (row < board.rows) {
    const progress = crossing - row;
    const x = bead.route[row] + (bead.route[row + 1] - bead.route[row]) * progress;
    const y = firstContact + crossing * board.rowHeight - Math.sin(Math.PI * progress) * 3 * radiusY;
    return [x, y];
  }
  const progress = Math.min(1, (elapsed - entryTime - board.rows * bounceTime) / settleTime);
  const top = firstContact + board.rows * board.rowHeight;
  const lastX = bead.route.at(-1);
  const targetX = lastX + ((bead.stack % 3) - 1) * radiusX * 2.35;
  const targetY = board.floor - (1.35 + Math.floor(bead.stack / 3) * 2.16) * radiusY;
  return [
    lastX + (targetX - lastX) * progress,
    top + (targetY - top) * progress ** 2,
  ];
}

function drawBoard(beads, elapsed) {
  const context = openingBoard.getContext("2d");
  if (!context) return;
  const scaleX = openingBoard.width / board.width;
  const scaleY = openingBoard.height / board.height;
  const scale = Math.min(scaleX, scaleY);
  context.setTransform(scaleX, 0, 0, scaleY, 0, 0);
  context.clearRect(0, 0, board.width, board.height);
  context.strokeStyle = "#699a93";
  context.lineWidth = 4;
  context.beginPath();
  context.moveTo(board.center - 50, 15);
  context.lineTo(board.center - 14, 65);
  context.moveTo(board.center + 50, 15);
  context.lineTo(board.center + 14, 65);
  const left = board.center - (board.rows + 1) * board.columnWidth / 2;
  for (let index = 0; index <= board.rows + 1; index++) {
    const x = left + index * board.columnWidth;
    context.moveTo(x, board.floor - board.binHeight);
    context.lineTo(x, board.floor);
  }
  context.moveTo(left, board.floor);
  context.lineTo(left + (board.rows + 1) * board.columnWidth, board.floor);
  context.stroke();

  context.fillStyle = "#a8d9cc";
  context.beginPath();
  for (let row = 0; row < board.rows; row++) {
    for (let column = 0; column <= row; column++) {
      const x = board.center + (column - row / 2) * board.columnWidth;
      const y = board.firstPeg + row * board.rowHeight;
      context.moveTo(x + 6 * scale / scaleX, y);
      context.ellipse(x, y, 6 * scale / scaleX, 6 * scale / scaleY, 0, 0, Math.PI * 2);
    }
  }
  context.fill();

  context.fillStyle = "#f6cc7a";
  const radiusX = beadRadius * scale / scaleX;
  const radiusY = beadRadius * scale / scaleY;
  context.beginPath();
  for (const bead of beads) {
    const age = elapsed - bead.released;
    if (age < 0) break;
    const [x, y] = beadPosition(bead, age, radiusX, radiusY);
    context.moveTo(x + radiusX, y);
    context.ellipse(x, y, radiusX, radiusY, 0, 0, Math.PI * 2);
  }
  context.fill();
}

function paintIntro() {
  if (!intro) return;
  const elapsed = performance.now() - intro.started;
  if (elapsed >= introDuration) {
    finishIntro();
    return;
  }
  const still = systemMotion.matches;
  drawBoard(intro.beads, still ? introDuration : elapsed);
  if (!still) intro.frame = requestAnimationFrame(paintIntro);
}

function refreshIntro() {
  if (!intro) return;
  cancelAnimationFrame(intro.frame);
  paintIntro();
}

function fitIntro() {
  if (!intro) return;
  const bounds = openingBoard.getBoundingClientRect();
  const density = Math.min(2, window.devicePixelRatio);
  openingBoard.width = Math.max(1, Math.round(bounds.width * density));
  openingBoard.height = Math.max(1, Math.round(bounds.height * density));
  refreshIntro();
}

function renderHome() {
  const home = el("div", "home");
  const symbols = el("div", "symbol-field");
  symbols.setAttribute("aria-hidden", "true");
  for (const [text, x, y, size, angle, tone] of homeSymbols) {
    const symbol = el("span", "symbol tone-" + tone, text);
    symbol.style.cssText = `--x:${x}%;--y:${y}%;--size:${size};--angle:${angle}deg`;
    symbols.append(symbol);
  }
  const hero = el("div", "home-hero");
  const heading = el("h2");
  for (const word of ["Games", "Statisticians", "Play"]) heading.append(el("span", "", word + " "));
  hero.append(icon(), heading, el("p", "muted", soloNickname ? `Welcome, ${soloNickname}.` : "Choose how you’d like to play."));
  const actions = el("div", "home-actions");
  actions.append(
    gameButton("Solo", () => { setup.mode = "solo"; go("levels"); },
      { primary: true, note: "Unlock levels with perfect rounds" }),
    gameButton("Pass-and-play", () => { setup.mode = "match"; go("levels"); },
      { note: "Two players · One phone" }),
  );
  actions.append(gameButton("About", () => go("about")));
  home.append(symbols, hero, actions);
  screen.append(home);
}

function renderAbout() {
  const about = el("article", "about-game");
  about.append(
    el("h2", "", "About the game"),
    el("p", "", "Games Statisticians Play · Volume 1 is an offline quiz about recognizing statistical ideas, reading formulas, and choosing the right method for a problem. Each question gives you five choices and 25 seconds to answer."),
    el("h3", "", "Solo"),
    el("p", "", "Choose 1 to 20 questions. Start at Level 100 and get every answer right in a round to unlock the next level. Your best score is saved on this device."),
    el("h3", "", "Pass-and-play"),
    el("p", "", "Play on one device with 1 to 20 matched questions each. All levels are open. Most correct answers wins, then faster average time on correct answers. Up to three extra pairs can break a remaining tie."),
    el("h3", "", "More ways to play"),
    el("p", "", "AI/ML Bonus draws from its own bank. Pro · Bring It All mixes mostly higher-year questions with AI/ML and earlier years. Both are available in either mode from the start."),
    gameButton("Watch the opening", () => openIntro("about")),
  );
  screen.append(backBar("Home", () => go("home"), "About"), about);
  if (!author) return;
  const profile = el("article", "author-profile");
  const portrait = el("img", "author-photo");
  portrait.src = author.photo;
  portrait.alt = "Portrait of " + author.name;
  portrait.width = 400;
  portrait.height = 400;
  const heading = el("div", "author-heading");
  heading.append(el("p", "credit-label", "Developed by"), el("h3", "", author.name));
  const link = el("a", "game-button", "Visit Thoughts by Your Hommie ↗");
  link.href = author.url;
  link.target = "_blank";
  link.rel = "noopener noreferrer";
  profile.append(el("h2", "", "About the creator"), portrait, heading, el("p", "author-bio", author.bio), link);
  screen.append(profile);
}

function renderLevels() {
  const list = el("div", "level-list");
  for (const level of [...rules.LEVELS, ...bonuses]) {
    if (level === bonuses[0]) list.append(el("p", "levels-subtitle", "Optional play"));
    const locked = setup.mode === "solo" && !unlocked(level);
    const note = locked ? "Locked" : setup.mode === "solo" && level in best
      ? "Best " + Math.round(best[level] * 100) + "%"
      : "";
    const [portraitKey, secretary] = levelSecretaries[level];
    const tile = gameButton(levelName(level), () => { setup.level = level; go("length"); }, { note, disabled: locked });
    tile.classList.add("level-tile");
    const details = tile.firstElementChild;
    details.classList.add("level-details");
    details.insertBefore(el("span", "secretary-name", secretary), details.querySelector(".button-note"));
    const portrait = el("img", "secretary-portrait");
    Object.assign(portrait, { src: `secretary-${portraitKey}.jpg`, alt: "", width: 54, height: 54 });
    portrait.addEventListener("error", () => { portrait.hidden = true; });
    tile.prepend(portrait);
    list.append(tile);
  }
  screen.append(backBar("Home", () => go("home"), modeName()), el("h2", "", "Choose a level"));
  screen.append(el("p", "muted", setup.mode === "solo"
    ? "Score 100% in a solo round to unlock the next level."
    : "All levels are open. Choose one for both players."));
  screen.append(list);
}

function renderLength() {
  const form = el("form", "length-form");
  const label = el("label", "", setup.mode === "solo" ? "Questions · 1 to 20" : "Questions per player · 1 to 20");
  label.htmlFor = "round-count";
  const input = el("input");
  Object.assign(input, { id: "round-count", type: "number", min: "1", max: "20", step: "1", required: true, value: setup.count });
  input.inputMode = "numeric";
  const solo = setup.mode === "solo";
  const nicknameLabels = solo ? ["Nickname (optional)"] : players.map(player => `${player} nickname (optional)`);
  form.append(label, input);
  const nicknames = nicknameLabels.map((text, index) => {
    const field = el("label", "nickname-field", text);
    const nickname = el("input");
    Object.assign(nickname, { type: "text", value: solo ? soloNickname : "", autocomplete: "off", spellcheck: false });
    nickname.placeholder = solo ? "Player" : players[index];
    nickname.addEventListener("change", () => { nickname.value = cleanNickname(nickname.value); });
    field.append(nickname);
    form.append(field);
    return nickname;
  });
  const submit = el("button", "game-button primary", solo ? "Start round" : "Start match");
  submit.type = "submit";
  form.append(submit);
  form.addEventListener("submit", event => {
    event.preventDefault();
    setup.count = input.valueAsNumber;
    if (solo) {
      soloNickname = cleanNickname(nicknames[0].value);
      writePreference(nicknameKey, soloNickname);
    }
    start(solo ? [soloNickname || "Player"] : matchNames(nicknames.map(nickname => nickname.value)));
  });
  screen.append(backBar("Levels", () => go("levels"), modeName()), el("h2", "", levelName(setup.level)));
  if (setup.level === "Pro") screen.append(el("p", "muted", "Mostly higher years, with AI/ML and earlier years mixed in."));
  screen.append(form);
}

function start(names) {
  const solo = setup.mode === "solo";
  session = {
    index: 0,
    solo: solo ? rules.drawSolo(bank, setup.level, setup.count) : null,
    pairs: solo ? null : rules.drawPairs(bank, setup.level, setup.count),
    outcomes: solo ? [[]] : [[], []],
    names,
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
  session.turn = { question, choices: rules.shuffle(question.choices), started: performance.now(), wallStarted: Date.now() };
  go("question");
}

function renderReady() {
  const player = session.names[session.index % 2];
  const handover = el("div", "handover");
  const ready = gameButton("Ready", startTurn, { primary: true });
  handover.append(
    el("p", "muted", "Pass the phone"), el("h2", "", player + ", your turn"),
    el("p", "", "The countdown starts when you tap Ready."), ready, exitButton(),
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
    button.append(letter, choiceContent(question, choice));
    button.addEventListener("click", () => onChoice(choice));
    options.append(button);
  });
  screen.append(el("h2", "quiz-heading", "Answer the question"), clueContent(question, "clue"), options);
}

function equationImage(tex, alt = "") {
  const equation = equations[tex];
  if (!equation) return null;
  const image = el("img", "equation-image");
  image.src = "data:image/png;base64," + equation.png;
  image.alt = alt;
  image.style.setProperty("--equation-width", equation.width / 2 + "px");
  image.width = equation.width;
  image.height = equation.height;
  return image;
}

function choiceContent(question, choice) {
  return equationImage(question.math_choices?.[choice], choice) ?? el("span", "", choice);
}

function clueContent(question, className = "") {
  if (!question.math_clue) return el("p", className, question.clue);
  const parts = question.math_clue.split(/\$([^$\r\n]+)\$/);
  const block = el("div", "equation-clue " + className);
  block.setAttribute("role", "img");
  block.setAttribute("aria-label", question.clue);
  for (const [index, part] of parts.entries()) {
    if (!part.trim()) continue;
    const chunk = index % 2 ? equationImage(part.trim()) : el("div", "", part.trim());
    if (!chunk) return el("p", className, question.clue);
    chunk.setAttribute("aria-hidden", "true");
    block.append(chunk);
  }
  return block;
}

function exitButton() {
  const button = el("button", "exit-button", session.solo ? "Exit round" : "Exit match");
  button.type = "button";
  button.addEventListener("click", () => {
    if (exitPending) return;
    exitDescription.textContent = phase === "question"
      ? "The countdown keeps running. An unfinished game won’t be saved."
      : "An unfinished game won’t be saved.";
    exitDialog.returnValue = "";
    exitPending = true;
    exitDialog.showModal();
  });
  return button;
}

function elapsedTime(turn) {
  return Math.min(duration, Math.floor(Math.max(performance.now() - turn.started, Date.now() - turn.wallStarted)));
}

function remainingTime(turn) {
  return duration - elapsedTime(turn);
}

function renderQuestion() {
  const turn = session.turn;
  const header = el("div", "screen-top");
  let description = levelName(setup.level) + " · " + (session.index + 1) + "/" + setup.count;
  if (session.pairs) {
    const pair = Math.floor(session.index / 2);
    description = session.names[session.index % 2] + " · " + (pair >= setup.count ? "Sudden death" : (pair + 1) + "/" + setup.count);
  }
  const remaining = remainingTime(turn);
  const timer = el("span", "countdown", Math.ceil(remaining / 1000) + "s");
  timer.id = "countdown";
  const track = el("div", "timer-track");
  track.setAttribute("aria-hidden", "true");
  const fill = el("div");
  fill.id = "timer-fill";
  fill.style.transform = "scaleX(" + remaining / duration + ")";
  track.append(fill);
  const controls = el("div", "question-controls");
  controls.append(exitButton(), timer);
  header.append(el("span", "", description), controls);
  screen.append(header, track);
  renderOptions(turn.question, turn.choices, choice => submitTurn(choice, turn));
}

function submitTurn(choice, turn) {
  if (exitPending || phase !== "question" || session?.turn !== turn) return;
  const elapsed = elapsedTime(turn);
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
  const remaining = remainingTime(turn);
  if (remaining === 0 && !exitPending) {
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
  screen.append(
    el("h2", "", status), outcomeNote(result.question, result.correct),
    gameButton("Next", () => {
      session.index++;
      if (session.index === setup.count) go("results");
      else startTurn();
    }, { primary: true }),
  );
  if (session.index + 1 < setup.count) screen.append(exitButton());
}

function outcomeNote(question, correct) {
  const note = el("div", "outcome-note");
  const formula = correct && question.math_choices?.[question.answer];
  const answer = el("p", "", correct ? "Answer" + (formula ? "" : " · " + question.answer) : "Hint");
  note.append(answer);
  if (formula) note.append(choiceContent(question, question.answer));
  note.append(el("p", "muted", correct ? question.explanation : question.hint));
  return note;
}

function renderResults() {
  if (session.solo) {
    screen.append(
      el("h2", "", "Round complete"),
      el("div", "score", correctCount(session.outcomes[0]) + "/" + setup.count),
      el("p", "muted", "Best " + Math.round(best[setup.level] * 100) + "%"),
      el("p", "muted", `${session.names[0]}, here’s how you did.`),
    );
    const after = rules.LEVELS[rules.LEVELS.indexOf(setup.level) + 1];
    if (rules.LEVELS.includes(setup.level) && after && unlocked(after)) {
      screen.append(el("p", "", levelName(after) + " is available."));
    }
  } else {
    const title = session.winner === "draw" ? "Draw" : session.names[session.winner] + " wins";
    screen.append(el("h2", "", title));
    for (const [player, outcomes] of session.outcomes.entries()) {
      const regulation = outcomes.slice(0, setup.count);
      screen.append(el("p", "", session.names[player] + " · " + correctCount(regulation) + "/" + setup.count + " correct"));
      const review = el("details", "review-list");
      review.append(el("summary", "", "Review " + session.names[player] + "’s answers"));
      for (const result of outcomes) {
        const item = el("div", "review-outcome");
        const status = result.correct ? "Correct" : result.choice === null ? "Time’s up" : "Incorrect";
        item.append(el("p", "review-status", status), clueContent(result.question),
          outcomeNote(result.question, result.correct));
        review.append(item);
      }
      screen.append(review);
    }
  }
  const actions = el("div", "result-actions");
  actions.append(
    gameButton("Play again", () => {
      if (session.solo) start(session.names);
      else {
        session = null;
        go("length");
      }
    }, { primary: true }),
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
    const note = outcomeNote(sample, formulaChoice === sample.answer);
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
  home: renderHome, about: renderAbout, levels: renderLevels, length: renderLength, ready: renderReady,
  question: renderQuestion, feedback: renderFeedback, results: renderResults,
  formula: renderFormula, launcher: renderLauncher,
};

function render(focus = true) {
  screen.replaceChildren();
  const view = inspection ?? phase;
  views[view]();
  screen.scrollTop = 0;
  resumeGame.hidden = inspection === null;
  if (focus) focusScreenTitle();
}

function focusScreenTitle() {
  const title = screen.querySelector("h2");
  if (title) {
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
  if (intro) return;
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
  if (intro || !bank?.length || !rules) return;
  formulaChoice = undefined;
  inspection = "formula";
  render();
});
document.querySelector("#inspect-launcher").addEventListener("click", () => {
  if (intro || !bank?.length || !rules) return;
  inspection = "launcher";
  render();
});
resumeGame.addEventListener("click", leaveInspection);
exitDialog.addEventListener("close", () => {
  exitPending = false;
  if (exitDialog.returnValue === "exit") {
    session = null;
    go("home");
  } else {
    tick();
  }
});
new ResizeObserver(fitDevice).observe(deviceArea);
window.addEventListener("resize", fitDevice);
window.addEventListener("resize", fitIntro);
systemMotion.addEventListener("change", refreshIntro);

if (bank?.length && rules) {
  render(false);
  openIntro("home");
  setInterval(tick, 100);
  document.addEventListener("visibilitychange", () => {
    refreshIntro();
    tick();
  });
} else {
  document.body.classList.remove("opening");
  fitDevice();
  screen.replaceChildren(el("p", "", "Couldn’t load the game. Keep this HTML file with the other preview files."));
}
