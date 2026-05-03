"""SCALE India — backend API regression tests (post SCALE+ removal + payments)."""
import os
import uuid
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://scale-talent-network.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"

ADMIN_EMAIL = "scalesupportteam2@gmail.com"
ADMIN_PASSWORD = "SCALEdaddySALLU67"


@pytest.fixture(scope="session")
def admin_token():
    r = requests.post(f"{API}/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}, timeout=15)
    assert r.status_code == 200, f"Admin login failed: {r.status_code} {r.text}"
    return r.json()["token"]


@pytest.fixture(scope="session")
def admin_headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}"}


@pytest.fixture(scope="session")
def user_token():
    email = f"TEST_user_{uuid.uuid4().hex[:8]}@example.com"
    r = requests.post(f"{API}/auth/signup", json={"email": email, "password": "Test1234!", "name": "Test User"}, timeout=15)
    assert r.status_code == 200
    return r.json()["token"]


@pytest.fixture(scope="session")
def user_headers(user_token):
    return {"Authorization": f"Bearer {user_token}"}


@pytest.fixture(scope="session")
def first_event():
    r = requests.get(f"{API}/events", timeout=10)
    assert r.status_code == 200
    items = r.json()
    assert len(items) >= 1
    return items[0]


# ----- health -----
class TestHealth:
    def test_root(self):
        r = requests.get(f"{API}/", timeout=10)
        assert r.status_code == 200
        assert "message" in r.json()


# ----- auth -----
class TestAuth:
    def test_admin_login(self):
        r = requests.post(f"{API}/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}, timeout=10)
        assert r.status_code == 200
        d = r.json()
        assert d["user"]["role"] == "admin"
        assert isinstance(d["token"], str) and len(d["token"]) > 20

    def test_login_bad(self):
        r = requests.post(f"{API}/auth/login", json={"email": ADMIN_EMAIL, "password": "wrong"}, timeout=10)
        assert r.status_code == 401


# ----- content & SCALE+ removal -----
class TestContent:
    def test_get_content(self):
        r = requests.get(f"{API}/content", timeout=10)
        assert r.status_code == 200
        d = r.json()
        assert d.get("id") == "main"
        assert d.get("hero_cta_primary") == "Explore Events"
        assert d.get("hero_cta_secondary") == "Our Story"

    def test_no_scale_plus_keys(self):
        r = requests.get(f"{API}/content", timeout=10).json()
        scale_plus_keys = ["scale_plus_intro", "scale_plus_sessions", "scale_plus_newsletter",
                           "pricing_monthly", "pricing_yearly", "scholarship_callout",
                           "scholarship_body", "situational_title", "situational_desc"]
        leftover = [k for k in scale_plus_keys if k in r]
        assert not leftover, f"SCALE+ keys still present: {leftover}"


# ----- events -----
class TestEvents:
    def test_list_events(self, first_event):
        # Verify new fields on event
        assert "about" in first_event
        assert "location" in first_event
        assert "price_inr" in first_event
        assert isinstance(first_event["price_inr"], (int, float))

    def test_get_event_by_id(self, first_event):
        r = requests.get(f"{API}/events/{first_event['id']}", timeout=10)
        assert r.status_code == 200
        d = r.json()
        assert d["id"] == first_event["id"]
        assert "about" in d and "location" in d and "price_inr" in d

    def test_get_event_404(self):
        r = requests.get(f"{API}/events/does-not-exist", timeout=10)
        assert r.status_code == 404


# ----- registrations -----
class TestRegistrations:
    def test_create_registration(self, first_event):
        payload = {
            "event_id": first_event["id"],
            "name": "TEST_Reg Student",
            "school": "TEST School",
            "grade": "11",
            "email": "test_reg_student@example.com",
            "phone": "+919999999999",
            "parent_name": "TEST Parent",
            "parent_phone": "+918888888888",
            "parent_email": "test_reg_parent@example.com",
            "extras": {"why_join": "TEST registration creation flow."},
        }
        r = requests.post(f"{API}/registrations", json=payload, timeout=30)
        assert r.status_code == 200, f"Got {r.status_code}: {r.text}"
        d = r.json()
        assert d["ok"] is True
        assert "registration_id" in d
        assert "payment_link" in d and f"/payment/{d['registration_id']}" in d["payment_link"]
        assert "scholarship_link" in d
        # Persistence
        g = requests.get(f"{API}/registrations/{d['registration_id']}", timeout=10)
        assert g.status_code == 200
        rec = g.json()
        assert rec["name"] == payload["name"]
        assert rec["event_id"] == first_event["id"]
        assert rec["payment_status"] == "pending"
        return d["registration_id"]

    def test_register_invalid_event(self):
        payload = {
            "event_id": "does-not-exist",
            "name": "x", "school": "x", "grade": "x",
            "email": "x@x.com", "phone": "1",
            "parent_name": "y", "parent_phone": "2", "parent_email": "y@y.com",
        }
        r = requests.post(f"{API}/registrations", json=payload, timeout=15)
        assert r.status_code == 404

    def test_get_registration_404(self):
        r = requests.get(f"{API}/registrations/nope-{uuid.uuid4().hex}", timeout=10)
        assert r.status_code == 404

    def test_admin_registrations_requires_admin(self, user_headers):
        r = requests.get(f"{API}/admin/registrations", headers=user_headers, timeout=10)
        assert r.status_code == 403

    def test_admin_registrations_list(self, admin_headers, first_event):
        # ensure at least one
        payload = {
            "event_id": first_event["id"],
            "name": "TEST_AdminListReg", "school": "S", "grade": "10",
            "email": "test_admin_list@example.com", "phone": "1",
            "parent_name": "p", "parent_phone": "2", "parent_email": "test_admin_list_p@example.com",
            "extras": {"why_join": "admin list test"},
        }
        c = requests.post(f"{API}/registrations", json=payload, timeout=30)
        assert c.status_code == 200
        new_id = c.json()["registration_id"]

        r = requests.get(f"{API}/admin/registrations", headers=admin_headers, timeout=15)
        assert r.status_code == 200
        items = r.json()
        assert isinstance(items, list)
        assert any(i["id"] == new_id for i in items)


# ----- event scholarship -----
class TestEventScholarship:
    def test_submit(self, first_event):
        payload = {
            "event_id": first_event["id"],
            "name": "TEST_Sch",
            "school": "S",
            "grade": "10",
            "email": "test_sch@example.com",
            "phone": "+911",
            "parent_name": "P",
            "parent_email": "test_sch_p@example.com",
            "financial_proof": "single income; below 5L INR/yr",
            "why_participate": "Interested in finance",
        }
        r = requests.post(f"{API}/forms/event-scholarship", json=payload, timeout=20)
        assert r.status_code == 200
        d = r.json()
        assert d["ok"] is True
        assert "id" in d

    def test_submit_invalid_event(self):
        payload = {
            "event_id": "nope", "name": "n", "school": "s", "grade": "g",
            "email": "a@a.com", "phone": "1", "parent_name": "p",
            "parent_email": "b@b.com", "financial_proof": "x", "why_participate": "y",
        }
        r = requests.post(f"{API}/forms/event-scholarship", json=payload, timeout=15)
        assert r.status_code == 404


# ----- payments -----
class TestPayments:
    def test_create_session_invalid_reg(self):
        r = requests.post(f"{API}/payments/create-session",
                          json={"registration_id": "nope-xyz", "origin_url": BASE_URL},
                          timeout=15)
        assert r.status_code == 404

    def test_create_session_and_status(self, first_event):
        # Need a valid registration first
        reg_payload = {
            "event_id": first_event["id"],
            "name": "TEST_Pay", "school": "S", "grade": "11",
            "email": "test_pay@example.com", "phone": "+91900",
            "parent_name": "P", "parent_phone": "+91900", "parent_email": "test_pay_p@example.com",
            "extras": {"why_join": "payment flow test"},
        }
        rr = requests.post(f"{API}/registrations", json=reg_payload, timeout=30)
        assert rr.status_code == 200
        reg_id = rr.json()["registration_id"]

        r = requests.post(f"{API}/payments/create-session",
                          json={"registration_id": reg_id, "origin_url": BASE_URL},
                          timeout=30)
        assert r.status_code == 200, f"Stripe session failed: {r.status_code} {r.text}"
        d = r.json()
        assert "url" in d and d["url"].startswith("http")
        assert "session_id" in d and len(d["session_id"]) > 5
        session_id = d["session_id"]

        s = requests.get(f"{API}/payments/status/{session_id}", timeout=20)
        assert s.status_code == 200, f"status endpoint failed: {s.status_code} {s.text}"
        sd = s.json()
        assert "payment_status" in sd
        # Acceptable: real stripe response, or graceful fallback DB state with note
        assert sd["payment_status"] in ("unpaid", "open", "paid", "no_payment_required", "initiated", "pending")
        # Graceful fallback: if stripe retrieval failed, note should be present
        # Not asserting presence of note since either path is acceptable per spec


# ----- admin submissions -----
class TestAdminSubmissions:
    def test_submissions_requires_admin(self):
        r = requests.get(f"{API}/submissions", timeout=10)
        assert r.status_code in (401, 403)

    def test_submissions_list_admin(self, admin_headers):
        # Seed at least one contact submission
        requests.post(f"{API}/forms/contact", json={
            "name": "TEST_adminSub", "school": "S", "subject": "general",
            "message": "hi", "email": "test_adminsub@example.com"
        }, timeout=15)
        r = requests.get(f"{API}/submissions", headers=admin_headers, timeout=20)
        assert r.status_code == 200, f"/api/submissions failed: {r.status_code} {r.text[:300]}"
        items = r.json()
        assert isinstance(items, list)
        # Ensure no ObjectId leakage
        import json
        json.dumps(items)  # will raise if not serializable
        for it in items[:20]:
            assert "_id" not in it
            assert "data" in it
            # data should be a dict without _id
            if isinstance(it.get("data"), dict):
                assert "_id" not in it["data"]


# ----- contact still works -----
class TestContact:
    def test_contact(self):
        payload = {"name": "TEST_c", "school": "S", "subject": "general",
                   "message": "hi", "email": "test_c@example.com"}
        r = requests.post(f"{API}/forms/contact", json=payload, timeout=20)
        assert r.status_code == 200
        assert r.json()["ok"] is True


# ----- file upload / scholarship proof / admin download -----
def _tiny_pdf_bytes() -> bytes:
    # Minimal valid PDF (~ a few hundred bytes)
    return (
        b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n"
        b"1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
        b"2 0 obj<</Type/Pages/Count 1/Kids[3 0 R]>>endobj\n"
        b"3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 200 200]/Contents 4 0 R/Resources<<>>>>endobj\n"
        b"4 0 obj<</Length 44>>stream\nBT /F1 12 Tf 10 100 Td (TEST proof) Tj ET\nendstream endobj\n"
        b"xref\n0 5\n0000000000 65535 f \n0000000015 00000 n \n0000000061 00000 n \n"
        b"0000000111 00000 n \n0000000196 00000 n \ntrailer<</Size 5/Root 1 0 R>>\nstartxref\n295\n%%EOF"
    )


class TestUploadAndAdminDownload:
    def test_upload_pdf_success(self, first_event, admin_headers):
        pdf = _tiny_pdf_bytes()
        files = {"file": ("TEST_proof.pdf", pdf, "application/pdf")}
        r = requests.post(f"{API}/upload/scholarship-proof", files=files, timeout=60)
        if r.status_code == 503:
            pytest.skip(f"Object storage unavailable: {r.text}")
        assert r.status_code == 200, f"Upload failed: {r.status_code} {r.text}"
        d = r.json()
        assert "id" in d and isinstance(d["id"], str) and len(d["id"]) > 5
        assert d["original_filename"] == "TEST_proof.pdf"
        assert d["size"] == len(pdf)
        file_id = d["id"]

        # Submit scholarship form referencing the proof_file_id
        sch_payload = {
            "event_id": first_event["id"],
            "name": "TEST_SchWithProof", "school": "S", "grade": "10",
            "email": "test_sch_proof@example.com", "phone": "+911",
            "parent_name": "P", "parent_email": "test_sch_proof_p@example.com",
            "financial_proof": "details", "why_participate": "interest",
            "proof_file_id": file_id,
        }
        sr = requests.post(f"{API}/forms/event-scholarship", json=sch_payload, timeout=20)
        assert sr.status_code == 200, sr.text
        assert sr.json()["ok"] is True

        # Admin download — returns raw bytes with correct content-type
        dl = requests.get(f"{API}/admin/files/{file_id}", headers=admin_headers, timeout=30)
        assert dl.status_code == 200, f"Download failed: {dl.status_code} {dl.text[:200]}"
        assert dl.headers.get("content-type", "").startswith("application/pdf")
        assert dl.content[:4] == b"%PDF", "Content header is not a PDF"
        assert len(dl.content) == len(pdf)

    def test_upload_rejects_unsupported_extensions(self):
        for fname, ctype in [("bad.exe", "application/octet-stream"), ("notes.txt", "text/plain")]:
            files = {"file": (fname, b"hello world", ctype)}
            r = requests.post(f"{API}/upload/scholarship-proof", files=files, timeout=20)
            assert r.status_code == 400, f"Expected 400 for {fname}, got {r.status_code}: {r.text}"
            detail = (r.json().get("detail") or "").lower()
            for ext in ("pdf", "jpg", "jpeg", "png", "webp"):
                assert ext in detail, f"Allowed types not listed in error for {fname}: {detail}"

    def test_upload_rejects_oversized(self):
        big = b"\x00" * (10 * 1024 * 1024 + 1024)  # 10MB + 1KB
        files = {"file": ("big.pdf", big, "application/pdf")}
        r = requests.post(f"{API}/upload/scholarship-proof", files=files, timeout=120)
        assert r.status_code == 400, f"Expected 400 for >10MB, got {r.status_code}"
        assert "10 mb" in (r.json().get("detail") or "").lower() or "larger" in (r.json().get("detail") or "").lower()

    def test_admin_download_unauth(self):
        r = requests.get(f"{API}/admin/files/anything", timeout=10)
        assert r.status_code in (401, 403)

    def test_admin_download_non_admin_forbidden(self, user_headers):
        r = requests.get(f"{API}/admin/files/anything", headers=user_headers, timeout=10)
        assert r.status_code == 403

    def test_admin_download_404(self, admin_headers):
        r = requests.get(f"{API}/admin/files/{uuid.uuid4().hex}", headers=admin_headers, timeout=10)
        assert r.status_code == 404


# ----- content persistence for all users (admin PUT, unauth GET) -----
class TestContentPersistence:
    def test_admin_put_then_unauth_get(self, admin_headers):
        # Read current content
        cur = requests.get(f"{API}/content", timeout=10).json()
        original_label = cur.get("hero_label", "India's First National Student Organisation")
        new_label = f"TEST_label_{uuid.uuid4().hex[:6]}"
        try:
            payload = dict(cur)
            payload["hero_label"] = new_label
            r = requests.put(f"{API}/content", headers=admin_headers, json=payload, timeout=15)
            assert r.status_code == 200, r.text
            assert r.json().get("hero_label") == new_label

            # Unauth GET — must reflect new value
            g = requests.get(f"{API}/content", timeout=10)
            assert g.status_code == 200
            assert g.json().get("hero_label") == new_label
        finally:
            # Restore
            payload = dict(cur)
            payload["hero_label"] = original_label
            requests.put(f"{API}/content", headers=admin_headers, json=payload, timeout=15)



# ----- Iteration 5: new editable content fields + Mock Stock individual ----
NEW_CONTENT_KEYS = [
    "pillars_eyebrow", "pillars_headline",
    "whatis_eyebrow", "whatis_headline",
    "why_eyebrow",
    "events_eyebrow", "events_headline",
    "story_eyebrow", "story_headline",
    "vision_eyebrow",
    "contact_eyebrow", "contact_headline",
    "hero_ticker",
    "event_detail_about_label",
    "event_detail_eligibility_label", "event_detail_eligibility_body",
    "event_detail_scholarship_label", "event_detail_scholarship_body",
]


class TestIteration5NewContentFields:
    def test_get_content_has_new_keys(self):
        r = requests.get(f"{API}/content", timeout=10)
        assert r.status_code == 200
        d = r.json()
        missing = [k for k in NEW_CONTENT_KEYS if k not in d]
        assert not missing, f"Missing new content keys: {missing}"
        # values should be non-empty strings
        for k in NEW_CONTENT_KEYS:
            assert isinstance(d[k], str) and len(d[k]) > 0, f"{k} is empty or not a string"

    def test_put_new_fields_persists(self, admin_headers):
        cur = requests.get(f"{API}/content", timeout=10).json()
        try:
            test_vals = {k: f"TEST_{k}_{uuid.uuid4().hex[:5]}" for k in NEW_CONTENT_KEYS}
            payload = dict(cur)
            payload.update(test_vals)
            pr = requests.put(f"{API}/content", headers=admin_headers, json=payload, timeout=15)
            assert pr.status_code == 200, pr.text
            updated = pr.json()
            for k, v in test_vals.items():
                assert updated.get(k) == v, f"{k} PUT response mismatch"

            # Unauth GET — all new values propagate
            g = requests.get(f"{API}/content", timeout=10).json()
            for k, v in test_vals.items():
                assert g.get(k) == v, f"{k} did not persist for unauth GET"
        finally:
            # Restore
            restore = dict(cur)
            requests.put(f"{API}/content", headers=admin_headers, json=restore, timeout=15)


class TestIteration5MockStockIndividual:
    def _find_mock_stock(self):
        r = requests.get(f"{API}/events", timeout=10)
        assert r.status_code == 200
        events = r.json()
        matches = [
            e for e in events
            if "mock stock" in (e.get("title") or "").lower()
            or "stock market" in (e.get("title") or "").lower()
            or "investment challenge" in (e.get("title") or "").lower()
        ]
        assert matches, f"Mock Stock event not found among {[e.get('title') for e in events]}"
        return matches[0]

    def test_mock_stock_about_says_individual_via_list(self):
        ev = self._find_mock_stock()
        about = (ev.get("about") or "").lower()
        assert "individual" in about, f"'individual' not in about text: {ev.get('about')}"
        assert "teams of 1-3" not in about and "teams of 1–3" not in about, \
            f"Old team-based text still present: {ev.get('about')}"

    def test_mock_stock_about_says_individual_via_detail(self):
        ev = self._find_mock_stock()
        r = requests.get(f"{API}/events/{ev['id']}", timeout=10)
        assert r.status_code == 200
        about = (r.json().get("about") or "").lower()
        assert "individual" in about, f"'individual' not in detail about: {about}"
        assert "teams of 1-3" not in about and "teams of 1–3" not in about, \
            f"Old team-based text still in detail: {about}"


# ======================= Iteration 6: per-event form builder =======================

def _find_event(title_substr):
    r = requests.get(f"{API}/events", timeout=10)
    assert r.status_code == 200
    matches = [e for e in r.json() if title_substr.lower() in (e.get("title") or "").lower()]
    assert matches, f"No event with '{title_substr}' found"
    return matches[0]


class TestIteration6EventFormConfig:
    """Verify backfilled per-event form-builder fields on GET /api/events."""

    def test_mock_stock_individual_config(self):
        ev = _find_event("Mock Stock")
        assert ev.get("registration_mode") == "individual"
        extras = ev.get("extra_fields") or []
        assert len(extras) == 2, f"Expected 2 extras, got {len(extras)}: {extras}"
        keys = {x.get("key"): x for x in extras}
        assert "why_join" in keys and keys["why_join"].get("type") == "textarea" and keys["why_join"].get("required") is True
        assert "has_demat" in keys and keys["has_demat"].get("type") == "yesno" and keys["has_demat"].get("required") is False

    def test_situational_team_config(self):
        ev = _find_event("Situational")
        assert ev.get("registration_mode") == "team"
        assert int(ev.get("team_size_min")) == 3
        assert int(ev.get("team_size_max")) == 5
        extras = ev.get("extra_fields") or []
        assert len(extras) == 1
        assert extras[0].get("key") == "team_tagline"
        assert extras[0].get("type") == "text"
        assert extras[0].get("required") is False


class TestIteration6IndividualValidation:
    def test_missing_required_extra_returns_400(self):
        ev = _find_event("Mock Stock")
        payload = {
            "event_id": ev["id"],
            "name": "TEST_Indiv",
            "school": "S", "grade": "11",
            "email": "test_indiv@example.com", "phone": "+91900",
            "parent_name": "P", "parent_phone": "+91901", "parent_email": "test_indiv_p@example.com",
            # extras.why_join intentionally missing
        }
        r = requests.post(f"{API}/registrations", json=payload, timeout=15)
        assert r.status_code == 400, f"Expected 400, got {r.status_code}: {r.text}"
        assert "extras.why_join" in (r.json().get("detail") or "")

    def test_with_extra_succeeds(self):
        ev = _find_event("Mock Stock")
        payload = {
            "event_id": ev["id"],
            "name": "TEST_IndivOK",
            "school": "S", "grade": "11",
            "email": "test_indiv_ok@example.com", "phone": "+91900",
            "parent_name": "P", "parent_phone": "+91901", "parent_email": "test_indiv_ok_p@example.com",
            "extras": {"why_join": "I love markets and want to learn portfolio management."}
        }
        r = requests.post(f"{API}/registrations", json=payload, timeout=30)
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
        d = r.json()
        assert d.get("ok") is True
        assert "registration_id" in d
        # Verify extras persisted
        g = requests.get(f"{API}/registrations/{d['registration_id']}", timeout=10).json()
        assert g.get("extras", {}).get("why_join")


class TestIteration6TeamValidation:
    def test_missing_team_name(self):
        ev = _find_event("Situational")
        payload = {
            "event_id": ev["id"],
            "members": [
                {"name": "A", "school": "S", "grade": "10", "email": "a@a.com", "phone": "1"},
                {"name": "B", "school": "S", "grade": "10", "email": "b@b.com", "phone": "2"},
                {"name": "C", "school": "S", "grade": "10", "email": "c@c.com", "phone": "3"},
            ],
            "parent_name": "P", "parent_phone": "+9", "parent_email": "p@p.com",
        }
        r = requests.post(f"{API}/registrations", json=payload, timeout=15)
        assert r.status_code == 400
        assert "team_name" in (r.json().get("detail") or "")

    def test_team_below_min_size(self):
        ev = _find_event("Situational")
        payload = {
            "event_id": ev["id"],
            "team_name": "TEST_TooSmall",
            "members": [
                {"name": "A", "school": "S", "grade": "10", "email": "a@a.com", "phone": "1"},
                {"name": "B", "school": "S", "grade": "10", "email": "b@b.com", "phone": "2"},
            ],
            "parent_name": "P", "parent_phone": "+9", "parent_email": "p@p.com",
        }
        r = requests.post(f"{API}/registrations", json=payload, timeout=15)
        assert r.status_code == 400
        detail = r.json().get("detail") or ""
        assert "between" in detail.lower() and "members" in detail.lower()

    def test_team_member_missing_fields(self):
        ev = _find_event("Situational")
        payload = {
            "event_id": ev["id"],
            "team_name": "TEST_BadMember",
            "members": [
                {"name": "A", "school": "S", "grade": "10", "email": "a@a.com", "phone": "1"},
                {"school": "S", "grade": "10", "phone": "2"},  # missing name + email
                {"name": "C", "school": "S", "grade": "10", "email": "c@c.com", "phone": "3"},
            ],
            "parent_name": "P", "parent_phone": "+9", "parent_email": "p@p.com",
        }
        r = requests.post(f"{API}/registrations", json=payload, timeout=15)
        assert r.status_code == 400
        detail = r.json().get("detail") or ""
        assert "members[1].name" in detail
        assert "members[1].email" in detail

    def test_valid_team_succeeds(self):
        ev = _find_event("Situational")
        payload = {
            "event_id": ev["id"],
            "team_name": "TEST_TeamOK",
            "members": [
                {"name": "TEST_A", "school": "S", "grade": "10", "email": "test_team_a@a.com", "phone": "1"},
                {"name": "TEST_B", "school": "S", "grade": "10", "email": "test_team_b@b.com", "phone": "2"},
                {"name": "TEST_C", "school": "S", "grade": "10", "email": "test_team_c@c.com", "phone": "3"},
            ],
            "parent_name": "P", "parent_phone": "+91900", "parent_email": "test_team_p@p.com",
            "extras": {"team_tagline": "We scale."}
        }
        r = requests.post(f"{API}/registrations", json=payload, timeout=30)
        assert r.status_code == 200, f"Got {r.status_code}: {r.text}"
        d = r.json()
        assert d.get("ok") is True
        rid = d["registration_id"]
        g = requests.get(f"{API}/registrations/{rid}", timeout=10).json()
        assert g.get("mode") == "team"
        assert g.get("team_name") == "TEST_TeamOK"
        assert len(g.get("members") or []) == 3
        assert g.get("extras", {}).get("team_tagline") == "We scale."


class TestIteration6AdminEditEvent:
    def test_admin_can_edit_form_config_and_persist(self, admin_headers):
        # Create a new event to avoid mutating Mock Stock / Situational (used by other tests)
        new_ev = {
            "title": f"TEST_Iter6Event_{uuid.uuid4().hex[:6]}",
            "description": "test", "about": "test about",
            "status": "live", "cta_label": "Details", "date": "TBA", "location": "Online",
            "price_inr": 100.0, "order": 99,
            "registration_mode": "individual",
            "team_size_min": 2, "team_size_max": 5,
            "eligibility": "individual eligibility text",
            "extra_fields": [],
        }
        c = requests.post(f"{API}/events", headers=admin_headers, json=new_ev, timeout=15)
        assert c.status_code == 200, c.text
        eid = c.json()["id"]
        try:
            update = {
                "registration_mode": "team",
                "team_size_min": 2,
                "team_size_max": 4,
                "eligibility": "team competition 2-4",
                "extra_fields": [
                    {"key": "tag", "label": "Team tagline", "type": "text", "required": True, "options": []}
                ],
            }
            u = requests.put(f"{API}/events/{eid}", headers=admin_headers, json=update, timeout=15)
            assert u.status_code == 200, u.text
            g = requests.get(f"{API}/events/{eid}", timeout=10).json()
            assert g.get("registration_mode") == "team"
            assert int(g.get("team_size_min")) == 2
            assert int(g.get("team_size_max")) == 4
            assert g.get("eligibility") == "team competition 2-4"
            assert len(g.get("extra_fields") or []) == 1
            assert g["extra_fields"][0]["key"] == "tag"
            assert g["extra_fields"][0]["required"] is True
        finally:
            requests.delete(f"{API}/events/{eid}", headers=admin_headers, timeout=10)

    def test_admin_create_team_event_with_extra(self, admin_headers):
        payload = {
            "title": f"TEST_TeamCreate_{uuid.uuid4().hex[:6]}",
            "description": "d", "about": "a",
            "status": "coming_soon", "cta_label": "Details", "date": "TBA", "location": "TBA",
            "price_inr": 200.0, "order": 100,
            "registration_mode": "team",
            "team_size_min": 2, "team_size_max": 4,
            "eligibility": "teams of 2-4",
            "extra_fields": [
                {"key": "tagline", "label": "Tagline", "type": "text", "required": False, "options": []}
            ],
        }
        c = requests.post(f"{API}/events", headers=admin_headers, json=payload, timeout=15)
        assert c.status_code == 200, c.text
        eid = c.json()["id"]
        try:
            g = requests.get(f"{API}/events/{eid}", timeout=10).json()
            assert g.get("registration_mode") == "team"
            assert int(g.get("team_size_min")) == 2
            assert int(g.get("team_size_max")) == 4
            assert len(g.get("extra_fields") or []) == 1
        finally:
            requests.delete(f"{API}/events/{eid}", headers=admin_headers, timeout=10)


# ======================= Iteration 7: PUT /events validation + POST Pydantic =======================
class TestIteration7PutEventValidation:
    """Iteration 7 — PUT /api/events/{id} now validates extra_fields shape, registration_mode, team_size."""

    def _get_mock_stock(self):
        return _find_event("Mock Stock")

    def test_put_rejects_bogus_registration_mode(self, admin_headers):
        ev = self._get_mock_stock()
        original_mode = ev.get("registration_mode", "individual")
        try:
            r = requests.put(
                f"{API}/events/{ev['id']}",
                headers=admin_headers,
                json={"registration_mode": "bogus"},
                timeout=10,
            )
            assert r.status_code == 400, r.text
            detail = (r.json().get("detail") or "").lower()
            assert "registration_mode" in detail and ("individual" in detail and "team" in detail), detail
        finally:
            # Restore (defensive — should not have been mutated, but belt-and-suspenders)
            requests.put(
                f"{API}/events/{ev['id']}",
                headers=admin_headers,
                json={"registration_mode": original_mode},
                timeout=10,
            )

    def test_put_rejects_invalid_extra_field_type(self, admin_headers):
        ev = self._get_mock_stock()
        original_extras = ev.get("extra_fields") or []
        try:
            r = requests.put(
                f"{API}/events/{ev['id']}",
                headers=admin_headers,
                json={"extra_fields": [{"key": "x", "label": "X", "type": "evil"}]},
                timeout=10,
            )
            assert r.status_code == 400, r.text
            detail = r.json().get("detail") or ""
            assert detail.startswith("Invalid extra_fields[0]"), f"Unexpected detail: {detail}"
        finally:
            requests.put(
                f"{API}/events/{ev['id']}",
                headers=admin_headers,
                json={"extra_fields": original_extras},
                timeout=10,
            )

    def test_put_accepts_valid_extra_field(self, admin_headers):
        ev = self._get_mock_stock()
        original_extras = ev.get("extra_fields") or []
        try:
            r = requests.put(
                f"{API}/events/{ev['id']}",
                headers=admin_headers,
                json={"extra_fields": [{"key": "q1", "label": "Q1", "type": "text"}]},
                timeout=10,
            )
            assert r.status_code == 200, r.text
            g = requests.get(f"{API}/events/{ev['id']}", timeout=10).json()
            extras = g.get("extra_fields") or []
            assert len(extras) == 1
            assert extras[0]["key"] == "q1"
            assert extras[0]["label"] == "Q1"
            assert extras[0]["type"] == "text"
        finally:
            # Restore original extras
            requests.put(
                f"{API}/events/{ev['id']}",
                headers=admin_headers,
                json={"extra_fields": original_extras},
                timeout=10,
            )

    def test_put_rejects_team_size_min_gt_max(self, admin_headers):
        ev = self._get_mock_stock()
        original_min = int(ev.get("team_size_min", 2))
        original_max = int(ev.get("team_size_max", 5))
        try:
            r = requests.put(
                f"{API}/events/{ev['id']}",
                headers=admin_headers,
                json={"team_size_min": 7, "team_size_max": 3},
                timeout=10,
            )
            assert r.status_code == 400, r.text
            detail = (r.json().get("detail") or "").lower()
            assert "team_size_min" in detail and "team_size_max" in detail, detail
        finally:
            requests.put(
                f"{API}/events/{ev['id']}",
                headers=admin_headers,
                json={"team_size_min": original_min, "team_size_max": original_max},
                timeout=10,
            )

    def test_put_rejects_non_integer_team_size_min(self, admin_headers):
        ev = self._get_mock_stock()
        r = requests.put(
            f"{API}/events/{ev['id']}",
            headers=admin_headers,
            json={"team_size_min": "notanumber"},
            timeout=10,
        )
        assert r.status_code == 400, r.text
        detail = (r.json().get("detail") or "")
        assert "team_size_min must be an integer" in detail, detail

    def test_post_event_with_invalid_extra_field_type_rejected_by_pydantic(self, admin_headers):
        """EventItem.extra_fields: List[ExtraField] now enforces Literal types via Pydantic -> 422."""
        payload = {
            "title": f"TEST_Iter7Bad_{uuid.uuid4().hex[:6]}",
            "description": "d", "about": "a",
            "status": "coming_soon", "cta_label": "Details", "date": "TBA", "location": "TBA",
            "price_inr": 0.0, "order": 999,
            "extra_fields": [{"key": "bad", "label": "Bad", "type": "not-a-valid-type"}],
        }
        r = requests.post(f"{API}/events", headers=admin_headers, json=payload, timeout=15)
        # Pydantic validation failure -> 422 (FastAPI default)
        assert r.status_code == 422, f"Expected 422, got {r.status_code}: {r.text}"
        # If it somehow gets in, clean up
        if r.status_code == 200:
            try:
                requests.delete(f"{API}/events/{r.json()['id']}", headers=admin_headers, timeout=10)
            except Exception:
                pass



# ======================= Iteration 8: registration_open gate =======================
class TestIteration8RegistrationOpenGate:
    """Iteration 8 — admin can disable registration per event; POST /registrations -> 403 when closed."""

    def _get_mock_stock(self):
        return _find_event("Mock Stock")

    def test_event_has_registration_open_default_true(self):
        ev = self._get_mock_stock()
        # Field must exist and default true
        assert ev.get("registration_open") is True, f"Expected registration_open True by default, got {ev.get('registration_open')}"
        # closed message field exists (string, may be default)
        assert "registration_closed_message" in ev

    def test_put_can_toggle_registration_open_and_message(self, admin_headers):
        ev = self._get_mock_stock()
        eid = ev["id"]
        original_open = ev.get("registration_open", True)
        original_msg = ev.get("registration_closed_message", "")
        try:
            r = requests.put(
                f"{API}/events/{eid}",
                headers=admin_headers,
                json={"registration_open": False, "registration_closed_message": "TEST_ClosedMsg"},
                timeout=15,
            )
            assert r.status_code == 200, r.text
            g = requests.get(f"{API}/events/{eid}", timeout=10).json()
            assert g.get("registration_open") is False
            assert g.get("registration_closed_message") == "TEST_ClosedMsg"
        finally:
            # Restore
            requests.put(
                f"{API}/events/{eid}",
                headers=admin_headers,
                json={"registration_open": original_open, "registration_closed_message": original_msg},
                timeout=15,
            )

    def test_post_registration_blocked_when_closed_then_allowed_when_open(self, admin_headers):
        ev = self._get_mock_stock()
        eid = ev["id"]
        original_open = ev.get("registration_open", True)
        original_msg = ev.get("registration_closed_message", "")
        try:
            # Close it
            cu = requests.put(
                f"{API}/events/{eid}",
                headers=admin_headers,
                json={"registration_open": False, "registration_closed_message": "Closed for testing"},
                timeout=15,
            )
            assert cu.status_code == 200, cu.text

            payload = {
                "event_id": eid,
                "name": "TEST_Iter8Closed",
                "school": "S", "grade": "11",
                "email": f"test_iter8_closed_{uuid.uuid4().hex[:6]}@example.com", "phone": "+91900",
                "parent_name": "P", "parent_phone": "+91901",
                "parent_email": f"test_iter8_closed_p_{uuid.uuid4().hex[:6]}@example.com",
                "extras": {"why_join": "testing closed gate"},
            }
            r = requests.post(f"{API}/registrations", json=payload, timeout=15)
            assert r.status_code == 403, f"Expected 403 when closed, got {r.status_code}: {r.text}"
            detail = (r.json().get("detail") or "").lower()
            assert "registration is closed" in detail or "closed" in detail, detail

            # Re-open
            ru = requests.put(
                f"{API}/events/{eid}",
                headers=admin_headers,
                json={"registration_open": True, "registration_closed_message": ""},
                timeout=15,
            )
            assert ru.status_code == 200, ru.text

            payload["email"] = f"test_iter8_open_{uuid.uuid4().hex[:6]}@example.com"
            payload["parent_email"] = f"test_iter8_open_p_{uuid.uuid4().hex[:6]}@example.com"
            payload["name"] = "TEST_Iter8Open"
            r2 = requests.post(f"{API}/registrations", json=payload, timeout=30)
            assert r2.status_code == 200, f"Expected 200 when re-opened, got {r2.status_code}: {r2.text}"
            assert r2.json().get("ok") is True
        finally:
            # ALWAYS restore original state
            requests.put(
                f"{API}/events/{eid}",
                headers=admin_headers,
                json={"registration_open": original_open, "registration_closed_message": original_msg},
                timeout=15,
            )
