import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient

MONGO_URL = os.getenv("MONGO_URL", "mongodb://localhost:27017")

MUSEUMS_DATA = [   {   'artifacts': [   {   'artifact_id': 'art_01_01',
                             'description_vi': 'Trống đồng cổ thuộc văn hóa Đông Sơn (thế kỷ 3-2 TCN), tượng trưng cho '
                                               'kỹ thuật đúc đồng đỉnh cao và đời sống văn hóa, tín ngưỡng tâm linh '
                                               'của người Việt cổ.',
                             'image_url': 'assets/images/artifacts/art_01_01_trong_dong_dong_son.jpg',
                             'name_vi': 'Trống đồng Đông Sơn',
                             'qr_code': 'QR_ART_01_01'},
                         {   'artifact_id': 'art_01_02',
                             'description_vi': 'Bảo vật Quốc gia thuộc nghệ thuật Champa (thế kỷ 9-10), đúc bằng đồng '
                                               'tinh xảo, thể hiện phong cách Phật giáo Đồng Dương tiêu biểu.',
                             'image_url': 'assets/images/artifacts/art_01_02_tuong_phat_dong_duong.jpg',
                             'name_vi': 'Tượng Phật Đồng Dương',
                             'qr_code': 'QR_ART_01_02'},
                         {   'artifact_id': 'art_01_03',
                             'description_vi': 'Bảo vật Quốc gia nghệ thuật Champa thế kỷ 10, chế tác từ đá sa thạch '
                                               'miêu tả vẻ đẹp thanh thoát và uy nghiêm của nữ thần Devi.',
                             'image_url': 'assets/images/artifacts/art_01_03_tuong_nu_than_devi.jpg',
                             'name_vi': 'Tượng Nữ Thần Devi (Hương Quế)',
                             'qr_code': 'QR_ART_01_03'},
                         {   'artifact_id': 'art_01_04',
                             'description_vi': 'Bảo vật Quốc gia thuộc văn hóa Óc Eo thế kỷ 6-7, tạc từ gỗ duối nguyên '
                                               'khối còn giữ nét điêu khắc uyển chuyển, thanh tao.',
                             'image_url': 'assets/images/artifacts/art_01_04_tuong_phat_son_tho.jpg',
                             'name_vi': 'Tượng Phật Sơn Thọ (Trà Vinh)',
                             'qr_code': 'QR_ART_01_04'},
                         {   'artifact_id': 'art_01_05',
                             'description_vi': 'Bảo vật Quốc gia nghệ thuật Champa thế kỷ 8-9, đúc bằng đồng thể hiện '
                                               'hình tượng Quan Thế Âm Bồ Tát uy nghiêm.',
                             'image_url': 'assets/images/artifacts/art_01_05_tuong_avalokitesvara_hoai_nhon.jpg',
                             'name_vi': 'Tượng Avalokitesvara Hoài Nhơn',
                             'qr_code': 'QR_ART_01_05'},
                         {   'artifact_id': 'art_01_06',
                             'description_vi': 'Bảo vật Quốc gia văn hóa Óc Eo thế kỷ 7, tượng đá sa thạch thể hiện nữ '
                                               'thần Durga 4 tay uy quyền trong tín ngưỡng Ấn Độ giáo.',
                             'image_url': 'assets/images/artifacts/art_01_06_tuong_nu_than_durga.jpg',
                             'name_vi': 'Tượng Nữ Thần Durga',
                             'qr_code': 'QR_ART_01_06'},
                         {   'artifact_id': 'art_01_07',
                             'description_vi': 'Bảo vật Quốc gia văn hóa Óc Eo (thế kỷ 4-6), tượng Phật đứng làm bằng '
                                               'gỗ sao nguyên khối tiêu biểu cho nghệ thuật Óc Eo sớm.',
                             'image_url': 'assets/images/artifacts/art_01_07_tuong_phat_binh_hoa.jpg',
                             'name_vi': 'Tượng Phật Bình Hòa',
                             'qr_code': 'QR_ART_01_07'},
                         {   'artifact_id': 'art_01_08',
                             'description_vi': 'Bảo vật Quốc gia thuộc văn hóa Óc Eo thế kỷ 5-7, tác phẩm điêu khắc đá '
                                               'thể hiện thần bảo hộ Vishnu với đường nét hài hòa.',
                             'image_url': 'assets/images/artifacts/art_01_08_tuong_than_vishnu.jpg',
                             'name_vi': 'Tượng Thần Vishnu',
                             'qr_code': 'QR_ART_01_08'},
                         {   'artifact_id': 'art_01_09',
                             'description_vi': 'Bảo vật Quốc gia nghệ thuật Champa thế kỷ 9-10, pho tượng đồng Quan '
                                               'Thế Âm Bồ Tát đạt trình độ tạo hình xuất sắc.',
                             'image_url': 'assets/images/artifacts/art_01_09_tuong_avalokitesvara_dai_huu.jpg',
                             'name_vi': 'Tượng Avalokitesvara Đại Hữu',
                             'qr_code': 'QR_ART_01_09'},
                         {   'artifact_id': 'art_01_10',
                             'description_vi': 'Cổ vật ấn đồng triều Nguyễn đúc năm 1833, được phong tặng cho các đại '
                                               'thần, tướng lĩnh có công thời vua Minh Mạng.',
                             'image_url': 'assets/images/artifacts/art_01_10_an_luong_tai_hau.jpg',
                             'name_vi': 'Ấn Lương Tài Hầu Chi Ấn',
                             'qr_code': 'QR_ART_01_10'}],
        'description_vi': 'Bảo tàng Lịch sử Thành phố Hồ Chí Minh là một trong những bảo tàng lâu đời nhất phương Nam, '
                          'được thành lập ngày 23/8/1929 với tên gọi ban đầu Musée Blanchard de la Brosse. Tòa nhà do '
                          'kiến trúc sư người Pháp Auguste Delaval thiết kế theo phong cách Đông Dương (Indochine) độc '
                          'đáo, kết hợp hài hòa giữa cấu trúc tân cổ điển phương Tây và tháp bát giác lợp ngói ống Á '
                          'Đông trang trí rồng phượng tinh xảo.\n'
                          '\n'
                          'Nơi đây hiện lưu giữ và trưng bày hơn 40.000 hiện vật, tư liệu vô giá phản ánh lịch sử, văn '
                          'hóa Việt Nam từ thời Tiền sử (khoảng 500.000 năm trước) đến năm 1945, cùng các bộ sưu tập '
                          'văn hóa phi bản địa Á Đông. Hệ thống trưng bày gồm 2 phần chính:\n'
                          '1. Tiến trình Lịch sử Việt Nam: Qua các thời kỳ Tiền sử, Văn hóa Đông Sơn, Sa Huỳnh, Óc Eo, '
                          'các triều đại Ngô, Đinh, Tiền Lê, Lý, Trần, Lê, Tây Sơn đến triều Nguyễn.\n'
                          '2. Chuyên đề Văn hóa Nam Bộ & Châu Á: Điêu khắc đá Champa, Nghệ thuật Phật giáo & Ấn Độ '
                          'giáo, Gốm sứ cổ châu Á và bộ sưu tập cổ vật của các quốc gia láng giềng.\n'
                          '\n'
                          'Bảo tàng vinh dự sở hữu 12 Bảo vật Quốc gia độc bản, bao gồm các pho tượng Phật, tượng thần '
                          'sa thạch Champa, tượng gỗ Óc Eo và cổ vật quý hiếm bậc nhất Việt Nam.',
        'history_and_architecture': '- Thành lập: Ngày 23 tháng 8 năm 1929.\n'
                                    '- Kiến trúc: Phong cách Đông Dương (Indochine) với tháp bát giác trung tâm, mái '
                                    'lợp ngói âm dương, trang trí họa tiết rồng phượng hoa lá thuần Việt.\n'
                                    '- Địa chỉ: Số 2 Nguyễn Bỉnh Khiêm, Phường Bến Nghé, Quận 1, TP.HCM (trong khuôn '
                                    'viên Thảo Cầm Viên).',
        'id': 'museum_01',
        'image_url': 'assets/images/museums/museum_01_bao_tang_my_thuat.jpg',
        'location': {'lat': 10.7878, 'lng': 106.7051},
        'name': 'Bảo tàng Lịch sử TP.HCM',
        'qr_code': 'QR_MUSEUM_01',
        'trigger_radius_meters': 30},
    {   'artifacts': [   {   'artifact_id': 'art_02_01',
                             'description_vi': 'Bảo vật Quốc gia kiệt tác của danh họa Nguyễn Gia Trí, sáng tác trong '
                                               '20 năm (1939-1954) thể hiện không gian lễ hội mùa xuân rực rỡ của 3 '
                                               'miền.',
                             'image_url': 'assets/images/artifacts/art_02_01_vuon_xuan_trung_nam_bac.jpg',
                             'name_vi': "Tranh sơn mài 'Vườn Xuân Trung Nam Bắc'",
                             'qr_code': 'QR_ART_02_01'},
                         {   'artifact_id': 'art_02_02',
                             'description_vi': 'Bảo vật Quốc gia do danh họa Nguyễn Sáng thể hiện năm 1978, tái hiện '
                                               'khí thế phong trào đấu tranh kiên cường của thanh niên Sài Gòn.',
                             'image_url': 'assets/images/artifacts/art_02_02_thanh_nien_thanh_dong.jpg',
                             'name_vi': "Tranh sơn mài 'Thanh niên Thành đồng'",
                             'qr_code': 'QR_ART_02_02'},
                         {   'artifact_id': 'art_02_03',
                             'description_vi': 'Tác phẩm tranh lụa dịu dàng, trong trẻo của nữ danh họa khóa 3 Trường '
                                               'Cao đẳng Mỹ thuật Đông Dương.',
                             'image_url': 'assets/images/artifacts/art_02_03_me_con_le_thi_luu.jpg',
                             'name_vi': "Tranh lụa 'Mẹ con' của Lê Thị Lựu",
                             'qr_code': 'QR_ART_02_03'},
                         {   'artifact_id': 'art_02_04',
                             'description_vi': 'Tác phẩm điêu khắc thạch cao giàu cảm xúc của nhà điêu khắc Diệp Minh '
                                               'Châu tôn vinh tinh thần yêu nước.',
                             'image_url': 'assets/images/artifacts/art_02_04_to_quoc_goi.jpg',
                             'name_vi': "Tượng điêu khắc 'Tổ quốc gọi'",
                             'qr_code': 'QR_ART_02_04'},
                         {   'artifact_id': 'art_02_05',
                             'description_vi': 'Hàng trăm bức ký họa trực tiếp tại chiến trường của các họa sĩ chiến '
                                               'sĩ, ghi lại cuộc sống và hình ảnh lịch sử.',
                             'image_url': 'assets/images/artifacts/art_02_05_ky_hoa_khang_chien.jpg',
                             'name_vi': 'Bộ sưu tập Ký họa Kháng chiến miền Nam',
                             'qr_code': 'QR_ART_02_05'},
                         {   'artifact_id': 'art_02_06',
                             'description_vi': 'Tác phẩm gốm Mỹ thuật Biên Hòa đầu thế kỷ 20 với sắc men xanh đồng trứ '
                                               'danh thế giới.',
                             'image_url': 'assets/images/artifacts/art_02_06_gom_bien_hoa.jpg',
                             'name_vi': 'Tượng gốm mỹ thuật Biên Hòa cổ',
                             'qr_code': 'QR_ART_02_06'},
                         {   'artifact_id': 'art_02_07',
                             'description_vi': 'Pho tượng gỗ gõ đỏ thế kỷ 18 chạm khắc công phu, thể hiện đỉnh cao mỹ '
                                               'thuật chạm khắc gỗ cổ truyền Nam Bộ.',
                             'image_url': 'assets/images/artifacts/art_02_07_tuong_go_quan_am.jpg',
                             'name_vi': "Tượng gỗ cổ 'Phật Quan Âm Bồ Tát'",
                             'qr_code': 'QR_ART_02_07'},
                         {   'artifact_id': 'art_02_08',
                             'description_vi': 'Bức tranh kết hợp kỹ thuật in thủ ấn họa độc đáo khắc họa nhịp sống đô '
                                               'thị phương Nam xưa.',
                             'image_url': 'assets/images/artifacts/art_02_08_pho_co_tu_duyen.jpg',
                             'name_vi': "Tranh thủ ấn họa 'Phố cổ Sài Gòn' - Tú Duyên",
                             'qr_code': 'QR_ART_02_08'},
                         {   'artifact_id': 'art_02_09',
                             'description_vi': 'Bộ đồ gốm gia dụng và trang trí hoa văn rồng phượng sinh động của lò '
                                               'gốm Lái Thiêu thế kỷ 19.',
                             'image_url': 'assets/images/artifacts/art_02_09_gom_lai_thieu.jpg',
                             'name_vi': 'Bộ gốm cổ Lái Thiêu hoa văn chạm nổi',
                             'qr_code': 'QR_ART_02_09'},
                         {   'artifact_id': 'art_02_10',
                             'description_vi': 'Tượng mộc khối gỗ tự nhiên thể hiện tình mẫu tử ấm áp qua nét đục hiện '
                                               'đại và phóng khoáng.',
                             'image_url': 'assets/images/artifacts/art_02_10_dieu_khac_go_me_con.jpg',
                             'name_vi': "Tác phẩm điêu khắc gỗ 'Mẹ con'",
                             'qr_code': 'QR_ART_02_10'}],
        'description_vi': 'Bảo tàng Mỹ thuật TP.HCM tọa lạc tại số 97A Phó Đức Chính, Quận 1, trong một tòa dinh thự '
                          'tráng lệ mang phong cách Art Deco kết hợp hài hòa giữa kiến trúc phương Tây và Á Đông. Công '
                          'trình xây dựng từ năm 1929 đến 1934, vốn là tư dinh của gia tộc Hứa Bổn Hòa (thường gọi là '
                          'Chú Hỏa) – một trong những thương nhân giàu có và có ảnh hưởng nhất Sài Gòn xưa. Tòa nhà '
                          'nổi bật với khung cửa kính màu phong cách Pháp, thang máy gỗ cổ điển nguyên bản và khuôn '
                          'viên sân trong lãng mạn.\n'
                          '\n'
                          'Bảo tàng chính thức thành lập năm 1987 và mở cửa đón khách từ năm 1989. Hiện nay, bảo tàng '
                          'lưu giữ gần 4.000 tác phẩm mỹ thuật quý giá, bao gồm hội họa, điêu khắc, cổ vật và đồ thủ '
                          'công mỹ nghệ qua các thời kỳ lịch sử.\n'
                          '\n'
                          'Nơi đây trưng bày nhiều tác phẩm đỉnh cao của mỹ thuật Việt Nam thế kỷ 20, đặc biệt là các '
                          'kiệt tác của thế hệ họa sĩ Trường Cao đẳng Mỹ thuật Đông Dương (Nguyễn Gia Trí, Nguyễn '
                          'Sáng, Lê Thị Lựu, Diệp Minh Châu...). Bảo tàng gồm 3 tòa nhà trưng bày theo chuyên đề: Mỹ '
                          'thuật hiện đại, Mỹ thuật truyền thống cổ truyền và Triển lãm chuyên đề ngắn hạn.',
        'history_and_architecture': '- Khởi công: 1929 - Hoàn thành: 1934 (Tư dinh Chú Hỏa).\n'
                                    '- Kiến trúc: Art Deco kết hợp họa tiết Á Đông (mái lợp ngói âm dương, ô văng chạm '
                                    'khắc, kính màu nghệ thuật châu Âu).\n'
                                    '- Địa chỉ: 97A Phó Đức Chính, Phường Nguyễn Thái Bình, Quận 1, TP.HCM.',
        'id': 'museum_02',
        'image_url': 'assets/images/museums/museum_02_bao_tang_my_thuat.jpg',
        'location': {'lat': 10.7698, 'lng': 106.6989},
        'name': 'Bảo tàng Mỹ thuật TP.HCM',
        'qr_code': 'QR_MUSEUM_02',
        'trigger_radius_meters': 30},
    {   'artifacts': [   {   'artifact_id': 'art_03_01',
                             'description_vi': 'Bản đồ quy hoạch đô thị sơ khai miêu tả chi tiết thành Bát Quái, kênh '
                                               'rạch và các xóm làng Sài Gòn - Gia Định cuối thế kỷ 18.',
                             'image_url': 'assets/images/artifacts/art_03_01_ban_do_tran_van_hoc_1799.jpg',
                             'name_vi': 'Bản đồ Sài Gòn 1799 của Trần Văn Học',
                             'qr_code': 'QR_ART_03_01'},
                         {   'artifact_id': 'art_03_02',
                             'description_vi': 'Hiện vật phương tiện giao thông công cộng bằng gỗ và kim loại phục vụ '
                                               'người dân Sài Gòn giữa thế kỷ 20.',
                             'image_url': 'assets/images/artifacts/art_03_02_xe_buyt_do_thanh.jpg',
                             'name_vi': 'Chiếc xe buýt cổ Đô Thành thập niên 1950',
                             'qr_code': 'QR_ART_03_02'},
                         {   'artifact_id': 'art_03_03',
                             'description_vi': 'Tập hợp đồng tiền kim loại, tiền giấy phát hành qua các thời kỳ phong '
                                               'kiến, Pháp thuộc và thương cảng Chợ Lớn.',
                             'image_url': 'assets/images/artifacts/art_03_03_bo_tien_co.jpg',
                             'name_vi': 'Bộ sưu tập Tiền cổ Sài Gòn - Gia Định',
                             'qr_code': 'QR_ART_03_03'},
                         {   'artifact_id': 'art_03_04',
                             'description_vi': 'Cổ vật ấn đồng triều Nguyễn đúc chạm tinh xảo dùng trong hành chính và '
                                               'thờ tự tại vùng đất phương Nam.',
                             'image_url': 'assets/images/artifacts/art_03_04_kiep_bac_chi_an.jpg',
                             'name_vi': "Ấn triều Nguyễn 'Kiếp Bạc Chi Ấn'",
                             'qr_code': 'QR_ART_03_04'},
                         {   'artifact_id': 'art_03_05',
                             'description_vi': 'Công cụ sản xuất tiểu thủ công nghiệp gắn liền với sự phát triển của '
                                               'làng nghề may mặc Sài Gòn xưa.',
                             'image_url': 'assets/images/artifacts/art_03_05_may_may_singer.jpg',
                             'name_vi': 'Chiếc máy may Singer đầu thế kỷ 20',
                             'qr_code': 'QR_ART_03_05'},
                         {   'artifact_id': 'art_03_06',
                             'description_vi': 'Bộ áo dài cưới thêu chỉ vàng tinh xảo phản ánh đời sống văn hóa đặc '
                                               'sắc của cộng đồng người Hoa tại Chợ Lớn.',
                             'image_url': 'assets/images/artifacts/art_03_06_trang_phuc_cuoi_cho_lon.jpg',
                             'name_vi': 'Trang phục cưới cổ của người Hoa Chợ Lớn',
                             'qr_code': 'QR_ART_03_06'},
                         {   'artifact_id': 'art_03_07',
                             'description_vi': 'Tái hiện căn hầm ngầm lưu trữ thiết bị lịch sử giữa lòng nội thành '
                                               'thời kỳ trước năm 1975.',
                             'image_url': 'assets/images/artifacts/art_03_07_ham_biet_dong.jpg',
                             'name_vi': 'Mô hình Hầm bí mật Biệt động Sài Gòn',
                             'qr_code': 'QR_ART_03_07'},
                         {   'artifact_id': 'art_03_08',
                             'description_vi': 'Các hiện vật bình, vò gốm đất nung thế kỷ 5 khai quật tại TP.HCM chứng '
                                               'minh lịch sử cư trú lâu đời.',
                             'image_url': 'assets/images/artifacts/art_03_08_gom_oc_eo.jpg',
                             'name_vi': 'Bộ gốm nung Óc Eo khảo cổ TP.HCM',
                             'qr_code': 'QR_ART_03_08'},
                         {   'artifact_id': 'art_03_09',
                             'description_vi': 'Biểu tượng nét sống đô thị và thời trang đường phố của thanh niên Sài '
                                               'Gòn những năm 1960.',
                             'image_url': 'assets/images/artifacts/art_03_09_xe_vespa_co.jpg',
                             'name_vi': 'Chiếc xe máy Vespa cổ thập niên 1960',
                             'qr_code': 'QR_ART_03_09'},
                         {   'artifact_id': 'art_03_10',
                             'description_vi': 'Máy in truyền đơn lịch sử của học sinh sinh viên Sài Gòn trong phong '
                                               'trào đô thị.',
                             'image_url': 'assets/images/artifacts/art_03_10_may_danh_chu_sinh_vien.jpg',
                             'name_vi': 'Máy đánh chữ phong trào Học sinh Sinh viên',
                             'qr_code': 'QR_ART_03_10'}],
        'description_vi': 'Bảo tàng Thành phố Hồ Chí Minh tọa lạc tại số 65 Lý Tự Trọng, Quận 1, trong tòa dinh thự cổ '
                          'kính xây dựng từ năm 1885 đến 1890 do kiến trúc sư người Pháp Alfred Foulhoux thiết kế. Tòa '
                          'nhà mang đậm phong cách kiến trúc Tân cổ điển phương Tây pha trộn đường nét Hy Lạp - La Mã, '
                          'từng được gọi là Dinh Gia Long. Nơi đây từng là Dinh Thống đốc Nam Kỳ, Dinh Khâm mạng và '
                          'Dinh Quốc trưởng trước khi trở thành không gian bảo tàng văn hóa - lịch sử.\n'
                          '\n'
                          'Bảo tàng hiện đang quản lý hệ thống 9 phòng trưng bày chuyên đề cố định, tái hiện sinh động '
                          'tiến trình 300 năm hình thành và phát triển của vùng đất Sài Gòn - Gia Định - TP.HCM:\n'
                          '1. Thiên nhiên & Địa chất Nam Bộ.\n'
                          '2. Quy hoạch đô thị & Địa chí Sài Gòn qua các thời kỳ.\n'
                          '3. Thương cảng, Thương mại & Dịch vụ.\n'
                          '4. Công nghiệp & Tiểu thủ công nghiệp truyền thống.\n'
                          '5. Văn hóa dân gian & Đời sống đa dạng cộng đồng Việt - Hoa - Khmer - Chăm.\n'
                          '6. Đấu tranh cách mạng (1930 - 1954) & Kháng chiến chống Mỹ (1954 - 1975).\n'
                          '7. Kỷ vật kháng chiến & Phong trào đô thị.\n'
                          '8. Tiền tệ Việt Nam qua các thời kỳ.\n'
                          '9. Đô thị TP.HCM hội nhập và phát triển.\n'
                          '\n'
                          'Bảo tàng còn lưu giữ hệ thống đường hầm bí mật kiên cố dưới lòng đất Dinh Gia Long, từng là '
                          'trung tâm chỉ huy đặc biệt thời kỳ trước 1975.',
        'history_and_architecture': '- Khởi công: 1885 - Hoàn thành: 1890 (Dinh Gia Long cũ).\n'
                                    '- Kiến trúc: Tân cổ điển Hy Lạp - La Mã kết hợp đường nét phương Tây lịch lãm.\n'
                                    '- Địa chỉ: 65 Lý Tự Trọng, Phường Bến Nghé, Quận 1, TP.HCM.',
        'id': 'museum_03',
        'image_url': 'assets/images/museums/museum_03_bao_tang_tp_hcm.jpg',
        'location': {'lat': 10.776, 'lng': 106.6995},
        'name': 'Bảo tàng Thành phố Hồ Chí Minh',
        'qr_code': 'QR_MUSEUM_03',
        'trigger_radius_meters': 30},
    {   'artifacts': [   {   'artifact_id': 'art_04_01',
                             'description_vi': 'Bảo vật Quốc gia, chiếc xe tăng húc văng cổng chính Dinh Độc Lập lúc '
                                               '10h45 ngày 30/4/1975, mở đầu cho giờ phút thống nhất đất nước.',
                             'image_url': 'assets/images/artifacts/art_04_01_xe_tang_390.jpg',
                             'name_vi': 'Xe tăng 390 (T-59)',
                             'qr_code': 'QR_ART_04_01'},
                         {   'artifact_id': 'art_04_02',
                             'description_vi': 'Bảo vật Quốc gia, chiếc xe tăng tiên phong húc vào cổng phụ Dinh Độc '
                                               'Lập trưa ngày 30/4/1975.',
                             'image_url': 'assets/images/artifacts/art_04_02_xe_tang_843.jpg',
                             'name_vi': 'Xe tăng 843 (T-54)',
                             'qr_code': 'QR_ART_04_02'},
                         {   'artifact_id': 'art_04_03',
                             'description_vi': 'Chiếc máy bay chiến đấu F-5E gắn liền với sự kiện lịch sử sáng ngày '
                                               '8/4/1975 tại Dinh Độc Lập.',
                             'image_url': 'assets/images/artifacts/art_04_03_may_bay_f5e.jpg',
                             'name_vi': 'Máy bay F-5E trưng bày lịch sử',
                             'qr_code': 'QR_ART_04_03'},
                         {   'artifact_id': 'art_04_04',
                             'description_vi': 'Đặt tại Phòng Trình quốc thư với thiết kế gỗ quý sang trọng, nơi diễn '
                                               'ra các cuộc họp nội các chính quyền cũ.',
                             'image_url': 'assets/images/artifacts/art_04_04_ban_tong_thong.jpg',
                             'name_vi': 'Bàn làm việc của Tổng thống',
                             'qr_code': 'QR_ART_04_04'},
                         {   'artifact_id': 'art_04_05',
                             'description_vi': 'Chiếc trực thăng đậu trên nóc Dinh tại vị trí ghi dấu sự kiện lịch sử '
                                               'năm 1975.',
                             'image_url': 'assets/images/artifacts/art_04_05_truc_thang_uh1.jpg',
                             'name_vi': 'Trực thăng UH-1 trên sân thượng',
                             'qr_code': 'QR_ART_04_05'},
                         {   'artifact_id': 'art_04_06',
                             'description_vi': 'Căn hầm ngầm bê tông cốt thép kiên cố trang bị hệ thống máy vô tuyến, '
                                               'đài đĩa truyền tin hiện đại.',
                             'image_url': 'assets/images/artifacts/art_04_06_ham_thong_tin.jpg',
                             'name_vi': 'Trung tâm Thông tin liên lạc ngầm',
                             'qr_code': 'QR_ART_04_06'},
                         {   'artifact_id': 'art_04_07',
                             'description_vi': 'Bức tranh hoành tráng ghép từ 40 tấm sơn mài tại Phòng Khánh tiết miêu '
                                               'tả chiến công hiển hách chống ngoại xâm.',
                             'image_url': 'assets/images/artifacts/art_04_07_tranh_binh_ngo_dai_cao.jpg',
                             'name_vi': "Bức tranh sơn mài 'Bình Ngô Đại Cáo'",
                             'qr_code': 'QR_ART_04_07'},
                         {   'artifact_id': 'art_04_08',
                             'description_vi': 'Chiếc xe ô tô hạng sang nguyên thủ dùng để đưa đón di chuyển trong '
                                               'thành phố.',
                             'image_url': 'assets/images/artifacts/art_04_08_xe_mercedes_200.jpg',
                             'name_vi': 'Xe Mercedes-Benz 200 Tổng thống',
                             'qr_code': 'QR_ART_04_08'},
                         {   'artifact_id': 'art_04_09',
                             'description_vi': 'Bức thảm thêu tay thủ công lớn đặt tại trung tâm lối vào Dinh, thể '
                                               'hiện uy quyền và nghệ thuật truyền thống.',
                             'image_url': 'assets/images/artifacts/art_04_09_tham_rong.jpg',
                             'name_vi': 'Thảm thêu Rồng tại Đại sảnh',
                             'qr_code': 'QR_ART_04_09'},
                         {   'artifact_id': 'art_04_10',
                             'description_vi': 'Phương tiện cơ giới dã chiến phục vụ công tác tuần tra và đưa đón di '
                                               'chuyển.',
                             'image_url': 'assets/images/artifacts/art_04_10_xe_jeep_willys.jpg',
                             'name_vi': 'Xe Jeep chỉ hữu Willys M151A2',
                             'qr_code': 'QR_ART_04_10'}],
        'description_vi': 'Dinh Độc Lập (tên gọi chính thức Di tích Quốc gia đặc biệt Dinh Độc Lập, còn gọi là Hội '
                          'trường Thống Nhất) nằm tại số 135 Nam Kỳ Khởi Nghĩa, Quận 1. Công trình được xây dựng trên '
                          'diện tích 12 hecta từ năm 1962 đến 1966 theo đồ án thiết kế của Kiến trúc sư Ngô Viết Thụ – '
                          'người Việt Nam đầu tiên đoạt Giải thưởng Khôi nguyên La Mã (Grand Prix de Rome).\n'
                          '\n'
                          'Tòa nhà là kiệt tác kiến trúc hiện đại kết hợp triết lý triết học phương Đông sâu sắc:\n'
                          '- Mặt bằng tổng thể tạo thành hình chữ CÁT (吉 - may mắn, lành tốt).\n'
                          '- Tâm Dinh là Phòng Trình quốc thư, Lầu 2 là chữ HƯNG (兴 - thịnh vượng).\n'
                          '- Đường nét hàng cột phía trước gợi hình ảnh các đốt trúc thanh cao.\n'
                          '\n'
                          'Dinh Độc Lập có diện tích sử dụng lên tới 20.000m2 với hơn 100 phòng trưng bày sang trọng: '
                          'Phòng Khánh tiết, Phòng Trình quốc thư, Phòng họp Nội các, Phòng Đại yến, Lầu Bát giác, '
                          'cùng hệ thống Hầm chỉ huy chiến tranh ngầm bê tông cốt thép kiên cố dưới lòng đất.\n'
                          '\n'
                          'Sáng ngày 30/4/1975, hai chiếc xe tăng mang số hiệu 390 và 843 của Quân giải phóng đã húc '
                          'văng cổng chính Dinh Độc Lập, đánh dấu giờ phút lịch sử kết thúc chiến tranh, giải phóng '
                          'miền Nam và thống nhất đất nước.',
        'history_and_architecture': '- Khởi công: 1/7/1962 - Khánh thành: 31/10/1966.\n'
                                    '- Kiến trúc sư: Ngô Viết Thụ (Giải thưởng Khôi nguyên La Mã).\n'
                                    '- Xếp hạng: Di tích Quốc gia đặc biệt năm 2009.\n'
                                    '- Địa chỉ: 135 Nam Kỳ Khởi Nghĩa, Phường Bến Thành, Quận 1, TP.HCM.',
        'id': 'museum_04',
        'image_url': 'assets/images/museums/museum_04_dinh_doc_lap.jpg',
        'location': {'lat': 10.777, 'lng': 106.6953},
        'name': 'Dinh Độc Lập',
        'qr_code': 'QR_MUSEUM_04',
        'trigger_radius_meters': 30},
    {   'artifacts': [   {   'artifact_id': 'art_05_01',
                             'description_vi': 'Hóa thạch động vật thân mềm vỏ xoắn ốc niên đại Kỷ Jura (hàng trăm '
                                               'triệu năm) phát hiện tại vùng núi Tây Nguyên.',
                             'image_url': 'assets/images/artifacts/art_05_01_cuc_da_ammonite.jpg',
                             'name_vi': 'Mẫu hóa thạch Cúc đá (Ammonite)',
                             'qr_code': 'QR_ART_05_01'},
                         {   'artifact_id': 'art_05_02',
                             'description_vi': 'Khối thân cây cổ đại bị silic hóa nguyên vẹn giữ nguyên từng vân gỗ '
                                               'qua hàng triệu năm biến đổi lòng đất.',
                             'image_url': 'assets/images/artifacts/art_05_02_go_hoa_thach.jpg',
                             'name_vi': 'Thân gỗ hóa thạch (Petrified Wood)',
                             'qr_code': 'QR_ART_05_02'},
                         {   'artifact_id': 'art_05_03',
                             'description_vi': 'Hốc tinh thể thạch anh tím tự nhiên lấp lánh nguyên khối khai quật từ '
                                               'các mỏ đá trầm tích Việt Nam.',
                             'image_url': 'assets/images/artifacts/art_05_03_thach_anh_tim.jpg',
                             'name_vi': 'Khối thạch anh tím tự nhiên (Amethyst)',
                             'qr_code': 'QR_ART_05_03'},
                         {   'artifact_id': 'art_05_04',
                             'description_vi': 'Khối tektite màu đen bóng nguồn gốc từ vũ trụ va chạm với Trái Đất rơi '
                                               'xuống Nam Bộ cách đây hàng trăm ngàn năm.',
                             'image_url': 'assets/images/artifacts/art_05_04_thien_thach_tektite.jpg',
                             'name_vi': 'Mẫu đá Thiên thạch Tektite',
                             'qr_code': 'QR_ART_05_04'},
                         {   'artifact_id': 'art_05_05',
                             'description_vi': 'Mẫu quặng nhôm màu đỏ gạch đại diện cho tài nguyên khoáng sản quy mô '
                                               'chiến lược của Tây Nguyên Việt Nam.',
                             'image_url': 'assets/images/artifacts/art_05_05_quang_bauxite.jpg',
                             'name_vi': 'Mẫu quặng Bauxite Tây Nguyên',
                             'qr_code': 'QR_ART_05_05'},
                         {   'artifact_id': 'art_05_06',
                             'description_vi': 'Mẫu đá trầm tích biển chứa tập đoàn san hô hóa thạch chứng minh vùng '
                                               'đất Nam Bộ từng là biển cổ đại.',
                             'image_url': 'assets/images/artifacts/art_05_06_hoa_thach_san_ho.jpg',
                             'name_vi': 'Đá vôi chứa hóa thạch San hô cổ',
                             'qr_code': 'QR_ART_05_06'},
                         {   'artifact_id': 'art_05_07',
                             'description_vi': 'Mẫu quặng thạch anh chứa các vảy vàng tự nhiên phát sáng khai thác tại '
                                               'mỏ vàng Bồng Miêu nổi tiếng.',
                             'image_url': 'assets/images/artifacts/art_05_07_quang_vang_bong_mieu.jpg',
                             'name_vi': 'Mẫu quặng Vàng tự nhiên Bồng Miêu',
                             'qr_code': 'QR_ART_05_07'},
                         {   'artifact_id': 'art_05_08',
                             'description_vi': 'Khoáng vật đồng màu xanh lá cây với các đường vân đồng tâm tuyệt đẹp '
                                               'dùng trong nghiên cứu địa chất.',
                             'image_url': 'assets/images/artifacts/art_05_08_da_malachite.jpg',
                             'name_vi': 'Khoáng vật Malachite (Đá Khổng Tước)',
                             'qr_code': 'QR_ART_05_08'},
                         {   'artifact_id': 'art_05_09',
                             'description_vi': 'Đá mácma xâm nhập có độ bền cao hình thành nên các dãy núi hùng vĩ tại '
                                               'miền Trung Việt Nam.',
                             'image_url': 'assets/images/artifacts/art_05_09_da_granit_hong.jpg',
                             'name_vi': 'Mẫu đá Granit hồng Dãy Trường Sơn',
                             'qr_code': 'QR_ART_05_09'},
                         {   'artifact_id': 'art_05_10',
                             'description_vi': 'Hóa thạch bộ răng loài voi cổ đại Stegodon sinh sống tại Việt Nam vào '
                                               'Kỷ Đệ Tứ (Pleistocene).',
                             'image_url': 'assets/images/artifacts/art_05_10_rang_voi_stegodon.jpg',
                             'name_vi': 'Mẫu hóa thạch Răng Voi cổ đại (Stegodon)',
                             'qr_code': 'QR_ART_05_10'}],
        'description_vi': 'Bảo tàng Địa chất TP.HCM tọa lạc tại số 2 Nguyễn Bỉnh Khiêm, Quận 1 (nằm kế bên Bảo tàng '
                          'Lịch sử), trực thuộc Cục Địa chất Việt Nam. Bảo tàng thành lập năm 1954, kế thừa kho tư '
                          'liệu và hiện vật khảo sát địa chất Đông Dương từ cuối thế kỷ 19.\n'
                          '\n'
                          'Nơi đây lưu giữ và trưng bày hơn 3.000 mẫu vật khoáng vật, đá, hóa thạch và tài nguyên '
                          'khoáng sản vô cùng phong phú, phản ánh lịch sử kiến tạo địa chất hành tinh và thổ nhưỡng '
                          'lãnh thổ Việt Nam qua hàng trăm triệu năm.\n'
                          '\n'
                          'Hệ thống gian trưng bày chia thành các chuyên đề chuyên sâu:\n'
                          '1. Lịch sử Kiến tạo & Địa chất Lãnh thổ Việt Nam: Mẫu đá đại diện cho các kỷ địa chất '
                          '(Precambri, Paleozoi, Mesozoi, Cenozoi).\n'
                          '2. Bộ sưu tập Hóa thạch Cổ sinh vật: Hóa thạch Cúc đá, San hô cổ, Gỗ hóa đá, Răng voi cổ '
                          'đại Stegodon.\n'
                          '3. Khoáng vật & Đá quý: Thạch anh, Malachite, Thiên thạch Tektite ngoài vũ trụ.\n'
                          '4. Tài nguyên Khoáng sản & Bản đồ Địa chất Việt Nam: Quặng Bauxite Tây Nguyên, Quặng Vàng '
                          'Bồng Miêu, Dầu mỏ thô mỏ Bạch Hổ...',
        'history_and_architecture': '- Khai trương: Năm 1954 tại TP.HCM.\n'
                                    '- Cơ quan chủ quản: Cục Địa chất Việt Nam.\n'
                                    '- Địa chỉ: 2 Nguyễn Bỉnh Khiêm, Phường Bến Nghé, Quận 1, TP.HCM.',
        'id': 'museum_05',
        'image_url': 'assets/images/museums/museum_05_bao_tang_dia_chat.jpg',
        'location': {'lat': 10.7865, 'lng': 106.7032},
        'name': 'Bảo tàng Địa chất',
        'qr_code': 'QR_MUSEUM_05',
        'trigger_radius_meters': 30},
    {   'artifacts': [   {   'artifact_id': 'art_06_01',
                             'description_vi': 'Máy bay vận tải hàng không hạng nặng trưng bày tại sân ngoài trời, gắn '
                                               'liền với lịch sử không vận thời chiến.',
                             'image_url': 'assets/images/artifacts/art_06_01_may_bay_c130.jpg',
                             'name_vi': 'Máy bay vận tải C-130 Hercules',
                             'qr_code': 'QR_ART_06_01'},
                         {   'artifact_id': 'art_06_02',
                             'description_vi': 'Xe tăng bọc thép hạng trung trang bị thiết bị thuộc bộ sưu tập cơ giới '
                                               'ngoài trời.',
                             'image_url': 'assets/images/artifacts/art_06_02_xe_tang_m48.jpg',
                             'name_vi': 'Xe tăng M48A3 Patton',
                             'qr_code': 'QR_ART_06_02'},
                         {   'artifact_id': 'art_06_03',
                             'description_vi': 'Khẩu pháo M107 cỡ nòng 175mm tầm xa lịch sử trưng bày tại không gian '
                                               'trưng bày ngoài trời.',
                             'image_url': 'assets/images/artifacts/art_06_03_phao_175mm.jpg',
                             'name_vi': 'Thiết bị pháo tự hành 175mm',
                             'qr_code': 'QR_ART_06_03'},
                         {   'artifact_id': 'art_06_04',
                             'description_vi': 'Phục dựng mô hình trại giam di tích lịch sử Côn Đảo phản ánh ý chí '
                                               'kiên cường của các chiến sĩ.',
                             'image_url': 'assets/images/artifacts/art_06_04_di_tich_con_dao.jpg',
                             'name_vi': 'Mô hình di tích Nhà tù Côn Đảo',
                             'qr_code': 'QR_ART_06_04'},
                         {   'artifact_id': 'art_06_05',
                             'description_vi': 'Hiện vật tư liệu lịch sử đầu thế kỷ 20 trưng bày để nghiên cứu giai '
                                               'đoạn đấu tranh của các nhà yêu nước.',
                             'image_url': 'assets/images/artifacts/art_06_05_tu_lieu_phap_thuoc.jpg',
                             'name_vi': 'Hiện vật tư liệu lịch sử thời Pháp thuộc',
                             'qr_code': 'QR_ART_06_05'},
                         {   'artifact_id': 'art_06_06',
                             'description_vi': 'Tập hợp các bức ảnh tư liệu do 135 phóng viên ảnh quốc tế ghi lại '
                                               'trong thời kỳ chiến tranh Đông Dương.',
                             'image_url': 'assets/images/artifacts/art_06_06_bo_anh_requiem.jpg',
                             'name_vi': "Bộ sưu tập ảnh 'Hồi niệm' (Requiem)",
                             'qr_code': 'QR_ART_06_06'},
                         {   'artifact_id': 'art_06_07',
                             'description_vi': 'Tác phẩm ảnh báo chí lịch sử đoạt giải Pulitzer phản ánh hậu quả chiến '
                                               'tranh năm 1972.',
                             'image_url': 'assets/images/artifacts/art_06_07_anh_tu_lieu_nick_ut.jpg',
                             'name_vi': 'Bức ảnh tư liệu lịch sử của Nick Út',
                             'qr_code': 'QR_ART_06_07'},
                         {   'artifact_id': 'art_06_08',
                             'description_vi': 'Mẫu vỏ khí tài nhiên liệu trưng bày phục vụ công tác nghiên cứu lịch '
                                               'sử quân sự.',
                             'image_url': 'assets/images/artifacts/art_06_08_vo_khi_tai_cbu55.jpg',
                             'name_vi': 'Vỏ mẫu khí tài CBU-55',
                             'qr_code': 'QR_ART_06_08'},
                         {   'artifact_id': 'art_06_09',
                             'description_vi': 'Tàn tích vỏ máy B-52 lưu giữ từ sự kiện lịch sử năm 1972.',
                             'image_url': 'assets/images/artifacts/art_06_09_xac_may_bay_b52.jpg',
                             'name_vi': 'Mảnh xác máy bay B-52 lịch sử',
                             'qr_code': 'QR_ART_06_09'},
                         {   'artifact_id': 'art_06_10',
                             'description_vi': 'Trực thăng vận tải hai cánh quạt hạng nặng dùng trong công tác cơ động '
                                               'và tiếp tế.',
                             'image_url': 'assets/images/artifacts/art_06_10_truc_thang_chinook.jpg',
                             'name_vi': 'Trực thăng CH-47 Chinook',
                             'qr_code': 'QR_ART_06_10'}],
        'description_vi': 'Bảo tàng Chứng tích Chiến tranh tọa lạc tại số 28 Võ Văn Tần, Quận 3. Thành lập ngày '
                          '4/9/1975, bảo tàng hiện là thành viên của Mạng lưới Bảo tàng vì Hòa bình Thế giới (INMP) và '
                          'Hệ thống Bảo tàng Quốc tế UNESCO. Đây là một trong những bảo tàng thu hút đông đảo du khách '
                          'trong và ngoài nước nhất Việt Nam (hơn 1 triệu lượt khách mỗi năm).\n'
                          '\n'
                          'Bảo tàng lưu giữ hơn 20.000 tài liệu, hiện vật và phim ảnh tái hiện sự thật lịch sử về các '
                          'cuộc chiến tranh xâm lược, hậu quả tàn khốc của chiến tranh đối với nhân dân Việt Nam, đồng '
                          'thời lan tỏa thông điệp mạnh mẽ về hòa bình, tình hữu nghị giữa các dân tộc trên thế giới.\n'
                          '\n'
                          'Hệ thống trưng bày gồm 2 khu vực chính:\n'
                          '1. Khu trưng bày ngoài trời: Trưng bày bộ sưu tập khí tài quân sự hạng nặng nguyên bản (Máy '
                          'bay vận tải C-130 Hercules, Trực thăng Chinook, Xe tăng M48 Patton, Pháo 175mm M107) và mô '
                          'hình phục dựng Trại giam Chuồng cọp Côn Đảo.\n'
                          '2. Các phòng trưng bày chuyên đề trong nhà:\n'
                          "   - Triển lãm ảnh 'Hồi niệm' (Requiem) – bộ sưu tập ảnh lịch sử từ 135 phóng viên chiến "
                          'trường hy sinh tại Đông Dương.\n'
                          "   - Chuyên đề 'Việt Nam – Bức tranh chiến tranh & Hòa bình'.\n"
                          "   - Chuyên đề 'Tội ác chiến tranh' & Hậu quả Chất độc da cam/Dioxin.\n"
                          '   - Phong trào nhân dân thế giới ủng hộ Việt Nam kháng chiến.',
        'history_and_architecture': '- Thành lập: Ngày 4 tháng 9 năm 1975.\n'
                                    '- Tên cũ: Nhà trưng bày Tội ác Mỹ - Ngụy (đổi tên năm 1995).\n'
                                    '- Thành viên: Mạng lưới Bảo tàng vì Hòa bình Thế giới (INMP).\n'
                                    '- Địa chỉ: 28 Võ Văn Tần, Phường Võ Thị Sáu, Quận 3, TP.HCM.',
        'id': 'museum_06',
        'image_url': 'assets/images/museums/museum_06_bao_tang_chung_tich.jpg',
        'location': {'lat': 10.7792, 'lng': 106.6921},
        'name': 'Bảo tàng Chứng tích Chiến tranh',
        'qr_code': 'QR_MUSEUM_06',
        'trigger_radius_meters': 30},
    {   'artifacts': [   {   'artifact_id': 'art_07_01',
                             'description_vi': 'Bức tượng đồng khắc họa người thanh niên Nguyễn Tất Thành đứng trên '
                                               'bến cảng nhìn ra đại dương năm 1911.',
                             'image_url': 'assets/images/artifacts/art_07_01_tuong_nguyen_tat_thanh.jpg',
                             'name_vi': 'Tượng đài Nguyễn Tất Thành ra đi tìm đường cứu nước',
                             'qr_code': 'QR_ART_07_01'},
                         {   'artifact_id': 'art_07_02',
                             'description_vi': 'Kỷ vật huyền thoại làm từ vỏ lốp xe ô tô cũ, gắn liền với tác phong '
                                               'giản dị, tiết kiệm của Bác suốt nhiều thập kỷ.',
                             'image_url': 'assets/images/artifacts/art_07_02_doi_dep_cao_su.jpg',
                             'name_vi': 'Đôi dép cao su của Bác Hồ',
                             'qr_code': 'QR_ART_07_02'},
                         {   'artifact_id': 'art_07_03',
                             'description_vi': 'Bộ trang phục vải Kaki bạc màu Bác Hồ thường mặc trong các sự kiện '
                                               'ngoại giao và sinh hoạt hàng ngày.',
                             'image_url': 'assets/images/artifacts/art_07_03_bo_quan_ao_kaki.jpg',
                             'name_vi': 'Bộ quần áo Kaki giản dị của Bác',
                             'qr_code': 'QR_ART_07_03'},
                         {   'artifact_id': 'art_07_04',
                             'description_vi': 'Vật dụng cá nhân Bác mang theo trong những năm tháng hoạt động cách '
                                               'mạng bôn ba qua Pháp, Anh, Liên Xô.',
                             'image_url': 'assets/images/artifacts/art_07_04_vali_go.jpg',
                             'name_vi': 'Chiếc Vali gỗ Bác dùng ở nước ngoài',
                             'qr_code': 'QR_ART_07_04'},
                         {   'artifact_id': 'art_07_05',
                             'description_vi': 'Tác phẩm lý luận cách mạng đầu tiên do Nguyễn Ái Quốc soạn thảo đặt '
                                               'nền móng tư tưởng cho cách mạng Việt Nam.',
                             'image_url': 'assets/images/artifacts/art_07_05_duong_kach_menh.jpg',
                             'name_vi': "Cuốn sách 'Đường Kách Mệnh' (1927)",
                             'qr_code': 'QR_ART_07_05'},
                         {   'artifact_id': 'art_07_06',
                             'description_vi': 'Chiếc máy đánh chữ Bác dùng để soạn thảo các văn kiện cách mạng, Lời '
                                               'kêu gọi kháng chiến.',
                             'image_url': 'assets/images/artifacts/art_07_06_may_danh_chu_bac_ho.jpg',
                             'name_vi': 'Chiếc máy đánh chữ Bác Hồ từng sử dụng',
                             'qr_code': 'QR_ART_07_06'},
                         {   'artifact_id': 'art_07_07',
                             'description_vi': 'Mô hình con tàu thương mại Pháp nơi anh Văn Ba làm phụ bếp bắt đầu '
                                               'hành trình vạn dặm tìm đường cứu nước.',
                             'image_url': 'assets/images/artifacts/art_07_07_tau_latouche_treville.jpg',
                             'name_vi': 'Mô hình Tàu Amiral Latouche-Tréville',
                             'qr_code': 'QR_ART_07_07'},
                         {   'artifact_id': 'art_07_08',
                             'description_vi': "Bản thảo thư lịch sử với câu nói khắc sâu tâm khảm: 'Nam Bộ là máu của "
                                               "máu Việt Nam, là thịt của thịt Việt Nam'.",
                             'image_url': 'assets/images/artifacts/art_07_08_thu_gui_nam_bo_1946.jpg',
                             'name_vi': 'Bức thư Bác Hồ gửi đồng bào Nam Bộ 1946',
                             'qr_code': 'QR_ART_07_08'},
                         {   'artifact_id': 'art_07_09',
                             'description_vi': 'Kỷ vật cá nhân Bác giữ bên mình từ thời dự Đại hội Tours (1920) tham '
                                               'gia thành lập Đảng Cộng sản Pháp.',
                             'image_url': 'assets/images/artifacts/art_07_09_dong_ho_bo_tui.jpg',
                             'name_vi': 'Chiếc Đồng hồ bỏ túi thời kỳ ở Pháp',
                             'qr_code': 'QR_ART_07_09'},
                         {   'artifact_id': 'art_07_10',
                             'description_vi': 'Chiếc gậy mây mòn vẹt đồng hành cùng Bác trên những chặng đường thăm '
                                               'chiến sĩ, đồng bào khắp mọi miền.',
                             'image_url': 'assets/images/artifacts/art_07_10_gay_may_bac_ho.jpg',
                             'name_vi': 'Chiếc gậy mây Bác dùng đi công tác',
                             'qr_code': 'QR_ART_07_10'}],
        'description_vi': 'Bảo tàng Hồ Chí Minh - Chi nhánh TP.HCM nằm tại số 1 Nguyễn Tất Thành, Quận 4, tọa lạc tại '
                          'Thương cảng Bến Nhà Rồng lịch sử. Tòa nhà được hãng vận tải biển Messageries Maritimes của '
                          'Pháp xây dựng năm 1863 làm trụ sở quản lý cảng. Tòa nhà mang phong cách kiến trúc phương '
                          'Tây đặc trưng, điểm nhấn là hai con rồng đắp gốm sứ châu đầu vào mặt tranh trên nóc mái, '
                          'nên người dân Sài Gòn quen gọi là Bến Nhà Rồng.\n'
                          '\n'
                          'Nơi đây đã ghi dấu sự kiện lịch sử trọng đại: Ngày 5/6/1911, người thanh niên yêu nước '
                          'Nguyễn Tất Thành (với tên gọi anh Văn Ba) đã xuống con tàu thương mại Amiral '
                          'Latouche-Tréville rời bến cảng Sài Gòn ra đi tìm đường cứu nước, bắt đầu hành trình bôn ba '
                          'vạn dặm kéo dài 30 năm qua 3 đại dương và 4 châu lục.\n'
                          '\n'
                          'Bảo tàng hiện có 9 phòng trưng bày chuyên đề lưu giữ hơn 11.000 tư liệu, hiện vật quý giá:\n'
                          '- Chủ đề cuộc đời và sự nghiệp cách mạng vĩ đại của Chủ tịch Hồ Chí Minh.\n'
                          '- Kỷ vật cá nhân mộc mạc: Đôi dép cao su, bộ quần áo Kaki, chiếc vali gỗ, chiếc máy đánh '
                          'chữ, chiếc gậy mây.\n'
                          "- Bản thảo lý luận cách mạng: Cuốn sách 'Đường Kách Mệnh' (1927), Báo 'Le Paria', Bản thảo "
                          'Thư gửi đồng bào Nam Bộ 1946...\n'
                          '- Tình cảm sâu nặng của Bác Hồ đối với đồng bào, chiến sĩ miền Nam và tình cảm kính yêu của '
                          'nhân dân phương Nam đối với Bác.',
        'history_and_architecture': '- Xây dựng: Năm 1863 bởi hãng tàu Pháp Messageries Maritimes.\n'
                                    '- Tên gọi lịch sử: Trụ sở Hãng Cảng Nhà Rồng / Bến Nhà Rồng.\n'
                                    '- Sự kiện lịch sử: Ngày 5/6/1911 Nguyễn Tất Thành ra đi tìm đường cứu nước.\n'
                                    '- Địa chỉ: 1 Nguyễn Tất Thành, Phường 12, Quận 4, TP.HCM.',
        'id': 'museum_07',
        'image_url': 'assets/images/museums/museum_07_ben_nha_rong.jpg',
        'location': {'lat': 10.7681, 'lng': 106.7068},
        'name': 'Bảo tàng Bến Nhà Rồng (Bảo tàng Hồ Chí Minh)',
        'qr_code': 'QR_MUSEUM_07',
        'trigger_radius_meters': 30}]

async def init_database():
    client = AsyncIOMotorClient(MONGO_URL)
    db = client["museum_db"]
    collection = db["POI"]
    
    for museum in MUSEUMS_DATA:
        await collection.update_one(
            {"id": museum["id"]},
            {"$set": museum},
            upsert=True
        )
    print("✅ Đã nạp thành công 7 Bảo tàng TP.HCM (Dữ liệu v2 chi tiết) vào MongoDB!")

if __name__ == "__main__":
    asyncio.run(init_database())
