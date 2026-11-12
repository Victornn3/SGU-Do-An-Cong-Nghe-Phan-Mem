/*
 * Nút tua lại / tua tới 10 giây và chỉnh tốc độ đọc cho cả hai trình phát
 * (trình phát nổi trên bản đồ và trình phát ở trang chi tiết).
 * Tốc độ đã chọn được nhớ trên máy khách và áp dụng cho mọi bài thuyết minh.
 */
(function () {
  const PLAYER_IDS = ["audioPlayer", "audioPlayerDetail"];
  const SPEEDS = [0.75, 1, 1.25, 1.5];
  const STORAGE_KEY = "vm_playback_rate";
  const SKIP_SECONDS = 10;

  function loadRate() {
    try {
      const saved = Number(localStorage.getItem(STORAGE_KEY));
      return SPEEDS.includes(saved) ? saved : 1;
    } catch (e) {
      return 1;
    }
  }

  let rate = loadRate();

  function applyRate(player) {
    // Đổi nguồn audio sẽ đặt lại playbackRate về defaultPlaybackRate, nên đặt cả hai.
    player.defaultPlaybackRate = rate;
    player.playbackRate = rate;
  }

  function setRate(newRate) {
    rate = newRate;
    try {
      localStorage.setItem(STORAGE_KEY, String(rate));
    } catch (e) {
      /* trình duyệt chặn lưu trữ: vẫn dùng được trong phiên này */
    }
    PLAYER_IDS.forEach((id) => {
      const player = document.getElementById(id);
      if (player) applyRate(player);
    });
    document.querySelectorAll(".audio-speed-select").forEach((select) => {
      select.value = String(rate);
    });
  }

  function skip(player, seconds) {
    if (!player || !Number.isFinite(player.duration)) return;
    player.currentTime = Math.min(Math.max(player.currentTime + seconds, 0), player.duration);
  }

  const BTN =
    "h-8 px-2.5 rounded-lg bg-slate-100 hover:bg-sky-100 text-slate-700 hover:text-sky-700 text-xs font-semibold " +
    "flex items-center gap-1 transition cursor-pointer";

  function buildControls(player) {
    const bar = document.createElement("div");
    bar.className = "audio-extra-controls flex items-center justify-between gap-2 mt-2";
    bar.innerHTML = `
      <div class="flex items-center gap-1.5">
        <button type="button" data-skip="-${SKIP_SECONDS}" class="${BTN}"
          title="Lùi 10 giây" aria-label="Lùi 10 giây"
          data-i18n-title="audio.rewind10" data-i18n-aria-label="audio.rewind10">
          <i class="fa-solid fa-rotate-left"></i><span>10s</span>
        </button>
        <button type="button" data-skip="${SKIP_SECONDS}" class="${BTN}"
          title="Tới 10 giây" aria-label="Tới 10 giây"
          data-i18n-title="audio.forward10" data-i18n-aria-label="audio.forward10">
          <span>10s</span><i class="fa-solid fa-rotate-right"></i>
        </button>
      </div>
      <label class="flex items-center gap-1.5 text-[11px] text-slate-500">
        <i class="fa-solid fa-gauge-high"></i>
        <span data-i18n="audio.speed">Tốc độ đọc</span>
        <select class="audio-speed-select h-8 rounded-lg border border-slate-200 bg-white px-1.5 text-xs font-semibold text-slate-700 cursor-pointer"
          data-i18n-aria-label="audio.speed" aria-label="Tốc độ đọc">
          ${SPEEDS.map((s) => `<option value="${s}">${s}x</option>`).join("")}
        </select>
      </label>`;

    bar.querySelectorAll("[data-skip]").forEach((btn) => {
      btn.addEventListener("click", () => skip(player, Number(btn.dataset.skip)));
    });
    const select = bar.querySelector("select");
    select.value = String(rate);
    select.addEventListener("change", () => setRate(Number(select.value)));
    return bar;
  }

  function init() {
    PLAYER_IDS.forEach((id) => {
      const player = document.getElementById(id);
      if (!player || player.dataset.extraControls) return;
      player.dataset.extraControls = "1";
      player.after(buildControls(player));
      applyRate(player);
      // Giữ tốc độ đã chọn khi chuyển sang bài thuyết minh khác
      ["loadedmetadata", "play"].forEach((ev) => player.addEventListener(ev, () => applyRate(player)));
    });
    if (typeof applyTranslations === "function") applyTranslations();
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
  else init();
})();
