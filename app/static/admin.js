const TOAST_VISIBLE_MS = 3000;
const HTTP_UNAUTHORIZED = 401;
const DEFAULT_IMAGE_SIZE = "1024x1024";

const $ = selector => document.querySelector(selector);
const $$ = selector => document.querySelectorAll(selector);

bindTabs();
bindActions();
loadStats();

function bindTabs() {
  $$(".tab").forEach(tab => {
    tab.addEventListener("click", () => activateTab(tab));
  });
}

function bindActions() {
  $("#logout-btn").addEventListener("click", logout);
  $("#refresh-stats-btn").addEventListener("click", loadStats);
  $("#save-config-btn").addEventListener("click", saveConfig);
  $("#test-btn").addEventListener("click", generateImage);
  $("#refresh-models-btn").addEventListener("click", loadModels);
  bindSizePresets();
}

function bindSizePresets() {
  $$(".size-presets .chip").forEach(chip => {
    chip.addEventListener("click", () => {
      $$(".size-presets .chip").forEach(item => item.classList.remove("active"));
      chip.classList.add("active");
    });
  });
}

function activateTab(tab) {
  $$(".tab").forEach(item => item.classList.remove("active"));
  $$(".tab-content").forEach(item => item.classList.add("hidden"));
  tab.classList.add("active");
  $(`#tab-${tab.dataset.tab}`).classList.remove("hidden");
  loadTabData(tab.dataset.tab);
}

function loadTabData(tabName) {
  if (tabName === "status") loadStats();
  if (tabName === "config") loadConfig();
  if (tabName === "models") loadModels();
  if (tabName === "test") loadTestModels();
}

async function api(path, options = {}) {
  const response = await fetch(path, options);
  if (response.status === HTTP_UNAUTHORIZED) redirectToLogin();
  if (!response.ok) throw new Error(await readError(response));
  return response.json();
}

async function readError(response) {
  const contentType = response.headers.get("content-type") || "";
  if (!contentType.includes("application/json")) return `HTTP ${response.status}`;
  const data = await response.json().catch(() => null);
  return data && typeof data.detail === "string" ? data.detail : `HTTP ${response.status}`;
}

function redirectToLogin() {
  window.location.href = "/";
}

function toast(message, type = "success") {
  const element = $("#toast");
  element.textContent = message;
  element.className = `toast ${type} show`;
  setTimeout(() => element.classList.remove("show"), TOAST_VISIBLE_MS);
}

async function loadStats() {
  try {
    renderStats(await api("/admin/stats"));
  } catch (error) {
    renderOfflineStats();
    toast(error.message || "加载状态失败", "error");
  }
}

function renderStats(data) {
  $("#st-dot").className = "status-dot online";
  $("#st-text").textContent = "在线";
  $("#st-cache").textContent = `${data.cache_count} / ${data.cache_max}`;
  $("#st-memory").textContent = `${data.cache_memory_mb} MB`;
  $("#st-total").textContent = data.total_requests;
  $("#st-success").textContent = data.success;
  $("#st-fail").textContent = data.fail;
  $("#st-apikey").textContent = data.api_key_masked;
}

function renderOfflineStats() {
  $("#st-dot").className = "status-dot offline";
  $("#st-text").textContent = "离线";
}

async function loadConfig() {
  try {
    renderConfig(await api("/admin/config"));
  } catch (error) {
    toast(error.message || "加载配置失败", "error");
  }
}

function renderConfig(data) {
  $("#cfg-apikey-current").textContent = data.pollinations_api_key;
  $("#cfg-ttl").value = data.image_cache_ttl;
  $("#cfg-maxsize").value = data.image_cache_max_size;
  $("#cfg-nologo").checked = data.default_nologo;
  $("#cfg-private").checked = data.default_private;
}

async function saveConfig() {
  try {
    await api("/admin/config", buildConfigRequest());
    $("#cfg-apikey").value = "";
    await loadConfig();
    toast("配置已保存");
  } catch (error) {
    toast(error.message || "保存失败", "error");
  }
}

function buildConfigRequest() {
  return {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify(readConfigForm()),
  };
}

function readConfigForm() {
  const config = {
    default_nologo: $("#cfg-nologo").checked,
    default_private: $("#cfg-private").checked,
  };
  addTextValue(config, "pollinations_api_key", $("#cfg-apikey").value.trim());
  addNumberValue(config, "image_cache_ttl", $("#cfg-ttl").value);
  addNumberValue(config, "image_cache_max_size", $("#cfg-maxsize").value);
  return config;
}

function addTextValue(target, key, value) {
  if (value) target[key] = value;
}

function addNumberValue(target, key, value) {
  const parsedValue = Number.parseInt(value, 10);
  if (!Number.isNaN(parsedValue)) target[key] = parsedValue;
}

async function loadModels() {
  try {
    renderModels((await api("/v1/models")).data);
  } catch (error) {
    toast(error.message || "加载模型失败", "error");
  }
}

function renderModels(models) {
  const tbody = $("#models-tbody");
  tbody.textContent = "";
  models.forEach((model, index) => {
    tbody.appendChild(createModelRow(model, index));
  });
}

function createModelRow(model, index) {
  const row = document.createElement("tr");
  row.appendChild(createCell(String(index + 1)));
  row.appendChild(createCell(model.id, "mono"));
  row.appendChild(createCell(model.owned_by));
  return row;
}

function createCell(text, className = "") {
  const cell = document.createElement("td");
  cell.textContent = text;
  if (className) cell.className = className;
  return cell;
}

async function loadTestModels() {
  const select = $("#test-model");
  if (select.options.length > 0) return;
  try {
    fillModelSelect((await api("/v1/models")).data);
  } catch (error) {
    toast(error.message || "加载模型失败", "error");
  }
}

function fillModelSelect(models) {
  const select = $("#test-model");
  models.forEach(model => {
    const option = document.createElement("option");
    option.value = model.id;
    option.textContent = model.id;
    select.appendChild(option);
  });
}

function getSelectedSize() {
  const active = $(".size-presets .chip.active");
  return active ? active.dataset.size : DEFAULT_IMAGE_SIZE;
}

async function generateImage() {
  const prompt = $("#test-prompt").value.trim();
  if (!prompt) {
    toast("请输入 Prompt", "error");
    return;
  }
  await runImageGeneration(prompt);
}

async function runImageGeneration(prompt) {
  const button = $("#test-btn");
  setButtonBusy(button, "生成中...");
  $("#test-result").classList.add("hidden");
  try {
    renderImageResult(await api("/v1/images/generations", buildImageRequest(prompt)));
    toast("图片生成成功");
  } catch (error) {
    toast(error.message || "图片生成失败", "error");
  } finally {
    resetButton(button, "生成图片");
  }
}

function buildImageRequest(prompt) {
  return {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify({
      model: $("#test-model").value,
      prompt,
      size: getSelectedSize(),
    }),
  };
}

function renderImageResult(data) {
  if (!data.data || data.data.length === 0) return;
  $("#test-img").src = data.data[0].url;
  $("#test-result").classList.remove("hidden");
}

function setButtonBusy(button, text) {
  button.disabled = true;
  button.textContent = text;
}

function resetButton(button, text) {
  button.disabled = false;
  button.textContent = text;
}

async function logout() {
  try {
    await api("/admin/logout", {method: "POST"});
  } finally {
    redirectToLogin();
  }
}
