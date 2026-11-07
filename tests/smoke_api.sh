#!/usr/bin/env bash
# Kiểm tra nhanh API khi hệ thống đang chạy (docker compose up).
# Dùng: ./tests/smoke_api.sh [địa_chỉ]   (mặc định http://localhost)
BASE="${1:-http://localhost}"
pass=0; fail=0
check() { # $1 = tên kiểm tra, $2 = lệnh điều kiện
  if eval "$2" >/dev/null 2>&1; then echo "PASS  $1"; pass=$((pass+1)); else echo "FAIL  $1"; fail=$((fail+1)); fi
}
code() { curl -s -o /dev/null -w "%{http_code}" "$@"; }

check "GET /api/languages = 200"           '[ "$(code $BASE/api/languages)" = 200 ]'
check "/api/languages có vi, en, zh"        'curl -s $BASE/api/languages | grep -q "\"zh\"" && curl -s $BASE/api/languages | grep -q "\"en\""'
check "GET /api/pois = 200"                 '[ "$(code $BASE/api/pois)" = 200 ]'
check "/api/pois trả đủ 11 POI"             '[ "$(curl -s $BASE/api/pois | grep -o "\"poi_code\"" | wc -l)" -eq 11 ]'
check "/api/zones đã bỏ (không còn 200)"    '[ "$(code $BASE/api/zones)" != 200 ]'
check "GET /api/narrations/P00?lang=en = 200" '[ "$(code "$BASE/api/narrations/P00?lang=en")" = 200 ]'
check "Ngôn ngữ lạ bị từ chối (4xx)"       '[ "$(code "$BASE/api/narrations/P00?lang=xx")" -ge 400 ]'
check "POI không tồn tại = 404"             '[ "$(code $BASE/api/pois/NOPE)" = 404 ]'
echo "Kết quả: $pass đạt, $fail lỗi"
[ "$fail" -eq 0 ]
