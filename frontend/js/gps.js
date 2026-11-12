// GPS: khoảng cách Haversine duy nhất của ứng dụng và luồng GPS thật.
// Nạp sau main.js; dùng các biến toàn cục của main.js (gpsMode, leafletMap, t...).

function getDistanceMeters(lat1, lon1, lat2, lon2) {
  const R = 6371000;
  const toRad = (deg) => (deg * Math.PI) / 180;
  const dLat = toRad(lat2 - lat1);
  const dLon = toRad(lon2 - lon1);
  const a =
    Math.sin(dLat / 2) ** 2 +
    Math.cos(toRad(lat1)) * Math.cos(toRad(lat2)) * Math.sin(dLon / 2) ** 2;
  return 2 * R * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
}

// Khoảng cách (m) từ một vị trí tới điểm tham quan gần nhất. Dùng các điểm thật
// thay vì một tâm cố định, vì khuôn viên Văn Miếu dài (cổng P00 cách tâm cũ ~300m).
function khoangCachToiKhuDiTich(lat, lng) {
  const diem = (Array.isArray(poisData) ? poisData : []).filter(
    (p) => typeof p.lat === "number" && typeof p.lng === "number"
  );
  if (!diem.length) return getDistanceMeters(lat, lng, VAN_MIEU_CENTER[0], VAN_MIEU_CENTER[1]);
  return Math.min(...diem.map((p) => getDistanceMeters(lat, lng, p.lat, p.lng)));
}

function dinhDangKhoangCach(m) {
  return m >= 1000 ? `${(m / 1000).toFixed(m >= 10000 ? 0 : 1)} km` : `${Math.round(m)} m`;
}

// Báo lý do không dùng được GPS thật. Nếu hộp chào mừng còn mở thì hiện ngay trong hộp
// (khách bấm tiếp nút giả lập); nếu đang ở bản đồ thì hiện ở thanh trạng thái.
function baoKhongDungDuocGpsThat(message) {
  const modal = document.getElementById("welcomeModal");
  const notice = document.getElementById("welcomeGpsNotice");
  if (modal && !modal.classList.contains("hidden") && notice) {
    notice.textContent = message;
    notice.classList.remove("hidden");
    document.getElementById("btnBatDauP00")?.classList.add("ring-4", "ring-sky-200");
  }
  setGpsStatus(message);
}

// Xử lý một vị trí GPS thật (dùng cho cả lần đo đầu và các lần cập nhật sau)
function handleRealPosition(position) {
  if (gpsMode !== "real") return;

  const lat = position.coords.latitude;
  const lng = position.coords.longitude;
  const accuracy = position.coords.accuracy;
  lastRealPosition = { lat, lng, accuracy };

  if (leafletMap) {
    updatePersonMarker(lat, lng, t("marker.real", "Vị trí của bạn", { acc: Math.round(accuracy) }));
  }

  if (khoangCachToiKhuDiTich(lat, lng) <= LOCATION_CONFIG.siteRadiusMeters) {
    checkGeofenceTrigger(lat, lng, accuracy);
  } else {
    setGpsStatus(t("status.gpsOutside", "Bạn đang ở ngoài khuôn viên Văn Miếu. Hãy chọn điểm trong danh sách để nghe, hoặc dùng chế độ giả lập vị trí."));
  }
}

function startWatchingRealGps() {
  if (realGpsWatchId !== null) return;

  realGpsWatchId = navigator.geolocation.watchPosition(
    handleRealPosition,
    (err) => console.warn("Lỗi cập nhật GPS ngầm:", err),
    { enableHighAccuracy: true, timeout: 15000, maximumAge: 5000 }
  );
}

// Khách chọn dùng GPS thật. Bị từ chối hoặc lỗi thì ứng dụng vẫn dùng được:
// xem bản đồ, đọc văn bản và nghe thủ công (PRD KL07).
function batDauGpsThat() {
  // Đang dùng GPS thật rồi (bấm lại nút ở màn bản đồ): chỉ báo lại, không xin quyền lần nữa
  if (gpsMode === "real" && lastRealPosition) {
    setGpsStatus(t("status.gpsActive", "Đang dùng vị trí thật của bạn."));
    handleRealPosition({ coords: { latitude: lastRealPosition.lat, longitude: lastRealPosition.lng, accuracy: lastRealPosition.accuracy } });
    return;
  }
  const closeWelcome = () => document.getElementById("welcomeModal")?.classList.add("hidden");
  document.getElementById("welcomeGpsNotice")?.classList.add("hidden");

  if (!navigator.geolocation) {
    baoKhongDungDuocGpsThat(t("status.gpsNotSupported", "Thiết bị không hỗ trợ định vị nên chưa dùng được chế độ GPS thật. Hãy chọn chế độ giả lập để nghe thử."));
    return;
  }

  setGpsStatus(t("status.gpsRequesting", "Đang xin quyền truy cập vị trí..."));
  navigator.geolocation.getCurrentPosition(
    (position) => {
      // Chỉ cho dùng GPS thật khi khách đang ở trong hoặc gần khu di tích.
      // Sai số lớn (định vị bằng mạng) thì cho hưởng phần sai số để không chặn nhầm.
      const { latitude, longitude, accuracy } = position.coords;
      const khoangCach = khoangCachToiKhuDiTich(latitude, longitude);
      const coTheODay = khoangCach - Math.min(accuracy || 0, 200);
      if (coTheODay > LOCATION_CONFIG.nearSiteMeters) {
        baoKhongDungDuocGpsThat(
          t("status.gpsTooFar", "Bạn đang cách Văn Miếu khoảng {dist} nên chưa dùng được chế độ GPS thật. Chế độ này chỉ dùng được khi bạn ở trong hoặc gần khu di tích. Hãy chọn chế độ giả lập để nghe thử.", { dist: dinhDangKhoangCach(khoangCach) })
        );
        return;
      }

      closeWelcome();
      sessionStorage.setItem("vm_experience_started", "1");
      gpsMode = "real";
      // Phân loại lượt truy cập chỉ ghi một lần, theo lựa chọn đầu tiên (PRD)
      if (!initialLocationMode) {
        initialLocationMode = "real";
        recordAccessClassification("real_gps", true);
      }
      currentSimulatedPoiId = null;
      guiHeartbeatTruyCap();
      document.getElementById("floatingAudioContainer")?.classList.remove("hidden");
      startWatchingRealGps();
      handleRealPosition(position);
      // Trình duyệt di động chặn tự phát âm thanh: nhắc khách chạm để bật (KL07)
      if (!autoPlayedPois.size) {
        setGpsStatus(t("status.gpsGranted", "Đã bật định vị. Chạm vào màn hình để bật âm thanh, rồi đi tới các điểm tham quan."));
      }
    },
    (err) => {
      console.warn("Không lấy được vị trí:", err);
      if (gpsMode !== "simulated") gpsMode = null;
      baoKhongDungDuocGpsThat(
        err && err.code === 1
          ? t("status.gpsDeniedChooseSim", "Bạn chưa cho phép truy cập vị trí nên chưa dùng được chế độ GPS thật. Hãy chọn chế độ giả lập để nghe thử.")
          : t("status.gpsUnavailableChooseSim", "Không xác định được vị trí của bạn nên chưa dùng được chế độ GPS thật. Hãy chọn chế độ giả lập để nghe thử.")
      );
    },
    { enableHighAccuracy: true, timeout: 15000, maximumAge: 5000 }
  );
}
