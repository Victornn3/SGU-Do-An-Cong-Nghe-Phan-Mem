"""Integration test cho luong Gateway -> Auth/Ticket -> Statistics -> Ticket.

Chi chay khi Docker Compose da khoi dong va database CI da duoc seed:
    RUN_INTEGRATION=1 pytest tests/integration/ -v

Trong pytest tests/ -v thong thuong, test nay duoc skip de khong can server.
"""
from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request

import pytest

BASE_URL = os.getenv("INTEGRATION_BASE_URL", "http://localhost").rstrip("/")
ADMIN_USERNAME = os.getenv("INTEGRATION_ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("INTEGRATION_ADMIN_PASSWORD", "")

pytestmark = pytest.mark.skipif(
    os.getenv("RUN_INTEGRATION") != "1",
    reason="Requires the Docker Compose integration environment",
)


def request_json(path: str, *, method: str = "GET", payload=None, token=None):
    """Gui HTTP request va tra ca HTTP status code lan JSON response."""
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    headers = {"Accept": "application/json"}
    if body is not None:
        headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = f"Bearer {token}"

    request = urllib.request.Request(
        f"{BASE_URL}{path}", data=body, headers=headers, method=method
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            raw = response.read().decode("utf-8")
            return response.status, json.loads(raw) if raw else {}
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        try:
            data = json.loads(raw) if raw else {}
        except json.JSONDecodeError:
            data = {"raw": raw}
        return exc.code, data


def wait_for_api(timeout_seconds: int = 180):
    """Cho Nginx -> Gateway -> POI Service san sang."""
    deadline = time.monotonic() + timeout_seconds
    last_error = "no response"
    while time.monotonic() < deadline:
        try:
            status, payload = request_json("/api/languages")
            if status == 200 and payload:
                return
            last_error = f"HTTP {status}: {payload}"
        except Exception as exc:  # service co the dang khoi dong
            last_error = repr(exc)
        time.sleep(3)
    pytest.fail(f"API not ready after {timeout_seconds}s: {last_error}")


def test_gateway_auth_ticket_and_statistics_integration():
    """Login -> protected API -> create ticket -> scan twice -> unique statistics."""
    assert ADMIN_PASSWORD, "INTEGRATION_ADMIN_PASSWORD must be configured for CI"
    wait_for_api()

    # 1. Gateway chuyen request dang nhap den Auth Service.
    status, login = request_json(
        "/api/auth/login",
        method="POST",
        payload={"username": ADMIN_USERNAME, "password": ADMIN_PASSWORD},
    )
    assert status == 200, f"Admin login failed: {login}"
    token = login.get("access_token")
    assert token, f"Auth Service did not return access_token: {login}"

    # 2. Gateway tu choi API thong ke neu khong co JWT.
    status, _ = request_json("/api/stats/tickets")
    assert status == 401

    # 3. Lay so lieu truoc khi tao ve. Statistics Service goi Ticket Service qua HTTP.
    status, before = request_json("/api/stats/tickets", token=token)
    assert status == 200, f"Statistics API failed: {before}"
    created_before = before["total_tickets_created"]
    scanned_before = before["total_tickets_scanned"]
    standard_before = before["standard_scanned"]

    # 4. Tao mot ve qua Gateway -> Ticket Service.
    status, created = request_json(
        "/api/tickets/create",
        method="POST",
        payload={"ticket_type": "STANDARD"},
        token=token,
    )
    assert status == 200, f"Ticket creation failed: {created}"
    ticket_code = created.get("ticket_code")
    assert ticket_code and ticket_code.startswith("VM-STD-"), created

    # 5. Endpoint scan la API cong khai cho khach tham quan.
    status, first_scan = request_json(
        f"/api/tickets/scan/{ticket_code}", method="POST"
    )
    assert status == 200 and first_scan.get("success") is True, first_scan
    assert first_scan.get("status") == "first_access", first_scan

    status, second_scan = request_json(
        f"/api/tickets/scan/{ticket_code}", method="POST"
    )
    assert status == 200 and second_scan.get("success") is True, second_scan
    assert second_scan.get("status") == "re_access", second_scan

    # 6. Quet lai khong tao them document ve; thong ke chi tang mot ve.
    status, after = request_json("/api/stats/tickets", token=token)
    assert status == 200, f"Statistics API failed after scan: {after}"
    assert after["total_tickets_created"] == created_before + 1, after
    assert after["total_tickets_scanned"] == scanned_before + 1, after
    assert after["standard_scanned"] == standard_before + 1, after
