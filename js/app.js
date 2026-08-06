"use strict";

const GROUPS = window.WAR_GROUPS || [];
const VALIDATION = window.WAR_VALIDATION || { summary: {}, issues: [] };
const POKEMON = window.WAR_POKEMON || [];
const META = window.WAR_META || {};
const PACKAGED_LIVE_CONFIG = window.WAR_LIVE_CONFIG || {};
const PACKAGED_ROSTER = window.WAR_ROSTER || [];
const PACKAGED_PREVIEW_CATCHES = window.WAR_PREVIEW_CATCHES || [];
const LIVE_STATE_URL = "data/live/state.json";
const STATIC_STATE_REFRESH_MS = 60_000;
const AUTO_CONTEXT_REFRESH_MS = 15_000;
const WAR_EVENT_START_UTC = Date.UTC(2026, 7, 1, 0, 0, 0);
const WAR_EVENT_END_UTC = Date.UTC(2026, 7, 29, 0, 0, 0);
const TIER_POINTS = Object.freeze({0:50, 1:45, 2:40, 3:30, 4:15, 5:10, 6:5, 7:3});
const ROTATIONAL_SETTING_KEYS = Object.freeze(["johtoSafariRotationalTier", "greatMarshRotationalTier"]);
const SLOW_BASELINE_METHOD = Object.freeze({"5x Horde":"5x Horde (Slowed)", "3x Horde":"3x Horde (Slowed)"});
const METHOD_SPEED_KEY = Object.freeze({
  "Old Rod":"Fishing", "Good Rod":"Fishing", "Super Rod":"Fishing",
  "Old Rod + Lure":"Fishing + Lure", "Good Rod + Lure":"Fishing + Lure", "Super Rod + Lure":"Fishing + Lure",
  "Old Rod + Chum Bucket":"Fishing + Chum Bucket", "Good Rod + Chum Bucket":"Fishing + Chum Bucket", "Super Rod + Chum Bucket":"Fishing + Chum Bucket",
  "Old Rod + Lure + Chum Bucket":"Fishing + Lure + Chum Bucket",
  "Good Rod + Lure + Chum Bucket":"Fishing + Lure + Chum Bucket",
  "Super Rod + Lure + Chum Bucket":"Fishing + Lure + Chum Bucket",
  "Safari Old Rod":"Safari Singles", "Safari Good Rod":"Safari Singles", "Safari Super Rod":"Safari Singles",
  "Safari Old Rod + Lure":"Lure Safari Singles", "Safari Good Rod + Lure":"Lure Safari Singles", "Safari Super Rod + Lure":"Lure Safari Singles"
});

const $ = (selector, root = document) => root.querySelector(selector);
const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];
const STORAGE_KEY = META.storageKey || "pokemmo-wartool-state-v9";
const OLD_STORAGE_KEYS = ["pokemmo-wartool-state-v7", "pokemmo-wartool-state-v6", "pokemmo-wartool-state-v5", "pokemmo-wartool-state-v4", "pokemmo-wartool-state-v3", "pokemmo-wartool-state-v2", "pokemmo-wartool-state-v1"];

const DEFAULT_SETTINGS = {
  baseShinyDenominator: 30000,
  eventWildBoost: 0.10,
  uniqueBonus: 8,
  secretBonus: 20,
  secretChance: 1 / 16,
  safariBonus: 10,
  safariCatchModel: 1,
  safariCatchChance: 1,
  safariUnknownCatchChance: 0.52,
  johtoSafariRotationalTier: -1,
  greatMarshRotationalTier: -1,
  methodSpeeds: {
    "5x Horde": 1200,
    "5x Horde (Slowed)": 1000,
    "3x Horde": 720,
    "3x Horde (Slowed)": 600,
    "Lure Singles": 280,
    "Singles": 220,
    "Safari Singles": 300,
    "Lure Safari Singles": 300,
    "Fishing": 270,
    "Fishing + Lure": 340,
    "Fishing + Chum Bucket": 400,
    "Fishing + Lure + Chum Bucket": 500,
    "Rock Smash": 120,
    "Headbutt": 120,
    "Honey Tree": 60,
    "Fossil": 120
  }
};

const DEFAULT_STATE = {
  version: 9,
  settings: structuredClone(DEFAULT_SETTINGS),
  rotationalOverrides: {},
  players: structuredClone(PACKAGED_ROSTER),
  selectedTeamId: PACKAGED_ROSTER[0]?.teamId || "",
  catches: structuredClone(PACKAGED_PREVIEW_CATCHES),
  liveConfig: {
    team1CatchesCsvUrl: "",
    team2CatchesCsvUrl: "",
    settingsCsvUrl: "",
    refreshSeconds: Number(PACKAGED_LIVE_CONFIG.refreshSeconds || 60)
  }
};

const pokemonById = new Map(POKEMON.map(p => [Number(p.id), p]));
const pokemonByName = new Map(POKEMON.map(p => [normalize(p.name), p]));
const lineInfo = buildLineInfo();

let state = loadState();
let remote = { mode: "fallback", source: "Bundled fallback", roster: null, catches: null, settings: null, errors: [], lastUpdated: null };
let currentRankingRows = [];
let liveRefreshTimer = null;
let staticStateRefreshTimer = null;
let lastLiveStateFingerprint = "";
let saveTimer = null;
let rankingObserver = null;
let rankingRenderToken = 0;
let autoContextTimer = null;
let lastAutoContextKey = "";

function normalize(value) {
  return String(value || "").trim().toLowerCase().replace(/[’]/g, "'").replace(/[^a-z0-9♀♂]+/g, "");
}
function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>'"]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;","'":"&#39;",'"':"&quot;"}[c]));
}
function formatNumber(value, digits = 4) {
  return Number(value || 0).toLocaleString("en-US", { minimumFractionDigits: digits, maximumFractionDigits: digits });
}
function formatPercent(value, digits = 1) {
  return `${(Number(value || 0) * 100).toFixed(digits)}%`;
}
function formatDate(value) {
  const date = new Date(value);
  return Number.isNaN(date.valueOf()) ? "Unknown" : date.toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" });
}
function formatCatchDate(item) {
  if (item?.dateMissing) return "Date not entered";
  const date = new Date(item?.caughtAt);
  if (Number.isNaN(date.valueOf())) return "Unknown";
  return item?.dateOnly
    ? date.toLocaleDateString(undefined, { dateStyle: "medium" })
    : date.toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" });
}
function localDateInputValue(date = new Date()) {
  const pad = n => String(n).padStart(2, "0");
  return `${date.getFullYear()}-${pad(date.getMonth()+1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`;
}
function pokeMMOClock(date = new Date()) {
  const gameSeconds = ((date.getTime() / 1000) * 4) % 86400;
  const normalized = (gameSeconds + 86400) % 86400;
  const hour = Math.floor(normalized / 3600);
  const minute = Math.floor((normalized % 3600) / 60);
  const second = Math.floor(normalized % 60);
  const totalMinutes = hour * 60 + minute;
  const period = totalMinutes >= 4 * 60 && totalMinutes < 11 * 60
    ? "Morning"
    : totalMinutes >= 11 * 60 && totalMinutes < 21 * 60
      ? "Day"
      : "Night";
  return { hour, minute, second, period, label: `${String(hour).padStart(2,"0")}:${String(minute).padStart(2,"0")}` };
}
function assumedWarWeek(date = new Date()) {
  const timestamp = date.getTime();
  if (timestamp < WAR_EVENT_START_UTC || timestamp >= WAR_EVENT_END_UTC) return "";
  const weekNumber = Math.floor((timestamp - WAR_EVENT_START_UTC) / (7 * 86400000)) + 1;
  return GROUPS.find(group => String(group.week).startsWith(`Week ${weekNumber} `))?.week || "";
}
function currentAutoContext(date = new Date()) {
  const game = pokeMMOClock(date);
  return { game, week: assumedWarWeek(date), time: game.period };
}
function updateAutoContextControls({ rerender = false } = {}) {
  const context = currentAutoContext();
  const weekSelect = $("#rankWeek");
  const timeSelect = $("#rankTime");
  const weekOption = weekSelect?.querySelector('option[value="auto"]');
  const timeOption = timeSelect?.querySelector('option[value="auto"]');
  if (weekOption) weekOption.textContent = context.week ? `Auto · ${context.week}` : "Auto · all weeks";
  if (timeOption) timeOption.textContent = `Auto · ${context.time} · ${context.game.label} GT`;
  const status = $("#autoContextStatus");
  if (status) {
    const weekLabel = context.week || "Outside assumed Aug 1–28 event window";
    status.textContent = `Automatic context: ${weekLabel} · ${context.time} · ${context.game.label} in-game`;
  }
  const key = `${context.week}|${context.time}`;
  const changed = key !== lastAutoContextKey;
  lastAutoContextKey = key;
  if (rerender && changed && (weekSelect?.value === "auto" || timeSelect?.value === "auto")) renderRankings();
  return context;
}
function scheduleAutoContextRefresh() {
  clearInterval(autoContextTimer);
  updateAutoContextControls();
  autoContextTimer = setInterval(() => updateAutoContextControls({ rerender: true }), AUTO_CONTEXT_REFRESH_MS);
  document.addEventListener("visibilitychange", () => {
    if (!document.hidden) updateAutoContextControls({ rerender: true });
  });
}
function uid(prefix = "id") {
  return `${prefix}-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 9)}`;
}
function sprite(id, shiny = false) {
  return `assets/sprites/${id}${shiny ? "-shiny" : ""}.png`;
}
function currentTheme() {
  return document.documentElement.dataset.theme === "dark" ? "dark" : "light";
}
function setTheme(theme) {
  const next = theme === "dark" ? "dark" : "light";
  document.documentElement.dataset.theme = next;
  localStorage.setItem("wartool.theme", next);
  const button = $("#themeToggle");
  if (button) {
    button.textContent = next === "dark" ? "☀" : "☾";
    button.title = next === "dark" ? "Use light theme" : "Use dark theme";
  }
}
function toggleTheme() {
  setTheme(currentTheme() === "dark" ? "light" : "dark");
}
function previewToolsEnabled() {
  return ["localhost", "127.0.0.1"].includes(location.hostname)
    && new URLSearchParams(location.search).get("preview") === "1";
}
function buildLineInfo() {
  const map = new Map();
  for (const p of POKEMON) {
    if (!map.has(p.line)) map.set(p.line, { line: p.line, tier: p.tier, points: p.points, pokemon: [], spriteId: p.id });
    const info = map.get(p.line);
    info.pokemon.push(p);
    if (p.id < info.spriteId) info.spriteId = p.id;
  }
  return [...map.values()].sort((a, b) => a.tier - b.tier || a.line.localeCompare(b.line));
}
function deepMergeSettings(value) {
  const source = value && typeof value === "object" ? value : {};
  return {
    ...structuredClone(DEFAULT_SETTINGS),
    ...source,
    methodSpeeds: { ...DEFAULT_SETTINGS.methodSpeeds, ...(source.methodSpeeds || {}) }
  };
}
function loadState() {
  try {
    let raw = localStorage.getItem(STORAGE_KEY);
    const currentStateFound = Boolean(raw);
    if (!raw) {
      for (const key of OLD_STORAGE_KEYS) {
        raw = localStorage.getItem(key);
        if (raw) break;
      }
    }
    if (!raw) return structuredClone(DEFAULT_STATE);
    const parsed = JSON.parse(raw);
    const rosterById = new Map(PACKAGED_ROSTER.map(p => [p.id, { ...p }]));
    for (const player of Array.isArray(parsed.players) ? parsed.players : []) {
      const id = player.id || normalize(player.name);
      const packaged = rosterById.get(id);
      rosterById.set(id, {
        ...packaged,
        ...player,
        id,
        name: player.name || packaged?.name || id,
        teamId: player.teamId || packaged?.teamId || DEFAULT_STATE.selectedTeamId,
        teamName: player.teamName || packaged?.teamName || PACKAGED_ROSTER[0]?.teamName || "Team",
        teamOrder: Number(player.teamOrder || packaged?.teamOrder || 99),
        active: player.active !== false
      });
    }
    const players = [...rosterById.values()];
    const migratedCatches = Array.isArray(parsed.catches) ? parsed.catches
      .filter(item => !(String(item?.id || "").startsWith("preview-surprise-") && String(item?.note || "") === "Static design-preview catch"))
      .map(item => {
        const packaged = rosterById.get(item.playerId);
        return {
          ...item,
          teamId: item.teamId || packaged?.teamId || parsed.selectedTeamId || DEFAULT_STATE.selectedTeamId,
          teamName: item.teamName || packaged?.teamName || PACKAGED_ROSTER[0]?.teamName || "Team"
        };
      }) : [];
    const catches = currentStateFound || migratedCatches.length
      ? migratedCatches
      : structuredClone(PACKAGED_PREVIEW_CATCHES);
    return {
      version: 9,
      settings: deepMergeSettings(parsed.settings),
      rotationalOverrides: parsed.rotationalOverrides && typeof parsed.rotationalOverrides === "object" ? { ...parsed.rotationalOverrides } : {},
      players,
      selectedTeamId: parsed.selectedTeamId || players[0]?.teamId || DEFAULT_STATE.selectedTeamId,
      catches,
      liveConfig: structuredClone(DEFAULT_STATE.liveConfig)
    };
  } catch (error) {
    console.error(error);
    return structuredClone(DEFAULT_STATE);
  }
}
function saveState(message = "Saved locally") {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
  const status = $("#saveStatus");
  if (status) {
    status.textContent = message;
    status.classList.add("flash");
    clearTimeout(saveTimer);
    saveTimer = setTimeout(() => status.classList.remove("flash"), 900);
  }
}
function packagedOrLocalConfig() {
  return {
    team1CatchesCsvUrl: String(state.liveConfig.team1CatchesCsvUrl || PACKAGED_LIVE_CONFIG.team1CatchesCsvUrl || "").trim(),
    team2CatchesCsvUrl: String(state.liveConfig.team2CatchesCsvUrl || PACKAGED_LIVE_CONFIG.team2CatchesCsvUrl || "").trim(),
    settingsCsvUrl: String(state.liveConfig.settingsCsvUrl || PACKAGED_LIVE_CONFIG.settingsCsvUrl || "").trim(),
    // v0.3 fallback fields remain readable for migration.
    rosterCsvUrl: String(state.liveConfig.rosterCsvUrl || PACKAGED_LIVE_CONFIG.rosterCsvUrl || "").trim(),
    catchesCsvUrl: String(state.liveConfig.catchesCsvUrl || PACKAGED_LIVE_CONFIG.catchesCsvUrl || "").trim(),
    refreshSeconds: Number(state.liveConfig.refreshSeconds ?? PACKAGED_LIVE_CONFIG.refreshSeconds ?? 60)
  };
}
function getBaseEffectiveSettings() {
  const local = deepMergeSettings(state.settings);
  if (!remote.settings) return local;
  return deepMergeSettings({
    ...local,
    ...remote.settings,
    methodSpeeds: { ...local.methodSpeeds, ...(remote.settings.methodSpeeds || {}) }
  });
}
function getEffectiveSettings() {
  const effective = getBaseEffectiveSettings();
  for (const key of ROTATIONAL_SETTING_KEYS) {
    if (Object.prototype.hasOwnProperty.call(state.rotationalOverrides || {}, key)) {
      const value = Number(state.rotationalOverrides[key]);
      if (Number.isInteger(value) && value >= -1 && value <= 7) effective[key] = value;
    }
  }
  return effective;
}
function currentRoster() {
  const source = Array.isArray(remote.roster) && remote.roster.length ? remote.roster : state.players;
  return source.filter(player => player.active !== false);
}
function allActiveCatches() {
  return Array.isArray(remote.catches) ? remote.catches : state.catches;
}
function allTeams() {
  const map = new Map();
  for (const player of currentRoster()) {
    if (!player.teamId) continue;
    if (!map.has(player.teamId)) map.set(player.teamId, { id: player.teamId, name: player.teamName || player.teamId, order: Number(player.teamOrder || 99) });
  }
  for (const item of allActiveCatches()) {
    if (!item.teamId) continue;
    if (!map.has(item.teamId)) map.set(item.teamId, { id: item.teamId, name: item.teamName || item.teamId, order: 99 });
  }
  return [...map.values()].sort((a,b) => a.order - b.order || a.name.localeCompare(b.name));
}
function selectedTeamId() {
  const teams = allTeams();
  if (!teams.length) return "";
  if (!teams.some(team => team.id === state.selectedTeamId)) state.selectedTeamId = teams[0].id;
  return state.selectedTeamId;
}
function selectedTeamName() {
  const id = selectedTeamId();
  return allTeams().find(team => team.id === id)?.name || "Team";
}
function activeCatches(teamId = selectedTeamId()) {
  return allActiveCatches().filter(item => !teamId || item.teamId === teamId);
}
function isRemoteCatchMode() {
  return Array.isArray(remote.catches);
}
function allPlayers(teamId = selectedTeamId()) {
  const map = new Map();
  for (const player of currentRoster()) {
    if (teamId && player.teamId !== teamId) continue;
    map.set(player.id, { ...player });
  }
  for (const item of activeCatches(teamId)) {
    if (!map.has(item.playerId)) map.set(item.playerId, {
      id: item.playerId,
      name: item.playerName || item.playerId,
      teamId: item.teamId || teamId,
      teamName: item.teamName || selectedTeamName(),
      teamOrder: 99,
      active: true
    });
  }
  return [...map.values()].sort((a, b) => a.name.localeCompare(b.name));
}
function teamForPlayer(playerName, explicitTeamName = "") {
  const playerId = normalize(playerName);
  const rosterPlayer = currentRoster().find(player => player.id === playerId);
  const fallbackTeam = allTeams()[0] || { id: DEFAULT_STATE.selectedTeamId, name: PACKAGED_ROSTER[0]?.teamName || "Team" };
  const teamName = rosterPlayer?.teamName || String(explicitTeamName || "").trim() || fallbackTeam.name;
  const teamId = rosterPlayer?.teamId || normalize(teamName) || fallbackTeam.id;
  return { teamId, teamName };
}
function eligibleSecret(method) {
  return !String(method).includes("Horde");
}
function methodSpeedKey(method) {
  return METHOD_SPEED_KEY[String(method)] || String(method);
}
function rodNameFromMethod(method) {
  return String(method || "").match(/^(?:Safari )?(Old Rod|Good Rod|Super Rod)/)?.[1] || "";
}
function rodMethodExplanation(group) {
  const rod = rodNameFromMethod(group?.method);
  if (!rod) return "";
  const parts = [group.lure
    ? `Uses 95% of the selected ${rod} table plus the location's modeled 5% Water Lure-exclusive slot.`
    : `Uses the selected ${rod} encounter table.`];
  if (String(group.method).includes("Chum Bucket")) {
    parts.push("Chum keeps this composition; its extra encounters are represented by the editable fishing-speed assumption.");
  }
  if (group.safari) parts.push("Safari capture odds and the Safari point bonus are applied after the encounter composition.");
  return parts.join(" ");
}
function shinyDenominatorForMethod(method, settings) {
  const wildBoost = method === "Fossil" ? 0 : Number(settings.eventWildBoost || 0);
  return Number(settings.baseShinyDenominator || 30000) / (1 + wildBoost);
}
function getCatchContext(teamId = selectedTeamId()) {
  const settings = getEffectiveSettings();
  const sorted = [...activeCatches(teamId)].sort((a,b) => new Date(a.caughtAt) - new Date(b.caughtAt) || String(a.id).localeCompare(String(b.id)));
  const teamLines = new Set();
  const playerLines = new Map();
  const scores = new Map();
  const playerTotals = new Map();
  const playerBaseTotals = new Map();
  let teamTotal = 0;
  let teamBaseTotal = 0;
  for (const catchItem of sorted) {
    const p = pokemonById.get(Number(catchItem.pokemonId));
    if (!p) continue;
    const line = catchItem.line || p.line;
    const seenTeam = teamLines.has(line);
    const seenPlayer = playerLines.get(catchItem.playerId) || new Set();
    const duplicate = seenPlayer.has(line);
    let base;
    if (duplicate) base = catchItem.alpha ? 35 : 1;
    else if (catchItem.alpha) base = 75;
    else if (catchItem.egg) base = Math.max(35, p.points);
    else base = p.points;
    const unique = seenTeam ? 0 : Number(settings.uniqueBonus);
    const secret = catchItem.secret ? Number(settings.secretBonus) : 0;
    const safari = catchItem.safari ? Number(settings.safariBonus) : 0;
    const total = base + unique + secret + safari;
    scores.set(catchItem.id, { total, base, unique, secret, safari, duplicate, line });
    teamLines.add(line);
    seenPlayer.add(line);
    playerLines.set(catchItem.playerId, seenPlayer);
    teamTotal += total;
    const withoutSpeciesBonus = base + secret + safari;
    teamBaseTotal += withoutSpeciesBonus;
    playerTotals.set(catchItem.playerId, (playerTotals.get(catchItem.playerId) || 0) + total);
    playerBaseTotals.set(catchItem.playerId, (playerBaseTotals.get(catchItem.playerId) || 0) + withoutSpeciesBonus);
  }
  return { teamLines, playerLines, scores, playerTotals, playerBaseTotals, teamTotal, teamBaseTotal };
}
function safariRotationalTier(group, settings) {
  const key = group.safariPool?.settingKey;
  const value = Number(key ? settings[key] : -1);
  return Number.isInteger(value) && value >= 0 && value <= 7 ? value : -1;
}
function safariRotationalLabel(group, settings) {
  const tier = safariRotationalTier(group, settings);
  return tier >= 0 ? `T${tier} rotational` : "rotational unscored";
}
function clampChance(value, fallback = 0) {
  const number = Number(value);
  return Number.isFinite(number) && number >= 0 && number <= 1 ? number : fallback;
}
function safariUsesGlobalOverride(settings) {
  return Number(settings.safariCatchModel) === 0;
}
function safariCaptureFor(component, settings) {
  if (safariUsesGlobalOverride(settings)) {
    return {
      chance: clampChance(settings.safariCatchChance, 1),
      source: "Global override",
      specific: false,
    };
  }
  const specific = Number(component.safariCapture?.ballsOnlySuccess);
  if (Number.isFinite(specific) && specific > 0 && specific <= 1) {
    return {
      chance: specific,
      source: component.safariCapture.scope || "Species estimate",
      specific: true,
      fleePerTurn: clampChance(component.safariCapture.fleePerTurn, 0),
      strategy: component.safariCapture.strategy || "Balls only, up to 30 Safari Balls",
    };
  }
  return {
    chance: clampChance(settings.safariUnknownCatchChance, 0.52),
    source: component.unknown ? "Unknown rotational fallback" : "Unmatched-species fallback",
    specific: false,
  };
}
function safariCaptureBadge(score) {
  if (!score || !Number.isFinite(score.captureAverage)) return "";
  const loss = Math.min(1, Math.max(0, 1 - score.captureAverage));
  return `<span class="safety-badge safari-capture">${formatPercent(loss, 0)} loss est.</span>`;
}
function slowdownExposure(group) {
  if (group.safari || !SLOW_BASELINE_METHOD[group.method]) return 0;
  const exposure = (group.components || []).reduce((total, component) =>
    total + ((component.slowAbilities || []).length ? Number(component.share || 0) : 0), 0);
  return Math.min(1, Math.max(0, exposure));
}
function speedProfile(group, settings) {
  const speedKey = methodSpeedKey(group.method);
  const standard = Math.max(0, Number(settings.methodSpeeds[speedKey] || 0));
  const baselineKey = SLOW_BASELINE_METHOD[group.method];
  const exposure = slowdownExposure(group);
  if (!baselineKey || exposure <= 0) {
    return { standard, fullDelay: standard, exposure: 0, hasRange: false, baselineKey: "" };
  }
  const configuredFullDelay = Math.max(0, Number(settings.methodSpeeds[baselineKey] ?? standard));
  const fullDelay = Math.min(standard, configuredFullDelay);
  return { standard, fullDelay, exposure, hasRange: fullDelay + 1e-9 < standard, baselineKey };
}
function scoreGroup(group, mode, playerId, context = getCatchContext()) {
  const settings = getEffectiveSettings();
  const selectedPlayerLines = context.playerLines.get(playerId) || new Set();
  const rotationalTier = safariRotationalTier(group, settings);
  const rotationalBasePoints = rotationalTier >= 0 ? TIER_POINTS[rotationalTier] : 0;
  const secretEV = eligibleSecret(group.method) ? settings.secretBonus * settings.secretChance : 0;
  const safariEV = group.safari ? settings.safariBonus : 0;
  let weightedBase = 0;
  let weightedCaught = 0;
  let captureAverage = group.safari ? 0 : 1;
  let speciesCaptureCoverage = 0;
  let missingShare = 0;
  const detail = group.components.map(c => {
    const unknown = Boolean(c.unknown || Number(c.pokemonId) <= 0);
    const rotationalEstimated = unknown && rotationalTier >= 0;
    const missingTeam = !unknown && !context.teamLines.has(c.line);
    const duplicatePlayer = !unknown && selectedPlayerLines.has(c.line);
    let score = unknown ? 0 : c.points;
    if (rotationalEstimated) {
      // Tier-only input cannot identify the actual evolution line. Live modes therefore use base tier value only.
      if (mode === "fresh") score = rotationalBasePoints + settings.uniqueBonus;
      else if (mode === "duplicate") score = 1;
      else score = rotationalBasePoints;
    } else if (!unknown) {
      if (mode === "fresh") score = c.points + settings.uniqueBonus;
      else if (mode === "base") score = c.points;
      else if (mode === "team") score = c.points + (missingTeam ? settings.uniqueBonus : 0);
      else if (mode === "player") score = (duplicatePlayer ? 1 : c.points) + (missingTeam ? settings.uniqueBonus : 0);
      else if (mode === "duplicate") score = 1;
    }
    const capture = group.safari ? safariCaptureFor(c, settings) : { chance: 1, source: "Guaranteed after battle", specific: false };
    const pointsIfCaught = score + secretEV + safariEV;
    weightedBase += c.share * score;
    if (group.safari) {
      weightedCaught += c.share * capture.chance * pointsIfCaught;
      captureAverage += c.share * capture.chance;
      if (capture.specific) speciesCaptureCoverage += c.share;
    }
    if (missingTeam) missingShare += c.share;
    return {
      ...c, score, pointsIfCaught, missingTeam, duplicatePlayer, unknown,
      rotationalEstimated, rotationalTier,
      catchChance: capture.chance, catchSource: capture.source,
      catchSpecific: capture.specific, fleePerTurn: capture.fleePerTurn || 0,
      catchStrategy: capture.strategy || "",
    };
  });
  const potentialAverage = weightedBase + secretEV + safariEV;
  const average = group.safari ? weightedCaught : potentialAverage;
  captureAverage = Math.min(1, Math.max(0, captureAverage));
  const speed = speedProfile(group, settings);
  const encountersPerHour = speed.standard;
  const denominator = shinyDenominatorForMethod(group.method, settings);
  const catchMultiplier = group.safari ? captureAverage : 1;
  const pointsPerHour = encountersPerHour / denominator * average;
  const fullDelayPointsPerHour = speed.fullDelay / denominator * average;
  return {
    average, potentialAverage, encountersPerHour, standardEncountersPerHour: speed.standard, fullDelayEncountersPerHour: speed.fullDelay,
    slowdownExposure: speed.exposure, hasSlowdownRange: speed.hasRange, standardPointsPerHour: pointsPerHour, fullDelayPointsPerHour, denominator, catchMultiplier,
    captureAverage, captureLoss: group.safari ? Math.min(1, Math.max(0, 1 - captureAverage)) : 0,
    speciesCaptureCoverage, captureMode: group.safari ? (safariUsesGlobalOverride(settings) ? "global" : "species") : "none",
    pointsPerHour, detail, missingShare, secretEV, safariEV, settings,
    rotationalTier, rotationalBasePoints,
  };
}

function parseCsv(text) {
  const rows = [];
  let row = [], field = "", quoted = false;
  for (let i = 0; i < text.length; i++) {
    const ch = text[i];
    if (quoted) {
      if (ch === '"' && text[i+1] === '"') { field += '"'; i++; }
      else if (ch === '"') quoted = false;
      else field += ch;
    } else if (ch === '"') quoted = true;
    else if (ch === ',') { row.push(field); field = ""; }
    else if (ch === '\n') { row.push(field.replace(/\r$/, "")); rows.push(row); row = []; field = ""; }
    else field += ch;
  }
  if (field.length || row.length) { row.push(field.replace(/\r$/, "")); rows.push(row); }
  return rows.filter(r => r.some(v => String(v).trim() !== ""));
}
function csvObjects(text) {
  const rows = parseCsv(text);
  if (!rows.length) return [];
  const headers = rows[0].map(h => normalize(h));
  return rows.slice(1).map((row, index) => {
    const obj = { _row: index + 2 };
    headers.forEach((h, i) => { obj[h] = row[i] ?? ""; });
    return obj;
  });
}
function firstField(row, names) {
  for (const name of names) if (row[normalize(name)] !== undefined && String(row[normalize(name)]).trim() !== "") return row[normalize(name)];
  return "";
}
function boolValue(value) {
  return ["1","true","yes","y","x","ja"].includes(String(value || "").trim().toLowerCase());
}
function numericValue(value) {
  const text = String(value ?? "").trim().replace(",", ".");
  if (!text) return null;
  if (text.endsWith("%")) {
    const n = Number(text.slice(0, -1));
    return Number.isFinite(n) ? n / 100 : null;
  }
  const n = Number(text);
  return Number.isFinite(n) ? n : null;
}
function parseRemoteDate(value) {
  const raw = String(value || "").trim();
  if (!raw) return null;
  const german = raw.match(/^(\d{1,2})\.(\d{1,2})\.(\d{4})(?:[ T](\d{1,2}):(\d{2})(?::(\d{2}))?)?$/);
  if (german) {
    const [, day, month, year, hour = "0", minute = "0", second = "0"] = german;
    const date = new Date(Number(year), Number(month) - 1, Number(day), Number(hour), Number(minute), Number(second));
    return Number.isNaN(date.valueOf()) ? null : date;
  }
  const parsed = new Date(raw);
  return Number.isNaN(parsed.valueOf()) ? null : parsed;
}
function parseRemoteRoster(text) {
  const players = [], errors = [];
  let teamOrder = 0;
  const teamOrders = new Map();
  for (const row of csvObjects(text)) {
    const teamName = String(firstField(row, ["Team", "Team Name"])).trim();
    const playerName = String(firstField(row, ["Player", "IGN", "Name"])).trim();
    if (!teamName && !playerName) continue;
    if (!teamName || !playerName) {
      errors.push(`Roster row ${row._row}: ${!teamName ? "missing team" : "missing player"}.`);
      continue;
    }
    const activeRaw = firstField(row, ["Active", "Enabled"]);
    const active = String(activeRaw).trim() === "" ? true : boolValue(activeRaw);
    const teamId = normalize(teamName);
    if (!teamOrders.has(teamId)) teamOrders.set(teamId, ++teamOrder);
    players.push({
      id: normalize(playerName),
      name: playerName,
      teamId,
      teamName,
      teamOrder: teamOrders.get(teamId),
      active
    });
  }
  return { roster: players, errors };
}
function parseRemoteCatches(text, forcedTeam = null) {
  const result = [], errors = [];
  for (const row of csvObjects(text)) {
    const playerName = String(firstField(row, ["Player", "IGN", "Name"])).trim();
    const pokemonName = String(firstField(row, ["Pokemon", "Pokémon", "Species"])).trim();
    if (!playerName && !pokemonName) continue;
    const pokemon = pokemonByName.get(normalize(pokemonName));
    if (!playerName || !pokemon) {
      errors.push(`Row ${row._row}: ${!playerName ? "missing player" : `unknown Pokémon “${pokemonName}”`}.`);
      continue;
    }
    const rawDate = firstField(row, ["Date", "Caught At", "CaughtAt", "Time"]);
    const parsedDate = parseRemoteDate(rawDate);
    const caughtAt = parsedDate ? parsedDate.toISOString() : `2026-08-01T00:00:${String(row._row % 60).padStart(2,"0")}Z`;
    const team = forcedTeam || teamForPlayer(playerName, firstField(row, ["Team", "Team Name"]));
    result.push({
      id: `sheet-${team.teamId}-${row._row}`,
      source: "sheet",
      playerId: normalize(playerName),
      playerName,
      teamId: team.teamId,
      teamName: team.teamName,
      pokemonId: pokemon.id,
      line: pokemon.line,
      caughtAt,
      secret: boolValue(firstField(row, ["Secret", "Secret Shiny"])),
      alpha: boolValue(firstField(row, ["Alpha"])),
      safari: boolValue(firstField(row, ["Safari"])),
      egg: boolValue(firstField(row, ["Egg"])),
      note: String(firstField(row, ["Note", "Notes", "Location"])).trim()
    });
  }
  return { catches: result, errors };
}
function parseRemoteSettings(text) {
  const settings = { methodSpeeds: {} };
  const errors = [];
  const known = new Set(["baseShinyDenominator","eventWildBoost","uniqueBonus","secretBonus","secretChance","safariBonus","safariCatchModel","safariCatchChance","safariUnknownCatchChance","johtoSafariRotationalTier","greatMarshRotationalTier"]);
  for (const row of csvObjects(text)) {
    const rawKey = String(firstField(row, ["Setting", "Key", "Name"])).trim();
    const value = numericValue(firstField(row, ["Value", "Number"]));
    if (!rawKey || value === null) continue;
    if (rawKey.toLowerCase().startsWith("method.")) {
      settings.methodSpeeds[rawKey.slice(7).trim()] = value;
    } else if (known.has(rawKey)) {
      if (["johtoSafariRotationalTier","greatMarshRotationalTier"].includes(rawKey) && (!Number.isInteger(value) || value < -1 || value > 7)) {
        errors.push(`Settings row ${row._row}: ${rawKey} must be an integer from -1 to 7.`);
      } else if (rawKey === "safariCatchModel" && (!Number.isInteger(value) || ![0, 1].includes(value))) {
        errors.push(`Settings row ${row._row}: safariCatchModel must be 1 (species estimates) or 0 (global override).`);
      } else if (["safariCatchChance","safariUnknownCatchChance"].includes(rawKey) && (value < 0 || value > 1)) {
        errors.push(`Settings row ${row._row}: ${rawKey} must be between 0 and 1.`);
      } else settings[rawKey] = value;
    } else errors.push(`Settings row ${row._row}: unknown key “${rawKey}”.`);
  }
  if (!Object.keys(settings.methodSpeeds).length) delete settings.methodSpeeds;
  return { settings, errors };
}
function cacheBust(url) {
  const separator = url.includes("?") ? "&" : "?";
  return `${url}${separator}_wartool=${Date.now()}`;
}
function csvCell(value) {
  const text = String(value ?? "");
  return `"${text.replaceAll('"', '""')}"`;
}
function gvizCellValue(cell) {
  if (!cell) return "";
  if (cell.f !== undefined && cell.f !== null) return cell.f;
  const value = cell.v;
  if (value === undefined || value === null) return "";
  if (value instanceof Date) {
    const pad = number => String(number).padStart(2, "0");
    return `${pad(value.getDate())}.${pad(value.getMonth() + 1)}.${value.getFullYear()}`;
  }
  if (typeof value === "boolean") return value ? "TRUE" : "FALSE";
  return value;
}
function gvizResponseToCsv(response) {
  if (!response || response.status === "error") {
    const message = response?.errors?.map(error => error.detailed_message || error.message).filter(Boolean).join("; ") || "Google Sheets query failed";
    throw new Error(message);
  }
  const table = response.table;
  if (!table || !Array.isArray(table.cols) || !Array.isArray(table.rows)) throw new Error("Google Sheets returned no table data");
  const headers = table.cols.map(column => column.label || column.id || "");
  const lines = [headers.map(csvCell).join(",")];
  for (const row of table.rows) {
    const cells = row.c || [];
    lines.push(headers.map((_, index) => csvCell(gvizCellValue(cells[index]))).join(","));
  }
  return lines.join("\n");
}
function googleSheetInfo(url) {
  let parsed;
  try { parsed = new URL(url, location.href); }
  catch { return null; }
  if (!/docs\.google\.com$/i.test(parsed.hostname) || !/\/spreadsheets\//i.test(parsed.pathname)) return null;
  const published = parsed.pathname.match(/\/spreadsheets\/d\/e\/([^/]+)/i);
  if (published) return {
    kind: "published",
    id: published[1],
    gid: parsed.searchParams.get("gid") || new URLSearchParams(parsed.hash.replace(/^#/, "")).get("gid") || "0"
  };
  const documentMatch = parsed.pathname.match(/\/spreadsheets\/d\/([^/]+)/i);
  if (!documentMatch) return null;
  return {
    kind: "document",
    id: documentMatch[1],
    gid: parsed.searchParams.get("gid") || new URLSearchParams(parsed.hash.replace(/^#/, "")).get("gid") || "0"
  };
}
function googleSheetGvizUrl(url, callbackName) {
  const info = googleSheetInfo(url);
  if (!info || info.kind !== "document") return null;
  const endpoint = new URL(`https://docs.google.com/spreadsheets/d/${info.id}/gviz/tq`);
  endpoint.searchParams.set("gid", info.gid);
  endpoint.searchParams.set("headers", "1");
  endpoint.searchParams.set("range", "A:H");
  endpoint.searchParams.set("tqx", `out:json;responseHandler:${callbackName}`);
  endpoint.searchParams.set("_wartool", String(Date.now()));
  return endpoint.toString();
}
function googleSheetCsvExportUrl(url) {
  const info = googleSheetInfo(url);
  if (!info) return url;
  if (info.kind === "published") {
    const endpoint = new URL(url);
    endpoint.searchParams.set("gid", info.gid);
    endpoint.searchParams.set("single", "true");
    endpoint.searchParams.set("output", "csv");
    endpoint.searchParams.delete("_wartool");
    return endpoint.toString();
  }
  const endpoint = new URL(`https://docs.google.com/spreadsheets/d/${info.id}/export`);
  endpoint.searchParams.set("format", "csv");
  endpoint.searchParams.set("gid", info.gid);
  return endpoint.toString();
}
function isLocalWarTool() {
  return ["localhost", "127.0.0.1"].includes(location.hostname);
}
async function fetchThroughLocalServer(url) {
  const target = googleSheetCsvExportUrl(url);
  const endpoint = `/api/fetch-csv?url=${encodeURIComponent(target)}`;
  const response = await fetch(cacheBust(endpoint), { cache: "no-store" });
  const text = await response.text();
  if (!response.ok) {
    let message = `Local Sheet proxy returned HTTP ${response.status}`;
    try {
      const payload = JSON.parse(text);
      message = payload.error || message;
      if (payload.detail) message += ` · ${payload.detail}`;
    } catch {}
    throw new Error(message);
  }
  if (/^\s*</.test(text)) throw new Error("Google returned an HTML page instead of CSV. Publish the tab to the web as CSV, then use that 2PACX link.");
  return text;
}
function fetchGoogleSheetJsonp(url) {
  return new Promise((resolve, reject) => {
    const callbackName = `wartoolSheet_${Date.now()}_${Math.random().toString(36).slice(2)}`;
    const source = googleSheetGvizUrl(url, callbackName);
    if (!source) { reject(new Error("This Google Sheets URL cannot use the JSONP fallback")); return; }
    const script = document.createElement("script");
    let finished = false;
    const cleanup = () => {
      try { delete window[callbackName]; } catch { window[callbackName] = undefined; }
      script.remove();
    };
    const timeout = setTimeout(() => {
      if (finished) return;
      finished = true;
      cleanup();
      reject(new Error("Google Sheets request timed out"));
    }, 15000);
    window[callbackName] = response => {
      if (finished) return;
      finished = true;
      clearTimeout(timeout);
      try { resolve(gvizResponseToCsv(response)); }
      catch (error) { reject(error); }
      finally { cleanup(); }
    };
    script.onerror = () => {
      if (finished) return;
      finished = true;
      clearTimeout(timeout);
      cleanup();
      reject(new Error("Google Sheets script request failed"));
    };
    script.src = source;
    document.head.appendChild(script);
  });
}
async function fetchCsv(url) {
  if (isLocalWarTool()) return fetchThroughLocalServer(url);

  const info = googleSheetInfo(url);
  if (info?.kind === "document") return fetchGoogleSheetJsonp(url);

  const response = await fetch(cacheBust(url), { cache: "no-store" });
  if (!response.ok) throw new Error(`HTTP ${response.status}`);
  return await response.text();
}
async function loadLiveData(showToast = false) {
  const config = packagedOrLocalConfig();
  clearInterval(liveRefreshTimer);
  remote = { roster: null, catches: null, settings: null, errors: [], lastUpdated: null };
  const hasLive = config.team1CatchesCsvUrl || config.team2CatchesCsvUrl || config.settingsCsvUrl || config.rosterCsvUrl || config.catchesCsvUrl;
  if (!hasLive) {
    setLiveStatus("local", "Local preview data");
    renderAll();
    scheduleLiveRefresh(config.refreshSeconds);
    if (showToast) toast("Using local preview data.");
    return;
  }
  setLiveStatus("local", "Loading live data…");
  const packagedTeams = [...new Map(PACKAGED_ROSTER.map(p => [p.teamId, { id:p.teamId, name:p.teamName, order:Number(p.teamOrder||99) }])).values()]
    .sort((a,b) => a.order-b.order || a.name.localeCompare(b.name));
  const jobs = [];
  if (config.team1CatchesCsvUrl) jobs.push(fetchCsv(config.team1CatchesCsvUrl).then(text => ({ type:"team1", text })).catch(error => ({ type:"team1", error })));
  if (config.team2CatchesCsvUrl) jobs.push(fetchCsv(config.team2CatchesCsvUrl).then(text => ({ type:"team2", text })).catch(error => ({ type:"team2", error })));
  if (config.settingsCsvUrl) jobs.push(fetchCsv(config.settingsCsvUrl).then(text => ({ type:"settings", text })).catch(error => ({ type:"settings", error })));
  // v0.3 fallback sources.
  if (config.rosterCsvUrl) jobs.push(fetchCsv(config.rosterCsvUrl).then(text => ({ type:"roster", text })).catch(error => ({ type:"roster", error })));
  if (config.catchesCsvUrl) jobs.push(fetchCsv(config.catchesCsvUrl).then(text => ({ type:"catches", text })).catch(error => ({ type:"catches", error })));
  const results = await Promise.all(jobs);
  const successful = new Map();
  for (const result of results) {
    if (result.error) remote.errors.push(`${result.type}: ${result.error.message}`);
    else successful.set(result.type, result.text);
  }
  if (successful.has("roster")) {
    const parsed = parseRemoteRoster(successful.get("roster"));
    remote.roster = parsed.roster;
    remote.errors.push(...parsed.errors);
  }
  if (successful.has("settings")) {
    const parsed = parseRemoteSettings(successful.get("settings"));
    remote.settings = parsed.settings;
    remote.errors.push(...parsed.errors);
  }
  const combinedCatches = [];
  if (successful.has("team1")) {
    const parsed = parseRemoteCatches(successful.get("team1"), packagedTeams[0] || null);
    combinedCatches.push(...parsed.catches); remote.errors.push(...parsed.errors);
  }
  if (successful.has("team2")) {
    const parsed = parseRemoteCatches(successful.get("team2"), packagedTeams[1] || null);
    combinedCatches.push(...parsed.catches); remote.errors.push(...parsed.errors);
  }
  if (successful.has("catches")) {
    const parsed = parseRemoteCatches(successful.get("catches"));
    combinedCatches.push(...parsed.catches); remote.errors.push(...parsed.errors);
  }
  if (successful.has("team1") || successful.has("team2") || successful.has("catches")) remote.catches = combinedCatches;
  remote.lastUpdated = new Date();
  if (remote.roster || remote.catches || remote.settings) setLiveStatus("live", `Live data · ${remote.lastUpdated.toLocaleTimeString([], {hour:"2-digit",minute:"2-digit"})}`);
  else setLiveStatus("error", "Live data failed");
  renderAll();
  scheduleLiveRefresh(config.refreshSeconds);
  if (showToast) toast(remote.errors.length ? `Refreshed with ${remote.errors.length} note(s).` : "Live data refreshed.");
}
function normalizeStaticCatch(item, index) {
  const pokemon = pokemonById.get(Number(item?.pokemonId)) || pokemonByName.get(normalize(item?.pokemon || item?.pokemonName));
  if (!pokemon) throw new Error(`Live data catch ${index + 1}: unknown Pokémon.`);
  const playerName = String(item?.playerName || item?.player || item?.playerId || "").trim();
  if (!playerName) throw new Error(`Live data catch ${index + 1}: missing player.`);
  const team = teamForPlayer(playerName, item?.teamName || "");
  const caughtAt = parseRemoteDate(item?.caughtAt || item?.date || item?.time) || new Date(`2026-08-01T00:00:${String(index % 60).padStart(2,"0")}Z`);
  return {
    id: String(item?.id || `live-${team.teamId}-${index + 1}`),
    source: String(item?.source || "live"),
    playerId: normalize(item?.playerId || playerName),
    playerName,
    teamId: String(item?.teamId || team.teamId),
    teamName: String(item?.teamName || team.teamName),
    pokemonId: pokemon.id,
    line: pokemon.line,
    caughtAt: caughtAt.toISOString(),
    dateOnly: boolValue(item?.dateOnly),
    dateMissing: boolValue(item?.dateMissing),
    secret: boolValue(item?.secret),
    alpha: boolValue(item?.alpha),
    safari: boolValue(item?.safari),
    egg: boolValue(item?.egg),
    note: String(item?.note || "").trim()
  };
}
async function loadStaticLiveState({ silent = false } = {}) {
  if (!silent) {
    remote = { mode: "fallback", source: "Bundled fallback", roster: null, catches: null, settings: null, errors: [], lastUpdated: null };
    setLiveStatus("local", "Loading team data…");
  }
  try {
    const response = await fetch(`${LIVE_STATE_URL}?refresh=${Date.now()}`, {
      cache: "no-store",
      headers: { "Cache-Control": "no-cache" }
    });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const payload = await response.json();
    if (Number(payload.schemaVersion) !== 1) throw new Error(`unsupported schema ${payload.schemaVersion}`);
    const fingerprint = JSON.stringify([payload.generatedAt || "", payload.catches || [], payload.settings || {}]);
    const changed = fingerprint !== lastLiveStateFingerprint;
    const catches = Array.isArray(payload.catches) ? payload.catches.map(normalizeStaticCatch) : [];
    const mode = payload.mode === "live" ? "live" : payload.mode === "preview" ? "preview" : "demo";
    const generated = parseRemoteDate(payload.generatedAt);
    remote = {
      mode,
      source: String(payload.source || (mode === "live" ? "Generated team data" : mode === "preview" ? "No catches imported yet" : "Bundled demonstration data")),
      roster: null,
      catches,
      settings: payload.settings && typeof payload.settings === "object" ? deepMergeSettings(payload.settings) : null,
      errors: [],
      lastUpdated: generated || new Date()
    };
    lastLiveStateFingerprint = fingerprint;
    const statusLabel = mode === "live" ? "Live team data" : mode === "preview" ? "No catches loaded" : "Demo data";
    setLiveStatus(mode === "live" ? "live" : "local", `${statusLabel} · ${remote.lastUpdated.toLocaleString([], {dateStyle:"medium", timeStyle:"short"})}`);
    return changed;
  } catch (error) {
    if (!silent) {
      remote.errors = [`Static data: ${error.message}`];
      setLiveStatus("error", "Bundled fallback data");
      console.error("WARtool live-state load failed", error);
    } else {
      console.warn("WARtool background refresh failed", error);
    }
    return false;
  }
}

async function refreshStaticLiveState({ notify = false } = {}) {
  const changed = await loadStaticLiveState({ silent: true });
  if (changed) renderAll();
  if (notify) toast(changed ? "Team data updated." : "Team data is already current.");
}

function scheduleStaticLiveStateRefresh() {
  clearInterval(staticStateRefreshTimer);
  staticStateRefreshTimer = setInterval(() => {
    if (!document.hidden) refreshStaticLiveState();
  }, STATIC_STATE_REFRESH_MS);
  document.addEventListener("visibilitychange", () => {
    if (!document.hidden) refreshStaticLiveState();
  });
}

function scheduleLiveRefresh(seconds) {
  const value = Number(seconds || 0);
  const cfg = packagedOrLocalConfig();
  if (value > 0 && (cfg.team1CatchesCsvUrl || cfg.team2CatchesCsvUrl || cfg.settingsCsvUrl || cfg.rosterCsvUrl || cfg.catchesCsvUrl)) {
    liveRefreshTimer = setInterval(() => loadLiveData(false), value * 1000);
  }
}
function setLiveStatus(kind, text) {
  const el = $("#liveStatus");
  el.className = `source-status ${kind}`;
  el.textContent = text;
}

function activateTab(name) {
  $$(".tab").forEach(el => el.classList.toggle("active", el.dataset.tab === name));
  $$(".tab-page").forEach(el => el.classList.toggle("active", el.id === `tab-${name}`));
  location.hash = name;
  if (name === "rankings") renderRankings();
  if (name === "catches") renderCatches();
  if (name === "players") renderLeaderboards();
  if (name === "progress") renderProgress();
  if (name === "settings") renderSettings();
  if (name === "quality") renderQuality();
}
function populateSelect(selector, values, sorter) {
  const el = $(selector);
  [...new Set(values.filter(Boolean))].sort(sorter).forEach(value => el.add(new Option(value, value)));
}
function renderTeamTabs() {
  const teams = allTeams();
  const selected = selectedTeamId();
  const container = $("#teamTabs");
  if (!container) return;
  container.innerHTML = teams.map(team => {
    const playerCount = currentRoster().filter(player => player.teamId === team.id && player.active !== false).length;
    return `<button class="team-tab ${team.id === selected ? "active" : ""}" data-team-id="${escapeHtml(team.id)}">${escapeHtml(team.name)}<small>${playerCount}</small></button>`;
  }).join("");
  $$('[data-team-id]', container).forEach(button => button.addEventListener("click", () => {
    state.selectedTeamId = button.dataset.teamId;
    saveState(`${allTeams().find(team => team.id === state.selectedTeamId)?.name || "Team"} selected`);
    renderAll();
  }));
}
function refreshPlayerSelects() {
  const players = allPlayers();
  for (const select of [$("#rankPlayer"), $("#catchPlayer")]) {
    const current = select.value;
    select.innerHTML = "";
    players.forEach(player => select.add(new Option(player.name, player.id)));
    if ([...select.options].some(o => o.value === current)) select.value = current;
  }
  const filter = $("#catchFilterPlayer");
  const currentFilter = filter.value;
  filter.innerHTML = '<option value="">All players</option>';
  players.forEach(player => filter.add(new Option(player.name, player.id)));
  if ([...filter.options].some(o => o.value === currentFilter)) filter.value = currentFilter;
}
function initializeStaticUi() {
  const weekMap = new Map();
  GROUPS.forEach(g => weekMap.set(g.week, g.season));
  [...weekMap].sort((a,b) => a[0].localeCompare(b[0], undefined, {numeric:true})).forEach(([week,season]) => $("#rankWeek").add(new Option(`${week} · ${season}`, week)));
  updateAutoContextControls();
  populateSelect("#rankRegion", GROUPS.flatMap(g => g.regions));
  populateSelect("#rankMethod", GROUPS.map(g => g.method));
  $("#pokemonList").innerHTML = POKEMON.map(p => `<option value="${escapeHtml(p.name)}"></option>`).join("");
  $("#catchDate").value = localDateInputValue();
  GROUPS.forEach(group => {
    group._search = normalize(`${group.locations.map(l => `${l.region} ${l.location} ${l.encounterTypes.join(" ")}`).join(" ")} ${group.method} ${group.components.map(c => `${c.pokemon} ${c.line} ${(c.hazards || []).map(h => `${h.name} ${h.category || ""} ${h.verificationStatus || ""}`).join(" ")} ${(c.slowAbilities || []).join(" ")}`).join(" ")}`);
  });
  refreshPlayerSelects();
}
function displayLocations(group) {
  const visible = new Map();
  for (const location of group?.locations || []) {
    const key = `${location.region}\u0000${location.location}`;
    if (!visible.has(key)) {
      visible.set(key, { ...location, encounterTypes: [...(location.encounterTypes || [])] });
      continue;
    }
    const current = visible.get(key);
    current.encounterTypes = [...new Set([...(current.encounterTypes || []), ...(location.encounterTypes || [])])].sort();
  }
  return [...visible.values()];
}
function groupLocationPresentation(group) {
  const locations = displayLocations(group);
  if (locations.length === 1) return { title: locations[0].location, subtitle: locations[0].region, alt: "" };
  const sameRegion = new Set(locations.map(location => location.region)).size === 1;
  if (locations.length === 2 && sameRegion) {
    return { title: `${locations[0].location} / ${locations[1].location}`, subtitle: locations[0].region, alt: "2 equivalent locations" };
  }
  const preview = locations.slice(1,4).map(l => `${l.location} (${l.region})`).join(" · ");
  return { title: locations[0].location, subtitle: locations[0].region, alt: `+${locations.length - 1} alternatives${preview ? ` · ${preview}` : ""}` };
}
function rankingFilters(group, context, autoContext = currentAutoContext()) {
  const query = normalize($("#rankSearch").value);
  if (query && !group._search.includes(query)) return false;
  const selectedWeek = $("#rankWeek").value === "auto" ? autoContext.week : $("#rankWeek").value;
  if (selectedWeek && group.week !== selectedWeek) return false;
  const time = $("#rankTime").value === "auto" ? autoContext.time : $("#rankTime").value;
  if (time === "Any time" && group.timeLabel !== "Any time") return false;
  if (time && time !== "Any time" && !group.times.includes(time)) return false;
  if ($("#rankRegion").value && !group.regions.includes($("#rankRegion").value)) return false;
  if ($("#rankMethod").value && group.method !== $("#rankMethod").value) return false;
  if (!$("#rankIncludeIncomplete").checked && group.incomplete) return false;
  const confidence = $("#rankConfidence").value;
  if (confidence === "high" && group.confidence !== "high") return false;
  if (confidence === "medium" && group.confidence === "low") return false;
  if ($("#rankOnlyMissing").checked && !group.components.some(c => !context.teamLines.has(c.line))) return false;
  return true;
}
const SAFETY_BADGE_META = {
  "self-ko": { label: "Self-KO risk", cls: "critical", order: 10 },
  "escape": { label: "Escape risk", cls: "critical", order: 20 },
  "redirection": { label: "Redirection risk", cls: "redirect", order: 30 },
  "held-item": { label: "Held-item risk", cls: "warning", order: 40 },
  "self-damage": { label: "Self-damage", cls: "warning", order: 50 },
  "pp-struggle": { label: "PP / Struggle", cls: "preparation", order: 60 },
  "setup-interaction": { label: "Setup-dependent", cls: "preparation", order: 70 },
};
function hazardCategory(hazard) {
  if (hazard.category) return hazard.category;
  if (hazard.kind === "redirection") return "redirection";
  if (hazard.severity === "critical") return "self-ko";
  return "self-damage";
}
function safetyBadges(group) {
  const hazards = group.hazards || [];
  const badges = new Map();
  hazards.forEach(hazard => {
    const category = hazardCategory(hazard);
    const meta = SAFETY_BADGE_META[category] || { label: "Safety warning", cls: hazard.severity === "critical" ? "critical" : "preparation", order: 90 };
    const weather = hazard.kind === "weather";
    const unverified = hazard.verificationStatus === "needs-in-game-test";
    const key = weather ? "weather" : unverified ? `verify:${category}` : category;
    const label = weather ? "Weather-dependent" : unverified ? "Needs verification" : meta.label;
    const cls = weather || unverified ? "preparation" : meta.cls;
    badges.set(key, { label, cls, order: weather ? 75 : unverified ? 80 : meta.order });
  });
  const safety = [...badges.values()].sort((a,b) => a.order - b.order)
    .map(item => `<span class="safety-badge ${item.cls}">${escapeHtml(item.label)}</span>`).join("");
  const slow = (group.slowdowns || []).length > 0
    ? '<span class="safety-badge slowdown"><img src="assets/encounter-slowdown.png" alt="">Start delay</span>'
    : "";
  return safety + slow;
}
function rankingScoreHtml(score, best = false, isSafari = false) {
  const cls = best ? "best-score" : "hunt-score";
  if (!score.hasSlowdownRange) {
    return `<div class="${cls}"><strong>${formatNumber(score.pointsPerHour,4)}</strong><span>points / hour</span><div class="hunt-subscore">${formatNumber(score.encountersPerHour,0)} enc/hr · ${formatNumber(score.average,2)} ${isSafari ? "expected caught pts" : "avg pts"}</div></div>`;
  }
  return `<div class="${cls} score-range">
    <div class="score-case standard"><small>Standard</small><strong>${formatNumber(score.pointsPerHour,4)}</strong><span>points / hour</span><div class="hunt-subscore">${formatNumber(score.standardEncountersPerHour,0)} enc/hr</div></div>
    <div class="score-case slowed"><small>100% slowed alternative</small><strong>${formatNumber(score.fullDelayPointsPerHour,4)}</strong><span>points / hour</span><div class="hunt-subscore">${formatNumber(score.fullDelayEncountersPerHour,0)} enc/hr</div></div>
  </div>`;
}
function pokemonSafetyMarkers(component) {
  const hazards = component.hazards || [];
  const critical = hazards.some(h => h.severity === "critical");
  const preparationOnly = hazards.length > 0 && hazards.every(h => h.severity === "preparation");
  const slow = component.slowAbilities || [];
  const title = hazards.map(h => `${h.name} [${hazardCategory(h)}]: ${h.consequence}`).join(" | ");
  const cls = critical ? "critical" : preparationOnly ? "preparation" : "warning";
  const danger = hazards.length ? `<b class="poke-warning ${cls}" title="${escapeHtml(title)}">⚠</b>` : "";
  const delay = slow.length ? `<b class="poke-slow" title="Start-of-battle delay: ${escapeHtml(slow.join(", "))}"><img src="assets/encounter-slowdown.png" alt=""></b>` : "";
  return danger + delay;
}
function componentSprite(component) {
  return component.unknown ? '<span class="unknown-sprite">?</span>' : `<img src="${sprite(component.pokemonId)}" alt="">`;
}
function compositionHtml(detail, max = 3) {
  return `<div class="composition-icons">${detail.slice(0,max).map(c => `<span class="poke-chip ${c.unknown ? "unknown" : ""}" title="${escapeHtml(c.pokemon)} · ${formatPercent(c.share)}${c.rotationalEstimated ? ` · Tier ${c.rotationalTier} estimate` : c.unknown ? " · unscored by default" : ` · Tier ${c.tier}`} ">${pokemonSafetyMarkers(c)}${componentSprite(c)}<span>${escapeHtml(c.pokemon)} ${formatPercent(c.share,0)}</span></span>`).join("")}${detail.length > max ? `<span class="method-pill">+${detail.length-max}</span>` : ""}</div>`;
}
function rankingCardHtml(row, index) {
  const rank = index + 1;
  const present = groupLocationPresentation(row.group);
  const alt = present.alt ? `<div class="hunt-subscore alt-count">${escapeHtml(present.alt)}</div>` : "";
  return `<article class="hunt-card" data-rank-index="${index}" tabindex="0" role="button">
    <div class="hunt-rank">#${rank}</div>
    <div class="hunt-title">
      <h3>${escapeHtml(present.title)}</h3>
      <div class="hunt-meta">${escapeHtml(present.subtitle)} · ${escapeHtml(row.group.week)} · ${escapeHtml(row.group.season)}</div>
      <div class="hunt-methods"><span class="method-pill">${escapeHtml(row.group.method)}</span><span class="availability-pill">${escapeHtml(row.group.timeLabel)}</span><span class="confidence ${row.group.confidence}">${escapeHtml(row.group.confidence)}</span>${safetyBadges(row.group)}${row.group.safari ? safariCaptureBadge(row.score) : ""}${row.group.safariPool ? `<span class="safety-badge coverage">${formatPercent(row.group.safariPool.documentedTotal,0)} documented · ${escapeHtml(safariRotationalLabel(row.group, row.score.settings))}</span>` : ""}</div>
      ${compositionHtml(row.score.detail, 4)}${alt}
    </div>
    ${rankingScoreHtml(row.score, false, row.group.safari)}
  </article>`;
}
function bindRankingCards(grid, mode, playerId) {
  $$('.hunt-card:not([data-bound])', grid).forEach(card => {
    const row = currentRankingRows[Number(card.dataset.rankIndex)];
    if (!row) return;
    card.dataset.bound = "true";
    const open = () => openSpotDialog(row.group, mode, playerId);
    card.addEventListener('click', open);
    card.addEventListener('keydown', event => {
      if (event.key === 'Enter' || event.key === ' ') {
        event.preventDefault();
        open();
      }
    });
  });
}
function stopRankingAutoload() {
  rankingRenderToken += 1;
  rankingObserver?.disconnect();
  rankingObserver = null;
}
function appendRankingChunk(mode, playerId, token) {
  if (token !== rankingRenderToken) return;
  const grid = $("#rankRows");
  const status = $("#rankLoadStatus");
  const start = Number(grid.dataset.rendered || 1);
  const end = Math.min(start + 250, currentRankingRows.length);
  if (end <= start) {
    status.classList.add("hidden");
    rankingObserver?.disconnect();
    rankingObserver = null;
    return;
  }
  grid.insertAdjacentHTML("beforeend", currentRankingRows.slice(start, end).map((row, offset) => rankingCardHtml(row, start + offset)).join(""));
  grid.dataset.rendered = String(end);
  bindRankingCards(grid, mode, playerId);
  if (end >= currentRankingRows.length) {
    status.classList.add("hidden");
    rankingObserver?.disconnect();
    rankingObserver = null;
  } else {
    status.textContent = `${end.toLocaleString()} / ${currentRankingRows.length.toLocaleString()} loaded`;
  }
}
function renderRankings() {
  stopRankingAutoload();
  const context = getCatchContext();
  const mode = $("#rankMode").value;
  const playerId = $("#rankPlayer").value || allPlayers()[0]?.id;
  const limitValue = $("#rankLimit").value || "100";
  const allMode = limitValue === "all";
  const numericLimit = Math.max(1, Number(limitValue) || 100);
  const autoContext = currentAutoContext();
  const allMatches = GROUPS
    .filter(group => rankingFilters(group, context, autoContext))
    .map(group => ({ group, score: scoreGroup(group, mode, playerId, context) }))
    .filter(row => row.score.encountersPerHour > 0)
    .sort((a,b) => b.score.pointsPerHour - a.score.pointsPerHour);

  const best = allMatches[0]?.score.pointsPerHour || 0;
  const ratio = Number($("#rankRange").value || 0);
  const cutoff = ratio > 0 ? best * ratio : 0;
  currentRankingRows = ratio > 0
    ? allMatches.filter(row => row.score.pointsPerHour + 1e-12 >= cutoff)
    : allMatches;
  const initialCount = allMode
    ? Math.min(250, currentRankingRows.length)
    : Math.min(numericLimit, currentRankingRows.length);
  const shown = currentRankingRows.slice(0, initialCount);

  $("#kpiMatches").textContent = currentRankingRows.length.toLocaleString();
  $("#kpiAllMatches").textContent = `${allMatches.length.toLocaleString()} before range`;
  $("#kpiBest").textContent = best ? formatNumber(best,4) : "—";
  $("#kpiCutoff").textContent = ratio > 0 && best ? `${formatNumber(cutoff,4)} · ${Math.round(ratio*100)}%` : "None";
  const settings = getEffectiveSettings();
  const denominator = currentRankingRows[0]
    ? shinyDenominatorForMethod(currentRankingRows[0].group.method, settings)
    : settings.baseShinyDenominator / (1 + settings.eventWildBoost);
  $("#kpiRate").textContent = `1 / ${Math.round(denominator).toLocaleString()}`;

  const bestWrap = $("#bestHunt");
  if (shown.length) {
    const row = shown[0];
    const present = groupLocationPresentation(row.group);
    bestWrap.innerHTML = `<article class="best-hunt" tabindex="0" role="button" aria-label="Open best hunt calculation">
      <div class="best-rank">#1</div>
      <div class="best-copy">
        <span class="best-method">${escapeHtml(row.group.method)}</span>
        <h2>${escapeHtml(present.title)}</h2>
        <p>${escapeHtml(present.subtitle)} · ${escapeHtml(row.group.week)} · ${escapeHtml(row.group.season)} · ${escapeHtml(row.group.timeLabel)}</p>
        <div class="hunt-methods best-badges">${safetyBadges(row.group)}${row.group.safari ? safariCaptureBadge(row.score) : ""}</div>
        ${present.alt ? `<p class="alt-count">${escapeHtml(present.alt)}</p>` : ""}
      </div>
      <div>${compositionHtml(row.score.detail, 6)}</div>
      ${rankingScoreHtml(row.score, true, row.group.safari)}
    </article>`;
    const bestCard = bestWrap.querySelector('.best-hunt');
    const open = () => openSpotDialog(row.group, mode, playerId);
    bestCard.addEventListener('click', open);
    bestCard.addEventListener('keydown', event => { if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); open(); } });
  } else {
    bestWrap.innerHTML = "";
  }

  const grid = $("#rankRows");
  grid.innerHTML = shown.slice(1).map((row, offset) => rankingCardHtml(row, offset + 1)).join("");
  grid.dataset.rendered = String(initialCount);
  bindRankingCards(grid, mode, playerId);

  const status = $("#rankLoadStatus");
  if (allMode && initialCount < currentRankingRows.length) {
    const token = rankingRenderToken;
    status.textContent = `${initialCount.toLocaleString()} / ${currentRankingRows.length.toLocaleString()} loaded`;
    status.classList.remove("hidden");
    rankingObserver = new IntersectionObserver(entries => {
      if (entries.some(entry => entry.isIntersecting)) appendRankingChunk(mode, playerId, token);
    }, { rootMargin: "1200px 0px" });
    rankingObserver.observe(status);
  } else {
    status.classList.add("hidden");
  }
  $("#rankEmpty").classList.toggle("hidden", currentRankingRows.length > 0);
}

function rawSourceFor(group, component) {
  if (group.lure) {
    const baseContribution = Number(component.baseShare || 0);
    const lureContribution = Number(component.lureShare || 0);
    if (baseContribution > 0 && lureContribution > 0) {
      return { label: `${formatPercent(baseContribution,1)} + ${formatPercent(lureContribution,1)}`, raw: null, explanation: "base + Lure slot" };
    }
    if (lureContribution > 0 || component.lureExclusive) {
      return { label: formatPercent(lureContribution || component.share, 1), raw: null, explanation: "Lure slot" };
    }
    if (baseContribution > 0) {
      return { label: formatPercent(baseContribution, 1), raw: null, explanation: "95% base contribution" };
    }
    const baseShare = component.share / 0.95;
    return { label: formatPercent(baseShare * group.rawTotal, 1), raw: baseShare * group.rawTotal, explanation: "Base table" };
  }
  const raw = component.rawRate ?? component.share * group.rawTotal;
  return { label: formatPercent(raw, 1), raw, explanation: "Dex rate" };
}
function openSpotDialog(group, mode, playerId) {
  const context = getCatchContext();
  const score = scoreGroup(group, mode, playerId, context);
  const player = allPlayers().find(p => p.id === playerId);
  const modeLabel = {player:`${player?.name || "Player"} · live`,team:"Team live",fresh:"Fresh event",base:"Base tier value",duplicate:"All duplicate"}[mode];
  const present = groupLocationPresentation(group);
  const rodExplanation = rodMethodExplanation(group);
  const methodExplanation = group.method.includes("Horde")
    ? `Sweet Scent uses only the ${formatPercent(group.rawTotal,0)} horde block. Each raw rate is divided by that block total.`
    : group.method === "Fossil"
      ? "Each fossil revives into one guaranteed species. The event's +10% wild-only shiny boost is not applied."
      : group.method === "Honey Tree"
        ? "The Dex Honey Tree pool is normalized for this time of day. Encounters/hour is an editable active-run assumption."
        : rodExplanation
          ? rodExplanation
        : group.safariPool
          ? `${group.safariPool.note} Known species keep their unconditional shares. ${score.rotationalTier >= 0 ? `The unknown slot is currently estimated as Tier ${score.rotationalTier} (${score.rotationalBasePoints} base points). Live modes cannot infer its evolution-line bonus or duplicate state from a tier alone.` : "The unknown slot is unscored until a rotational tier is selected in Settings, so the result is a lower bound."}`
        : group.lure
          ? "The complete random encounter pool, including natural hordes, is scaled to 95%, then the 5% lure-exclusive roll is added."
          : group.method.includes("Chum Bucket")
            ? "Chum keeps the underlying fishing species table; its extra encounters are represented by the editable encounters/hour assumption."
            : group.rawTotal < 0.999
              ? `The numeric ${group.method.toLowerCase()} block totals ${formatPercent(group.rawTotal,1)} and is normalized within this method.`
              : "The encounter composition already totals 100% for this method.";
  const rows = score.detail.map(c => {
    const raw = rawSourceFor(group, c);
    const status = c.rotationalEstimated ? `<span class="confidence medium">T${c.rotationalTier} estimate</span>` : c.unknown ? '<span class="confidence medium">rotation unscored</span>' : c.duplicatePlayer ? '<span class="confidence low">duplicate</span>' : c.missingTeam ? '<span class="confidence high">unique open</span>' : '<span class="confidence medium">line caught</span>';
    const catchCell = group.safari
      ? `<td class="numeric"><strong>${formatPercent(c.catchChance)}</strong><small class="muted">${escapeHtml(c.catchSource)}</small></td>`
      : "";
    return `<tr><td>${componentSprite(c)}${pokemonSafetyMarkers(c)}${escapeHtml(c.pokemon)}</td><td>${raw.label}<small class="muted"> · ${raw.explanation}</small></td><td class="numeric">${formatPercent(c.share)}</td>${catchCell}<td class="numeric">${c.unknown && !c.rotationalEstimated ? "—" : formatNumber(c.score,1)}</td><td>${status}</td></tr>`;
  }).join("");
  const notes = group.validation.map(note => `<div class="validation-note ${note.level}">${escapeHtml(note.message)}</div>`).join("");
  const hazardRows = (group.hazards || []).map(h => {
    const category = hazardCategory(h);
    const meta = SAFETY_BADGE_META[category] || { label: category || "Safety warning" };
    const verification = h.verificationStatus && h.verificationStatus !== "confirmed"
      ? `<em class="verification-status ${escapeHtml(h.verificationStatus)}">${escapeHtml(h.verificationStatus === "needs-in-game-test" ? "Needs in-game verification" : "Community documented")}</em>`
      : "";
    return `<div class="safety-row ${h.severity}"><strong>${escapeHtml(h.pokemon)} · ${escapeHtml(h.name)} <span class="hazard-category">${escapeHtml(meta.label)}</span>${verification}</strong><span>${escapeHtml(h.levelRange ? `Lv. ${h.levelRange} · ` : "")}${escapeHtml(h.consequence)}</span><small>${escapeHtml(h.counter)}</small></div>`;
  }).join("");
  const slowdownRows = (group.slowdowns || []).map(x => `<div class="safety-row slowdown"><strong>${escapeHtml(x.pokemon)} · ${escapeHtml(x.abilities.join(" / "))}</strong><span>May add a start-of-battle animation or message.</span></div>`).join("");
  const safetySection = hazardRows || slowdownRows ? `<section class="dialog-section"><h4>Shiny safety</h4><div class="safety-list">${hazardRows}${slowdownRows}</div></section>` : "";
  const locations = displayLocations(group).map(location => `<div class="location-option"><div><strong>${escapeHtml(location.location)}</strong><small>${escapeHtml(location.region)}</small></div><small>${escapeHtml(location.encounterTypes.join(" / "))}</small></div>`).join("");
  const captureExplanation = group.safari
    ? score.captureMode === "global"
      ? `Global Safari catch override: ${formatPercent(score.captureAverage)} success (${formatPercent(score.captureLoss)} loss).`
      : `Weighted Safari catch estimate: ${formatPercent(score.captureAverage)} success (${formatPercent(score.captureLoss)} loss). ${formatPercent(score.speciesCaptureCoverage)} of the shown pool has matched Johto/Great Marsh species data; the remainder uses the ${formatPercent(score.settings.safariUnknownCatchChance)} fallback.`
    : "";
  const formula = group.safari
    ? `${formatNumber(score.encountersPerHour,0)} encounters/hr ÷ ${Math.round(score.denominator).toLocaleString()} × ${formatNumber(score.average,2)} expected captured points/shiny<br><small>${escapeHtml(captureExplanation)}</small><br><span class="calc-result">= ${formatNumber(score.pointsPerHour,4)} expected points/hour</span>`
    : score.hasSlowdownRange
      ? `<strong>Standard estimate</strong><br>${formatNumber(score.standardEncountersPerHour,0)} encounters/hr ÷ ${Math.round(score.denominator).toLocaleString()} × ${formatNumber(score.average,2)} avg points<br><span class="calc-result">= ${formatNumber(score.pointsPerHour,4)} expected points/hour</span><hr><strong>100% slowed alternative</strong><br>${formatNumber(score.fullDelayEncountersPerHour,0)} encounters/hr ÷ ${Math.round(score.denominator).toLocaleString()} × ${formatNumber(score.average,2)} avg points<br><span class="calc-result">= ${formatNumber(score.fullDelayPointsPerHour,4)} points/hour</span><br><small>The slowed alternative uses the full editable slowed baseline whenever this hunt contains any start-delay ability. Encounter share is not used to interpolate the result.</small>`
      : `${formatNumber(score.encountersPerHour,0)} encounters/hr ÷ ${Math.round(score.denominator).toLocaleString()} × ${formatNumber(score.average,2)} avg points<br><span class="calc-result">= ${formatNumber(score.pointsPerHour,4)} expected points/hour</span>`;
  $("#spotDialogContent").innerHTML = `<div class="dialog-body">
    <div class="dialog-title"><div><h3>${escapeHtml(present.title)}</h3><p>${escapeHtml(group.week)} · ${escapeHtml(group.season)} · ${escapeHtml(group.timeLabel)} · ${escapeHtml(group.method)}</p></div></div>
    <div class="dialog-score-grid"><div class="dialog-score"><span>${score.hasSlowdownRange ? "Standard points/hour" : "Points/hour"}</span><strong>${formatNumber(score.pointsPerHour,4)}</strong></div><div class="dialog-score"><span>${group.safari ? "Expected captured points/shiny" : score.hasSlowdownRange ? "100% slowed points/hour" : "Average points/shiny"}</span><strong>${group.safari ? formatNumber(score.average,2) : score.hasSlowdownRange ? formatNumber(score.fullDelayPointsPerHour,4) : formatNumber(score.average,2)}</strong></div><div class="dialog-score"><span>${group.safari ? "Catch success estimate" : score.hasSlowdownRange ? "Standard / slowed speed" : "Encounters/hour"}</span><strong>${group.safari ? formatPercent(score.captureAverage,1) : score.hasSlowdownRange ? `${formatNumber(score.standardEncountersPerHour,0)} / ${formatNumber(score.fullDelayEncountersPerHour,0)}` : formatNumber(score.encountersPerHour,0)}</strong></div></div>
    <p class="muted">Scoring mode: <strong>${escapeHtml(modeLabel)}</strong>. Secret expected value if caught: ${formatNumber(score.secretEV,2)}. Safari bonus if caught: ${formatNumber(score.safariEV,2)}.${group.safari ? ` Balls-only community estimates model up to 30 Safari Balls; unmatched species and unknown rotationals use the editable fallback unless the global override is selected.` : ""}</p>
    <section class="dialog-section"><h4>Equivalent locations</h4><div class="location-list">${locations}</div></section>
    <section class="dialog-section"><h4>Encounter calculation</h4><p class="muted">${escapeHtml(methodExplanation)}</p><table class="raw-table"><thead><tr><th>Pokémon</th><th>Raw source</th><th>Final share</th>${group.safari ? "<th>Catch estimate</th>" : ""}<th>Score if caught</th><th>Live status</th></tr></thead><tbody>${rows}</tbody></table></section>
    ${safetySection}
    <section class="dialog-section"><h4>Points/hour formula</h4><div class="calc-box">${formula}</div></section>
    ${notes ? `<section class="dialog-section"><h4>Validation and assumptions</h4><div class="note-list">${notes}</div></section>` : ""}
  </div>`;
  $("#spotDialog").showModal();
}
function resetRankingFilters() {
  ["rankSearch","rankRegion","rankMethod","rankConfidence"].forEach(id => $("#"+id).value = "");
  $("#rankWeek").value = "auto";
  $("#rankTime").value = "auto";
  $("#rankMode").value = "player";
  $("#rankRange").value = "0.8";
  $("#rankLimit").value = "100";
  $("#rankOnlyMissing").checked = false;
  $("#rankIncludeIncomplete").checked = false;
  renderRankings();
}
function downloadRankingCsv() {
  const headers = ["rank","locations","regions","week","season","time","method","encounters_per_hour_standard","encounters_per_hour_100pct_slowed","slowdown_exposure","average_points","points_per_hour_standard","points_per_hour_100pct_slowed","confidence","composition","safety_warnings","slowdown_abilities","safari_coverage","safari_catch_success","safari_loss_chance","safari_catch_model","safari_component_estimates"];
  const rows = currentRankingRows.map((row,index) => [index+1,displayLocations(row.group).map(l=>`${l.region}: ${l.location}`).join(" | "),row.group.regions.join(" | "),row.group.week,row.group.season,row.group.timeLabel,row.group.method,row.score.standardEncountersPerHour,row.score.hasSlowdownRange ? row.score.fullDelayEncountersPerHour : "",row.score.slowdownExposure,row.score.average,row.score.pointsPerHour,row.score.hasSlowdownRange ? row.score.fullDelayPointsPerHour : "",row.group.confidence,row.score.detail.map(c=>`${c.pokemon} ${formatPercent(c.share)}`).join("; "),(row.group.hazards||[]).map(h=>`${h.pokemon}: ${h.name} [${h.category || h.kind}/${h.severity}/${h.verificationStatus || "confirmed"}]`).join("; "),(row.group.slowdowns||[]).map(x=>`${x.pokemon}: ${x.abilities.join("/")}`).join("; "),row.group.safariPool ? `${formatPercent(row.group.safariPool.documentedTotal)} documented; ${formatPercent(row.group.safariPool.unknownShare)} rotational; ${row.score.rotationalTier >= 0 ? `T${row.score.rotationalTier} estimate` : "unscored"}` : "",row.group.safari ? row.score.captureAverage : "",row.group.safari ? row.score.captureLoss : "",row.group.safari ? row.score.captureMode : "",row.group.safari ? row.score.detail.map(c=>`${c.pokemon}: ${formatPercent(c.catchChance)} (${c.catchSource})`).join("; ") : ""]);
  const csv = [headers,...rows].map(r => r.map(v => `"${String(v ?? "").replaceAll('"','""')}"`).join(",")).join("\n");
  downloadBlob("wartool-filtered-rankings.csv", new Blob([csv], {type:"text/csv;charset=utf-8"}));
}

function resolvePokemon(value) {
  return pokemonByName.get(normalize(value));
}
function renderPlayers() {
  refreshPlayerSelects();
  const remoteMode = isRemoteCatchMode();
  $("#playerChips").innerHTML = allPlayers().map(p => `<span class="player-chip">${escapeHtml(p.name)}${!remoteMode && state.players.length > 1 && state.players.some(x=>x.id===p.id) ? `<button data-remove-player="${p.id}" title="Remove">×</button>` : ""}</span>`).join("");
  $$('[data-remove-player]').forEach(btn => btn.addEventListener("click", () => removePlayer(btn.dataset.removePlayer)));
}
function addPlayer(name) {
  const clean = String(name || "").trim();
  if (!clean) return;
  const id = normalize(clean);
  if (allPlayers().some(p => p.id === id)) return toast("That player already exists.");
  state.players.push({ id, name: clean, teamId: selectedTeamId(), teamName: selectedTeamName(), teamOrder: allTeams().find(t => t.id === selectedTeamId())?.order || 99, active: true });
  saveState("Player added");
  renderAll();
}
function removePlayer(id) {
  if (state.catches.some(c => c.playerId === id && c.teamId === selectedTeamId())) return toast("Remove that player's local catches first.");
  state.players = state.players.filter(p => !(p.id === id && p.teamId === selectedTeamId()));
  saveState("Player removed");
  renderAll();
}
function addCatch(event) {
  event.preventDefault();
  if (isRemoteCatchMode()) return toast("Catches are managed in the connected Google Sheet.");
  const pokemon = resolvePokemon($("#catchPokemon").value);
  if (!pokemon) return toast("Choose a Pokémon from the list.");
  const player = allPlayers().find(p => p.id === $("#catchPlayer").value);
  const caughtAt = new Date($("#catchDate").value);
  state.catches.push({
    id: uid("catch"), source: "local", playerId: player.id, playerName: player.name,
    teamId: player.teamId || selectedTeamId(), teamName: player.teamName || selectedTeamName(),
    pokemonId: pokemon.id, line: pokemon.line,
    caughtAt: Number.isNaN(caughtAt.valueOf()) ? new Date().toISOString() : caughtAt.toISOString(),
    secret: $("#catchSecret").checked, alpha: $("#catchAlpha").checked,
    safari: $("#catchSafari").checked, egg: $("#catchEgg").checked,
    note: $("#catchNote").value.trim()
  });
  saveState("Shiny added");
  event.target.reset();
  $("#catchDate").value = localDateInputValue();
  renderAll();
  toast(`${pokemon.name} added.`);
}
function deleteCatch(id) {
  if (isRemoteCatchMode()) return;
  state.catches = state.catches.filter(c => c.id !== id);
  saveState("Shiny removed");
  renderAll();
}
function tierRowsHtml(itemsByTier, options = {}) {
  const caughtBoard = options.caughtBoard === true;
  return Array.from({ length: 8 }, (_, tier) => {
    const items = itemsByTier.get(tier) || [];
    const points = [50,45,40,30,15,10,5,3][tier];
    const content = items.length
      ? items.map(item => {
          const classes = ["tier-mon", item.caught === false ? "missing" : "caught", item.dim ? "search-dim" : ""].filter(Boolean).join(" ");
          const score = item.score != null ? `<span class="score-dot">${formatNumber(item.score,0)}</span>` : "";
          const flag = item.flag ? `<span class="flag-dot">${escapeHtml(item.flag)}</span>` : "";
          const shiny = item.shiny !== false;
          return `<div class="${classes}" data-tooltip="${escapeHtml(item.tooltip || item.name)}">${flag}${score}<img src="${sprite(item.pokemonId, shiny)}" alt="${escapeHtml(item.name)}"><strong>${escapeHtml(item.name)}</strong>${item.subtitle ? `<small>${escapeHtml(item.subtitle)}</small>` : ""}</div>`;
        }).join("")
      : `<span class="tier-empty">${caughtBoard ? "—" : "No matching evolution lines."}</span>`;
    return `<section class="tier-row" data-tier="${tier}"><div class="tier-label">T${tier}<small>${points} points</small></div><div class="tier-cell">${content}</div></section>`;
  }).join("");
}

function leaderboardRows(team) {
  const context = getCatchContext(team.id);
  const catches = activeCatches(team.id);
  const catchCounts = new Map();
  const lineSets = new Map();
  for (const item of catches) {
    catchCounts.set(item.playerId, (catchCounts.get(item.playerId) || 0) + 1);
    const pokemon = pokemonById.get(Number(item.pokemonId));
    if (!pokemon) continue;
    const lines = lineSets.get(item.playerId) || new Set();
    lines.add(item.line || pokemon.line);
    lineSets.set(item.playerId, lines);
  }
  return allPlayers(team.id).map(player => ({
    player,
    points: Number(context.playerTotals.get(player.id) || 0),
    basePoints: Number(context.playerBaseTotals.get(player.id) || 0),
    catches: Number(catchCounts.get(player.id) || 0),
    lines: Number(lineSets.get(player.id)?.size || 0),
  })).sort((a,b) => b.points - a.points || b.catches - a.catches || b.lines - a.lines || a.player.name.localeCompare(b.player.name));
}
function renderLeaderboards() {
  const teams = allTeams();
  const container = $("#playerLeaderboards");
  if (!container) return;
  container.innerHTML = teams.map(team => {
    const context = getCatchContext(team.id);
    const rows = leaderboardRows(team);
    const teamCatches = activeCatches(team.id).length;
    const body = rows.length ? rows.map((row,index) => {
      const rankClass = index < 3 ? ` top-${index + 1}` : "";
      return `<div class="leaderboard-row${rankClass}">
        <span class="leader-rank">#${index + 1}</span>
        <strong>${escapeHtml(row.player.name)}</strong>
        <span class="leader-stat"><b>${formatNumber(row.points,0)}</b><small>points</small></span>
        <span class="leader-stat no-species" title="Only the team-first species/evolution-line bonus is removed. Secret Shiny and Safari bonuses still count."><b>${formatNumber(row.basePoints,0)}</b><small>no species bonus</small></span>
        <span class="leader-stat"><b>${row.catches}</b><small>catches</small></span>
        <span class="leader-stat"><b>${row.lines}</b><small>lines</small></span>
      </div>`;
    }).join("") : '<div class="empty-state">No players available.</div>';
    return `<article class="panel leaderboard-card ${team.id === selectedTeamId() ? "selected" : ""}">
      <div class="panel-heading leaderboard-heading">
        <div><span class="panel-kicker">${escapeHtml(team.name)}</span><h2>Player leaderboard</h2><small>${teamCatches} ${teamCatches === 1 ? "catch" : "catches"}</small></div>
        <div class="leaderboard-team-total">
          <span><strong>${formatNumber(context.teamTotal,0)}</strong><small>points</small></span>
          <span class="no-species" title="Only the team-first species/evolution-line bonus is removed. Secret Shiny and Safari bonuses still count."><strong>${formatNumber(context.teamBaseTotal,0)}</strong><small>no species bonus</small></span>
        </div>
      </div>
      <div class="leaderboard-columns" aria-hidden="true"><span>Rank</span><span>Player</span><span>Points</span><span>No species bonus</span><span>Catches</span><span>Lines</span></div>
      <div class="leaderboard-rows">${body}</div>
    </article>`;
  }).join("");
}

function renderCatches() {
  renderPlayers();
  const remoteMode = isRemoteCatchMode();
  const previewMode = previewToolsEnabled() && !remoteMode;
  $("#localCatchEditor").classList.toggle("hidden", !previewMode);
  const showNotice = remoteMode && remote.mode !== "live";
  $("#remoteCatchNotice").classList.toggle("hidden", !showNotice);
  if (showNotice) {
    $("#remoteCatchNotice").textContent = remote.mode === "preview"
      ? "Waiting for the first Sheet import."
      : "Preview data is active.";
  }
  $("#catchPageDescription").textContent = "";

  const context = getCatchContext();
  const filter = $("#catchFilterPlayer").value;
  const allTeamCatches = [...activeCatches()].sort((a,b) => new Date(b.caughtAt) - new Date(a.caughtAt));
  const catches = allTeamCatches.filter(item => !filter || item.playerId === filter);
  $("#catchCountBadge").textContent = allTeamCatches.length;
  $("#catchSummary").innerHTML = `<article class="summary-card"><span>Team points</span><strong>${formatNumber(context.teamTotal,0)}</strong></article><article class="summary-card"><span>Catches</span><strong>${allTeamCatches.length}</strong></article><article class="summary-card"><span>Unique lines</span><strong>${context.teamLines.size}</strong></article>`;

  const tierMap = new Map(Array.from({length:8}, (_,tier) => [tier, []]));
  for (const item of catches) {
    const pokemon = pokemonById.get(Number(item.pokemonId));
    if (!pokemon) continue;
    const scored = context.scores.get(item.id) || { total: 0, duplicate: false };
    const flags = [item.secret && "Secret", item.alpha && "Alpha", item.safari && "Safari", item.egg && "Egg", scored.duplicate && "Duplicate"].filter(Boolean);
    tierMap.get(Number(pokemon.tier)).push({
      pokemonId: pokemon.id,
      name: pokemon.name,
      subtitle: item.playerName || item.playerId,
      shiny: true,
      score: scored.total,
      flag: item.secret ? "S" : item.alpha ? "A" : item.safari ? "Z" : item.egg ? "E" : "",
      tooltip: `${pokemon.name}\n${item.playerName || item.playerId} · ${formatCatchDate(item)}\n${formatNumber(scored.total,0)} points${flags.length ? ` · ${flags.join(" · ")}` : ""}`
    });
  }
  for (const values of tierMap.values()) values.sort((a,b) => a.name.localeCompare(b.name) || a.subtitle.localeCompare(b.subtitle));
  $("#catchTierBoard").classList.toggle("hidden", catches.length === 0);
  $("#catchTierBoard").innerHTML = catches.length ? tierRowsHtml(tierMap, { caughtBoard: true }) : "";
  $("#recentCatchPanel").classList.toggle("hidden", catches.length === 0);

  $("#catchRows").innerHTML = catches.map(item => {
    const pokemon = pokemonById.get(Number(item.pokemonId));
    const scored = context.scores.get(item.id) || { total:0, duplicate:false };
    const flags = [item.secret&&"Secret",item.alpha&&"Alpha",item.safari&&"Safari",item.egg&&"Egg",scored.duplicate&&"Duplicate"].filter(Boolean);
    return `<article class="catch-row"><img src="${sprite(pokemon.id,true)}" alt=""><div><strong>${escapeHtml(pokemon.name)}</strong><small>${escapeHtml(item.playerName || item.playerId)} · ${formatCatchDate(item)} · Tier ${pokemon.tier}</small><div class="catch-meta">${flags.map(flag => `<span class="flag">${escapeHtml(flag)}</span>`).join("")}${item.note ? `<span class="flag">${escapeHtml(item.note)}</span>` : ""}</div></div><div><div class="score-badge">${formatNumber(scored.total,0)} pts</div>${remoteMode ? "" : `<button class="icon-button" data-delete-catch="${item.id}" title="Delete">×</button>`}</div></article>`;
  }).join("");
  $("#catchEmpty").classList.toggle("hidden", catches.length > 0);
  $$('[data-delete-catch]').forEach(button => button.addEventListener("click", () => deleteCatch(button.dataset.deleteCatch)));
}
function renderProgress() {
  const context = getCatchContext();
  const query = normalize($("#progressSearch").value);
  const status = $("#progressStatus").value;
  const selectedTier = $("#progressTier").value;
  const catchesByLine = new Map();
  for (const item of activeCatches()) {
    const pokemon = pokemonById.get(Number(item.pokemonId));
    if (!pokemon || catchesByLine.has(pokemon.line)) continue;
    catchesByLine.set(pokemon.line, item);
  }

  $("#progressKpis").innerHTML = `<article class="summary-card"><span>Evolution lines caught</span><strong>${context.teamLines.size}</strong></article><article class="summary-card"><span>Lines remaining</span><strong>${Math.max(0,lineInfo.length-context.teamLines.size)}</strong></article><article class="summary-card"><span>Team catches</span><strong>${activeCatches().length}</strong></article><article class="summary-card"><span>Team points</span><strong>${formatNumber(context.teamTotal,0)}</strong></article>`;

  const tierMap = new Map(Array.from({length:8}, (_,tier) => [tier, []]));
  for (const info of lineInfo) {
    const caught = context.teamLines.has(info.line);
    if (status === "caught" && !caught) continue;
    if (status === "missing" && caught) continue;
    if (selectedTier !== "" && Number(selectedTier) !== Number(info.tier)) continue;
    const queryMatch = !query || normalize(`${info.line} ${info.pokemon.map(p => p.name).join(" ")}`).includes(query);
    if (!queryMatch) continue;
    const catchItem = catchesByLine.get(info.line);
    const caughtPokemon = catchItem ? pokemonById.get(Number(catchItem.pokemonId)) : null;
    tierMap.get(Number(info.tier)).push({
      pokemonId: caughtPokemon?.id || info.spriteId,
      name: info.line,
      subtitle: caught ? (catchItem?.playerName || "Caught") : "Missing",
      shiny: caught,
      caught,
      flag: caught ? "✓" : "",
      tooltip: caught
        ? `${info.line}\nCaught by ${catchItem?.playerName || "team"}\nTier ${info.tier} · ${info.points} base points`
        : `${info.line}\nMissing evolution line\nTier ${info.tier} · ${info.points} base points`
    });
  }
  for (const values of tierMap.values()) values.sort((a,b) => a.name.localeCompare(b.name));
  $("#progressGrid").innerHTML = tierRowsHtml(tierMap);
}

const SCORING_FIELDS = [
  ["baseShinyDenominator","Base shiny denominator","30000"],
  ["eventWildBoost","Wild event boost","0.10"],
  ["uniqueBonus","Unique-line bonus","8"],
  ["secretBonus","Secret Shiny bonus","20"],
  ["secretChance","Secret chance given shiny","0.0625"],
  ["safariBonus","Safari catch bonus","10"]
];
const SAFARI_CATCH_FIELDS = [
  ["safariUnknownCatchChance","Unknown / unmatched Safari success","0.52"],
  ["safariCatchChance","Global Safari catch success","1.0"]
];
const ROTATIONAL_FIELDS = [
  ["johtoSafariRotationalTier", "Johto Safari rotational (10%)"],
  ["greatMarshRotationalTier", "Great Marsh rotational (20%)"]
];
function rotationalTierOptions(key, baseValue) {
  const hasOverride = Object.prototype.hasOwnProperty.call(state.rotationalOverrides || {}, key);
  const selected = hasOverride ? Number(state.rotationalOverrides[key]) : "default";
  const baseTier = Number(baseValue);
  const baseLabel = Number.isInteger(baseTier) && baseTier >= 0 && baseTier <= 7 ? `T${baseTier}` : "unscored";
  const options = [["default", `Use team/default (${baseLabel})`], [-1,"Unscored / unknown"], ...Object.entries(TIER_POINTS).map(([tier, points]) => [Number(tier), `Tier ${tier} · ${points} pts`])];
  return options.map(([value,label]) => `<option value="${value}" ${String(selected) === String(value) ? "selected" : ""}>${escapeHtml(label)}</option>`).join("");
}
function renderSettings() {
  const effective = getEffectiveSettings();
  const baseEffective = getBaseEffectiveSettings();
  const remoteOverride = Boolean(remote.settings);
  const previewMode = previewToolsEnabled() && !remoteOverride;
  $("#clearCatches").classList.toggle("hidden", Array.isArray(remote.catches));
  $("#remoteSettingsNotice").classList.add("hidden");
  $("#backupPreviewCard").classList.toggle("hidden", !previewMode);
  const safariModel = Number(effective.safariCatchModel) === 0 ? 0 : 1;
  const numericField = ([key,label,step], extraDisabled = false) => {
    const chance = key.toLowerCase().includes("chance");
    return `<div class="setting-row"><label>${escapeHtml(label)}</label><input class="settings-input" data-setting="${key}" type="number" ${chance ? 'min="0" max="1"' : ""} step="${step.includes('.') ? '0.0001' : '1'}" value="${effective[key]}" ${remoteOverride || extraDisabled ? "disabled" : ""}></div>`;
  };
  $("#scoringSettings").innerHTML = SCORING_FIELDS.map(field => numericField(field)).join("")
    + `<div class="setting-row"><label>Safari catch model</label><select class="settings-input" data-setting-select="safariCatchModel" ${remoteOverride ? "disabled" : ""}><option value="1" ${safariModel === 1 ? "selected" : ""}>Species estimates + fallback</option><option value="0" ${safariModel === 0 ? "selected" : ""}>Global override</option></select><small>Species estimates use community balls-only odds where matched.</small></div>`
    + SAFARI_CATCH_FIELDS.map(field => numericField(field, field[0] === "safariCatchChance" ? safariModel === 1 : safariModel === 0)).join("")
    + ROTATIONAL_FIELDS.map(([key,label]) => `<div class="setting-row"><label>${escapeHtml(label)}</label><select class="settings-input" data-rotational-setting="${key}">${rotationalTierOptions(key, baseEffective[key])}</select></div>`).join("");
  const methodSettingLabel = method => ({
    "5x Horde (Slowed)": "5× Horde · 100% start-delay baseline",
    "3x Horde (Slowed)": "3× Horde · 100% start-delay baseline",
    "Fishing": "Fishing · Old / Good / Super Rod",
    "Fishing + Lure": "Fishing + Lure · any rod",
    "Fishing + Chum Bucket": "Fishing + Chum Bucket · any rod",
    "Fishing + Lure + Chum Bucket": "Fishing + Lure + Chum Bucket · any rod",
  }[method] || method);
  $("#methodSettings").innerHTML = Object.entries(effective.methodSpeeds).map(([method,value]) => `<div class="setting-row"><label>${escapeHtml(methodSettingLabel(method))}</label><input class="settings-input" data-method="${escapeHtml(method)}" type="number" min="0" step="1" value="${value}" ${remoteOverride ? "disabled" : ""}>${SLOW_BASELINE_METHOD[method] ? "" : method.includes("(Slowed)") ? '<small>Shown as the 100% slowed alternative whenever the horde contains any start-delay ability.</small>' : ""}</div>`).join("");
  $$('[data-setting]').forEach(input => input.addEventListener("change", () => { state.settings[input.dataset.setting] = Number(input.value); saveState(); renderRankings(); renderSettings(); }));
  $$('[data-setting-select]').forEach(input => input.addEventListener("change", () => { state.settings[input.dataset.settingSelect] = Number(input.value); saveState(); renderRankings(); renderSettings(); }));
  $$('[data-rotational-setting]').forEach(input => input.addEventListener("change", () => {
    const key = input.dataset.rotationalSetting;
    state.rotationalOverrides ||= {};
    if (input.value === "default") delete state.rotationalOverrides[key];
    else state.rotationalOverrides[key] = Number(input.value);
    saveState();
    renderRankings();
    renderSettings();
  }));
  $$('[data-method]').forEach(input => input.addEventListener("change", () => { state.settings.methodSpeeds[input.dataset.method] = Number(input.value); saveState(); renderRankings(); }));
  const cfg = packagedOrLocalConfig();
  $("#sheetTeam1Url").value = state.liveConfig.team1CatchesCsvUrl || PACKAGED_LIVE_CONFIG.team1CatchesCsvUrl || "";
  $("#sheetTeam2Url").value = state.liveConfig.team2CatchesCsvUrl || PACKAGED_LIVE_CONFIG.team2CatchesCsvUrl || "";
  $("#sheetSettingsUrl").value = state.liveConfig.settingsCsvUrl || PACKAGED_LIVE_CONFIG.settingsCsvUrl || "";
  $("#sheetRefreshSeconds").value = String(cfg.refreshSeconds || 0);
  const connectionStatus = $("#sheetConnectionStatus");
  const configured = Boolean(cfg.team1CatchesCsvUrl || cfg.team2CatchesCsvUrl || cfg.settingsCsvUrl);
  connectionStatus.classList.toggle("hidden", !configured);
  if (configured) {
    if (remote.errors.length) {
      connectionStatus.innerHTML = `<strong>Sheet connection problem.</strong><br>${remote.errors.map(error => escapeHtml(error)).join("<br>")}`;
    } else if (remote.lastUpdated && (remote.catches || remote.settings)) {
      connectionStatus.innerHTML = `<strong>Connected.</strong> Last update: ${escapeHtml(remote.lastUpdated.toLocaleTimeString([], {hour:"2-digit", minute:"2-digit"}))}.`;
    } else {
      connectionStatus.innerHTML = `<strong>Static preview.</strong> The Google Sheet pipeline is intentionally disabled in this design patch.`;
    }
  }
}
function resetSettings() {
  if (!confirm("Reset every local scoring and encounter-speed value?")) return;
  state.settings = structuredClone(DEFAULT_SETTINGS);
  state.rotationalOverrides = {};
  saveState("Settings reset");
  renderAll();
}
function saveSheetConfig() {
  state.liveConfig = {
    team1CatchesCsvUrl: $("#sheetTeam1Url").value.trim(),
    team2CatchesCsvUrl: $("#sheetTeam2Url").value.trim(),
    settingsCsvUrl: $("#sheetSettingsUrl").value.trim(),
    refreshSeconds: Number($("#sheetRefreshSeconds").value || 0)
  };
  saveState("Sheet connection saved");
  loadLiveData(true);
}
function clearSheetConfig() {
  state.liveConfig = { team1CatchesCsvUrl:"", team2CatchesCsvUrl:"", settingsCsvUrl:"", refreshSeconds:0 };
  remote = { roster:null, catches:null, settings:null, errors:[], lastUpdated:null };
  saveState("Local mode enabled");
  loadLiveData(true);
}
function exportState() {
  const payload = { ...state, exportedAt: new Date().toISOString(), siteVersion: META.siteVersion };
  downloadBlob(`wartool-backup-${new Date().toISOString().slice(0,10)}.json`, new Blob([JSON.stringify(payload,null,2)], {type:"application/json"}));
}
function clearCatches() {
  if (!state.catches.length) return;
  if (!confirm("Delete every local preview catch?")) return;
  state.catches = [];
  saveState("Local catches cleared");
  renderAll();
}
function downloadBlob(name, blob) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url; a.download = name; a.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
function renderQuality() {
  const s = VALIDATION.summary || {};
  $("#qualityKpis").innerHTML = `<article class="kpi"><span>Raw ranking rows</span><strong>${Number(s.rawVariants||0).toLocaleString()}</strong></article><article class="kpi"><span>Clean display groups</span><strong>${Number(s.displayGroups||0).toLocaleString()}</strong><small>${Number(s.mergedGroups||0).toLocaleString()} include alternative locations</small></article><article class="kpi"><span>Any-time groups</span><strong>${Number(s.anyTimeGroups||0).toLocaleString()}</strong></article><article class="kpi"><span>Fatal validation errors</span><strong>${Number(s.fatalChecks||0).toLocaleString()}</strong><small>${Number(s.warnings||0).toLocaleString()} warnings · ${Number(s.assumptions||0).toLocaleString()} assumptions</small></article>`;
  $("#buildInfo").innerHTML = `<dt>WARtool version</dt><dd>${escapeHtml(META.siteVersion || "unknown")}</dd><dt>Generated</dt><dd>${escapeHtml(META.generatedAt || "unknown")}</dd><dt>Pokémon in dump</dt><dd>${Number(META.monsters_in_dump||0).toLocaleString()}</dd><dt>Time/location rows</dt><dd>${Number(s.locationTimeCollapsed||0).toLocaleString()}</dd><dt>Display groups</dt><dd>${Number(s.displayGroups||0).toLocaleString()}</dd><dt>Team-data source</dt><dd>${escapeHtml(remote.source || (remote.mode === "live" ? "Generated live data" : "Bundled preview"))}</dd>`;
  const level = $("#qualityLevel").value;
  const issueRows = [];
  for (const issue of VALIDATION.issues || []) {
    for (const note of issue.notes || []) {
      if (level && note.level !== level) continue;
      issueRows.push({ ...note, issue });
    }
  }
  $("#qualityIssues").innerHTML = issueRows.slice(0,250).map(row => `<div class="issue-row"><span class="confidence ${row.level === 'fatal' ? 'low' : row.level === 'warning' ? 'medium' : 'high'}">${escapeHtml(row.level)}</span><strong>${escapeHtml(row.issue.method)}</strong><div><strong>${escapeHtml(row.issue.locations.slice(0,2).join(" / "))}${row.issue.locations.length>2 ? ` +${row.issue.locations.length-2}` : ""}</strong><p>${escapeHtml(row.message)}</p></div></div>`).join("") || '<div class="empty">No notes at this level.</div>';
}
function renderAll() {
  renderTeamTabs();
  refreshPlayerSelects();
  renderRankings();
  renderCatches();
  renderLeaderboards();
  renderProgress();
  renderSettings();
  renderQuality();
}
function toast(message) {
  const el = $("#toast");
  el.textContent = message;
  el.classList.remove("hidden");
  clearTimeout(toast.timer);
  toast.timer = setTimeout(() => el.classList.add("hidden"), 2600);
}
function bindEvents() {
  $$(".tab").forEach(tab => tab.addEventListener("click", () => activateTab(tab.dataset.tab)));
  $$(`[data-tab-jump]`).forEach(button => button.addEventListener("click", () => activateTab(button.dataset.tabJump)));
  $("#themeToggle")?.addEventListener("click", toggleTheme);
  ["rankSearch","rankWeek","rankTime","rankRegion","rankMethod","rankMode","rankPlayer","rankConfidence","rankRange","rankLimit","rankOnlyMissing","rankIncludeIncomplete"].forEach(id => $("#"+id).addEventListener(id === "rankSearch" ? "input" : "change", renderRankings));
  $("#rankResetFilters").addEventListener("click", resetRankingFilters);
  $("#rankDownload").addEventListener("click", downloadRankingCsv);
  $("#catchForm").addEventListener("submit", addCatch);
  $("#playerForm").addEventListener("submit", event => { event.preventDefault(); addPlayer($("#playerName").value); event.target.reset(); });
  $("#catchFilterPlayer").addEventListener("change", renderCatches);
  $("#progressSearch").addEventListener("input", renderProgress);
  $("#progressStatus").addEventListener("change", renderProgress);
  $("#progressTier").addEventListener("change", renderProgress);
  $("#resetSettings").addEventListener("click", resetSettings);
  $("#saveSheetConfig").addEventListener("click", saveSheetConfig);
  $("#clearSheetConfig").addEventListener("click", clearSheetConfig);
  $("#exportState").addEventListener("click", exportState);
  $("#quickExport")?.addEventListener("click", exportState);
  $("#quickRefresh")?.addEventListener("click", () => refreshStaticLiveState({ notify: true }));
  $("#refreshCatches").addEventListener("click", () => refreshStaticLiveState({ notify: true }));
  $("#clearCatches").addEventListener("click", clearCatches);
  $("#qualityLevel").addEventListener("change", renderQuality);
  $("#importState").addEventListener("change", async event => {
    const file = event.target.files[0];
    if (!file) return;
    try {
      const parsed = JSON.parse(await file.text());
      const rosterById = new Map(PACKAGED_ROSTER.map(p => [p.id, p]));
      state = {
        version: 9,
        settings: deepMergeSettings(parsed.settings),
        rotationalOverrides: parsed.rotationalOverrides && typeof parsed.rotationalOverrides === "object" ? { ...parsed.rotationalOverrides } : {},
        players: (() => {
          const map = new Map(PACKAGED_ROSTER.map(player => [player.id, { ...player }]));
          for (const player of Array.isArray(parsed.players) ? parsed.players : []) map.set(player.id || normalize(player.name), { ...map.get(player.id || normalize(player.name)), ...player });
          return [...map.values()];
        })(),
        selectedTeamId: parsed.selectedTeamId || DEFAULT_STATE.selectedTeamId,
        catches: (Array.isArray(parsed.catches) ? parsed.catches : []).map(item => ({ ...item, teamId: item.teamId || rosterById.get(item.playerId)?.teamId || DEFAULT_STATE.selectedTeamId, teamName: item.teamName || rosterById.get(item.playerId)?.teamName || PACKAGED_ROSTER[0]?.teamName || "Team" })),
        liveConfig: structuredClone(DEFAULT_STATE.liveConfig)
      };
      saveState("Backup imported");
      await loadLiveData(false);
      toast("Backup imported.");
    } catch (error) { toast(`Import failed: ${error.message}`); }
    event.target.value = "";
  });
}
async function start() {
  if (!GROUPS.length || !POKEMON.length) {
    $("#fatal").classList.remove("hidden");
    $("#fatal").innerHTML = `WARtool could not load its data files.<code>Run START_WARTOOL.bat instead of opening index.html directly.</code>`;
    return;
  }
  initializeStaticUi();
  bindEvents();
  const requested = location.hash.replace("#", "");
  if (["rankings","catches","players","progress","settings","quality"].includes(requested)) activateTab(requested);
  else activateTab("rankings");
  setTheme(currentTheme());
  renderAll();
  await loadStaticLiveState();
  renderAll();
  scheduleStaticLiveStateRefresh();
  scheduleAutoContextRefresh();
}

start().catch(error => {
  console.error(error);
  $("#fatal").classList.remove("hidden");
  $("#fatal").textContent = `WARtool failed to start: ${error.message}`;
});
