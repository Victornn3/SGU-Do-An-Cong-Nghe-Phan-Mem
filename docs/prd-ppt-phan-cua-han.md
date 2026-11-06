# Nội dung PRD và PPT – phần của Người 1 (Hân)

Cách dùng: mở file PRD/PPT gốc, thay đúng đoạn tương ứng bằng nội dung dưới đây. Mục A là sửa PRD, mục B là bảng nghiệm thu AC08–AC17, mục C là 10 câu hỏi–đáp, mục D là nội dung slide.

## A. Các chỗ phải sửa trong PRD để khớp mã nguồn

| Chỗ trong PRD | Đang ghi | Sửa thành |
|---|---|---|
| Mô tả sản phẩm, Key Features F04, phần dữ liệu POI | "15 địa điểm tham quan thuộc 5 cụm di tích" | "11 điểm tham quan (POI) theo danh sách phẳng, không chia cụm" |
| Tiêu đề "Cấu trúc 15 POI thuộc 5 cụm tham quan" | như trên | "Danh sách 11 POI" (P00–P10) |
| Data Schema: collection `zones` | có | **Xóa** collection `zones` (bảng dưới thay thế) |
| FAQ "Vì sao không tự dịch hay tạo giọng đọc bằng AI?" | "ngoài phạm vi MVP; audio do Admin tải lên" | Mã nguồn **đang dùng gTTS** để tạo MP3 từ bản dịch do con người viết. Sửa thành: "Bản dịch do nhóm biên soạn, không dịch tự động. Giọng đọc MP3 được tạo bằng gTTS từ văn bản đó." |
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

Cột "Kết quả" chỉ ghi **ĐẠT** khi đã thấy tận mắt. Mình điền sẵn những dòng có ảnh chụp màn hình bạn gửi ngày 3/11; các dòng còn lại là **CHƯA KIỂM** cho tới khi bạn làm theo cột "Cách thử". Nếu mã AC trong PRD nhóm bạn khác, đổi số cho khớp (PRD gán KL03 → AC08–AC12, KL04 → AC16–AC17, KL05 → AC14, KL07 → AC12 và AC15).

| Mã | Tiêu chí | Cách thử (mở http://localhost) | Kết quả |
|---|---|---|---|
| AC08 | Mở app lần đầu, ngôn ngữ mặc định là tiếng Việt | Mở cửa sổ ẩn danh, vào trang, xem giao diện | CHƯA KIỂM |
| AC09 | Ô chọn ngôn ngữ hiện đúng 3 ngôn ngữ lấy từ `/api/languages` | Bấm ô chọn ngôn ngữ | ĐẠT (ảnh chụp 3/11) |
| AC10 | Chọn English thì giao diện, tên và mô tả POI chuyển sang English | Chọn English, xem thanh trạng thái và danh sách POI | ĐẠT (ảnh chụp 3/11) |
| AC11 | Thiếu bản dịch thì hiện "Nội dung đang cập nhật" | Ở trang admin-content, xóa bản dịch en của một POI, mở POI đó ở English | CHƯA KIỂM |
| AC12 | Thiếu audio thì vô hiệu hóa nút phát, hiện "Chưa có audio cho ngôn ngữ này", không phát ngôn ngữ khác | Đổi tên tạm một file MP3 (`mv data/audio/zh/P00.mp3 data/audio/zh/P00.bak`), chọn tiếng Trung, mở P00; sau đó đổi tên lại | ĐẠT (ảnh chụp 3/11) |
| AC13 | Đổi ngôn ngữ không tải lại danh sách POI, không mất phiên | DevTools > Network, đổi ngôn ngữ, xem không có yêu cầu `/api/pois` mới | CHƯA KIỂM |
| AC14 | Nhiều vùng Geofence chồng nhau thì chọn POI gần nhất | Dùng nút mô phỏng vị trí giữa hai POI gần nhau | CHƯA KIỂM |
| AC15 | Từ chối quyền GPS vẫn xem bản đồ và nghe thủ công | Chặn quyền vị trí cho trang, bấm chọn POI và nút phát | CHƯA KIỂM |
| AC16 | Vào bán kính 15 m thì audio tự phát một lần | Dùng mô phỏng vị trí trong bán kính một POI | CHƯA KIỂM |
| AC17 | Bấm Pause thì không tự phát lại khi vẫn đứng trong vùng | Sau AC16, bấm Pause, đợi 10 giây | CHƯA KIỂM |

Kiểm thử tự động (thư mục `tests/`): 23 test đạt, gồm quy tắc bán kính 10–25 m, trạng thái POI, tọa độ, bản dịch và dữ liệu mẫu (11 POI, 3 ngôn ngữ, khóa giao diện đồng nhất). Lệnh: `python -m unittest discover tests -v`. Trang `admin-content.html` và các API quản lý POI đã được chạy thử với dữ liệu giả lập; cần chạy lại trên hệ thống Docker thật bằng `./tests/smoke_api.sh`.

Chưa xác minh: tọa độ 11 POI chưa đối chiếu hết ngoài thực địa (`coordinate_status` vẫn là `pending_field_verification`). Ghi đúng như vậy trong báo cáo, không ghi "đã xác minh".

## C. 10 câu hỏi–đáp để chuẩn bị bảo vệ

1. **Vì sao chỉ có 11 POI, không phải 15 POI thuộc 5 cụm như PRD cũ?** Nhóm thu gọn theo dữ liệu thực tế có đủ nội dung và audio cho 3 ngôn ngữ. Danh sách phẳng đơn giản hơn cho khách và cho admin; PRD đã được sửa khớp.
2. **Thêm tiếng Hàn thì làm gì?** Thêm một bản ghi vào `languages.json` (mã `ko`, `tts_locale`, các chuỗi giao diện), thêm `translations.ko` cho POI và nội dung thuyết minh, chạy lại seed. Không sửa code vì giao diện và backend xử lý theo mã ngôn ngữ.
3. **Thiếu bản dịch hoặc audio thì sao?** Không tự chuyển sang ngôn ngữ khác. API trả `content_available` và `audio_available`; giao diện hiện thông báo và vô hiệu hóa nút phát.
4. **Vì sao bán kính mặc định 15 m, và đổi được không?** 15 m đủ để bắt vị trí GPS điện thoại ngoài trời mà không kích hoạt nhầm POI bên cạnh. Admin chỉnh được trong khoảng 10–25 m; API từ chối giá trị ngoài khoảng. Con số sẽ được hiệu chỉnh sau pilot.
5. **Geofence tính ở đâu và vì sao?** Tính trên điện thoại bằng công thức Haversine (một hàm duy nhất trong `main.js`), không phụ thuộc đường truyền và phản hồi ngay khi vào vùng. Server chỉ nhận thống kê.
6. **DRAFT, PUBLISHED, HIDDEN khác nhau thế nào?** POI mới luôn là DRAFT. Chỉ PUBLISHED được gửi cho khách. HIDDEN là POI bị gỡ khỏi trang khách nhưng vẫn giữ dữ liệu, có thể xuất bản lại.
7. **Audio tạo bằng cách nào, vì sao không đưa MP3 vào Git?** Văn bản do nhóm biên soạn; MP3 sinh bằng gTTS (`generate_33_audio.py` hoặc tự động khi admin lưu thuyết minh). File MP3 nặng nên bị chặn trong `.gitignore` và được cấp riêng khi triển khai.
8. **Tọa độ lấy từ đâu, đã chính xác chưa?** Lấy từ Google Maps và đối chiếu ảnh vệ tinh; đánh dấu `pending_field_verification` cho tới khi nhóm đo thực địa. Đây là hạn chế đã biết.
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
- 23 test tự động đạt; kiểm tay AC09, AC10, AC12 đạt; các AC còn lại ghi đúng trạng thái trong bảng
- Hạn chế: tọa độ chưa đo thực địa; bảo vệ API ghi phụ thuộc phần xác thực của Người 2
