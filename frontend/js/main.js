// Ngôn ngữ nằm trong dữ liệu: collection `languages`, đọc qua API /api/languages.
// Thêm ngôn ngữ mới chỉ cần thêm một bản ghi, không phải sửa file này.
const DEFAULT_LANG = 'vi';
const DEFAULT_GEOFENCE_RADIUS = 15; // mét, khớp PRD (mặc định 15 m, cho phép 10–25 m)
let currentLang = DEFAULT_LANG;
let languagesData = []; // [{ code, native_name, flag, html_lang, ui: {...} }]
let poisData = [];
let activePoiId = null;
let previousTab = 'map';

// Ghi nhớ POI riêng của từng trình phát
let mapAudioPoiId = null;
let detailAudioPoiId = null;

// Ngăn nội dung thuyết minh cũ ghi đè nội dung ngôn ngữ mới
let detailLanguageRequestId = 0;

// Quản lý trạng thái định vị và phân loại phiên
let initialLocationMode = null; // 'real' hoặc 'simulated'
let gpsMode = null;              // 'real' hoặc 'simulated'
let realGpsWatchId = null;
let lastRealPosition = null;

const DEFAULT_POI_CODE = "P00";
let autoPlayedPois = new Set(); // Bộ nhớ lưu các POI đã tự động phát trong phiên

// Cấu hình kiểm tra GPS và Geofence
const LOCATION_CONFIG = {
  maxGpsAccuracyMeters: 30,       // Sai số tối đa chấp nhận để kích hoạt Geofence POI (30m)
  siteRadiusMeters: 220,          // Coi là "trong khuôn viên" khi cách điểm tham quan gần nhất không quá 220m
  nearSiteMeters: 300             // Chỉ cho bật chế độ GPS thật khi cách điểm tham quan gần nhất không quá 300m
};

let VAN_MIEU_CENTER = [21.03020, 105.83540]; // Tâm địa lý toàn khu (Nhà bia / Giếng Thiên Quang)
const MAP_DEFAULT_ZOOM = 18;

let leafletMap = null;
let poiMarkers = {};
let userGpsMarker = null;
let geofenceLayer = null;
let mapNotices = {};

function getPoiTranslation(poi) {
  return (poi && poi.translations && poi.translations[currentLang]) || null;
}


function getPoiLocalizedName(poi) {
  if (!poi) return "";

  const translations = poi.translations || {};

  return (
    (translations[currentLang] && translations[currentLang].name) ||
    (translations.en && translations.en.name) ||
    poi.name ||
    ""
  );
}

function getPoiLocalizedDescription(poi) {
  if (!poi) return "";

  const translations = poi.translations || {};

  return (
    (translations[currentLang] && translations[currentLang].description) ||
    (translations.en && translations.en.description) ||
    poi.description ||
    ""
  );
}


function updateAudioTitles() {
  const mapPoi = poisData.find(
    poi => poi.poi_code === mapAudioPoiId
  );

  const detailPoi = poisData.find(
    poi => poi.poi_code === detailAudioPoiId
  );

  const mapTitle = document.getElementById("currentAudioTitle");
  const detailTitle = document.getElementById("detailAudioTitle");

  if (mapTitle) {
    mapTitle.textContent = mapPoi
      ? `${mapPoi.poi_code} - ${getPoiLocalizedName(mapPoi)}`
      : "--";
  }

  if (detailTitle) {
    detailTitle.textContent = detailPoi
      ? `${detailPoi.poi_code} - ${getPoiLocalizedName(detailPoi)}`
      : "--";
  }
}

// ---------- Ngôn ngữ & chuỗi giao diện (lấy từ dữ liệu) ----------

function getCurrentLanguage() {
  return languagesData.find((l) => l.code === currentLang) || null;
}

function getDisplayRadius() {
  // Bán kính hiển thị lấy theo dữ liệu điểm (giá trị phổ biến nhất), không viết cứng.
  const counts = {};
  poisData.forEach((p) => {
    const r = Number(p.geofence_radius);
    if (Number.isFinite(r) && r > 0) counts[r] = (counts[r] || 0) + 1;
  });
  const best = Object.entries(counts).sort((a, b) => b[1] - a[1])[0];
  return best ? Number(best[0]) : DEFAULT_GEOFENCE_RADIUS;
}


// Ngôn ngữ dự phòng cho giao diện
const UI_FALLBACK_LANG = "en";

function uiText(lang, key) {
  const value = lang && lang.ui ? lang.ui[key] : undefined;

  return value !== undefined && String(value).trim() !== ""
    ? value
    : undefined;
}

function t(key, fallback, extra = {}) {
  // Ưu tiên ngôn ngữ đang chọn
  let raw = uiText(getCurrentLanguage(), key);

  // Nếu thiếu thì lấy tiếng Anh
  if (raw === undefined) {
    const englishLang = languagesData.find(
      (lang) => lang.code === UI_FALLBACK_LANG
    );

    raw = uiText(englishLang, key);
  }

  // Nếu tiếng Anh cũng thiếu thì dùng fallback có sẵn
  const template = raw !== undefined ? raw : fallback;

  if (template === undefined) return undefined;

  const vars = {
    radius: getDisplayRadius(),
    count: poisData.length,
    ...extra
  };

  return String(template).replace(
    /\{(\w+)\}/g,
    (m, name) => (name in vars ? vars[name] : m)
  );
}


function htmlLangOf(code) {
  const lang = languagesData.find((l) => l.code === code);
  return (lang && lang.html_lang) || code;
}

function detectInitialLanguage() {
  const codes = languagesData.map((l) => l.code);
  const prefs = (navigator.languages && navigator.languages.length)
    ? navigator.languages
    : [navigator.language || DEFAULT_LANG];
  for (const pref of prefs) {
    const norm = String(pref).toLowerCase();
    const hit = codes.find((c) => norm === c.toLowerCase() || norm.startsWith(c.toLowerCase() + '-'));
    if (hit) return hit;
  }
  return codes.includes(DEFAULT_LANG) ? DEFAULT_LANG : codes[0];
}

function renderLanguageSelector() {
  const selector = document.getElementById("langSelect");
  if (!selector) return;
  selector.innerHTML = "";
  languagesData.forEach((lang) => {
    const option = document.createElement("option");
    option.value = lang.code;
    option.textContent = `${lang.flag || ""} ${lang.native_name || lang.name || lang.code}`.trim();
    selector.appendChild(option);
  });
  selector.value = currentLang;
}

async function loadLanguages() {
  try {
    const res = await fetch("/api/languages");
    if (res.ok) {
      const json = await res.json();
      const list = Array.isArray(json) ? json : (json && Array.isArray(json.data) ? json.data : []);
      if (list.length) languagesData = list;
    }
  } catch (err) {
    console.warn("Không tải được danh sách ngôn ngữ:", err);
  }

  if (!languagesData.length) {
    // Dự phòng khi API lỗi: chỉ tiếng Việt, chữ giao diện lấy từ index.html.
    languagesData = [{ code: DEFAULT_LANG, name: "Vietnamese", native_name: "Tiếng Việt", flag: "🇻🇳", html_lang: "vi", ui: {} }];
  }

  currentLang = detectInitialLanguage();
  renderLanguageSelector();
  document.documentElement.lang = htmlLangOf(currentLang);
}

// ---------- Thông tin thuyết minh/audio theo ngôn ngữ (cache) ----------

const narrationCache = {};
const detailNotices = {};

async function fetchNarrationInfo(poi, lang = currentLang) {
  if (!poi) return null;
  const key = `${poi.poi_code}|${lang}`;
  if (key in narrationCache) return narrationCache[key];
  try {
    const res = await fetch(`/api/narrations/${encodeURIComponent(poi.poi_code)}?lang=${encodeURIComponent(lang)}`);
    if (res.ok) {
      narrationCache[key] = await res.json();
    } else if (res.status === 404) {
      narrationCache[key] = { content: null, content_available: false, audio_url: null, audio_available: false };
    } else {
      return null; // lỗi máy chủ: chưa biết, không cache
    }
  } catch (err) {
    return null;
  }
  return narrationCache[key];
}

function prefetchNarrations() {
  poisData.forEach((poi) => fetchNarrationInfo(poi));
}

function isAudioAvailable(info) {
  return info ? info.audio_available !== false : true; // chưa biết thì cứ thử phát
}

function renderDetailNotices() {
  const el = document.getElementById("detailNotice");
  if (!el) return;
  const messages = Object.values(detailNotices);
  el.textContent = messages.join(" ");
  el.classList.toggle("hidden", messages.length === 0);
}

function setDetailNotice(key, message) {
  if (message) detailNotices[key] = message;
  else delete detailNotices[key];
  renderDetailNotices();
}

// Nạp audio cho một trình phát. Thiếu audio: báo rõ, khóa nút phát, không phát nhầm ngôn ngữ khác.
async function setPlayerSource(player, poi) {
  if (!player || !poi) return false;
  const lang = currentLang;
  const info = await fetchNarrationInfo(poi, lang);
  if (lang !== currentLang) return false; // người dùng đã đổi ngôn ngữ trong lúc chờ

  const ok = isAudioAvailable(info);
  const message = ok ? null : t("notice.audioMissing", "Chưa có audio cho ngôn ngữ này.");

  if (player.id === "audioPlayer") {
    setMapNotice("audio", message);
  } else {
    setDetailNotice("audio", message);
    const btn = document.getElementById("btnPlayDetail");
    if (btn) {
      btn.disabled = !ok;
      btn.classList.toggle("opacity-50", !ok);
      btn.classList.toggle("cursor-not-allowed", !ok);
    }
  }

  player.style.opacity = ok ? "" : "0.4";
  player.style.pointerEvents = ok ? "" : "none";

  if (!ok) {
    player.pause();
    player.removeAttribute("src");
    player.load();
    return false;
  }

  const url = getAudioUrl(poi);
  const desired = new URL(url, window.location.href).href;
  if ((player.currentSrc || player.src) !== desired) {
    player.src = url;
    player.load();
  }
  return true;
}

// Hiện nội dung thuyết minh; thiếu bản dịch thì hiện thông báo, không lấy ngôn ngữ khác.
function applyNarrationContent(poi, info, descriptionEl) {
  if (!descriptionEl) return;
  if (info && info.content_available && info.content) {
    descriptionEl.textContent = info.content;
    setDetailNotice("content", null);
  } else if (info) {
    descriptionEl.textContent = getPoiLocalizedDescription(poi);
    setDetailNotice("content", t("notice.contentMissing", "Nội dung thuyết minh bằng ngôn ngữ này đang được cập nhật."));
  }
}

// Mã khách gắn với MÃ VÉ: một vé là một khách, dù quét lại bao nhiêu lần hay mở trên
// bao nhiêu điện thoại (lượt ghé mỗi điểm vì vậy cũng chỉ tính 1 lần cho mỗi vé).
// Không có vé (Xem thử ứng dụng) thì mỗi điện thoại là một khách (lưu trong localStorage).
function getOrCreateSessionId() {
  const ticket = (new URLSearchParams(window.location.search).get("ticket") || "").trim().toUpperCase();
  if (/^VM-(STD|PRI)-[A-Z0-9]+$/.test(ticket) && sessionStorage.getItem("vm_ticket_demo") !== "true") {
    return "ve_" + ticket;
  }
  const key = "vm_session_demo";
  let sId = null;
  try { sId = localStorage.getItem(key); } catch (e) { /* trình duyệt chặn bộ nhớ */ }
  if (!sId) sId = sessionStorage.getItem("vm_session_id");
  if (!sId) {
    sId = "sess_" + Date.now() + "_" + Math.random().toString(36).substring(2, 9);
  }
  try { localStorage.setItem(key, sId); } catch (e) { /* bỏ qua */ }
  sessionStorage.setItem("vm_session_id", sId);
  return sId;
}

async function recordAccessClassification(accessType, isVerified) {
  if (sessionStorage.getItem("vm_access_recorded")) {
    return;
  }

  sessionStorage.setItem("vm_access_recorded", accessType);
  const payload = {
    session_id: getOrCreateSessionId(),
    initial_mode: initialLocationMode,
    access_type: accessType,
    is_real_visit: isVerified,
    timestamp: new Date().toISOString()
  };

  try {
    await fetch("/api/stats/visit", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
  } catch (err) {
    console.warn("Lỗi gửi thống kê visit:", err);
  }
}

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, (ch) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
  }[ch]));
}

function setGpsStatus(message) {
  const el = document.getElementById("gpsStatusText");
  if (el) el.textContent = message;
}

function setMapNotice(key, message) {
  if (message) mapNotices[key] = message;
  else delete mapNotices[key];

  const el = document.getElementById("mapNotice");
  if (!el) return;
  const messages = Object.values(mapNotices);
  el.innerHTML = messages.map((m) => `<div>${escapeHtml(m)}</div>`).join("");
  el.classList.toggle("hidden", messages.length === 0);
}

function applyTranslations() {
  document.querySelectorAll("[data-i18n]").forEach((el) => {
    const translatedText = t(el.dataset.i18n);
    if (translatedText !== undefined && el.children.length === 0) {
      el.textContent = translatedText;
    }
  });

  document.querySelectorAll("[data-i18n-placeholder]").forEach((el) => {
    const v = t(el.dataset.i18nPlaceholder);
    if (v !== undefined) el.placeholder = v;
  });

  document.querySelectorAll("[data-i18n-title]").forEach((el) => {
    const v = t(el.dataset.i18nTitle);
    if (v !== undefined) el.title = v;
  });

  document.querySelectorAll("[data-i18n-aria-label]").forEach((el) => {
    const v = t(el.dataset.i18nAriaLabel);
    if (v !== undefined) el.setAttribute("aria-label", v);
  });
}

function normalizePoi(raw) {
  const poi = { ...raw };
  const lat = Number(raw.latitude ?? raw.lat);
  const lng = Number(raw.longitude ?? raw.lng);

  if (Number.isFinite(lat) && Number.isFinite(lng) && lat >= -90 && lat <= 90 && lng >= -180 && lng <= 180) {
    poi.lat = lat;
    poi.lng = lng;
  } else {
    delete poi.lat;
    delete poi.lng;
  }
  return poi;
}

async function fetchPoisAndNarrations() {
  let list = null;
  let reason = "";

  try {
    const res = await fetch("/api/pois").catch(() => null);
    if (!res) {
      reason = "không kết nối được tới /api/pois";
    } else if (!res.ok) {
      reason = `/api/pois trả về HTTP ${res.status}`;
    } else {
      const json = await res.json();
      const data = Array.isArray(json) ? json : (json && Array.isArray(json.data) ? json.data : null);
      if (!data) reason = "định dạng phản hồi không hợp lệ";
      else if (data.length === 0) reason = "danh sách rỗng";
      else list = data;
    }
  } catch (err) {
    reason = `lỗi (${err.message})`;
  }

  if (list) {
    poisData = list.map(normalizePoi);
    setMapNotice("poi", null);
  } else {
    console.warn("Dùng danh sách dự phòng do:", reason);
    poisData = getFallbackPois().map(normalizePoi);
    setMapNotice("poi", t("notice.fallbackData", "Chưa tải được dữ liệu mới nhất, đang hiển thị danh sách lưu sẵn.", { reason }));
  }

  applyTranslations(); // cập nhật chữ có biến {radius}/{count} theo dữ liệu điểm
  renderPoiList();
  renderMapMarkers();
  centerMapOnGate();
  prefetchNarrations();
}

function switchTab(tab) {
  previousTab = tab;
  const tabMap = document.getElementById('tabMap');
  const tabList = document.getElementById('tabList');
  const btnMap = document.getElementById('btnTabMap');
  const btnList = document.getElementById('btnTabList');

  if (tab === 'map') {
    tabMap.classList.remove('hidden');
    if (leafletMap) setTimeout(() => leafletMap.invalidateSize(), 50);
    tabList.classList.add('hidden');
    btnMap.className = "flex flex-col items-center text-sky-600 transition cursor-pointer";
    btnList.className = "flex flex-col items-center text-slate-400 hover:text-slate-600 transition cursor-pointer";
  } else {
    tabMap.classList.add('hidden');
    tabList.classList.remove('hidden');
    btnList.className = "flex flex-col items-center text-sky-600 transition cursor-pointer";
    btnMap.className = "flex flex-col items-center text-slate-400 hover:text-slate-600 transition cursor-pointer";
  }
}

async function changeLanguage(lang) {
  if (!languagesData.some((l) => l.code === lang)) return;

  // Nếu ngôn ngữ không thay đổi thì không tải lại âm thanh.
  if (lang === currentLang) return;

  const mapPlayer = document.getElementById("audioPlayer");
  const detailPlayer = document.getElementById("audioPlayerDetail");

  // Ghi nhận trình phát nào đang phát trước khi đổi ngôn ngữ.
  const mapWasPlaying = Boolean(
    mapPlayer && !mapPlayer.paused && !mapPlayer.ended
  );

  const detailWasPlaying = Boolean(
    detailPlayer && !detailPlayer.paused && !detailPlayer.ended
  );

  const resumeMap = false;
  const resumeDetail = false;

  // Cập nhật ngôn ngữ hiện tại.
  currentLang = lang;
  document.documentElement.lang = htmlLangOf(lang);

  const selector = document.getElementById("langSelect");
  if (selector) selector.value = lang;

  setMapNotice("audio", null);
  setDetailNotice("audio", null);
  setDetailNotice("content", null);
  applyTranslations();
  renderPoiList();
  renderMapMarkers();
  updateAudioTitles();
  prefetchNarrations();

  // Tải lại âm thanh của từng trình phát theo POI riêng.
  function reloadPlayerLanguage(player, poiCode, shouldResume) {
    if (!player || !poiCode) return;

    const poi = poisData.find(
      item => item.poi_code === poiCode
    );

    if (!poi) return;

    // Dừng file cũ trước khi tải file mới.
    player.pause();
    player.currentTime = 0;
    

    // Chỉ phát lại khi trình phát đó đang phát trước khi đổi ngôn ngữ.
    if (shouldResume) {
      player.addEventListener(
        "loadedmetadata",
        function onNewAudioLoaded() {
          player.currentTime = 0;

          player.play().catch(error => {
            console.warn(
              "Trình duyệt không cho phép tự phát âm thanh mới:",
              error
            );
          });
        },
        { once: true }
      );
    }
    setPlayerSource(player, poi);
  }

  // Cập nhật thanh nghe trên bản đồ.
  reloadPlayerLanguage(
    mapPlayer,
    mapAudioPoiId,
    resumeMap
  );

  const mapTitle = document.getElementById("currentAudioTitle");
  const mapPoi = poisData.find(
    item => item.poi_code === mapAudioPoiId
  );

  if (mapTitle && mapPoi) {
    mapTitle.textContent =
      `${mapPoi.poi_code} - ${getPoiLocalizedName(mapPoi)}`;
  }

  // Cập nhật thanh nghe trong trang chi tiết.
  reloadPlayerLanguage(
    detailPlayer,
    detailAudioPoiId,
    resumeDetail
  );

  const detailTitle = document.getElementById("detailAudioTitle");
  const detailPoi = poisData.find(
    item => item.poi_code === detailAudioPoiId
  );

  if (detailTitle && detailPoi) {
    detailTitle.textContent =
      `${detailPoi.poi_code} - ${getPoiLocalizedName(detailPoi)}`;
  }

  // Nếu trang chi tiết đang mở, tải lại nội dung thuyết minh.
  const detailView = document.getElementById("detailView");
  const isDetailOpen =
    detailView && !detailView.classList.contains("hidden");

  if (isDetailOpen && detailPoi) {
    const requestId = ++detailLanguageRequestId;
    const poiCode = detailPoi.poi_code;
    const requestedLang = lang;

    const localizedName = getPoiLocalizedName(detailPoi);
    const header = document.getElementById("detailHeaderTitle");
    const name = document.getElementById("detailName");
    const description = document.getElementById("detailDescription");

    if (header) header.textContent = localizedName;
    if (name) name.textContent = localizedName;
    if (description) description.textContent = getPoiLocalizedDescription(detailPoi);

    const info = await fetchNarrationInfo(detailPoi, requestedLang);

    // Không dùng kết quả của yêu cầu cũ.
    if (
      requestId !== detailLanguageRequestId ||
      requestedLang !== currentLang ||
      poiCode !== detailAudioPoiId
    ) {
      return;
    }

    applyNarrationContent(detailPoi, info, description);
  }
}

function renderPoiList() {
  const container = document.getElementById('poiListContainer');
  if (!container) return;
  container.innerHTML = '';

  poisData.forEach(poi => {
    const card = document.createElement('div');
    card.className = "bg-white border border-slate-200 rounded-2xl p-4 shadow-sm flex items-center justify-between hover:border-sky-300 transition";
    card.innerHTML = `
      <div class="flex items-center space-x-3">
        <div class="w-12 h-12 rounded-xl bg-sky-50 text-sky-600 font-bold flex items-center justify-center text-sm border border-sky-100">
          ${escapeHtml(poi.poi_code)}
        </div>
        <div>
          <h4 class="font-bold text-sm text-slate-900">${escapeHtml(getPoiLocalizedName(poi))}</h4>
          <p class="text-xs text-slate-500 line-clamp-1 mt-0.5">${escapeHtml(getPoiLocalizedDescription(poi))}</p>
        </div>
      </div>
      <button onclick="openDetailView('${escapeHtml(poi.poi_code)}')" class="bg-sky-50 hover:bg-sky-100 text-sky-700 text-xs font-semibold px-3 py-2 rounded-xl transition flex items-center space-x-1 shrink-0 cursor-pointer">
        <span>${escapeHtml(t("detail.view", "Xem chi tiết"))}</span>
        <i class="fa-solid fa-chevron-right text-[10px]"></i>
      </button>
    `;
    container.appendChild(card);
  });
}

function centerMapOnGate() {
  if (!leafletMap) return;
  const gate = poisData.find((p) => p.poi_code === DEFAULT_POI_CODE && typeof p.lat === "number");
  if (!gate) return;
  leafletMap.setView([gate.lat, gate.lng], MAP_DEFAULT_ZOOM);
}

function initLeafletMap() {
  const el = document.getElementById("leafletMap");
  if (!el || leafletMap || !window.L) return;

  leafletMap = L.map(el, { 
    zoomControl: false,
    maxZoom: 22 
  }).setView(VAN_MIEU_CENTER, MAP_DEFAULT_ZOOM);

  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxNativeZoom: 19,
    maxZoom: 22,
    attribution: '&copy; OpenStreetMap contributors'
  }).addTo(leafletMap);

  geofenceLayer = L.layerGroup().addTo(leafletMap);
  renderMapMarkers();
}

function renderMapMarkers() {
  if (!leafletMap || !Array.isArray(poisData)) return;

  Object.values(poiMarkers).forEach((marker) => marker.remove());
  poiMarkers = {};
  if (geofenceLayer) geofenceLayer.clearLayers();

  poisData.forEach((poi) => {
    if (typeof poi.lat !== "number" || typeof poi.lng !== "number") return;

    const imgUrl = poi.image_url || `/images/poi_${poi.poi_code}.jpg`;
    const localizedName = getPoiLocalizedName(poi);

    const icon = L.divIcon({
      className: "poi-custom-marker",
      html: `
        <div class="poi-marker-container">
          <div class="poi-marker__frame">
            <img src="${imgUrl}" alt="${escapeHtml(localizedName)}" class="poi-marker__img" onerror="this.src='/images/poi_P00_cong_van_mieu.jpg'" />
          </div>
          <span class="poi-marker__tip"></span>
          <div class="poi-marker__title">${escapeHtml(localizedName)}</div>
        </div>
      `,
      iconSize: [80, 75],
      iconAnchor: [40, 48],
      popupAnchor: [0, -48]
    });

    const marker = L.marker([poi.lat, poi.lng], { icon, title: `${poi.poi_code} - ${localizedName}` })
      .addTo(leafletMap)
      .bindPopup(`<b>${escapeHtml(poi.poi_code)}</b><br>${escapeHtml(localizedName)}`);

    marker.on("click", () => openDetailView(poi.poi_code));
    poiMarkers[poi.poi_code] = marker;

    const radius = Number(poi.geofence_radius) || DEFAULT_GEOFENCE_RADIUS;
    L.circle([poi.lat, poi.lng], {
      radius,
      color: "#0284c7",
      weight: 1.5,
      fillColor: "#38bdf8",
      fillOpacity: 0.15,
      interactive: false
    }).addTo(geofenceLayer);
  });
}

function updatePersonMarker(lat, lng, popupText = t("marker.you", "Vị trí của bạn")) {
  if (!leafletMap) return;
  const pos = [lat, lng];
  if (userGpsMarker) {
    userGpsMarker.setLatLng(pos);
  } else {
    userGpsMarker = L.marker(pos, {
      icon: L.divIcon({
        className: "user-marker",
        html: '<span class="user-marker__dot"></span>',
        iconSize: [24, 24],
        iconAnchor: [12, 12]
      }),
      zIndexOffset: 1000
    }).addTo(leafletMap).bindPopup(popupText);
  }
}

function checkGeofenceTrigger(userLat, userLng, accuracy = 0) {
  if (gpsMode === "real" && accuracy > LOCATION_CONFIG.maxGpsAccuracyMeters) {
    setGpsStatus(t("status.weakAccuracy", "Tín hiệu định vị đang yếu (sai số khoảng {acc} m). Hãy tiến lại gần điểm tham quan để nghe.", { acc: Math.round(accuracy) }));
    return;
  }

  let insidePoi = null;
  let minDistance = Infinity;

  poisData.forEach((poi) => {
    if (typeof poi.lat === "number" && typeof poi.lng === "number") {
      const dist = getDistanceMeters(userLat, userLng, poi.lat, poi.lng);
      const radius = Number(poi.geofence_radius) || DEFAULT_GEOFENCE_RADIUS;

      if (dist <= radius && dist < minDistance) {
        minDistance = dist;
        insidePoi = poi;
      }
    }
  });

  const floatingAudio = document.getElementById("floatingAudioContainer");

  if (insidePoi) {
    setGpsStatus(t("status.insideGeofence", "Bạn đang ở {poi}", { code: insidePoi.poi_code, poi: getPoiLocalizedName(insidePoi), dist: Math.round(minDistance) }));
    if (floatingAudio) floatingAudio.classList.remove("hidden");

    // Khi chuyển sang POI mới, cập nhật ngay lập tức
    if (currentSimulatedPoiId !== insidePoi.poi_code) {
      // Rời POI cũ: đặt lại cờ để lần sau vào lại POI đó sẽ tự phát lại (PRD KL04)
      if (currentSimulatedPoiId) autoPlayedPois.delete(currentSimulatedPoiId);
      currentSimulatedPoiId = insidePoi.poi_code;
      activePoiId = insidePoi.poi_code;
      
      const currentMode = gpsMode === "real" ? "REAL_GPS" : "SIMULATED";
      guiCapNhatTrangThaiPhien(currentMode, insidePoi.poi_code, true, "ACTIVE");
    }

    if (!autoPlayedPois.has(insidePoi.poi_code)) {
      autoPlayedPois.add(insidePoi.poi_code);
      loadAndPlayAudio(insidePoi, true);
    }
  } else {
    // Ra ngoài vùng POI (về trạng thái không đứng ở điểm nào nhưng vẫn online)
    if (currentSimulatedPoiId !== null) {
      // Vừa rời điểm: tắt thuyết minh đang phát (chỉ làm một lần lúc rời, để khách
      // tự bấm nghe lại ở ngoài vùng thì GPS cập nhật sau đó không tắt ngang)
      dungThuyetMinhKhiRaNgoaiVung();
      autoPlayedPois.delete(currentSimulatedPoiId); // rời vùng: đặt lại cờ tự phát
      currentSimulatedPoiId = null;
      const currentMode = gpsMode === "real" ? "REAL_GPS" : "SIMULATED";
      guiCapNhatTrangThaiPhien(currentMode, null, false, "ACTIVE");
    }

    setGpsStatus(
      gpsMode === "simulated"
        ? t("status.simOutside", "Bạn chưa ở gần điểm tham quan nào", { dist: Math.round(minDistance) })
        : t("status.realInCampus", "Bạn đang ở trong khuôn viên Văn Miếu. Hãy đi tới các điểm tham quan để nghe thuyết minh.", { nearest: insidePoi ? getPoiLocalizedName(insidePoi) : Math.round(minDistance) + "m" })
    );
  }
}

function simulateGpsLocation(poi) {
  if (!poi) {
    console.error("Không tìm thấy POI để giả lập GPS.");
    return;
  }

  if (realGpsWatchId !== null) {
    navigator.geolocation.clearWatch(realGpsWatchId);
    realGpsWatchId = null;
  }

  gpsMode = "simulated";
  activePoiId = poi.poi_code;

  // Rời điểm cũ: đặt lại cờ tự phát để lần sau vào lại điểm đó sẽ phát lại (PRD KL04).
  // Phải làm TRƯỚC khi ghi đè currentSimulatedPoiId bên dưới.
  if (currentSimulatedPoiId && currentSimulatedPoiId !== poi.poi_code) {
    autoPlayedPois.delete(currentSimulatedPoiId);
  }

  const hasCoords = typeof poi.lat === "number" && typeof poi.lng === "number";
  if (!hasCoords) {
    setGpsStatus(t("status.noCoords", "Điểm {code} chưa có vị trí trên bản đồ", { code: poi.poi_code }));
    return;
  }

  if (leafletMap) {
    leafletMap.setView([poi.lat, poi.lng], 19);
    updatePersonMarker(poi.lat, poi.lng, t("marker.simulated", "Vị trí của bạn"));
  }

  const simPanel = document.getElementById("simulatorPanel");
  if (simPanel) simPanel.classList.add("hidden");

  // Cập nhật vị trí mô phỏng và gửi thẳng lên backend ngay lập tức
  currentSimulatedPoiId = poi.poi_code;
  guiCapNhatTrangThaiPhien("SIMULATED", poi.poi_code, true, "ACTIVE");

  checkGeofenceTrigger(poi.lat, poi.lng, 0);
}

function toggleSimulator() {
  const panel = document.getElementById('simulatorPanel');
  if (panel) panel.classList.toggle('hidden');
}

function renderSimulatorButtons() {
  const container = document.getElementById('simulatorButtons');
  if (!container) return;
  container.innerHTML = '';

  poisData.forEach(poi => {
    const btn = document.createElement('button');
    btn.onclick = () => simulateGpsLocation(poi);
    btn.className = "bg-slate-100 hover:bg-sky-600 hover:text-white text-slate-700 text-xs font-bold py-1.5 rounded-lg border border-slate-200 transition cursor-pointer";
    btn.innerText = poi.poi_code;
    container.appendChild(btn);
  });
// 2. Thêm 1 nút kiểm thử: Đứng giữa sân (Ngoài phạm vi Geofence của mọi POI)
  const outsideBtn = document.createElement('button');
  outsideBtn.className = "col-span-2 bg-amber-50 hover:bg-amber-500 hover:text-white text-amber-800 text-xs font-bold py-1.5 rounded-lg border border-amber-200 transition cursor-pointer";
  outsideBtn.innerHTML = '<i class="fa-solid fa-person-walking"></i> Sân trống (Ngoài vùng)';
  
  outsideBtn.onclick = () => {
    // Tọa độ khoảng sân giữa Nhà Bia và Khuê Văn Các (cách xa tâm các POI tầm 25m - 30m)
    const emptyYardCoords = {
      poi_code: "OUTSIDE",
      name: "Sân giữa vườn",
      lat: 21.029068, 
      lng: 105.835524
    };
    simulateGpsLocation(emptyYardCoords);
  };

  container.appendChild(outsideBtn);

}

// Biến lưu POI hiện tại của phiên mô phỏng để nhận biết khi chuyển điểm
let currentSimulatedPoiId = null;

async function guiCapNhatTrangThaiPhien(gpsModeType, poiId = null, insideGeofence = false, status = "ACTIVE") {
  const payload = {
    session_id: getOrCreateSessionId(),
    gps_mode: gpsModeType,
    poi_id: poiId,
    inside_geofence: insideGeofence,
    status: status,
    timestamp: new Date().toISOString()
  };

  try {
    await fetch("/api/stats/session-location", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
  } catch (err) {
    console.warn("Lỗi gửi trạng thái phiên:", err);
  }
}

// Heartbeat truy cập web độc lập với GPS/Geofence: online khi trang còn mở.
function guiHeartbeatTruyCap() {
  // Chỉ tính online sau khi người dùng nhấn Bắt đầu.
  if (sessionStorage.getItem("vm_experience_started") !== "1") return;
  const currentMode = gpsMode === "real" ? "REAL_GPS" : "SIMULATED";
  guiCapNhatTrangThaiPhien(currentMode, currentSimulatedPoiId || null, Boolean(currentSimulatedPoiId), "ACTIVE");
}
setInterval(guiHeartbeatTruyCap, 5000);
window.addEventListener("pageshow", guiHeartbeatTruyCap);
window.addEventListener("pagehide", () => {
  if (sessionStorage.getItem("vm_experience_started") !== "1") return;
  const payload = new Blob([JSON.stringify({
    session_id: getOrCreateSessionId(), gps_mode: gpsMode === "real" ? "REAL_GPS" : "SIMULATED",
    poi_id: null, inside_geofence: false, status: "OFFLINE", timestamp: new Date().toISOString()
  })], { type: "application/json" });
  navigator.sendBeacon("/api/stats/session-location", payload);
});

// Cập nhật hàm mở trang chi tiết để gán đúng audio riêng biệt cho detailPlayer
async function openDetailView(poiCode) {
  // Tăng mã yêu cầu để vô hiệu hóa những yêu cầu mở chi tiết trước đó.
  const requestId = ++detailLanguageRequestId;
  const requestLang = currentLang;

  // Tạm dừng trình phát trên bản đồ.
  const mapPlayer = document.getElementById("audioPlayer");
  if (mapPlayer) {
    mapPlayer.pause();
  }

  const poi = poisData.find(
    item => item.poi_code === poiCode
  );

  if (!poi) return;

  activePoiId = poiCode;
  detailAudioPoiId = poi.poi_code;

  // Cập nhật thông tin cơ bản của POI.
  const badge = document.getElementById("detailPoiCodeBadge");
  const header = document.getElementById("detailHeaderTitle");
  const name = document.getElementById("detailName");
  const description = document.getElementById("detailDescription");
  const imgEl = document.getElementById("detailImage");

  const localizedName = getPoiLocalizedName(poi);

  if (badge) badge.textContent = poi.poi_code;
  if (header) header.textContent = localizedName;
  if (name) name.textContent = localizedName;

  if (imgEl) {
    imgEl.className = "w-full h-full object-contain";
    imgEl.src =
      poi.image_url || "/images/poi_P00_cong_van_mieu.jpg";
  }

  // Hiển thị mô tả mặc định trong khi chờ API.
  if (description) {
    description.textContent = getPoiLocalizedDescription(poi);
  }

  // Xóa thông báo dự phòng của lần xem trước.
  setDetailNotice("audio", null);
  setDetailNotice("content", null);

  // Hiện trang chi tiết.
  document.getElementById("tabMap")?.classList.add("hidden");
  document.getElementById("tabList")?.classList.add("hidden");
  document.getElementById("bottomNav")?.classList.add("hidden");

  const detailView = document.getElementById("detailView");

  if (detailView) {
    detailView.classList.remove("hidden");
    detailView.classList.add("flex");
  }

  // Thiết lập trình phát âm thanh riêng cho trang chi tiết.
  const detailPlayer = document.getElementById("audioPlayerDetail");
  const titleEl = document.getElementById("detailAudioTitle");

  if (titleEl) {
    titleEl.textContent = `${poi.poi_code} - ${localizedName}`;
  }

  if (detailPlayer) {
    detailPlayer.pause();
    detailPlayer.currentTime = 0;
    setPlayerSource(detailPlayer, poi);
  }

  // Tải nội dung thuyết minh theo ngôn ngữ tại thời điểm gửi yêu cầu.
  const narrationData = await fetchNarrationInfo(poi, requestLang);

  // Chỉ cập nhật nếu đây vẫn là yêu cầu mới nhất,
  // ngôn ngữ chưa thay đổi và POI vẫn được chọn.
  if (
    requestId !== detailLanguageRequestId ||
    requestLang !== currentLang ||
    poiCode !== detailAudioPoiId
  ) {
    return;
  }

  applyNarrationContent(poi, narrationData, description);
}


function getAudioUrl(poi) {
  return `/audio/${currentLang}/${encodeURIComponent(poi.poi_code)}.mp3`;
}

function getVisibleAudioPlayer() {
  const detailView = document.getElementById("detailView");
  const isDetailOpen = detailView && !detailView.classList.contains("hidden");

  return document.getElementById(
    isDetailOpen ? "audioPlayerDetail" : "audioPlayer"
  );
}

function pauseOtherAudioPlayers(activePlayer) {
  ["audioPlayer", "audioPlayerDetail"].forEach((id) => {
    const player = document.getElementById(id);
    if (player && player !== activePlayer) {
      player.pause();
    }
  });
}

function transferAudioState(fromPlayer, toPlayer) {
  if (!fromPlayer || !toPlayer || fromPlayer === toPlayer) return;

  const source = fromPlayer.currentSrc || fromPlayer.src;
  const time = Number.isFinite(fromPlayer.currentTime) ? fromPlayer.currentTime : 0;
  const wasPlaying = !fromPlayer.paused && !fromPlayer.ended;

  fromPlayer.pause();
  toPlayer.pause();

  if (!source) return;

  const currentSource = toPlayer.currentSrc || toPlayer.src;

  if (currentSource !== source) {
    toPlayer.src = source;
    toPlayer.load();
  }

  const restoreTimeAndPlayback = () => {
    toPlayer.currentTime = Math.min(
      time,
      Number.isFinite(toPlayer.duration) ? toPlayer.duration : time
    );

    if (wasPlaying) {
      toPlayer.play().catch((err) => {
        console.warn("Không thể tiếp tục phát âm thanh:", err);
      });
    }
  };

  if (toPlayer.readyState >= 1) {
    restoreTimeAndPlayback();
  } else {
    toPlayer.addEventListener("loadedmetadata", restoreTimeAndPlayback, { once: true });
  }
}

// Khách ra khỏi vùng của mọi điểm: dừng thuyết minh tự động trên thanh nghe bản đồ
// (tua về đầu, vẫn giữ bài để khách tự bấm nghe lại nếu muốn). Trang chi tiết chỉ bị
// dừng khi đang phát đúng điểm vừa rời; khách tự mở điểm khác để nghe thì không ảnh hưởng.
function dungThuyetMinhKhiRaNgoaiVung() {
  const mapPlayer = document.getElementById("audioPlayer");
  if (mapPlayer && !mapPlayer.paused) {
    mapPlayer.pause();
    try { mapPlayer.currentTime = 0; } catch (e) { /* chưa tải xong */ }
  }
  const detailPlayer = document.getElementById("audioPlayerDetail");
  if (detailPlayer && !detailPlayer.paused && mapAudioPoiId && detailAudioPoiId === mapAudioPoiId) {
    detailPlayer.pause();
  }
}

// Thuyết minh tự động chỉ được phát khi khách vẫn đang ở trong vùng của điểm đó
function vanOTrongVung(poi) {
  return Boolean(poi) && currentSimulatedPoiId === poi.poi_code;
}

async function loadAndPlayAudio(poi, autoPlay = false) {
  if (!poi) return;

  const titleText = `${poi.poi_code} - ${getPoiLocalizedName(poi)}`;
  const title1 = document.getElementById("currentAudioTitle");

  if (title1) {
    title1.innerText = titleText;
  }
  // Âm thanh tự động theo Geofence luôn thuộc trình phát bản đồ.
  const activePlayer = document.getElementById("audioPlayer");
  if (!activePlayer) return;

  mapAudioPoiId = poi.poi_code;

  pauseOtherAudioPlayers(activePlayer);

  const audioSrc = getAudioUrl(poi);
  const available = await setPlayerSource(activePlayer, poi);
  if (!available) return; // thiếu audio: đã báo và khóa trình phát
  if (mapAudioPoiId !== poi.poi_code) return; // đã chuyển sang điểm khác trong lúc chờ
  if (autoPlay && !vanOTrongVung(poi)) return; // đã ra ngoài vùng trong lúc chờ tải

  activePlayer.onerror = () => {
    console.error(`[Audio] Không tải được: ${audioSrc}`);
    setGpsStatus(t("status.audioLoadFailed", "Không tải được âm thanh cho điểm {code}.", { code: poi.poi_code }));
  };

  if (autoPlay) {
    activePlayer.play().catch((err) => {
      console.warn("Trình duyệt tạm chặn autoplay:", err);
      setGpsStatus(t("status.arrivedTapToPlay", "Đã tới {poi}. Chạm vào màn hình để nghe thuyết minh.", { poi: getPoiLocalizedName(poi) }));
      
      const unlockAudio = () => {
        // Chạm màn hình sau khi đã rời điểm (vd. bấm "Sân trống") thì không phát nữa
        if (!vanOTrongVung(poi) || mapAudioPoiId !== poi.poi_code) return;
        activePlayer.play();
        document.removeEventListener("click", unlockAudio);
      };
      document.addEventListener("click", unlockAudio, { once: true });
    });
  }
}

function expandToDetail() {
  if (activePoiId) openDetailView(activePoiId);
}

function closeDetailView() {
  // Dừng hẳn audio chi tiết khi bấm nút đóng (X)
  const detailPlayer = document.getElementById("audioPlayerDetail");
  if (detailPlayer) {
    detailPlayer.pause();
    detailPlayer.currentTime = 0;
  }

  const detailView = document.getElementById("detailView");
  detailView.classList.remove("flex");
  detailView.classList.add("hidden");

  document.getElementById("bottomNav")?.classList.remove("hidden");

  // Trở về tab trước đó (Bản đồ hoặc Danh sách) mà thanh nghe bản đồ vẫn giữ nguyên điểm cũ
  switchTab(previousTab);
}

// Bắt đầu trải nghiệm mặc định ở chế độ mô phỏng tại cổng P00
// Bắt đầu trải nghiệm mặc định tại cổng P00 và tự động phát thuyết minh
function batDauTraiNghiemP00() {
  // Phiên online chỉ bắt đầu khi khách nhấn nút Bắt đầu.
  sessionStorage.setItem("vm_experience_started", "1");

  // 1. Ẩn modal chào mừng
  document.getElementById("welcomeModal")?.classList.add("hidden");

  // 2. Thiết lập chế độ mặc định tham quan
  initialLocationMode = "simulated";
  gpsMode = "simulated";

  // 3. Ghi nhận phân loại thống kê lượt truy cập
  recordAccessClassification("demo_simulation", false);
  setGpsStatus(t("status.visiting", "Bạn đang ở {poi}", { poi: getPoiLocalizedName(poisData.find((p) => p.poi_code === DEFAULT_POI_CODE)) || "Cổng Văn Miếu", code: DEFAULT_POI_CODE }));

  // 4. Lấy dữ liệu POI P00 từ danh sách đã tải
  const gate = poisData.find((p) => p.poi_code === DEFAULT_POI_CODE) || {
    poi_code: "P00",
    name: "Cổng Văn Miếu",
    lat: 21.02875,
    lng: 105.83615,
    geofence_radius: DEFAULT_GEOFENCE_RADIUS
  };

  activePoiId = gate.poi_code;
  mapAudioPoiId = gate.poi_code;
  currentSimulatedPoiId = gate.poi_code;
  guiHeartbeatTruyCap();

  // 5. Di chuyển góc nhìn bản đồ và đặt vị trí người dùng tại P00
  if (leafletMap && typeof gate.lat === "number" && typeof gate.lng === "number") {
    leafletMap.setView([gate.lat, gate.lng], 19);
    updatePersonMarker(gate.lat, gate.lng, t("marker.youAt", "Vị trí của bạn", { code: "P00" }));
  }

  // 6. Hiển thị thanh trình phát âm thanh nổi ở góc dưới
  const floatingAudio = document.getElementById("floatingAudioContainer");
  if (floatingAudio) {
    floatingAudio.classList.remove("hidden");
  }

  // 7. Báo cho Backend biết người dùng đang có mặt tại P00 (thời gian thực)
  guiCapNhatTrangThaiPhien("SIMULATED", gate.poi_code, true, "ACTIVE");

  // 8. Tải và PHÁT NGAY âm thanh thuyết minh của P00 (tận dụng tương tác click vừa xong)
  loadAndPlayAudio(gate, true);
}

// Cổng vé (ticket-gate.js, Người 2): chỉ cho vào khi có vé hợp lệ hoặc chế độ Demo.
// Nếu bị chặn, chờ khách nhập vé (trang tải lại) hoặc bấm "Vào chế độ Demo" rồi mới khởi tạo.
async function kiemTraCongVe() {
  if (!window.VMTicketGate) return true; // chưa nạp ticket-gate.js: không chặn
  const result = await window.VMTicketGate.verify();
  if (result && result.allowed) return true;
  await new Promise((resolve) => {
    const timer = setInterval(() => {
      if (sessionStorage.getItem("vm_ticket_demo") === "true") {
        clearInterval(timer);
        resolve();
      }
    }, 200);
  });
  return true;
}

document.addEventListener("DOMContentLoaded", async () => {
  await loadLanguages();
  applyTranslations();
  await kiemTraCongVe();
  initLeafletMap();
  await fetchPoisAndNarrations();
  renderSimulatorButtons();
});

// Phát âm thanh thủ công tại trang chi tiết (Không thay đổi vị trí bản đồ hay tính lượt tham quan tự động)
// Phát âm thanh thủ công tại trang chi tiết (Không thay đổi vị trí bản đồ hay tính lượt tham quan tự động)
function playDetailAudioManually() {
  const detailPlayer = document.getElementById("audioPlayerDetail");
  if (!detailPlayer) return;

  if (detailPlayer.paused) {
    detailPlayer.play().catch((err) => {
      console.warn("Không thể tự phát âm thanh chi tiết:", err);
      setGpsStatus(t("status.tapForAudio", "Chạm vào màn hình để cấp quyền phát âm thanh."));
    });
  } else {
    detailPlayer.pause();
  }
}

function zoomMap(delta) {
  if (!leafletMap) return;
  const currentZoom = leafletMap.getZoom();
  leafletMap.setZoom(Math.max(15, Math.min(22, currentZoom + (delta > 0 ? 1 : -1))));
}

function resetZoomMap() {
  if (leafletMap) leafletMap.setView(VAN_MIEU_CENTER, 18);
}

// Dữ liệu dự phòng khi API lỗi — đồng bộ với data/seed/pois.json
function getFallbackPois() {
  return [
    {"poi_code": "P00", "name": "Cổng Văn Miếu", "description": "Cổng chính dẫn vào khu Nội tự Văn Miếu - Quốc Tử Giám.", "latitude": 21.027526, "longitude": 105.835622, "geofence_radius": 15, "image_url": "/images/poi_P00_cong_van_mieu.jpg", "translations": {"vi": {"name": "Cổng Văn Miếu", "description": "Cổng chính dẫn vào khu Nội tự Văn Miếu - Quốc Tử Giám."}, "en": {"name": "Van Mieu Gate", "description": "Main gate leading into the inner precinct of the Temple of Literature – Imperial Academy."}, "zh": {"name": "文庙门", "description": "通往文庙—国子监内院的正门。"}}},
    {"poi_code": "P01", "name": "Cổng Đại Trung", "description": "Cổng thứ hai dẫn vào không gian Nhập Đạo.", "latitude": 21.028129, "longitude": 105.835891, "geofence_radius": 15, "image_url": "/images/poi_P01_cong_dai_trung.jpg", "translations": {"vi": {"name": "Cổng Đại Trung", "description": "Cổng thứ hai dẫn vào không gian Nhập Đạo."}, "en": {"name": "Dai Trung Gate", "description": "The second gate, leading into the Nhap Dao courtyard."}, "zh": {"name": "大中门", "description": "通往“入道”空间的第二道门。"}}},
    {"poi_code": "P02", "name": "Khuê Văn Các", "description": "Lầu gác gỗ biểu tượng văn hóa của Thủ đô Hà Nội.", "latitude": 21.028575, "longitude": 105.835838, "geofence_radius": 15, "image_url": "/images/poi_P02_khue_van_cac.jpg", "translations": {"vi": {"name": "Khuê Văn Các", "description": "Lầu gác gỗ biểu tượng văn hóa của Thủ đô Hà Nội."}, "en": {"name": "Khue Van Pavilion", "description": "A wooden pavilion, the cultural symbol of Hanoi."}, "zh": {"name": "奎文阁", "description": "木结构楼阁，河内的文化象征。"}}},
    {"poi_code": "P03", "name": "Nhà Bia Tiến Sĩ", "description": "Nơi lưu giữ 82 bia Tiến sĩ Di sản tư liệu thế giới.", "latitude": 21.028665, "longitude": 105.83615, "geofence_radius": 15, "image_url": "/images/poi_P03_nha_bia_tien_si.jpg", "translations": {"vi": {"name": "Nhà Bia Tiến Sĩ", "description": "Nơi lưu giữ 82 bia Tiến sĩ Di sản tư liệu thế giới."}, "en": {"name": "Doctoral Stelae Hall", "description": "Home of the 82 Doctoral Stelae, a UNESCO-recognised documentary heritage."}, "zh": {"name": "进士碑亭", "description": "保存着82块进士碑，是世界记忆遗产。"}}},
    {"poi_code": "P04", "name": "Giếng Thiên Quang", "description": "Hồ nước hình vuông soi bóng Khuê Văn Các.", "latitude": 21.028689, "longitude": 105.835903, "geofence_radius": 15, "image_url": "/images/poi_P04_gieng_thien_quang.jpg", "translations": {"vi": {"name": "Giếng Thiên Quang", "description": "Hồ nước hình vuông soi bóng Khuê Văn Các."}, "en": {"name": "Thien Quang Well", "description": "A square pond reflecting the Khue Van Pavilion."}, "zh": {"name": "天光井", "description": "映照奎文阁倒影的方形水池。"}}},
    {"poi_code": "P05", "name": "Cổng Đại Thành", "description": "Cổng lớn dẫn vào khu vực thờ tự trung tâm.", "latitude": 21.028975, "longitude": 105.836032, "geofence_radius": 15, "image_url": "/images/poi_P05_cong_dai_thanh.jpg", "translations": {"vi": {"name": "Cổng Đại Thành", "description": "Cổng lớn dẫn vào khu vực thờ tự trung tâm."}, "en": {"name": "Dai Thanh Gate", "description": "The grand gate leading to the central worship area."}, "zh": {"name": "大成门", "description": "通往中央祭祀区的大门。"}}},
    {"poi_code": "P06", "name": "Điện Đại Thành", "description": "Tòa điện thờ linh thiêng Khổng Tử và các bậc hiền triết.", "latitude": 21.029236, "longitude": 105.836131, "geofence_radius": 15, "image_url": "/images/poi_P06_dien_dai_thanh.jpg", "translations": {"vi": {"name": "Điện Đại Thành", "description": "Tòa điện thờ linh thiêng Khổng Tử và các bậc hiền triết."}, "en": {"name": "Dai Thanh Sanctuary", "description": "The sacred sanctuary honouring Confucius and the sages."}, "zh": {"name": "大成殿", "description": "供奉孔子与先贤的神圣大殿。"}}},
    {"poi_code": "P07", "name": "Nhà Thái Học", "description": "Tòa nhà tôn vinh truyền thống giáo dục và các vị danh nhân.", "latitude": 21.029783, "longitude": 105.836326, "geofence_radius": 15, "image_url": "/images/poi_P07_nha_thai_hoc.jpg", "translations": {"vi": {"name": "Nhà Thái Học", "description": "Tòa nhà tôn vinh truyền thống giáo dục và các vị danh nhân."}, "en": {"name": "Thai Hoc Hall", "description": "A hall honouring the tradition of learning and eminent scholars."}, "zh": {"name": "太学堂", "description": "颂扬教育传统与名士的殿堂。"}}},
    {"poi_code": "P08", "name": "Lầu Trống", "description": "Lầu gác lưu giữ chiếc trống sấm đại lễ.", "latitude": 21.029879, "longitude": 105.836656, "geofence_radius": 15, "image_url": "/images/poi_P08_lau_trong.jpg", "translations": {"vi": {"name": "Lầu Trống", "description": "Lầu gác lưu giữ chiếc trống sấm đại lễ."}, "en": {"name": "Drum Tower", "description": "A pavilion housing the ceremonial drum."}, "zh": {"name": "鼓楼", "description": "收藏大典鼓的楼阁。"}}},
    {"poi_code": "P09", "name": "Lầu Chuông", "description": "Lầu gác treo quả chuông đồng cổ kính.", "latitude": 21.030063, "longitude": 105.836138, "geofence_radius": 15, "image_url": "/images/poi_P09_lau_chuong.jpg", "translations": {"vi": {"name": "Lầu Chuông", "description": "Lầu gác treo quả chuông đồng cổ kính."}, "en": {"name": "Bell Tower", "description": "A pavilion housing the ancient bronze bell."}, "zh": {"name": "钟楼", "description": "悬挂古铜钟的楼阁。"}}},
    {"poi_code": "P10", "name": "Vườn Giám", "description": "Khu vườn thanh tịnh nằm phía Tây khu di tích Văn Miếu - Quốc Tử Giám, không gian xanh mát và lịch sử.", "latitude": 21.028297, "longitude": 105.835066, "geofence_radius": 15, "image_url": "/images/poi_P10_vuon_giam.jpg", "translations": {"vi": {"name": "Vườn Giám", "description": "Khu vườn thanh tịnh nằm phía Tây khu di tích Văn Miếu - Quốc Tử Giám, không gian xanh mát và lịch sử."}, "en": {"name": "Giam Garden", "description": "A tranquil garden on the west side of the site, green and steeped in history."}, "zh": {"name": "监园", "description": "遗址西侧的清幽花园，绿意盎然、饱含历史。"}}},
  ];
}