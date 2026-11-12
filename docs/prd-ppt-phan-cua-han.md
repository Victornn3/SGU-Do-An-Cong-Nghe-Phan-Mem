# Nội dung PRD và PPT – phần của Người 1 (Hân)

Tài liệu này tổng hợp các phần cần cập nhật trong PRD/PPT. Mục A là sửa PRD, mục B là bảng nghiệm thu AC08–AC17, mục C là 10 câu hỏi–đáp, mục D là nội dung slide.

## A. Các chỗ phải sửa trong PRD để khớp mã nguồn

| Chỗ trong PRD | Đang ghi | Sửa thành |
|---|---|---|
| Mô tả sản phẩm, Key Features F04, phần dữ liệu POI | "15 địa điểm tham quan thuộc 5 cụm di tích" | "11 điểm tham quan (POI) theo danh sách phẳng, không chia cụm" |
| Tiêu đề "Cấu trúc 15 POI thuộc 5 cụm tham quan" | như trên | "Danh sách 11 POI" (P00–P10) |
| Data Schema: collection `zones` | có | **Xóa** collection `zones` (bảng dưới thay thế) |
| FAQ "Vì sao không tự dịch hay tạo giọng đọc bằng AI?" | "ngoài phạm vi MVP; audio do Admin tải lên" | Mã nguồn **đang dùng gTTS** để tạo MP3 từ bản dịch do con người viết. Sửa thành: "Bản dịch do nhóm biên soạn, không dịch tự động. Giọng đọc MP3 được tạo bằng gTTS từ văn bản đó." |
| KL03 "Tiếng Việt là mặc định" | luôn mặc định tiếng Việt | "Ngôn ngữ ban đầu theo ngôn ngữ trình duyệt nếu hệ thống hỗ trợ (vi, en, zh); nếu không thì tiếng Việt." (mã nguồn tự chọn English khi trình duyệt là tiếng Anh) |
| KL03 "đổi ngôn ngữ không gọi lại API" | không gọi API | "Đổi ngôn ngữ không tải lại danh sách POI và không mất phiên; bài thuyết minh của ngôn ngữ mới được tải một lần rồi lưu tạm." |
| KL04/KL07 GPS thật | khách cấp quyền GPS, tự phát theo vị trí thật | Màn hình chào có hai cách bắt đầu: "Dùng vị trí GPS thật" (xin quyền; chỉ dùng được khi khách cách điểm tham quan gần nhất không quá 300 m, ở xa, từ chối quyền hoặc lỗi thì báo lý do ngay trên màn hình chào để khách chọn chế độ giả lập) và "Bắt đầu với điểm P00" (mô phỏng vị trí, dùng để demo trong nhà) |
| Open Question 5 | "15 POI" | "11 POI" |
| Open Question 3 | 5 service chạy chung hay tách | Trả lời: tách thành container riêng (auth, poi, narration, ticket, statistics) cùng một API gateway |

### Data Schema thay thế (khớp mã nguồn)

| Collection | Trường chính | Ràng buộc |
|---|---|---|
| `languages` | `code` (_id), `name`, `native_name`, `flag`, `html_lang`, `tts_locale`, `display_order`, `is_active`, `ui{}` | `code` duy nhất; thêm ngôn ngữ mới = thêm một bản ghi |
| `pois` | `poi_code` (_id), `latitude`, `longitude`, `geofence_radius`, `status`, `coordinate_status`, `display_order`, `image_url`, `translations{mã_ngôn_ngữ: {name, description}}` | `geofence_radius` từ 10 đến 25 m, mặc định 15; `status` là DRAFT, PUBLISHED hoặc HIDDEN; `vi` bắt buộc có tên |
| `narrations` | `target_id` (= poi_code), `title`, `content{mã_ngôn_ngữ: văn bản}`, `audio_status{}`, `audio_paths{}` | `target_id` duy nhất; thiếu ngôn ngữ nào thì giao diện hiện thông báo dự phòng |
| `admins`, `tickets` | (phần của Người 2) | Người 2 đối chiếu tên collection với PRD |

Điểm khác với PRD cũ: nội dung từng ngôn ngữ nằm trong `translations{}` (đối tượng theo mã ngôn ngữ) thay vì mảng `contents[]`; văn bản thuyết minh dài tách sang collection `narrations`.

## B. Bảng nghiệm thu AC08–AC17 (điền kết quả thật)

Cột "Kết quả" chỉ ghi ĐẠT khi tiêu chí đã được chạy thật; các dòng ghi "giả lập" chạy bằng trình duyệt tự động. Mã AC suy ra từ các quy tắc KL03–KL07 trong PRD (KL03 → AC08–AC12, KL04 → AC16–AC17, KL05 → AC14, KL07 → AC12 và AC15); nếu bảng AC của PRD nhóm đánh số khác thì đổi lại cho khớp.

| Mã | Tiêu chí | Cách thử (mở http://localhost) | Kết quả |
|---|---|---|---|
| AC08 | Ngôn ngữ ban đầu: tiếng Việt, hoặc theo ngôn ngữ trình duyệt nếu hỗ trợ | Mở cửa sổ ẩn danh, xem giao diện; thử đổi ngôn ngữ trình duyệt | ĐẠT (kiểm bằng trình duyệt giả lập: trình duyệt vi và fr cho `vi`, trình duyệt en cho `en`). Cần sửa câu chữ PRD, xem mục A |
| AC09 | Ô chọn ngôn ngữ hiện đúng 3 ngôn ngữ lấy từ `/api/languages` | Bấm ô chọn ngôn ngữ | ĐẠT (ảnh chụp 3/11 và giả lập) |
| AC10 | Chọn English thì giao diện, tên và mô tả POI chuyển sang English | Chọn English, xem thanh trạng thái và danh sách POI | ĐẠT (ảnh chụp 3/11 và giả lập) |
| AC11 | Thiếu bản dịch thì hiện thông báo "đang cập nhật", không hiện tiếng Việt thay thế | Ở trang admin-content, xóa bản dịch en của một POI, mở POI đó ở English | ĐẠT (giả lập: thông báo "The narration text in this language is being updated.") |
| AC12 | Thiếu audio thì khóa nút phát, hiện thông báo, không phát ngôn ngữ khác | Đổi tên tạm một file MP3 (`mv data/audio/zh/P00.mp3 data/audio/zh/P00.bak`), chọn tiếng Trung, mở P00; sau đó đổi tên lại | ĐẠT (ảnh chụp 3/11 và giả lập) |
| AC13 | Đổi ngôn ngữ không tải lại danh sách POI, không mất phiên | DevTools > Network, đổi ngôn ngữ, xem có yêu cầu `/api/pois` mới hay không | ĐẠT MỘT PHẦN (giả lập: không gọi `/api/pois`; thuyết minh của ngôn ngữ mới tải 11 yêu cầu lần đầu, đổi lại lần sau 0 yêu cầu). Khác câu chữ PRD "không gọi lại API", xem mục A |
| AC14 | Nhiều vùng Geofence chồng nhau thì chọn POI gần nhất | Dùng nút mô phỏng vị trí giữa hai POI gần nhau | ĐẠT (giả lập: P03 và P04 cách nhau 25,8 m; điểm trong cả hai vùng chọn đúng P04 là điểm gần hơn) |
| AC15 | Từ chối quyền GPS vẫn xem bản đồ và nghe thủ công | Bấm "Dùng vị trí GPS thật", bấm Chặn khi trình duyệt hỏi quyền; sau đó chọn một POI trong danh sách và bấm nút phát | ĐẠT (giả lập: từ chối quyền thì màn hình chào vẫn mở và hiện thông báo, khách chọn chế độ giả lập để xem danh sách và nghe; thông báo có đủ vi, en, zh, ko). Cần thử lại trên điện thoại thật |
| AC16 | Vào bán kính 15 m thì audio tự phát một lần | Dùng GPS thật hoặc mô phỏng vị trí trong bán kính một POI | ĐẠT (giả lập: vị trí mô phỏng và GPS thật do trình duyệt giả lập cấp, phát đúng 1 lần). Chưa thử ngoài thực địa |
| AC17 | Bấm Pause thì không tự phát lại khi vẫn đứng trong vùng; rời vùng rồi vào lại thì phát lại | Sau AC16, bấm Pause, đợi 10 giây; sau đó ra ngoài rồi vào lại | ĐẠT (giả lập), **sau khi sửa lỗi**: trước đó cờ "đã tự phát" không được đặt lại khi rời vùng nên vào lại không phát lại |

Ghi chú về cách kiểm: các dòng "giả lập" được chạy bằng trình duyệt tự động với dữ liệu API giả, **chưa thử trên điện thoại thật**. Nên thử lại bằng tay AC14, AC16, AC17 trên http://localhost (nút mô phỏng vị trí) để có ảnh chụp.

Kiểm thử tự động (thư mục `tests/`): 23 test đạt, gồm quy tắc bán kính 10–25 m, trạng thái POI, tọa độ, bản dịch và dữ liệu mẫu (11 POI, 3 ngôn ngữ, khóa giao diện đồng nhất). Lệnh: `python -m unittest discover tests -v`. Trang `admin-content.html` và các API quản lý POI đã được chạy thử với dữ liệu giả lập; cần chạy lại trên hệ thống Docker thật bằng `./tests/smoke_api.sh`.

Tọa độ 11 POI đã được đối chiếu thủ công trên Google Maps (ảnh vệ tinh) ngày 07/11/2026, `coordinate_status = verified`. Lưu ý: đây là đối chiếu trên bản đồ, chưa đo bằng GPS tại hiện trường; ghi đúng như vậy trong báo cáo.

## C. 10 câu hỏi–đáp để chuẩn bị bảo vệ

1. **Vì sao chỉ có 11 POI, không phải 15 POI thuộc 5 cụm như PRD cũ?** Nhóm thu gọn theo dữ liệu thực tế có đủ nội dung và audio cho 3 ngôn ngữ. Danh sách phẳng đơn giản hơn cho khách và cho admin; PRD đã được sửa khớp.
2. **Thêm tiếng Hàn thì làm gì?** Thêm một bản ghi vào `languages.json` (mã `ko`, `tts_locale`, các chuỗi giao diện), thêm `translations.ko` cho POI và nội dung thuyết minh, chạy lại seed. Không sửa code vì giao diện và backend xử lý theo mã ngôn ngữ.
3. **Thiếu bản dịch hoặc audio thì sao?** Không tự chuyển sang ngôn ngữ khác. API trả `content_available` và `audio_available`; giao diện hiện thông báo và vô hiệu hóa nút phát.
4. **Vì sao bán kính mặc định 15 m, và đổi được không?** 15 m đủ để bắt vị trí GPS điện thoại ngoài trời mà không kích hoạt nhầm POI bên cạnh. Admin chỉnh được trong khoảng 10–25 m; API từ chối giá trị ngoài khoảng. Con số sẽ được hiệu chỉnh sau pilot.
5. **Geofence tính ở đâu và vì sao?** Tính trên điện thoại bằng công thức Haversine (một hàm duy nhất trong `main.js`), không phụ thuộc đường truyền và phản hồi ngay khi vào vùng. Server chỉ nhận thống kê. Giao diện có hai chế độ: GPS thật (xin quyền, chỉ bật khi khách ở trong hoặc gần khu di tích; không dùng được thì báo lý do và mời chọn giả lập) và mô phỏng vị trí để demo trong nhà.
6. **DRAFT, PUBLISHED, HIDDEN khác nhau thế nào?** POI mới luôn là DRAFT. Chỉ PUBLISHED được gửi cho khách. HIDDEN là POI bị gỡ khỏi trang khách nhưng vẫn giữ dữ liệu, có thể xuất bản lại.
7. **Audio tạo bằng cách nào, vì sao không đưa MP3 vào Git?** Văn bản do nhóm biên soạn; MP3 sinh bằng gTTS (`generate_33_audio.py` hoặc tự động khi admin lưu thuyết minh). File MP3 nặng nên bị chặn trong `.gitignore` và được cấp riêng khi triển khai.
8. **Tọa độ lấy từ đâu, đã chính xác chưa?** Lấy từ Google Maps và đối chiếu từng điểm trên ảnh vệ tinh, đánh dấu `verified`. Chưa đo bằng GPS tại hiện trường nên sai số vài mét là có thể; bán kính 15 m đủ bù sai số này. Điểm tạo mới qua trang admin mặc định là `pending_field_verification` cho tới khi được đối chiếu.
9. **Xóa POI thì dữ liệu có mất không?** Không. `DELETE` chỉ chuyển sang HIDDEN (xóa mềm) để tránh mất dữ liệu do thao tác nhầm.
10. **API ghi dữ liệu được bảo vệ thế nào?** Mọi API ghi và `GET /api/pois/admin/all` yêu cầu token JWT; gateway kiểm tra token trước khi chuyển tiếp (phần của Người 2). Trang quản trị gửi token từ `localStorage.admin_token`. Trước khi phần xác thực của Người 2 được gộp vào, các API này chưa bị chặn ở gateway.

## D. Nội dung slide (3 slide)

**Slide 1 – Dữ liệu và đa ngôn ngữ**
- 11 POI (P00–P10), 3 ngôn ngữ: Việt, Anh, Trung
- Bảng `languages` + `translations{}`: thêm ngôn ngữ chỉ cần thêm dữ liệu
- Thiếu bản dịch hoặc audio: hiện thông báo, không phát ngôn ngữ khác

**Slide 2 – Quản lý nội dung (Admin)**
- Trang `admin-content.html`: thêm, sửa, xuất bản, ẩn POI
- Vòng đời: DRAFT → PUBLISHED ↔ HIDDEN
- Kiểm tra dữ liệu: bán kính 10–25 m, tọa độ trong khu vực, bắt buộc tên tiếng Việt

**Slide 3 – Kiểm thử và hạn chế**
- 23 test tự động đạt; AC08–AC17 đạt trên trình duyệt giả lập (AC13 đạt một phần)
- Hạn chế: chưa thử GPS ngoài thực địa; tọa độ mới đối chiếu trên bản đồ, chưa đo GPS tại hiện trường; bảo vệ API ghi phụ thuộc phần xác thực của Người 2
