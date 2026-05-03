"""Iteration 9 backend tests — Custom Pages CMS + extended ExtraField types + member-scope extras."""
import os
import uuid
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
API = f"{BASE_URL}/api"

ADMIN_EMAIL = "scalesupportteam2@gmail.com"
ADMIN_PASSWORD = "SCALEdaddySALLU67"


@pytest.fixture(scope="module")
def admin_headers():
    r = requests.post(f"{API}/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}, timeout=15)
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['token']}"}


def _find_event(title_substr):
    r = requests.get(f"{API}/events", timeout=10)
    assert r.status_code == 200
    matches = [e for e in r.json() if title_substr.lower() in (e.get("title") or "").lower()]
    assert matches, f"No event with '{title_substr}' found"
    return matches[0]


# ===================== Pages CMS =====================
class TestPagesCMS:
    def test_public_list_pages(self):
        r = requests.get(f"{API}/pages", timeout=10)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_admin_list_pages_requires_auth(self):
        r = requests.get(f"{API}/admin/pages", timeout=10)
        assert r.status_code in (401, 403)

    def test_admin_list_pages_with_auth(self, admin_headers):
        r = requests.get(f"{API}/admin/pages", headers=admin_headers, timeout=10)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_create_page_without_auth_forbidden(self):
        r = requests.post(f"{API}/pages", json={
            "slug": "test-noauth", "title": "x"
        }, timeout=10)
        assert r.status_code in (401, 403)

    def test_get_page_by_slug_404(self):
        r = requests.get(f"{API}/pages/does-not-exist-xyz-{uuid.uuid4().hex[:6]}", timeout=10)
        assert r.status_code == 404

    def test_create_update_get_delete_page(self, admin_headers):
        slug = f"test-page-{uuid.uuid4().hex[:6]}"
        body = {
            "slug": slug,
            "title": "TEST Page",
            "nav_label": "TEST Nav",
            "show_in_nav": True,
            "published": True,
            "order": 50,
            "blocks": [
                {"type": "hero", "props": {"headline": "Hello", "sub": "World"}},
                {"type": "section", "props": {"body": "Lorem ipsum"}},
            ],
        }
        c = requests.post(f"{API}/pages", headers=admin_headers, json=body, timeout=15)
        assert c.status_code == 200, c.text
        created = c.json()
        page_id = created["id"]
        assert created["slug"] == slug
        assert len(created["blocks"]) == 2
        assert created["blocks"][0]["type"] == "hero"

        try:
            # Duplicate slug should fail
            d = requests.post(f"{API}/pages", headers=admin_headers, json=body, timeout=15)
            assert d.status_code == 400, d.text
            assert "already exists" in (d.json().get("detail") or "").lower()

            # Public GET by slug
            g = requests.get(f"{API}/pages/{slug}", timeout=10)
            assert g.status_code == 200
            assert g.json()["title"] == "TEST Page"

            # Public list should include it (since published=True)
            lst = requests.get(f"{API}/pages", timeout=10).json()
            assert any(p["slug"] == slug for p in lst)

            # PUT partial update — only title
            u = requests.put(f"{API}/pages/{page_id}", headers=admin_headers,
                             json={"title": "TEST Page Updated"}, timeout=15)
            assert u.status_code == 200, u.text
            assert u.json()["title"] == "TEST Page Updated"
            assert u.json()["slug"] == slug  # unchanged

            # PUT slug uniqueness: create a 2nd page and try to steal its slug
            slug2 = f"test-clash-{uuid.uuid4().hex[:6]}"
            c2 = requests.post(f"{API}/pages", headers=admin_headers,
                               json={"slug": slug2, "title": "Other"}, timeout=15)
            assert c2.status_code == 200
            page_id2 = c2.json()["id"]
            try:
                clash = requests.put(f"{API}/pages/{page_id}", headers=admin_headers,
                                     json={"slug": slug2}, timeout=15)
                assert clash.status_code == 400, clash.text
                assert "already in use" in (clash.json().get("detail") or "").lower()
            finally:
                requests.delete(f"{API}/pages/{page_id2}", headers=admin_headers, timeout=10)

            # Unpublish — should disappear from public list but still in admin list
            up = requests.put(f"{API}/pages/{page_id}", headers=admin_headers,
                              json={"published": False}, timeout=15)
            assert up.status_code == 200
            lst2 = requests.get(f"{API}/pages", timeout=10).json()
            assert not any(p["slug"] == slug for p in lst2)
            alst = requests.get(f"{API}/admin/pages", headers=admin_headers, timeout=10).json()
            assert any(p["slug"] == slug for p in alst)
        finally:
            # DELETE
            dl = requests.delete(f"{API}/pages/{page_id}", headers=admin_headers, timeout=10)
            assert dl.status_code == 200
            # Confirm it's gone
            g2 = requests.get(f"{API}/pages/{slug}", timeout=10)
            assert g2.status_code == 404

    def test_create_page_empty_slug_rejected(self, admin_headers):
        r = requests.post(f"{API}/pages", headers=admin_headers,
                          json={"slug": "   ", "title": "x"}, timeout=10)
        assert r.status_code == 400
        assert "slug" in (r.json().get("detail") or "").lower()


# ===================== ExtraField new types =====================
class TestExtraFieldNewTypes:
    def test_create_event_with_all_field_types(self, admin_headers):
        payload = {
            "title": f"TEST_ExtraTypes_{uuid.uuid4().hex[:6]}",
            "description": "d", "about": "a",
            "status": "coming_soon", "cta_label": "x",
            "date": "TBA", "location": "TBA",
            "price_inr": 0.0, "order": 900,
            "registration_mode": "individual",
            "extra_fields": [
                {"key": "f_text", "label": "T", "type": "text", "required": True},
                {"key": "f_ta", "label": "TA", "type": "textarea"},
                {"key": "f_email", "label": "E", "type": "email", "required": True},
                {"key": "f_num", "label": "N", "type": "number"},
                {"key": "f_yn", "label": "YN", "type": "yesno"},
                {"key": "f_sel", "label": "S", "type": "select", "options": ["A", "B"]},
                {"key": "f_radio", "label": "R", "type": "radio", "options": ["X", "Y"]},
                {"key": "f_chk", "label": "C", "type": "checkbox"},
                {"key": "f_file", "label": "F", "type": "file", "help_text": "upload me"},
            ],
        }
        c = requests.post(f"{API}/events", headers=admin_headers, json=payload, timeout=15)
        assert c.status_code == 200, c.text
        eid = c.json()["id"]
        try:
            g = requests.get(f"{API}/events/{eid}", timeout=10).json()
            types = [x["type"] for x in g["extra_fields"]]
            assert types == ["text", "textarea", "email", "number", "yesno", "select", "radio", "checkbox", "file"]
            assert g["extra_fields"][8]["help_text"] == "upload me"

            # Missing required f_text + f_email should 400
            bad = {
                "event_id": eid,
                "name": "TEST_x", "school": "s", "grade": "11",
                "email": "tx@example.com", "phone": "+9",
                "parent_name": "p", "parent_phone": "+9", "parent_email": "p@p.com",
                "extras": {"f_num": "5"},
            }
            rb = requests.post(f"{API}/registrations", json=bad, timeout=15)
            assert rb.status_code == 400, rb.text
            detail = rb.json().get("detail") or ""
            assert "extras.f_text" in detail and "extras.f_email" in detail, detail

            # Full success — non-required can be empty
            good = dict(bad)
            good["email"] = f"test_all_{uuid.uuid4().hex[:6]}@example.com"
            good["parent_email"] = f"test_all_p_{uuid.uuid4().hex[:6]}@example.com"
            good["extras"] = {
                "f_text": "hello", "f_email": "student@example.com",
                "f_num": "42", "f_yn": "yes", "f_sel": "A", "f_radio": "X", "f_chk": "on",
            }
            rg = requests.post(f"{API}/registrations", json=good, timeout=30)
            assert rg.status_code == 200, rg.text
            rid = rg.json()["registration_id"]
            rec = requests.get(f"{API}/registrations/{rid}", timeout=10).json()
            assert rec["extras"]["f_text"] == "hello"
            assert rec["extras"]["f_email"] == "student@example.com"
            assert rec["extras"]["f_num"] == "42"
        finally:
            requests.delete(f"{API}/events/{eid}", headers=admin_headers, timeout=10)

    def test_invalid_field_type_rejected(self, admin_headers):
        payload = {
            "title": f"TEST_BadType_{uuid.uuid4().hex[:6]}",
            "description": "d", "about": "a",
            "status": "coming_soon", "cta_label": "x",
            "extra_fields": [{"key": "k", "label": "L", "type": "url"}],
        }
        r = requests.post(f"{API}/events", headers=admin_headers, json=payload, timeout=10)
        assert r.status_code == 422, r.text


# ===================== Member-scope extras =====================
class TestMemberScopeExtras:
    def test_team_event_with_member_scope_extras(self, admin_headers):
        payload = {
            "title": f"TEST_TeamMemberScope_{uuid.uuid4().hex[:6]}",
            "description": "d", "about": "a",
            "status": "coming_soon", "cta_label": "x",
            "date": "TBA", "location": "TBA",
            "price_inr": 0.0, "order": 950,
            "registration_mode": "team",
            "team_size_min": 2, "team_size_max": 3,
            "extra_fields": [
                {"key": "tagline", "label": "Tagline", "type": "text", "required": True, "scope": "team"},
                {"key": "shirt", "label": "Shirt", "type": "select", "options": ["S", "M", "L"],
                 "required": True, "scope": "member"},
                {"key": "diet", "label": "Diet", "type": "text", "required": False, "scope": "member"},
            ],
        }
        c = requests.post(f"{API}/events", headers=admin_headers, json=payload, timeout=15)
        assert c.status_code == 200, c.text
        eid = c.json()["id"]
        try:
            g = requests.get(f"{API}/events/{eid}", timeout=10).json()
            scopes = {f["key"]: f.get("scope") for f in g["extra_fields"]}
            assert scopes["tagline"] == "team"
            assert scopes["shirt"] == "member"
            assert scopes["diet"] == "member"

            # Missing per-member required extra -> 400
            bad = {
                "event_id": eid,
                "team_name": "TEST_TeamA",
                "members": [
                    {"name": "A", "school": "S", "grade": "10", "email": "a@a.com", "phone": "1",
                     "extras": {"shirt": "M"}},
                    {"name": "B", "school": "S", "grade": "10", "email": "b@b.com", "phone": "2"},
                    # member 1 missing shirt
                ],
                "parent_name": "P", "parent_phone": "+9", "parent_email": "p@p.com",
                "extras": {"tagline": "We scale"},
            }
            rb = requests.post(f"{API}/registrations", json=bad, timeout=15)
            assert rb.status_code == 400, rb.text
            detail = rb.json().get("detail") or ""
            assert "members[1].extras.shirt" in detail, detail

            # Valid team with all member-scope extras
            good = {
                "event_id": eid,
                "team_name": "TEST_TeamOK",
                "members": [
                    {"name": "TEST_A", "school": "S", "grade": "10",
                     "email": f"test_ms_a_{uuid.uuid4().hex[:5]}@a.com", "phone": "1",
                     "extras": {"shirt": "M", "diet": "veg"}},
                    {"name": "TEST_B", "school": "S", "grade": "10",
                     "email": f"test_ms_b_{uuid.uuid4().hex[:5]}@b.com", "phone": "2",
                     "extras": {"shirt": "L"}},
                ],
                "parent_name": "P", "parent_phone": "+91900",
                "parent_email": f"test_ms_p_{uuid.uuid4().hex[:5]}@p.com",
                "extras": {"tagline": "Scale!"},
            }
            rg = requests.post(f"{API}/registrations", json=good, timeout=30)
            assert rg.status_code == 200, rg.text
            rid = rg.json()["registration_id"]
            rec = requests.get(f"{API}/registrations/{rid}", timeout=10).json()
            # Persistence of per-member extras
            members = rec.get("members") or []
            assert len(members) == 2
            mem_extras = [(m.get("extras") or {}) for m in members]
            assert mem_extras[0].get("shirt") == "M"
            assert mem_extras[0].get("diet") == "veg"
            assert mem_extras[1].get("shirt") == "L"
            # Team-scope extras persisted at top
            assert rec.get("extras", {}).get("tagline") == "Scale!"
        finally:
            requests.delete(f"{API}/events/{eid}", headers=admin_headers, timeout=10)


# ===================== Spot check existing =====================
class TestSpotCheckExisting:
    def test_get_events_still_works(self):
        r = requests.get(f"{API}/events", timeout=10)
        assert r.status_code == 200
        assert len(r.json()) >= 1

    def test_get_content_still_works(self):
        r = requests.get(f"{API}/content", timeout=10)
        assert r.status_code == 200
        assert r.json().get("id") == "main"

    def test_admin_login_still_works(self):
        r = requests.post(f"{API}/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}, timeout=10)
        assert r.status_code == 200
