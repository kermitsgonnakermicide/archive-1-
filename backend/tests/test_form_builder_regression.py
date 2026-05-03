"""Regression tests for the form-builder bug discovered 2026-02:
The frontend round-trips the full event payload (including `id`, etc.) when the
admin saves an event, but `EventUpdate` had `extra="forbid"` which rejected the
request with HTTP 422. Same applied to PageUpdate. These tests guard against a
recurrence.
"""
import os
import requests

API_BASE = os.environ.get("API_URL") or "http://localhost:8001"
ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "scalesupportteam2@gmail.com")
ADMIN_PASS = os.environ.get("ADMIN_PASSWORD", "SCALEdaddySALLU67")


def _admin_token() -> str:
    r = requests.post(f"{API_BASE}/api/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASS}, timeout=10)
    r.raise_for_status()
    return r.json()["token"]


def test_event_put_accepts_full_round_trip_payload():
    """PUT /events/{id} must accept the full GET /events/{id} payload back unchanged.
    The frontend admin editor sends the entire event object on save, including `id`."""
    token = _admin_token()
    headers = {"Authorization": f"Bearer {token}"}
    events = requests.get(f"{API_BASE}/api/events", timeout=10).json()
    assert events, "no seed events"
    eid = events[0]["id"]
    full = requests.get(f"{API_BASE}/api/events/{eid}", timeout=10).json()
    assert "id" in full
    # Round-trip the entire body — must not 422.
    r = requests.put(f"{API_BASE}/api/events/{eid}", json=full, headers=headers, timeout=10)
    assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
    body = r.json()
    assert body["id"] == eid
    assert body["title"] == full["title"]


def test_page_put_accepts_full_round_trip_payload():
    """PUT /pages/{id} must accept the full page payload back. Same root cause as events."""
    token = _admin_token()
    headers = {"Authorization": f"Bearer {token}"}
    # Create a throwaway page
    create = requests.post(
        f"{API_BASE}/api/pages",
        json={"slug": "regression-test-roundtrip", "title": "Regression Roundtrip Test", "blocks": []},
        headers=headers, timeout=10,
    )
    assert create.status_code == 200, create.text
    page = create.json()
    try:
        # Round-trip the whole object
        r = requests.put(f"{API_BASE}/api/pages/{page['id']}", json=page, headers=headers, timeout=10)
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
        assert r.json()["id"] == page["id"]
    finally:
        requests.delete(f"{API_BASE}/api/pages/{page['id']}", headers=headers, timeout=10)


def test_event_put_persists_all_nine_extra_field_types():
    """Admin must be able to save extra_fields with all 9 supported types + scope."""
    token = _admin_token()
    headers = {"Authorization": f"Bearer {token}"}
    events = requests.get(f"{API_BASE}/api/events", timeout=10).json()
    eid = events[0]["id"]
    snapshot_before = requests.get(f"{API_BASE}/api/events/{eid}", timeout=10).json()
    try:
        new_fields = [
            {"key": "q_text", "label": "Text", "type": "text", "required": False, "options": [], "scope": "team", "help_text": ""},
            {"key": "q_textarea", "label": "Long", "type": "textarea", "required": False, "options": [], "scope": "team", "help_text": ""},
            {"key": "q_email", "label": "Em", "type": "email", "required": False, "options": [], "scope": "team", "help_text": ""},
            {"key": "q_number", "label": "N", "type": "number", "required": False, "options": [], "scope": "team", "help_text": ""},
            {"key": "q_yesno", "label": "Y/N", "type": "yesno", "required": False, "options": [], "scope": "team", "help_text": ""},
            {"key": "q_select", "label": "Sel", "type": "select", "required": False, "options": ["a", "b"], "scope": "team", "help_text": ""},
            {"key": "q_radio", "label": "Rad", "type": "radio", "required": False, "options": ["x", "y"], "scope": "team", "help_text": ""},
            {"key": "q_checkbox", "label": "Chk", "type": "checkbox", "required": False, "options": [], "scope": "team", "help_text": ""},
            {"key": "q_file", "label": "File", "type": "file", "required": False, "options": [], "scope": "team", "help_text": ""},
        ]
        r = requests.put(f"{API_BASE}/api/events/{eid}", json={"extra_fields": new_fields}, headers=headers, timeout=10)
        assert r.status_code == 200, r.text
        saved = r.json()["extra_fields"]
        assert len(saved) == 9
        types = {f["key"]: f["type"] for f in saved}
        assert types == {
            "q_text": "text", "q_textarea": "textarea", "q_email": "email", "q_number": "number",
            "q_yesno": "yesno", "q_select": "select", "q_radio": "radio", "q_checkbox": "checkbox", "q_file": "file",
        }
    finally:
        requests.put(f"{API_BASE}/api/events/{eid}", json={"extra_fields": snapshot_before.get("extra_fields", [])}, headers=headers, timeout=10)
