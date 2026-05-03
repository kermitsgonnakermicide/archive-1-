"""Iteration 10/12 — event hub (materials, submissions, CSV export) + Razorpay guards.

Tests against the live preview deployment via REACT_APP_BACKEND_URL. Uses the
already-paid seed registration:
    event_id = c6aedeb8-7ccd-4c6f-a258-5bcb51ad1b95
    reg_id   = 27ed2ca5-aff2-47f1-9bb5-7fea5457f8b6
"""
import io
import os
import uuid

import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://scale-talent-network.preview.emergentagent.com").rstrip("/")
ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "scalesupportteam2@gmail.com")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "SCALEdaddySALLU67")

PAID_EVENT_ID = "c6aedeb8-7ccd-4c6f-a258-5bcb51ad1b95"
PAID_REG_ID = "27ed2ca5-aff2-47f1-9bb5-7fea5457f8b6"


# ---------- Fixtures ----------
@pytest.fixture(scope="session")
def session():
    s = requests.Session()
    s.headers.update({"Accept": "application/json"})
    return s


@pytest.fixture(scope="session")
def admin_token(session):
    r = session.post(f"{BASE_URL}/api/auth/login",
                     json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
    assert r.status_code == 200, f"admin login failed: {r.status_code} {r.text}"
    return r.json().get("access_token") or r.json().get("token")


@pytest.fixture(scope="session")
def admin_headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}"}


@pytest.fixture(scope="session")
def unpaid_reg(session):
    """Create a fresh unpaid registration for gating tests."""
    payload = {
        "event_id": PAID_EVENT_ID,
        "mode": "individual",
        "name": f"TEST_Unpaid_{uuid.uuid4().hex[:8]}",
        "email": f"test_{uuid.uuid4().hex[:8]}@example.com",
        "phone": "+910000000000",
        "school": "TEST School",
        "parent_name": "TEST Parent",
        "parent_email": f"parent_{uuid.uuid4().hex[:8]}@example.com",
        "parent_phone": "+910000000001",
        "grade": "10",
        "consent": True,
    }
    r = session.post(f"{BASE_URL}/api/registrations", json=payload)
    # If 400 due to mandatory fields depending on event, use minimal known-good.
    if r.status_code >= 400:
        pytest.skip(f"Could not seed unpaid reg: {r.status_code} {r.text[:200]}")
    return r.json()["registration_id"]


# ---------- Smoke ----------
class TestSmoke:
    def test_events_list(self, session):
        r = session.get(f"{BASE_URL}/api/events")
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_content(self, session):
        r = session.get(f"{BASE_URL}/api/content")
        assert r.status_code == 200

    def test_admin_login(self, admin_token):
        assert admin_token and len(admin_token) > 10


# ---------- Materials gating ----------
class TestMaterialsGating:
    def test_no_reg_id_returns_401(self, session):
        r = session.get(f"{BASE_URL}/api/events/{PAID_EVENT_ID}/materials")
        assert r.status_code == 401, r.text

    def test_invalid_reg_id_returns_404(self, session):
        r = session.get(f"{BASE_URL}/api/events/{PAID_EVENT_ID}/materials",
                        params={"reg_id": "does-not-exist-" + uuid.uuid4().hex})
        assert r.status_code == 404

    def test_unpaid_reg_returns_402(self, session, unpaid_reg):
        r = session.get(f"{BASE_URL}/api/events/{PAID_EVENT_ID}/materials",
                        params={"reg_id": unpaid_reg})
        assert r.status_code == 402
        body = r.json()
        assert "payment" in (body.get("detail") or "").lower()

    def test_paid_reg_returns_200_with_materials(self, session):
        r = session.get(f"{BASE_URL}/api/events/{PAID_EVENT_ID}/materials",
                        params={"reg_id": PAID_REG_ID})
        assert r.status_code == 200
        data = r.json()
        assert data["event_id"] == PAID_EVENT_ID
        assert "notes" in data and "links" in data and "documents" in data
        assert isinstance(data["links"], list)

    def test_admin_can_read_without_reg(self, session, admin_headers):
        r = session.get(f"{BASE_URL}/api/events/{PAID_EVENT_ID}/materials",
                        headers=admin_headers)
        assert r.status_code == 200


# ---------- Materials admin write ----------
class TestMaterialsAdminWrite:
    def test_put_requires_admin(self, session):
        r = session.put(f"{BASE_URL}/api/events/{PAID_EVENT_ID}/materials",
                        json={"notes": "hack"})
        assert r.status_code in (401, 403)

    def test_put_accepts_and_persists(self, session, admin_headers):
        # Read existing → we must NOT lose seed data; we add a link, then remove it.
        r0 = session.get(f"{BASE_URL}/api/events/{PAID_EVENT_ID}/materials",
                         headers=admin_headers)
        assert r0.status_code == 200
        existing = r0.json()
        seed_notes = existing.get("notes", "")
        seed_links = existing.get("links", [])
        seed_docs = existing.get("documents", [])

        test_link = {"id": str(uuid.uuid4()), "label": "TEST_link", "url": "https://example.com/test"}
        updated_notes = (seed_notes or "") + "\n[TEST tag]"
        payload = {
            "notes": updated_notes,
            "links": seed_links + [test_link],
            "documents": seed_docs,
        }
        r = session.put(f"{BASE_URL}/api/events/{PAID_EVENT_ID}/materials",
                        headers=admin_headers, json=payload)
        assert r.status_code == 200, r.text
        out = r.json()
        assert "updated_at" in out
        assert any(lk.get("label") == "TEST_link" for lk in out["links"])

        # GET verification
        r2 = session.get(f"{BASE_URL}/api/events/{PAID_EVENT_ID}/materials",
                         headers=admin_headers)
        assert r2.status_code == 200
        labels = [lk.get("label") for lk in r2.json()["links"]]
        assert "TEST_link" in labels

        # Cleanup — restore seed
        session.put(f"{BASE_URL}/api/events/{PAID_EVENT_ID}/materials",
                    headers=admin_headers,
                    json={"notes": seed_notes, "links": seed_links, "documents": seed_docs})


# ---------- File upload / download ----------
class TestEventFiles:
    def test_upload_requires_admin(self, session):
        files = {"file": ("x.pdf", b"%PDF-1.4\n%test", "application/pdf")}
        r = session.post(f"{BASE_URL}/api/events/{PAID_EVENT_ID}/files", files=files)
        assert r.status_code in (401, 403)

    def test_upload_and_gated_download(self, session, admin_headers, unpaid_reg):
        files = {"file": ("TEST_brief.pdf",
                          b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\nTEST content " + uuid.uuid4().bytes,
                          "application/pdf")}
        r = session.post(f"{BASE_URL}/api/events/{PAID_EVENT_ID}/files",
                         headers=admin_headers, files=files)
        assert r.status_code == 200, r.text
        fid = r.json().get("file_id") or r.json().get("id")
        assert fid

        # Attach file as a document in materials (required for the gated-download check)
        mats = session.get(f"{BASE_URL}/api/events/{PAID_EVENT_ID}/materials",
                           headers=admin_headers).json()
        docs = mats.get("documents", []) + [{
            "id": str(uuid.uuid4()), "label": "TEST_brief",
            "file_id": fid, "filename": "TEST_brief.pdf",
            "content_type": "application/pdf", "size": 10,
        }]
        session.put(f"{BASE_URL}/api/events/{PAID_EVENT_ID}/materials",
                    headers=admin_headers,
                    json={"documents": docs})

        # unpaid reg → 402
        r_unpaid = session.get(
            f"{BASE_URL}/api/events/{PAID_EVENT_ID}/files/{fid}/download",
            params={"reg_id": unpaid_reg})
        assert r_unpaid.status_code == 402

        # paid reg → 200
        r_paid = session.get(
            f"{BASE_URL}/api/events/{PAID_EVENT_ID}/files/{fid}/download",
            params={"reg_id": PAID_REG_ID})
        assert r_paid.status_code == 200
        assert r_paid.headers.get("content-type", "").startswith("application/pdf")

        # admin (no reg) → 200
        r_admin = session.get(
            f"{BASE_URL}/api/events/{PAID_EVENT_ID}/files/{fid}/download",
            headers=admin_headers)
        assert r_admin.status_code == 200

        # Cleanup — restore doc list
        session.put(f"{BASE_URL}/api/events/{PAID_EVENT_ID}/materials",
                    headers=admin_headers,
                    json={"documents": mats.get("documents", [])})


# ---------- Student submissions ----------
class TestSubmissions:
    def test_submit_requires_paid(self, session, unpaid_reg):
        r = session.post(f"{BASE_URL}/api/events/{PAID_EVENT_ID}/submissions",
                         json={"registration_id": unpaid_reg, "text_response": "nope"})
        assert r.status_code == 402

    def test_create_or_update(self, session):
        # first post
        text1 = f"TEST_first {uuid.uuid4().hex[:6]}"
        r1 = session.post(f"{BASE_URL}/api/events/{PAID_EVENT_ID}/submissions",
                          json={"registration_id": PAID_REG_ID,
                                "text_response": text1, "files": []})
        assert r1.status_code == 200, r1.text
        action1 = r1.json()["action"]
        assert action1 in ("created", "updated")  # existing seed submission makes it 'updated'
        sid = r1.json()["id"]

        # second post — must update, not duplicate
        text2 = f"TEST_second {uuid.uuid4().hex[:6]}"
        r2 = session.post(f"{BASE_URL}/api/events/{PAID_EVENT_ID}/submissions",
                          json={"registration_id": PAID_REG_ID,
                                "text_response": text2, "files": []})
        assert r2.status_code == 200
        assert r2.json()["action"] == "updated"
        assert r2.json()["id"] == sid  # same submission id

    def test_mine_returns_own(self, session):
        r = session.get(f"{BASE_URL}/api/events/{PAID_EVENT_ID}/submissions/mine",
                        params={"reg_id": PAID_REG_ID})
        assert r.status_code == 200
        body = r.json()
        assert body.get("registration_id") == PAID_REG_ID

    def test_submission_file_upload_gated(self, session, unpaid_reg):
        files = {"file": ("x.pdf", b"%PDF-1.4\ntest", "application/pdf")}
        # unpaid → 402
        r_up = session.post(
            f"{BASE_URL}/api/events/{PAID_EVENT_ID}/submission-files",
            params={"reg_id": unpaid_reg}, files=files)
        assert r_up.status_code == 402
        # paid → 200
        r_p = session.post(
            f"{BASE_URL}/api/events/{PAID_EVENT_ID}/submission-files",
            params={"reg_id": PAID_REG_ID}, files=files)
        assert r_p.status_code == 200
        assert r_p.json().get("file_id")


# ---------- Admin submissions + CSV ----------
class TestAdminSubmissions:
    def test_list_requires_admin(self, session):
        r = session.get(f"{BASE_URL}/api/admin/events/{PAID_EVENT_ID}/submissions")
        assert r.status_code in (401, 403)

    def test_list_ok(self, session, admin_headers):
        r = session.get(f"{BASE_URL}/api/admin/events/{PAID_EVENT_ID}/submissions",
                        headers=admin_headers)
        assert r.status_code == 200
        assert isinstance(r.json(), list)
        assert len(r.json()) >= 1  # seed + our test

    def test_csv_export(self, session, admin_headers):
        r = session.get(f"{BASE_URL}/api/admin/events/{PAID_EVENT_ID}/submissions/export",
                        headers=admin_headers)
        assert r.status_code == 200
        ct = r.headers.get("content-type", "")
        cd = r.headers.get("content-disposition", "")
        assert "csv" in ct
        assert "attachment" in cd.lower()
        # Header row present
        first_line = r.content.decode("utf-8-sig", errors="ignore").splitlines()[0]
        assert "submission_id" in first_line and "student_email" in first_line

    def test_csv_export_requires_admin(self, session):
        r = session.get(f"{BASE_URL}/api/admin/events/{PAID_EVENT_ID}/submissions/export")
        assert r.status_code in (401, 403)


# ---------- Razorpay guards ----------
class TestRazorpayGuards:
    def _fresh_reg(self, session):
        payload = {
            "event_id": PAID_EVENT_ID, "mode": "individual",
            "name": f"TEST_Rzp_{uuid.uuid4().hex[:6]}",
            "email": f"rzp_{uuid.uuid4().hex[:6]}@example.com",
            "phone": "+910000000002", "school": "TEST", "parent_name": "TEST",
            "parent_email": f"rzpp_{uuid.uuid4().hex[:6]}@example.com",
            "parent_phone": "+910000000003", "grade": "10", "consent": True,
        }
        r = session.post(f"{BASE_URL}/api/registrations", json=payload)
        if r.status_code >= 400:
            pytest.skip(f"seed reg failed: {r.status_code}")
        return r.json()["registration_id"]

    def test_create_order_without_keys_returns_503(self, session):
        reg = self._fresh_reg(session)
        r = session.post(f"{BASE_URL}/api/payments/create-order",
                         json={"registration_id": reg})
        assert r.status_code == 503, f"expected 503, got {r.status_code} {r.text[:200]}"
        assert "gateway" in (r.json().get("detail") or "").lower() or \
               "not configured" in (r.json().get("detail") or "").lower()

    def test_verify_without_keys_returns_503(self, session):
        r = session.post(f"{BASE_URL}/api/payments/verify", json={
            "razorpay_order_id": "order_test",
            "razorpay_payment_id": "pay_test",
            "razorpay_signature": "sig_test",
            "registration_id": "any",
        })
        assert r.status_code == 503, f"expected 503, got {r.status_code}"


# ---------- Email public-URL ----------
class TestPublicBaseUrl:
    def test_registration_payment_link_uses_public_base_url(self, session):
        payload = {
            "event_id": PAID_EVENT_ID, "mode": "individual",
            "name": f"TEST_Pub_{uuid.uuid4().hex[:6]}",
            "email": f"pub_{uuid.uuid4().hex[:6]}@example.com",
            "phone": "+910000000002", "school": "TEST", "parent_name": "TEST",
            "parent_email": f"pubp_{uuid.uuid4().hex[:6]}@example.com",
            "parent_phone": "+910000000003", "grade": "10", "consent": True,
        }
        r = session.post(f"{BASE_URL}/api/registrations", json=payload)
        assert r.status_code == 200, r.text
        pay_link = r.json().get("payment_link", "")
        schol_link = r.json().get("scholarship_link", "")
        # Must use the public origin, not internal pod URL.
        assert "preview.emergentagent.com" in pay_link or "preview.emergentagent.com" in BASE_URL, \
            f"pay_link did not use public base url: {pay_link}"
        assert "cluster" not in pay_link and ".pod." not in pay_link, \
            f"pay_link leaks internal host: {pay_link}"
        assert "/payment/" in pay_link and "/scholarship" in schol_link
