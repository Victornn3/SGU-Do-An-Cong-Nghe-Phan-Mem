/**
 * Ticket Gate Module (M8) - Phụ trách bởi Người 2
 * Kiểm soát quyền truy cập của khách dựa trên mã vé QR.
 */
(function () {
  const TicketGate = {
    ticketInfo: null,

    // Hàm lấy tham số từ URL
    getTicketFromUrl() {
      const params = new URLSearchParams(window.location.search);
      return params.get("ticket");
    },

    // Hàm gọi API xác thực vé với backend
    async scanTicket(ticketCode) {
      try {
        const response = await fetch(`/api/tickets/scan/${encodeURIComponent(ticketCode)}`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
        });
        return await response.json();
      } catch (err) {
        console.error("Lỗi kết nối cổng vé:", err);
        return { success: false, message: "Không thể kết nối đến máy chủ soát vé!" };
      }
    },

    // Hiển thị màn hình chặn khi không có vé hoặc vé lỗi
    showGateOverlay(errorMessage = "") {
      let overlay = document.getElementById("ticket-gate-overlay");
      if (!overlay) {
        overlay = document.createElement("div");
        overlay.id = "ticket-gate-overlay";
        overlay.style.cssText = `
          position: fixed; inset: 0; z-index: 99999;
          background: rgba(15, 23, 42, 0.95); backdrop-filter: blur(8px);
          display: flex; align-items: center; justify-content: center;
          font-family: system-ui, -apple-system, sans-serif; color: white;
          padding: 20px;
        `;
        document.body.appendChild(overlay);
      }

      overlay.innerHTML = `
        <div style="background: #1e293b; border: 1px solid #334155; border-radius: 16px; max-width: 420px; width: 100%; padding: 24px; text-align: center; box-shadow: 0 20px 25px -5px rgba(0,0,0,0.5);">
          <div style="font-size: 48px; margin-bottom: 12px;">🎟️</div>
          <h2 style="margin: 0 0 8px 0; font-size: 20px; font-weight: 700; color: #f8fafc;">Xác nhận vé tham quan</h2>
          <p style="color: #94a3b8; font-size: 14px; margin-bottom: 20px;">Quét mã QR in trên vé, hoặc nhập mã vé bên dưới để bắt đầu nghe thuyết minh.</p>
          
          ${errorMessage ? `<div style="background: rgba(239,68,68,0.2); border: 1px solid #ef4444; color: #fca5a5; padding: 10px; border-radius: 8px; font-size: 13px; margin-bottom: 16px;">${errorMessage}</div>` : ""}

          <form id="gate-form" style="display: flex; gap: 8px; margin-bottom: 16px;">
            <input type="text" id="manual-ticket-input" placeholder="Mã vé, ví dụ VM-STD-ABC123" 
              style="flex: 1; padding: 10px 14px; border-radius: 8px; border: 1px solid #475569; background: #0f172a; color: white; font-size: 14px; outline: none;">
            <button type="submit" style="background: #d97706; hover:background: #b45309; color: white; border: none; padding: 10px 16px; border-radius: 8px; font-weight: 600; cursor: pointer;">Vào</button>
          </form>

          <div style="border-top: 1px dashed #334155; padding-top: 16px; margin-top: 16px;">
            <p style="font-size: 12px; color: #64748b; margin-bottom: 8px;">Chưa có vé?</p>
            <button id="btn-demo-mode" style="background: #334155; color: #cbd5e1; border: none; padding: 8px 14px; border-radius: 6px; font-size: 12px; cursor: pointer;">
              Xem thử ứng dụng
            </button>
          </div>
        </div>
      `;

      // Xử lý khi tự gõ mã vé
      document.getElementById("gate-form").addEventListener("submit", (e) => {
        e.preventDefault();
        const code = document.getElementById("manual-ticket-input").value.trim();
        if (code) {
          window.location.search = `?ticket=${encodeURIComponent(code)}`;
        }
      });

      // Xử lý nút Demo
      document.getElementById("btn-demo-mode").addEventListener("click", () => {
        sessionStorage.setItem("vm_ticket_demo", "true");
        overlay.remove();
        console.log("Đã kích hoạt chế độ Demo.");
      });
    },

    // Hiển thị lời chào theo loại vé
    showWelcomeToast(ticket) {
      const type = ticket.ticket_type || "STANDARD";
      const isPriority = type === "PRIORITY";
      const toast = document.createElement("div");
      toast.style.cssText = `
        position: fixed; top: 20px; left: 50%; transform: translateX(-50%);
        background: ${isPriority ? "linear-gradient(135deg, #78350f, #d97706)" : "#1e293b"};
        border: 1px solid ${isPriority ? "#f59e0b" : "#475569"};
        color: white; padding: 10px 20px; border-radius: 30px; font-size: 14px;
        font-weight: 600; z-index: 9999; box-shadow: 0 10px 15px -3px rgba(0,0,0,0.3);
        display: flex; align-items: center; gap: 8px;
      `;
      toast.innerHTML = `
        <span>${isPriority ? "⭐ Vé ưu tiên" : "🎟️ Vé thường"}:</span>
        <span style="color: #fde68a;">${ticket.ticket_code}</span>
      `;
      document.body.appendChild(toast);
      setTimeout(() => toast.remove(), 4000);
    },

    // HÀM CHÍNH: Gọi hàm này để kiểm tra vé (Điểm giao duy nhất với Người 1)
    async verify() {
      // 1. Kiểm tra nếu đang ở chế độ Demo
      if (sessionStorage.getItem("vm_ticket_demo") === "true") {
        return { allowed: true, ticket_type: "DEMO" };
      }

      // 2. Lấy vé từ URL
      const ticketCode = this.getTicketFromUrl();
      if (!ticketCode) {
        this.showGateOverlay("Vui lòng quét vé để tiếp tục!");
        return { allowed: false, ticket_type: null };
      }

      // 3. Quét vé trên server
      const result = await this.scanTicket(ticketCode);
      if (result.success) {
        this.ticketInfo = result.ticket;
        this.showWelcomeToast(result.ticket);
        return { 
          allowed: true, 
          ticket_type: result.ticket.ticket_type,
          ticket_code: result.ticket.ticket_code 
        };
      } else {
        this.showGateOverlay(result.message);
        return { allowed: false, ticket_type: null };
      }
    },
  };

  // Xuất ra toàn cục theo đúng cam kết trong PRD
  window.VMTicketGate = TicketGate;
})();