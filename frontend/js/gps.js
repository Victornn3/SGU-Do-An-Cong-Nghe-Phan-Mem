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

// Xử lý một vị trí GPS thật (dùng cho cả lần đo đầu và các lần cập nhật sau)
function handleRealPosition(position) {
  if (gpsMode !== "real") return;

  const lat = position.coords.latitude;
  const lng = position.coords.longitude;
  const accuracy = position.coords.accuracy;
  lastRealPosition = { lat, lng, accuracy };

  if (leafletMap) {
    updatePersonMarker(lat, lng, t("marker.real", "Vị trí thật (±{acc}m)", { acc: Math.round(accuracy) }));
  }

  const distToCenter = getDistanceMeters(lat, lng, VAN_MIEU_CENTER[0], VAN_MIEU_CENTER[1]);
  if (distToCenter <= LOCATION_CONFIG.siteRadiusMeters) {
    checkGeofenceTrigger(lat, lng, accuracy);
  } else {
    setGpsStatus(t("status.gpsOutside", "Bạn đang ở ngoài khuôn viên Văn Miếu. Hãy chọn điểm trong danh sách để nghe, hoặc dùng chế độ mô phỏng."));
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
    setGpsStatus(t("status.gpsActive", "Đang dùng GPS thật."));
    handleRealPosition({ coords: { latitude: lastRealPosition.lat, longitude: lastRealPosition.lng, accuracy: lastRealPosition.accuracy } });
    return;
  }
  const closeWelcome = () => document.getElementById("welcomeModal")?.classList.add("hidden");

  if (!navigator.geolocation) {
    closeWelcome();
    setGpsStatus(t("status.gpsUnavailable", "Không xác định được vị trí. Bạn vẫn có thể xem bản đồ và chọn điểm trong danh sách để nghe."));
    return;
  }

  setGpsStatus(t("status.gpsRequesting", "Đang xin quyền vị trí..."));
  navigator.geolocation.getCurrentPosition(
    (position) => {
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
        setGpsStatus(t("status.gpsGranted", "Đã bật GPS. Chạm vào màn hình để bật âm thanh, rồi đi tới các điểm tham quan."));
      }
    },
    (err) => {
      console.warn("Không lấy được vị trí:", err);
      closeWelcome();
      if (gpsMode !== "simulated") gpsMode = null;
      setGpsStatus(
        err && err.code === 1
          ? t("status.gpsDenied", "Bạn đã từ chối quyền vị trí. Vẫn xem được bản đồ và chọn điểm trong danh sách để nghe thuyết minh.")
          : t("status.gpsUnavailable", "Không xác định được vị trí. Bạn vẫn có thể xem bản đồ và chọn điểm trong danh sách để nghe.")
      );
    },
    { enableHighAccuracy: true, timeout: 15000, maximumAge: 5000 }
  );
}
