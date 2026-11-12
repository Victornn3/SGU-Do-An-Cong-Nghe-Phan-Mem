/*
 * Tab "Quản lý POI & Audio" trong admin.html (trước đây là trang riêng admin-content.html).
 * Admin chỉ nhập tiếng Việt; khi lưu, narration-service tự dịch sang các ngôn ngữ đang bật
 * và tạo MP3 cho mọi ngôn ngữ. Mọi biến nằm trong IIFE để không đụng biến của admin.html;
 * chỉ lộ ra window.PoiAdmin.
 */
(function () {
  const API = "/api";
  let languages = [];
  let pois = {};
  let editingCode = null; // null = đang thêm mới
  let originalVi = null; // tên/mô tả/thuyết minh tiếng Việt lúc mở form
  let originalDetail = {}; // {mã_ngôn_ngữ: {name, description, narration}} lúc mở khung "sửa chi tiết"
  let detailLoaded = false; // khung "sửa chi tiết" đã được mở và nạp dữ liệu chưa
  const FIELDS = ["name", "description", "narration"];

  const $ = (id) => document.getElementById(id);
  const esc = (s) =>
    String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const token = () => localStorage.getItem("admin_token");
  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

  function toast(text) {
    if (typeof window.hienThBaoNhanh === "function") window.hienThBaoNhanh(text);
  }

  function showMsg(text, ok = true) {
    const el = $("poi-msg");
    el.textContent = text;
    el.className = "rounded-xl p-3 text-xs font-medium " +
      (ok ? "bg-emerald-50 text-emerald-800 border border-emerald-200" : "bg-red-50 text-red-700 border border-red-200");
  }

  function setFormStatus(kind, html) {
    const el = $("poi-form-status");
    const color = {
      info: "bg-slate-100 text-slate-700 border border-slate-200",
      ok: "bg-emerald-50 text-emerald-800 border border-emerald-200",
      warn: "bg-amber-50 text-amber-800 border border-amber-200",
      error: "bg-red-50 text-red-700 border border-red-200",
    }[kind];
    el.className = "rounded-xl p-3 text-xs font-medium " + color;
    el.innerHTML = html;
  }

  async function call(method, path, body) {
    const res = await fetch(API + path, {
      method,
      headers: { "Content-Type": "application/json", ...(token() ? { Authorization: "Bearer " + token() } : {}) },
      body: body ? JSON.stringify(body) : undefined,
    });
    const data = await res.json().catch(() => ({}));
    if (res.status === 401 || res.status === 403)
      throw new Error("Phiên đăng nhập hết hạn hoặc không đủ quyền. Hãy đăng xuất và đăng nhập lại.");
    if (!res.ok) {
      const d = data.detail;
      throw new Error(typeof d === "string" ? d : "Lỗi " + res.status);
    }
    return data;
  }

  // ---------- Hiển thị ----------
  function statusBadge(status) {
    const color = {
      PUBLISHED: "bg-emerald-100 text-emerald-700",
      DRAFT: "bg-amber-100 text-amber-700",
      HIDDEN: "bg-slate-200 text-slate-600",
    }[status] || "bg-slate-100 text-slate-600";
    return `<span class="px-2 py-0.5 rounded-full text-[10px] font-bold ${color}">${esc(status || "?")}</span>`;
  }

  async function fetchNarration(code, lang) {
    try {
      const res = await fetch(`${API}/narrations/${encodeURIComponent(code)}?lang=${encodeURIComponent(lang)}`);
      if (!res.ok) return null; // 404: chưa có thuyết minh
      return await res.json();
    } catch (e) {
      return null;
    }
  }

  function audioState(n) {
    if (!n || !n.content_available) return "empty";
    if (n.audio_available) return "completed";
    if (n.audio_status === "failed") return "failed";
    return n.audio_status === "processing" ? "processing" : "missing";
  }

  function audioBadge(lang, state) {
    const [color, text] = {
      completed: ["bg-emerald-100 text-emerald-700", "có"],
      processing: ["bg-amber-100 text-amber-700", "đang tạo"],
      failed: ["bg-red-100 text-red-700", "lỗi"],
      missing: ["bg-red-100 text-red-700", "thiếu"],
      empty: ["bg-slate-100 text-slate-400", "trống"],
    }[state] || ["bg-slate-100 text-slate-500", state];
    return `<span class="inline-block px-2 py-0.5 rounded-full text-[10px] font-semibold ${color}">${esc(lang)}: ${esc(text)}</span>`;
  }

  async function loadAudioCell(code) {
    const cell = document.getElementById("poi-audio-" + code);
    if (!cell) return;
    const states = await Promise.all(languages.map(async (l) => [l.code, audioState(await fetchNarration(code, l.code))]));
    cell.innerHTML = states.map(([c, st]) => audioBadge(c, st)).join(" ");
  }

  const BTN = "px-2.5 py-1 rounded-lg text-[11px] font-semibold transition cursor-pointer";

  async function load() {
    const tbody = $("poi-rows");
    if (!tbody) return;
    if (!token()) {
      tbody.innerHTML = `<tr><td colspan="7" class="py-6 text-center text-slate-400">Hãy đăng nhập để quản lý POI.</td></tr>`;
      return;
    }
    try {
      const [langRes, poiRes] = await Promise.all([call("GET", "/languages"), call("GET", "/pois/admin/all")]);
      languages = langRes.data || [];
      const list = poiRes.data || [];
      pois = Object.fromEntries(list.map((p) => [p.poi_code, p]));
      $("poi-count").textContent = `Tổng: ${list.length} POI`;

      if (!list.length) {
        tbody.innerHTML = `<tr><td colspan="7" class="py-6 text-center text-slate-400">Chưa có POI nào. Bấm "Thêm POI" để tạo.</td></tr>`;
        return;
      }
      tbody.innerHTML = list.map((p) => {
        const code = esc(p.poi_code);
        const have = languages.filter((l) => (p.translations?.[l.code]?.name || "").trim()).map((l) => l.code).join(", ") || "—";
        const toggle = p.status === "PUBLISHED"
          ? `<button data-act="HIDDEN" data-code="${code}" class="${BTN} bg-slate-200 hover:bg-slate-300 text-slate-700">Ẩn</button>`
          : `<button data-act="PUBLISHED" data-code="${code}" class="${BTN} bg-emerald-600 hover:bg-emerald-700 text-white">Xuất bản</button>`;
        return `<tr class="hover:bg-slate-50 transition">
          <td class="py-2.5 px-4 font-mono font-bold text-blue-700">${code}</td>
          <td class="py-2.5 px-4 font-semibold text-slate-800">${esc(p.translations?.vi?.name || p.name)}</td>
          <td class="py-2.5 px-4">${esc(p.geofence_radius)} m</td>
          <td class="py-2.5 px-4 text-slate-500">${esc(have)}</td>
          <td class="py-2.5 px-4 space-x-1 whitespace-nowrap" id="poi-audio-${code}"><span class="text-slate-400">...</span></td>
          <td class="py-2.5 px-4">${statusBadge(p.status)}</td>
          <td class="py-2.5 px-4 text-right whitespace-nowrap space-x-1">
            <button data-edit="${code}" class="${BTN} bg-amber-500 hover:bg-amber-600 text-white"><i class="fa-solid fa-pen-to-square mr-1"></i>Sửa</button>${toggle}<button data-delete="${code}" class="${BTN} bg-red-600 hover:bg-red-700 text-white"><i class="fa-solid fa-trash mr-1"></i>Xóa</button>
          </td>
        </tr>`;
      }).join("");
      list.forEach((p) => loadAudioCell(p.poi_code));
    } catch (e) {
      tbody.innerHTML = `<tr><td colspan="7" class="py-6 text-center text-red-500">${esc(e.message)}</td></tr>`;
    }
  }

  // ---------- Form thêm / sửa ----------
  function renderPreview(translations) {
    const others = languages.filter((l) => l.code !== "vi");
    const rows = others.map((l) => {
      const t = translations[l.code];
      return `<div><b>${esc(l.native_name || l.name || l.code)}:</b> ${t?.name ? esc(t.name) : '<span class="text-slate-400">chưa có, sẽ tự dịch khi Lưu</span>'}</div>`;
    });
    $("poi-preview").innerHTML = '<div class="font-semibold text-slate-600 mb-1">Bản dịch tự động</div>' + rows.join("");
    const detailOpen = !$("poi-lang-detail").classList.contains("hidden");
    $("poi-preview").classList.toggle("hidden", others.length === 0 || detailOpen);
  }

  // ---------- Khung "Sửa chi tiết các ngôn ngữ khác" (không bắt buộc) ----------
  const INPUT = "w-full text-sm border border-slate-300 rounded-xl px-3 py-2 bg-slate-50 focus:ring-2 focus:ring-blue-500 focus:outline-none";
  const LABEL = "block text-xs font-semibold text-slate-700 mb-1";

  function setDetailOpen(open) {
    $("poi-lang-detail").classList.toggle("hidden", !open);
    $("poi-preview").classList.toggle("hidden", open || languages.length <= 1);
    $("poi-detail-label").textContent = open
      ? "Thu gọn"
      : "Sửa chi tiết các ngôn ngữ khác";
  }

  async function toggleDetail() {
    const open = $("poi-lang-detail").classList.contains("hidden");
    setDetailOpen(open);
    if (!open || detailLoaded) return;

    const others = languages.filter((l) => l.code !== "vi");
    const code = editingCode;
    const translations = (code && pois[code]?.translations) || {};
    $("poi-lang-blocks").innerHTML = '<p class="text-xs text-slate-400">Đang tải bản dịch...</p>';
    const narrations = await Promise.all(others.map(async (l) => [l.code, code ? await fetchNarration(code, l.code) : null]));
    if (editingCode !== code) return;

    originalDetail = {};
    narrations.forEach(([lang, n]) => {
      originalDetail[lang] = {
        name: translations[lang]?.name || "",
        description: translations[lang]?.description || "",
        narration: (n && n.content) || "",
      };
    });
    $("poi-lang-blocks").innerHTML = others.map((l) => {
      const o = originalDetail[l.code];
      const c = esc(l.code);
      return `<div class="border border-slate-200 rounded-xl p-4 space-y-2">
        <p class="text-sm font-bold text-slate-900">${esc(l.flag || "")} ${esc(l.native_name || l.name || l.code)} <span class="font-normal text-slate-400">(${c})</span></p>
        <div><label class="${LABEL}">Tên điểm</label><input data-detail="${c}" data-field="name" value="${esc(o.name)}" placeholder="Để trống: tự dịch" class="${INPUT}" /></div>
        <div><label class="${LABEL}">Mô tả</label><textarea data-detail="${c}" data-field="description" rows="2" placeholder="Để trống: tự dịch" class="${INPUT}">${esc(o.description)}</textarea></div>
        <div><label class="${LABEL}">Nội dung thuyết minh (đọc thành audio)</label><textarea data-detail="${c}" data-field="narration" rows="3" placeholder="Để trống: tự dịch" class="${INPUT}">${esc(o.narration)}</textarea></div>
      </div>`;
    }).join("");
    detailLoaded = true;
  }

  // Những ô ngôn ngữ khác mà admin đã sửa so với lúc mở: {en: {name: "..."}}
  function collectManualEdits() {
    const edits = {};
    if (!detailLoaded) return edits;
    document.querySelectorAll("#poi-lang-blocks [data-detail]").forEach((el) => {
      const lang = el.dataset.detail;
      const field = el.dataset.field;
      const value = el.value.trim();
      if (value && value !== (originalDetail[lang]?.[field] || "")) {
        (edits[lang] = edits[lang] || {})[field] = value;
      }
    });
    return edits;
  }

  function refreshDetailFields(translations, narrationByLang) {
    if (!detailLoaded) return;
    Object.keys(originalDetail).forEach((lang) => {
      const next = {
        name: translations[lang]?.name ?? originalDetail[lang].name,
        description: translations[lang]?.description ?? originalDetail[lang].description,
        narration: narrationByLang[lang] ?? originalDetail[lang].narration,
      };
      originalDetail[lang] = next;
      FIELDS.forEach((f) => {
        const el = document.querySelector(`#poi-lang-blocks [data-detail="${lang}"][data-field="${f}"]`);
        if (el) el.value = next[f];
      });
    });
  }

  async function openForm(code) {
    editingCode = code;
    const p = code ? pois[code] : null;
    $("poi-form-title").textContent = code ? "Sửa POI " + code : "Thêm POI mới";
    $("poi-f-code").value = code || "";
    $("poi-f-code").disabled = !!code;
    $("poi-f-radius").value = p ? p.geofence_radius : 15;
    $("poi-f-lat").value = p ? p.latitude : "";
    $("poi-f-lng").value = p ? p.longitude : "";
    const vi = p?.translations?.vi || {};
    $("poi-f-name").value = vi.name || p?.name || "";
    $("poi-f-desc").value = vi.description || p?.description || "";
    $("poi-f-narr").value = "";
    $("poi-other-langs").textContent =
      languages.filter((l) => l.code !== "vi").map((l) => l.native_name || l.name || l.code).join(", ") || "chưa có ngôn ngữ khác";
    renderPreview(p?.translations || {});
    originalVi = null;
    originalDetail = {};
    detailLoaded = false;
    $("poi-lang-blocks").innerHTML = "";
    setDetailOpen(false);
    $("poi-form-status").classList.add("hidden");
    $("poi-btn-save").disabled = false;
    $("poi-modal").classList.remove("hidden");

    if (code) {
      setFormStatus("info", "Đang tải nội dung thuyết minh...");
      const n = await fetchNarration(code, "vi");
      if (editingCode !== code) return;
      const narr = (n && n.content) || "";
      $("poi-f-narr").value = narr && narr !== $("poi-f-desc").value.trim() ? narr : "";
      originalVi = { name: $("poi-f-name").value.trim(), description: $("poi-f-desc").value.trim(), narration: narr };
      $("poi-form-status").classList.add("hidden");
    }
  }

  function closeForm() {
    $("poi-modal").classList.add("hidden");
    editingCode = null;
  }

  // Hỏi lại narration-service mỗi 2 giây (tối đa ~90 giây) cho tới khi audio tạo xong.
  async function waitForAudio(code, langs) {
    for (let i = 0; i < 45; i++) {
      const states = await Promise.all(langs.map(async (l) => [l, audioState(await fetchNarration(code, l))]));
      const done = states.every(([, st]) => st === "completed" || st === "failed");
      setFormStatus(done ? "ok" : "info",
        (done ? "Đã tạo xong audio." : '<i class="fa-solid fa-spinner fa-spin mr-1"></i> Đang tạo audio thuyết minh...') +
        "<br>" + states.map(([l, st]) => audioBadge(l, st)).join(" "));
      if (done) return states.filter(([, st]) => st === "failed").map(([l]) => l);
      await sleep(2000);
    }
    return null;
  }

  async function save(ev) {
    ev.preventDefault();
    const name = $("poi-f-name").value.trim();
    const description = $("poi-f-desc").value.trim();
    const narrationVi = $("poi-f-narr").value.trim() || description;
    const isNew = !editingCode;
    const code = isNew ? $("poi-f-code").value.trim().toUpperCase() : editingCode;
    if (!code) return setFormStatus("error", "Vui lòng nhập mã POI (VD: P11).");
    if (!name || !description) return setFormStatus("error", "Vui lòng nhập tên và mô tả tiếng Việt.");

    const existing = (!isNew && pois[code]?.translations) || {};
    const body = {
      latitude: Number($("poi-f-lat").value),
      longitude: Number($("poi-f-lng").value),
      geofence_radius: Number($("poi-f-radius").value),
      translations: { ...existing, vi: { name, description } }, // giữ bản dịch cũ cho tới khi dịch lại
    };

    $("poi-btn-save").disabled = true;
    try {
      // 1. Lưu POI
      setFormStatus("info", '<i class="fa-solid fa-spinner fa-spin mr-1"></i> Đang lưu POI...');
      if (isNew) await call("POST", "/pois", { ...body, poi_code: code });
      else await call("PUT", "/pois/" + encodeURIComponent(code), body);
      if (isNew) {
        editingCode = code; // bấm Lưu lần nữa sẽ là sửa, không tạo trùng
        $("poi-f-code").disabled = true;
        pois[code] = { poi_code: code, translations: body.translations };
      }
      $("poi-form-title").textContent = "Sửa POI " + code;

      // 2. Có cần dịch lại + tạo audio không?
      const manual = collectManualEdits();
      const manualLangs = Object.keys(manual);
      const viChanged = !originalVi || originalVi.name !== name || originalVi.description !== description || originalVi.narration !== narrationVi;
      const states = await Promise.all(languages.map(async (l) => audioState(await fetchNarration(code, l.code))));
      const missing = states.some((st) => st !== "completed") || languages.some((l) => l.code !== "vi" && !existing[l.code]?.name);

      let translations = { ...existing, vi: { name, description } };
      let waitLangs = [];
      let failedTranslate = {};
      let narrationByLang = {};

      if (isNew || viChanged || missing) {
        // 2a. Dịch tự động; ô nào admin đã sửa thì gửi kèm để giữ nguyên văn
        setFormStatus("info", '<i class="fa-solid fa-spinner fa-spin mr-1"></i> Đã lưu POI. Đang tự dịch sang các ngôn ngữ khác...');
        const auto = await call("POST", "/narrations/auto", { poi_id: code, name, description, narration: narrationVi, overrides: manual });
        translations = { ...translations, ...auto.translations };
        waitLangs = auto.narration_languages;
        failedTranslate = auto.failed_languages || {};
        originalVi = { name, description, narration: narrationVi };
        // Bản dịch đang có trên server sau khi dịch, để cập nhật lại các ô chi tiết
        const fresh = await Promise.all(waitLangs.map(async (l) => [l, (await fetchNarration(code, l))?.content]));
        fresh.forEach(([l, c]) => { if (c) narrationByLang[l] = c; });
      } else if (manualLangs.length) {
        // 2b. Tiếng Việt không đổi, admin chỉ chỉnh tay vài ngôn ngữ: không dịch lại
        setFormStatus("info", '<i class="fa-solid fa-spinner fa-spin mr-1"></i> Đang lưu bản dịch đã chỉnh...');
        const contents = {};
        manualLangs.forEach((l) => {
          const { narration, ...nameDesc } = manual[l];
          translations[l] = { ...(existing[l] || {}), ...nameDesc };
          if (narration) contents[l] = narration;
        });
        if (Object.keys(contents).length) {
          await call("POST", "/narrations", { poi_id: code, title: name, contents });
          waitLangs = Object.keys(contents);
          narrationByLang = contents;
        }
      } else {
        setFormStatus("ok", "Đã lưu thông tin POI. Nội dung không đổi nên giữ nguyên bản dịch và audio cũ.");
        toast(`Đã cập nhật POI ${code}.`);
        await load();
        return;
      }

      // 3. Lưu tên/mô tả các ngôn ngữ vào POI
      await call("PUT", "/pois/" + encodeURIComponent(code), { translations });
      pois[code] = { ...(pois[code] || {}), translations };
      renderPreview(translations);
      refreshDetailFields(translations, narrationByLang);

      // 4. Chờ audio tạo xong (nếu có ngôn ngữ cần tạo)
      const failedLangs = Object.keys(failedTranslate);
      const failedAudio = waitLangs.length ? await waitForAudio(code, waitLangs) : [];
      const notes = [];
      if (failedLangs.length) {
        const reason = failedTranslate[failedLangs[0]] || "";
        notes.push("Không dịch được: <b>" + esc(failedLangs.join(", ")) + "</b>. Bấm Lưu lại để thử lần nữa." +
          (reason ? '<br><span class="text-[11px]">Lý do: ' + esc(reason) + "</span>" : ""));
      }
      if (failedAudio === null) notes.push("Audio vẫn đang được tạo ở nền, vài phút sau tải lại để kiểm tra.");
      else if (failedAudio.length) notes.push("Tạo audio lỗi ở: <b>" + esc(failedAudio.join(", ")) + "</b>.");

      const manualNote = manualLangs.length ? " Giữ nguyên phần bạn tự sửa ở: " + manualLangs.join(", ") + "." : "";
      if (notes.length) {
        setFormStatus("warn", "Đã lưu POI." + esc(manualNote) + "<br>" + notes.join("<br>"));
      } else if (waitLangs.length) {
        setFormStatus("ok", "Đã lưu và tạo xong audio cho: " + waitLangs.map((l) => audioBadge(l, "completed")).join(" ") + esc(manualNote));
        toast(isNew ? `Đã thêm POI ${code}, tự dịch và tạo audio.` : `Đã cập nhật POI ${code}.`);
      } else {
        setFormStatus("ok", "Đã lưu bản dịch." + esc(manualNote));
        toast(`Đã cập nhật POI ${code}.`);
      }
      await load();
    } catch (e) {
      setFormStatus("error", esc(e.message));
    } finally {
      $("poi-btn-save").disabled = false;
    }
  }

  async function deletePoi(code) {
    const p = pois[code] || {};
    const name = p.translations?.vi?.name || p.name || code;
    const warn = p.status === "PUBLISHED" ? '\n\nĐiểm này ĐANG HIỆN cho khách. Nếu chỉ muốn tạm ẩn, hãy bấm "Ẩn" thay vì xóa.' : "";
    if (!confirm(`Xóa hẳn POI ${code} – ${name}?\n\nSẽ xóa luôn bản dịch, thuyết minh và các file audio MP3 của điểm này. Không thể khôi phục.${warn}`)) return;
    try {
      await call("DELETE", "/pois/" + encodeURIComponent(code) + "/permanent");
      try {
        await call("DELETE", "/narrations/" + encodeURIComponent(code));
        showMsg(`Đã xóa POI ${code} cùng thuyết minh và audio.`);
      } catch (e) {
        showMsg(`Đã xóa POI ${code}, nhưng chưa xóa được thuyết minh/audio: ${e.message}`, false);
      }
      toast(`Đã xóa POI ${code}.`);
      await load();
    } catch (e) {
      showMsg(e.message, false);
    }
  }

  async function changeStatus(code, status) {
    try {
      await call("PATCH", "/pois/" + encodeURIComponent(code) + "/status", { status });
      toast(status === "PUBLISHED" ? `Đã xuất bản POI ${code}.` : `Đã ẩn POI ${code}.`);
      await load();
    } catch (e) {
      showMsg(e.message, false);
    }
  }

  function init() {
    if (!$("poi-rows")) return;
    // Đưa hộp thoại ra khung bên phải (không cuộn) để luôn phủ đúng vùng nội dung, sidebar vẫn hiện.
    const main = document.querySelector("main");
    if (main && main.parentElement) main.parentElement.appendChild($("poi-modal"));
    $("poi-btn-new").onclick = () => openForm(null);
    $("poi-btn-detail").onclick = toggleDetail;
    $("poi-btn-cancel").onclick = closeForm;
    $("poi-btn-close").onclick = closeForm;
    $("poi-form").onsubmit = save;
    $("poi-rows").onclick = (ev) => {
      const btn = ev.target.closest("button");
      if (!btn) return;
      if (btn.dataset.edit) return openForm(btn.dataset.edit);
      if (btn.dataset.delete) return deletePoi(btn.dataset.delete);
      if (btn.dataset.act) return changeStatus(btn.dataset.code, btn.dataset.act);
    };
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
  else init();

  window.PoiAdmin = { load };
})();
