"""SCALE — national student org website backend."""
from fastapi import FastAPI, APIRouter, HTTPException, Depends, Request, UploadFile, File, Response
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import re
import base64
import logging
import uuid
import requests
import bcrypt
import jwt
from pathlib import Path
from pydantic import BaseModel, Field, EmailStr, ConfigDict
from typing import List, Optional, Literal
from datetime import datetime, timezone, timedelta

from email_service import send_email, notify_admin
from storage_service import init_storage, put_object, get_object, build_upload_path

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

# --- MongoDB ---
mongo_url = os.environ["MONGO_URL"]
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ["DB_NAME"]]

JWT_SECRET = os.environ.get("JWT_SECRET", "scale-dev-secret")
JWT_ALG = "HS256"
JWT_EXP_HOURS = 24 * 7

app = FastAPI(title="SCALE India API")
api_router = APIRouter(prefix="/api")

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

security = HTTPBearer(auto_error=False)


# ===================== Models =====================
def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class User(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    email: EmailStr
    name: str = ""
    role: str = "user"
    created_at: str = Field(default_factory=now_iso)


class UserCreate(BaseModel):
    email: EmailStr
    password: str
    name: Optional[str] = ""


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class ExtraField(BaseModel):
    key: str
    label: str
    type: Literal[
        "text", "textarea", "email", "number",
        "yesno", "select", "checkbox", "radio", "file",
    ] = "text"
    required: bool = False
    options: List[str] = []  # for select / radio
    # In team-mode events, "team" = single answer for the team (captain fills),
    # "member" = each member answers individually. Ignored for individual-mode events.
    scope: Literal["team", "member"] = "team"
    help_text: str = ""


class EventItem(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    description: str = ""
    about: str = ""  # long-form for detail page
    status: str = "live"  # live | coming_soon
    cta_label: str = "Event Details"
    date: str = ""
    location: str = ""
    price_inr: float = 500.0
    order: int = 0
    # Per-event form config
    registration_mode: Literal["individual", "team"] = "individual"
    team_size_min: int = 2
    team_size_max: int = 5
    eligibility: str = ""
    extra_fields: List[ExtraField] = []
    registration_open: bool = True
    registration_closed_message: str = "Registration is currently closed for this event. Check back soon."


class EventUpdate(BaseModel):
    """Partial update schema for PUT /events/{id}. All fields optional; enforces
    the same type constraints as EventItem when provided. Use .model_dump(exclude_unset=True)
    to persist only what the admin sent. Extra fields (like `id`, `created_at`) are
    silently ignored — the frontend often round-trips the full event object."""
    model_config = ConfigDict(extra="ignore")

    title: Optional[str] = None
    description: Optional[str] = None
    about: Optional[str] = None
    status: Optional[Literal["live", "coming_soon"]] = None
    cta_label: Optional[str] = None
    date: Optional[str] = None
    location: Optional[str] = None
    price_inr: Optional[float] = None
    order: Optional[int] = None
    registration_mode: Optional[Literal["individual", "team"]] = None
    team_size_min: Optional[int] = None
    team_size_max: Optional[int] = None
    eligibility: Optional[str] = None
    extra_fields: Optional[List[ExtraField]] = None
    registration_open: Optional[bool] = None
    registration_closed_message: Optional[str] = None


def _serialize_event(doc: dict) -> dict:
    """Run a DB doc through EventItem to apply defaults to legacy rows."""
    if not doc:
        return doc
    return EventItem(**doc).model_dump()


class SessionItem(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    topic: str
    speaker: str
    date: str
    description: str = ""
    order: int = 0


class ContactForm(BaseModel):
    name: str
    school: Optional[str] = ""
    subject: str
    message: str
    email: EmailStr


class EventRegistrationForm(BaseModel):
    """Flexible registration payload; shape validated server-side per event config."""
    event_id: str
    # Individual mode fields (required when mode == individual)
    name: Optional[str] = None
    school: Optional[str] = None
    grade: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    parent_name: Optional[str] = None
    parent_phone: Optional[str] = None
    parent_email: Optional[EmailStr] = None
    # Team mode fields (required when mode == team)
    team_name: Optional[str] = None
    members: Optional[List[dict]] = None  # [{name, school, grade, email, phone}]
    # Custom extra answers
    extras: Optional[dict] = None  # {key: value}


class EventScholarshipForm(BaseModel):
    event_id: str
    name: str
    school: str
    grade: str
    email: EmailStr
    phone: str
    parent_name: str
    parent_email: EmailStr
    financial_proof: str  # text describing situation / link to doc
    why_participate: str
    proof_file_id: Optional[str] = None  # uploaded file reference (FileRef.id)


class ThemeConfig(BaseModel):
    crimson: str = "#B01020"
    dark_red: str = "#4A0008"
    white: str = "#FFFFFF"
    off_white: str = "#FAF8F5"
    black: str = "#0F0F0F"
    gold: str = "#C9931A"
    gold_light: str = "#F5C842"
    cream: str = "#F4ECD8"


class SiteContent(BaseModel):
    """All editable text blocks. Single document with id='main'."""
    id: str = "main"
    hero_label: str = "India's First National Student Organisation"
    hero_headline: str = "India's Home for the Next Generation of Business, Finance & Leadership Talent."
    hero_subtext: str = "SCALE gives India's high school students real-world business experience through competitions, expert sessions, and a national community of equally ambitious peers."
    hero_cta_primary: str = "Explore Events"
    hero_cta_secondary: str = "Our Story"
    fields_strip: List[str] = ["Business Strategy", "Finance & Investing", "Marketing", "Leadership"]
    pillars: List[dict] = [
        {"title": "PARTICIPATE", "desc": "Join national competitions that test your business, finance, and leadership instincts against India's sharpest high schoolers."},
        {"title": "LEARN", "desc": "Attend exclusive sessions with industry leaders, founders, investors, and analysts shaping the economy."},
        {"title": "LEAD", "desc": "Step up as a chapter head, competition captain, or national ambassador — lead peers and build real leadership experience."},
        {"title": "GROW", "desc": "Build a portfolio of competitions, credentials, and a peer network that compounds for years to come."},
    ]
    upcoming_event_title: str = "Mock Stock Market & Investment Challenge"
    upcoming_event_date: str = "Launching May 2025"
    upcoming_event_desc: str = "Test your investing instincts. Analyse real markets, build a portfolio, and defend your financial decisions to a panel of judges."
    about_paragraph: str = "SCALE — the Society of Commerce, Analytics, Leadership and Entrepreneurship — is India's first national student organisation built for high schoolers serious about business, finance, marketing, and leadership. We exist to give ambitious students the stage, the skills, and the network that India's current education system rarely provides at the high school level."
    why_scale_items: List[dict] = [
        {"title": "A credential, not a club", "desc": "SCALE participation is a verifiable marker of ambition, initiative, and real-world capability — the kind that strengthens college applications to the world's top universities."},
        {"title": "Real-world skills", "desc": "Stock market simulation, business strategy, case competitions, marketing teardowns — all designed around how business actually works, not textbook theory."},
        {"title": "India needs this", "desc": "India produces the most number of high schoolers on the planet. Until now, none have had a dedicated national platform for business, finance, and leadership. We are that platform."},
    ]
    competitions_teaser: str = "More competitions coming across business, finance, marketing, and leadership."
    founder_name: str = "Veer Singh Sahni"
    founder_title: str = "Founder, SCALE"
    founder_story: str = "SCALE was founded by Veer Singh Sahni, a high school student with a deep passion for business, law, and finance. After years of participating in competitions, attending programmes, and watching peers navigate the complex world of applications, Veer realised that India had no single, serious, national platform for students like him. Everything was either a one-off club, a paid coaching programme, or a foreign opportunity. So he built one. SCALE is the platform Veer wished existed when he was in 9th grade — a place where any ambitious Indian high schooler can train, compete, and be taken seriously."
    vision_quote: str = "To become India's most trusted platform for student business, finance, and leadership education — building the next generation of founders, analysts, strategists, and leaders from every corner of the country."
    contact_email: str = "scalesupportteam2@gmail.com"
    contact_instagram: str = "@scale.national"
    contact_linkedin: str = "SCALE India"
    footer_tagline: str = "SCALE is not a club. It is a credential."

    # Eyebrow labels + section headlines — all admin-editable
    pillars_eyebrow: str = "The SCALE Experience"
    pillars_headline: str = "Four pillars. One serious platform for India's ambitious high schoolers."
    whatis_eyebrow: str = "What is SCALE"
    whatis_headline: str = "India's first serious national platform for high school business talent."
    why_eyebrow: str = "Why SCALE"
    events_eyebrow: str = "Events & Sessions"
    events_headline: str = "Compete nationally. Learn from the best. Build a track record."
    story_eyebrow: str = "Our Story"
    story_headline: str = "Built by a student. For students who want to be taken seriously."
    vision_eyebrow: str = "The Vision"
    contact_eyebrow: str = "Contact"
    contact_headline: str = "Reach out. We read every message."
    hero_ticker: str = "Credential · Competition · Community"

    # Event detail page chrome (shared across events)
    event_detail_about_label: str = "About this event"
    event_detail_eligibility_label: str = "Eligibility"
    event_detail_eligibility_body: str = "Open to students in grades 9–12. This is an individual competition — one student, one entry."
    event_detail_scholarship_label: str = "Need financial support?"
    event_detail_scholarship_body: str = "SCALE offers full scholarships for students who cannot afford the registration fee. Apply confidentially."


class FormSubmissionRecord(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    type: str
    data: dict
    created_at: str = Field(default_factory=now_iso)


# ===================== Custom Pages (admin-managed) =====================
class PageBlock(BaseModel):
    """A single content block on a custom page. `props` is a flexible dict
    interpreted by the frontend renderer based on `type`."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    type: Literal["hero", "section", "cards", "cta", "image", "richtext"] = "section"
    props: dict = Field(default_factory=dict)


class Page(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    slug: str  # URL slug, e.g. "scale-plus"
    title: str
    nav_label: str = ""
    show_in_nav: bool = True
    published: bool = True
    order: int = 0
    blocks: List[PageBlock] = []
    created_at: str = Field(default_factory=now_iso)
    updated_at: str = Field(default_factory=now_iso)


class PageUpdate(BaseModel):
    model_config = ConfigDict(extra="ignore")
    slug: Optional[str] = None
    title: Optional[str] = None
    nav_label: Optional[str] = None
    show_in_nav: Optional[bool] = None
    published: Optional[bool] = None
    order: Optional[int] = None
    blocks: Optional[List[PageBlock]] = None


class PaymentTransaction(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str
    registration_id: Optional[str] = None
    event_id: Optional[str] = None
    amount: float
    currency: str = "inr"
    payment_status: str = "initiated"
    metadata: dict = {}
    created_at: str = Field(default_factory=now_iso)
    updated_at: str = Field(default_factory=now_iso)


# ===================== Auth helpers =====================
def _resolve_public_origin(request: Request) -> str:
    """Return a public, user-facing base URL (no trailing slash) for use in
    outbound emails. The internal pod `request.base_url` is not publicly
    resolvable, so we prefer PUBLIC_BASE_URL env, then Origin / Referer headers."""
    env_url = (os.environ.get("PUBLIC_BASE_URL") or "").strip()
    if env_url:
        return env_url.rstrip("/")
    origin = (request.headers.get("origin") or "").strip()
    if origin:
        return origin.rstrip("/")
    referer = (request.headers.get("referer") or "").strip()
    if referer:
        from urllib.parse import urlsplit
        parts = urlsplit(referer)
        if parts.scheme and parts.netloc:
            return f"{parts.scheme}://{parts.netloc}"
    return str(request.base_url).rstrip("/")


def hash_password(pw: str) -> str:
    return bcrypt.hashpw(pw.encode(), bcrypt.gensalt()).decode()


def verify_password(pw: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(pw.encode(), hashed.encode())
    except Exception:
        return False


def create_token(user_id: str, role: str) -> str:
    payload = {
        "sub": user_id,
        "role": role,
        "exp": datetime.now(timezone.utc) + timedelta(hours=JWT_EXP_HOURS),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALG)


async def get_current_user(creds: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    if not creds:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        payload = jwt.decode(creds.credentials, JWT_SECRET, algorithms=[JWT_ALG])
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
    user = await db.users.find_one({"id": payload["sub"]}, {"_id": 0, "password": 0})
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user


async def require_admin(user: dict = Depends(get_current_user)) -> dict:
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    return user


# ===================== Seed + init =====================
@app.on_event("startup")
async def startup():
    # Initialise object storage (non-blocking — log failure but continue)
    try:
        init_storage()
    except Exception as e:
        logger.warning(f"Object storage unavailable: {e}")

    admin_email = os.environ.get("ADMIN_EMAIL", "scalesupportteam2@gmail.com")
    admin_pw = os.environ.get("ADMIN_PASSWORD", "SCALEdaddySALLU67")
    existing = await db.users.find_one({"email": admin_email}, {"_id": 0})
    if not existing:
        admin = User(email=admin_email, name="SCALE Admin", role="admin")
        doc = admin.model_dump()
        doc["password"] = hash_password(admin_pw)
        await db.users.insert_one(doc)
        logger.info(f"Seeded admin user: {admin_email}")
    else:
        await db.users.update_one(
            {"email": admin_email},
            {"$set": {"role": "admin", "password": hash_password(admin_pw)}},
        )

    existing_content = await db.content.find_one({"id": "main"}, {"_id": 0})
    if not existing_content:
        await db.content.insert_one(SiteContent().model_dump())
        logger.info("Seeded default site content")
    else:
        # Remove SCALE+ keys if leftover from previous schema
        await db.content.update_one(
            {"id": "main"},
            {"$unset": {
                "scale_plus_intro": "",
                "scale_plus_sessions": "",
                "scale_plus_newsletter": "",
                "pricing_monthly": "",
                "pricing_yearly": "",
                "scholarship_callout": "",
                "scholarship_body": "",
                "situational_title": "",
                "situational_desc": "",
            }},
        )

    existing_theme = await db.theme.find_one({"id": "main"}, {"_id": 0})
    if not existing_theme:
        doc = ThemeConfig().model_dump()
        doc["id"] = "main"
        await db.theme.insert_one(doc)

    count = await db.events.count_documents({})
    if count == 0:
        e1 = EventItem(
            title="Mock Stock Market & Investment Challenge",
            description="Test your investing instincts. Analyse real markets, build a portfolio, and defend your financial decisions to a panel of judges.",
            about="The Mock Stock Market & Investment Challenge is SCALE's flagship live competition. Teams of 1–3 students receive a virtual portfolio of ₹10,00,000 and trade real-time market data over a 4-week window. Performance is evaluated not just on returns, but also on the rigour of investment thesis, risk management, and sector calls. The top 12 teams pitch their strategies live to a panel of analysts and CFAs in the national finals. Open to all students from grades 9–12 across India.",
            status="live",
            cta_label="Event Details",
            date="May 2025",
            location="Online + Mumbai Finals",
            price_inr=500.0,
            order=1,
        )
        e2 = EventItem(
            title="Situational Business Challenge",
            description="Teams placed in high-pressure real-world business scenarios. Think fast, strategise sharp, present with conviction.",
            about="The Situational Business Challenge drops teams into real-world Indian business scenarios — pricing crisis, distribution failure, brand controversy — with 90 minutes to build a recovery strategy and present it to a jury of MBAs and operators. Tests strategic thinking, time management, and on-the-spot communication.",
            status="coming_soon",
            cta_label="Event Details",
            date="Coming Soon",
            location="TBA",
            price_inr=500.0,
            order=2,
        )
        await db.events.insert_many([e1.model_dump(), e2.model_dump()])

    scount = await db.sessions_list.count_documents({})
    if scount == 0:
        s1 = SessionItem(topic="Reading Financial Statements Like a CFA", speaker="Industry Analyst — TBA", date="TBA", order=1)
        s2 = SessionItem(topic="How Founders Actually Build Brands", speaker="Founder Speaker — TBA", date="TBA", order=2)
        await db.sessions_list.insert_many([s1.model_dump(), s2.model_dump()])


@app.on_event("shutdown")
async def shutdown():
    client.close()


# ===================== Auth routes =====================
@api_router.post("/auth/signup")
async def signup(body: UserCreate):
    existing = await db.users.find_one({"email": body.email}, {"_id": 0})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    user = User(email=body.email, name=body.name or "", role="user")
    doc = user.model_dump()
    doc["password"] = hash_password(body.password)
    await db.users.insert_one(doc)
    token = create_token(user.id, user.role)
    return {"token": token, "user": user.model_dump()}


@api_router.post("/auth/login")
async def login(body: UserLogin):
    user = await db.users.find_one({"email": body.email}, {"_id": 0})
    if not user or not verify_password(body.password, user.get("password", "")):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_token(user["id"], user["role"])
    user.pop("password", None)
    return {"token": token, "user": user}


@api_router.get("/auth/me")
async def me(user: dict = Depends(get_current_user)):
    return user


# ===================== Content (CMS) =====================
@api_router.get("/content")
async def get_content():
    doc = await db.content.find_one({"id": "main"}, {"_id": 0})
    if not doc:
        doc = SiteContent().model_dump()
    return doc


@api_router.put("/content")
async def update_content(body: dict, _admin: dict = Depends(require_admin)):
    body["id"] = "main"
    await db.content.update_one({"id": "main"}, {"$set": body}, upsert=True)
    doc = await db.content.find_one({"id": "main"}, {"_id": 0})
    return doc


# ===================== Theme =====================
@api_router.get("/theme")
async def get_theme():
    doc = await db.theme.find_one({"id": "main"}, {"_id": 0})
    if not doc:
        doc = ThemeConfig().model_dump()
        doc["id"] = "main"
    return doc


@api_router.put("/theme")
async def update_theme(body: dict, _admin: dict = Depends(require_admin)):
    body["id"] = "main"
    await db.theme.update_one({"id": "main"}, {"$set": body}, upsert=True)
    doc = await db.theme.find_one({"id": "main"}, {"_id": 0})
    return doc


# ===================== Events =====================
@api_router.get("/events")
async def list_events():
    items = await db.events.find({}, {"_id": 0}).sort("order", 1).to_list(200)
    return [_serialize_event(it) for it in items]


@api_router.get("/events/{event_id}")
async def get_event(event_id: str):
    doc = await db.events.find_one({"id": event_id}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Event not found")
    return _serialize_event(doc)


@api_router.post("/events")
async def create_event(body: EventItem, _admin: dict = Depends(require_admin)):
    doc = body.model_dump()
    await db.events.insert_one(doc)
    doc.pop("_id", None)
    return _serialize_event(doc)


@api_router.put("/events/{event_id}")
async def update_event(event_id: str, body: EventUpdate, _admin: dict = Depends(require_admin)):
    patch = body.model_dump(exclude_unset=True)
    # Cross-field invariant that Pydantic alone can't express
    tmin = patch.get("team_size_min")
    tmax = patch.get("team_size_max")
    if tmin is not None and tmax is not None and tmin > tmax:
        raise HTTPException(status_code=400, detail="team_size_min cannot exceed team_size_max")
    if not patch:
        doc = await db.events.find_one({"id": event_id}, {"_id": 0})
        if not doc:
            raise HTTPException(status_code=404, detail="Event not found")
        return _serialize_event(doc)

    await db.events.update_one({"id": event_id}, {"$set": patch})
    doc = await db.events.find_one({"id": event_id}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Event not found")
    return _serialize_event(doc)


@api_router.delete("/events/{event_id}")
async def delete_event(event_id: str, _admin: dict = Depends(require_admin)):
    await db.events.delete_one({"id": event_id})
    return {"ok": True}


# ===================== Custom Pages CMS =====================
def _serialize_page(doc: dict) -> dict:
    if not doc:
        return doc
    return Page(**doc).model_dump()


@api_router.get("/pages")
async def list_pages():
    items = await db.pages.find({"published": True}, {"_id": 0}).sort("order", 1).to_list(200)
    return [_serialize_page(it) for it in items]


@api_router.get("/admin/pages")
async def admin_list_pages(_admin: dict = Depends(require_admin)):
    items = await db.pages.find({}, {"_id": 0}).sort("order", 1).to_list(200)
    return [_serialize_page(it) for it in items]


@api_router.get("/pages/{slug}")
async def get_page(slug: str):
    doc = await db.pages.find_one({"slug": slug, "published": True}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Page not found")
    return _serialize_page(doc)


@api_router.get("/admin/pages/{page_id}")
async def admin_get_page(page_id: str, _admin: dict = Depends(require_admin)):
    """Admin can fetch any page (incl. drafts) by id."""
    doc = await db.pages.find_one({"id": page_id}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Page not found")
    return _serialize_page(doc)


SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,63}$")


def _normalize_slug(raw: str) -> str:
    s = (raw or "").strip().lower().replace(" ", "-")
    if not SLUG_RE.match(s):
        raise HTTPException(status_code=400, detail="Slug must be lowercase letters, digits, and hyphens (max 64 chars, must start with a letter or digit).")
    return s


@api_router.post("/pages")
async def create_page(body: Page, _admin: dict = Depends(require_admin)):
    slug = _normalize_slug(body.slug)
    existing = await db.pages.find_one({"slug": slug}, {"_id": 0})
    if existing:
        raise HTTPException(status_code=400, detail=f"Page with slug '{slug}' already exists")
    data = body.model_dump()
    data["slug"] = slug
    data["created_at"] = now_iso()
    data["updated_at"] = now_iso()
    await db.pages.insert_one(data)
    data.pop("_id", None)
    return _serialize_page(data)


@api_router.put("/pages/{page_id}")
async def update_page(page_id: str, body: PageUpdate, _admin: dict = Depends(require_admin)):
    existing = await db.pages.find_one({"id": page_id}, {"_id": 0})
    if not existing:
        raise HTTPException(status_code=404, detail="Page not found")
    patch = body.model_dump(exclude_unset=True)
    if "slug" in patch:
        patch["slug"] = _normalize_slug(patch["slug"])
        clash = await db.pages.find_one({"slug": patch["slug"], "id": {"$ne": page_id}}, {"_id": 0})
        if clash:
            raise HTTPException(status_code=400, detail=f"Slug '{patch['slug']}' already in use")
    patch["updated_at"] = now_iso()
    await db.pages.update_one({"id": page_id}, {"$set": patch})
    doc = await db.pages.find_one({"id": page_id}, {"_id": 0})
    return _serialize_page(doc)


@api_router.delete("/pages/{page_id}")
async def delete_page(page_id: str, _admin: dict = Depends(require_admin)):
    await db.pages.delete_one({"id": page_id})
    return {"ok": True}


# ===================== Sessions =====================
@api_router.get("/sessions")
async def list_sessions():
    items = await db.sessions_list.find({}, {"_id": 0}).sort("order", 1).to_list(200)
    return items


@api_router.post("/sessions")
async def create_session(body: SessionItem, _admin: dict = Depends(require_admin)):
    doc = body.model_dump()
    await db.sessions_list.insert_one(doc)
    doc.pop("_id", None)
    return doc


@api_router.put("/sessions/{sid}")
async def update_session(sid: str, body: dict, _admin: dict = Depends(require_admin)):
    body.pop("_id", None)
    await db.sessions_list.update_one({"id": sid}, {"$set": body})
    doc = await db.sessions_list.find_one({"id": sid}, {"_id": 0})
    return doc


@api_router.delete("/sessions/{sid}")
async def delete_session(sid: str, _admin: dict = Depends(require_admin)):
    await db.sessions_list.delete_one({"id": sid})
    return {"ok": True}


# ===================== Forms =====================
async def save_submission(submission_type: str, data: dict) -> str:
    rec = FormSubmissionRecord(type=submission_type, data=data)
    await db.submissions.insert_one(rec.model_dump())
    return rec.id


def _email_html_table(title: str, rows: list[tuple[str, str]], intro: str = "", cta_html: str = "") -> str:
    body = "".join(
        f"<tr><td style='padding:8px 12px;border:1px solid #eee;font-weight:600;width:35%'>{k}</td>"
        f"<td style='padding:8px 12px;border:1px solid #eee'>{v}</td></tr>"
        for k, v in rows
    )
    intro_html = f"<p style='font-size:15px;line-height:1.6;color:#333'>{intro}</p>" if intro else ""
    return f"""
    <div style="font-family: 'Helvetica Neue', Arial, sans-serif; max-width:640px; margin:0 auto; background:#FAF8F5; padding:24px;">
      <div style="background:#4A0008;color:#fff;padding:18px 24px;">
        <div style="font-size:11px;letter-spacing:0.3em;color:#F5C842;text-transform:uppercase;font-weight:700">SCALE India</div>
        <h2 style="margin:6px 0 0;font-family:Georgia,serif">{title}</h2>
      </div>
      <div style="background:#fff;padding:24px;border:1px solid #eee;border-top:none">
        {intro_html}
        <table style="border-collapse:collapse;width:100%;margin-top:12px;font-size:14px">{body}</table>
        {cta_html}
        <p style="color:#666;font-size:12px;margin-top:20px">— SCALE Support Team</p>
      </div>
    </div>
    """


@api_router.post("/forms/contact")
async def submit_contact(body: ContactForm):
    sid = await save_submission("contact", body.model_dump())
    html = _email_html_table("New Contact Form Submission", [
        ("Name", body.name),
        ("School/Organisation", body.school or "-"),
        ("Subject", body.subject),
        ("Contact Email", body.email),
        ("Message", body.message),
    ])
    notify_admin(f"SCALE Contact — {body.subject}", html, reply_to=body.email)
    return {"ok": True, "id": sid}


# ===================== Registration helpers =====================
def validate_mode_payload(body: "EventRegistrationForm", event: dict) -> list[str]:
    """Return a list of missing/invalid field paths for this registration body
    against the event's configured registration_mode + extra_fields. Raises
    HTTPException for unrecoverable mode/team-size violations."""
    mode = event.get("registration_mode", "individual")
    missing: list[str] = []

    if mode == "individual":
        for f in ["name", "school", "grade", "email", "phone", "parent_name", "parent_phone", "parent_email"]:
            if not getattr(body, f, None):
                missing.append(f)
    elif mode == "team":
        if not body.team_name:
            missing.append("team_name")
        if not body.members or not isinstance(body.members, list):
            missing.append("members")
        else:
            tmin = int(event.get("team_size_min", 2))
            tmax = int(event.get("team_size_max", 5))
            if not (tmin <= len(body.members) <= tmax):
                raise HTTPException(status_code=400, detail=f"Team must have between {tmin} and {tmax} members")
            for i, m in enumerate(body.members):
                for k in ["name", "school", "grade", "email", "phone"]:
                    if not m.get(k):
                        missing.append(f"members[{i}].{k}")
        for f in ["parent_name", "parent_phone", "parent_email"]:
            if not getattr(body, f, None):
                missing.append(f)
    else:
        raise HTTPException(status_code=400, detail=f"Unknown registration_mode '{mode}'")

    # Required extra_fields. Per-member-scoped extras live inside each member's `extras` dict.
    extras = body.extras or {}
    for ef in event.get("extra_fields", []):
        scope = ef.get("scope", "team")
        if not ef.get("required"):
            continue
        if mode == "team" and scope == "member":
            for i, m in enumerate(body.members or []):
                m_extras = (m.get("extras") or {}) if isinstance(m, dict) else {}
                if not m_extras.get(ef.get("key")):
                    missing.append(f"members[{i}].extras.{ef.get('key')}")
        else:
            if not extras.get(ef.get("key")):
                missing.append(f"extras.{ef.get('key')}")

    return missing


def build_email_rows(body: "EventRegistrationForm", event: dict, reg_id: str, mode: str) -> tuple[list[tuple[str, str]], list[tuple[str, str]]]:
    """Build the (student/parent rows, admin rows) for confirmation emails."""
    base_rows: list[tuple[str, str]] = [
        ("Event", event["title"]),
        ("Date", event.get("date", "-")),
        ("Mode", "Team" if mode == "team" else "Individual"),
        ("Registration ID", reg_id),
        ("Amount", f"₹{int(event.get('price_inr', 500))}"),
    ]
    if mode == "team":
        members_html = "<br>".join(
            f"{i+1}. {m.get('name','')} — {m.get('grade','')} — {m.get('school','')} ({m.get('email','')}, {m.get('phone','')})"
            for i, m in enumerate(body.members or [])
        )
        base_rows = [("Team", body.team_name)] + base_rows + [("Members", members_html)]
    else:
        base_rows = [("Student", body.name), ("School", body.school), ("Grade", body.grade)] + base_rows

    admin_rows: list[tuple[str, str]] = list(base_rows) + [
        ("Primary Contact", f"{body.parent_name} · {body.parent_phone} · {body.parent_email}"),
    ]
    extras = body.extras or {}
    for ef in event.get("extra_fields", []):
        scope = ef.get("scope", "team")
        label = ef.get("label") or ef.get("key")
        if mode == "team" and scope == "member":
            answers = []
            for i, m in enumerate(body.members or []):
                m_extras = (m.get("extras") or {}) if isinstance(m, dict) else {}
                ans = m_extras.get(ef.get("key"))
                if ans not in (None, ""):
                    answers.append(f"{m.get('name', f'Member {i+1}')}: {ans}")
            admin_rows.append((label, "<br>".join(answers) if answers else "-"))
        else:
            admin_rows.append((label, str(extras.get(ef.get("key"), "-"))))
    return base_rows, admin_rows


@api_router.post("/registrations")
async def register_for_event(body: EventRegistrationForm, request: Request):
    """Register student/team for an event based on event.registration_mode."""
    event = await db.events.find_one({"id": body.event_id}, {"_id": 0})
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    if event.get("registration_open") is False:
        raise HTTPException(status_code=403, detail="Registration is closed for this event")

    mode = event.get("registration_mode", "individual")
    missing = validate_mode_payload(body, event)
    if missing:
        raise HTTPException(status_code=400, detail=f"Missing required fields: {', '.join(missing)}")

    # --- Compute display + contact values ---
    if mode == "team":
        display_name = body.team_name
        primary_email = body.members[0].get("email")
        primary_name = body.members[0].get("name")
    else:
        display_name = body.name
        primary_email = body.email
        primary_name = body.name

    reg_id = str(uuid.uuid4())
    rec = {
        "id": reg_id,
        "event_id": body.event_id,
        "event_title": event["title"],
        "mode": mode,
        "name": display_name,
        "school": body.school if mode == "individual" else (body.members[0].get("school") if body.members else ""),
        "grade": body.grade if mode == "individual" else (body.members[0].get("grade") if body.members else ""),
        "email": primary_email,
        "phone": body.phone if mode == "individual" else (body.members[0].get("phone") if body.members else ""),
        "parent_name": body.parent_name,
        "parent_phone": body.parent_phone,
        "parent_email": body.parent_email,
        "team_name": body.team_name,
        "members": body.members or [],
        "extras": body.extras or {},
        "amount_inr": event.get("price_inr", 500.0),
        "payment_status": "pending",
        "created_at": now_iso(),
    }
    await db.registrations.insert_one(rec)
    rec.pop("_id", None)
    await save_submission("registration", rec)

    # --- Email ---
    # Derive public-facing origin. The internal pod base_url
    # (`*.cluster-XX.preview.emergentcf.cloud`) is NOT publicly resolvable, so
    # emails must point at the user-facing host. Priority:
    #   1) PUBLIC_BASE_URL env var (set in deployment), 2) Origin header from
    #   the browser, 3) Referer header host, 4) fallback to request.base_url.
    origin = _resolve_public_origin(request)
    pay_link = f"{origin}/payment/{reg_id}"
    schol_link = f"{origin}/events/{event['id']}/scholarship?reg={reg_id}"
    cta_html = f"""
    <div style="margin-top:24px">
      <a href="{pay_link}" style="background:#B01020;color:#fff;text-decoration:none;padding:12px 24px;font-weight:600;display:inline-block;margin-right:8px">Complete Payment (₹{int(event.get('price_inr',500))})</a>
      <a href="{schol_link}" style="background:#fff;color:#B01020;text-decoration:none;padding:11px 23px;font-weight:600;display:inline-block;border:1.5px solid #B01020">Apply for Scholarship</a>
    </div>
    <p style="color:#666;font-size:12px;margin-top:12px">UPI and Credit Card accepted. Scholarships available — financial circumstances should never be a barrier.</p>
    """
    base_rows, admin_rows = build_email_rows(body, event, reg_id, mode)

    team_suffix = " (and your team's)" if mode == "team" else ""
    html_student = _email_html_table(
        "Registration Received",
        base_rows,
        intro=f"Hi {primary_name}, we've received your registration for <strong>{event['title']}</strong>. To confirm your spot{team_suffix}, please complete the payment below. If financial support is needed, a scholarship application is available.",
        cta_html=cta_html,
    )
    parent_intro_subject = "your child" if mode == "individual" else f"the team led by {primary_name}"
    html_parent = _email_html_table(
        "Your Child's SCALE Registration",
        base_rows,
        intro=f"Hello {body.parent_name}, {parent_intro_subject} has registered for SCALE's <strong>{event['title']}</strong>. To confirm the registration, please complete the payment using the button below.",
        cta_html=cta_html,
    )
    if mode == "team":
        for m in body.members or []:
            if m.get("email"):
                send_email(m["email"], m.get("name", "Participant"),
                           f"SCALE — Team registration received for {event['title']}",
                           html_student, reply_to=os.environ.get("ADMIN_EMAIL"))
    else:
        send_email(primary_email, primary_name,
                   f"SCALE — Registration received for {event['title']}",
                   html_student, reply_to=os.environ.get("ADMIN_EMAIL"))

    send_email(body.parent_email, body.parent_name,
               f"SCALE — {primary_name}'s registration for {event['title']}",
               html_parent, reply_to=os.environ.get("ADMIN_EMAIL"))

    admin_html = _email_html_table("New Event Registration", admin_rows)
    notify_admin(f"New registration: {display_name} → {event['title']}", admin_html, reply_to=primary_email)

    return {"ok": True, "registration_id": reg_id, "payment_link": pay_link, "scholarship_link": schol_link}


@api_router.get("/registrations/{reg_id}")
async def get_registration(reg_id: str):
    doc = await db.registrations.find_one({"id": reg_id}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Registration not found")
    return doc


@api_router.get("/admin/registrations")
async def list_registrations(_admin: dict = Depends(require_admin)):
    items = await db.registrations.find({}, {"_id": 0}).sort("created_at", -1).to_list(2000)
    return items


@api_router.post("/forms/event-scholarship")
async def submit_event_scholarship(body: EventScholarshipForm, request: Request):
    event = await db.events.find_one({"id": body.event_id}, {"_id": 0})
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    sid = await save_submission("event_scholarship", body.model_dump() | {"event_title": event["title"]})

    # Attach uploaded proof file (if any) — admin-only download link
    file_row = None
    if body.proof_file_id:
        file_row = await db.file_refs.find_one({"id": body.proof_file_id}, {"_id": 0})

    rows = [
        ("Event", event["title"]),
        ("Student", body.name),
        ("School", body.school),
        ("Grade", body.grade),
        ("Email", body.email),
        ("Phone", body.phone),
        ("Parent Name", body.parent_name),
        ("Parent Email", body.parent_email),
        ("Financial Background", body.financial_proof),
        ("Why Participate", body.why_participate),
    ]
    if file_row:
        rows.append(("Proof file", f"{file_row.get('original_filename','(file)')} ({int((file_row.get('size') or 0)/1024)} KB)"))
    admin_html = _email_html_table("Event Scholarship Application", rows,
                                   intro="A new scholarship application has been received. Please review and respond within 5–7 business days.")
    notify_admin(f"Scholarship — {body.name} → {event['title']}", admin_html, reply_to=body.email)

    student_html = _email_html_table(
        "Scholarship Application Received",
        [("Event", event["title"]), ("Status", "Under review")],
        intro=f"Hi {body.name}, we've received your scholarship application for <strong>{event['title']}</strong>. Every application is reviewed with care and confidentiality. We'll respond within 5–7 business days.",
    )
    send_email(body.email, body.name, f"SCALE Scholarship — Application received for {event['title']}", student_html, reply_to=os.environ.get("ADMIN_EMAIL"))

    return {"ok": True, "id": sid}


# ===================== File uploads =====================
MAX_UPLOAD_SIZE = 10 * 1024 * 1024  # 10 MB
MAX_EVENT_FILE_SIZE = 25 * 1024 * 1024  # 25 MB for admin event material uploads
ALLOWED_EXT = {"pdf", "jpg", "jpeg", "png", "webp"}
# Broader set for event materials & student submissions (docs + media)
ALLOWED_MATERIAL_EXT = {
    "pdf", "doc", "docx", "ppt", "pptx", "xls", "xlsx",
    "txt", "md", "csv", "zip",
    "jpg", "jpeg", "png", "webp", "gif",
    "mp4", "mp3", "wav", "m4a",
}
MIME_BY_EXT = {
    "pdf": "application/pdf",
    "jpg": "image/jpeg", "jpeg": "image/jpeg",
    "png": "image/png", "webp": "image/webp", "gif": "image/gif",
    "doc": "application/msword",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "ppt": "application/vnd.ms-powerpoint",
    "pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "xls": "application/vnd.ms-excel",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "txt": "text/plain", "md": "text/markdown", "csv": "text/csv",
    "zip": "application/zip",
    "mp4": "video/mp4", "mp3": "audio/mpeg", "wav": "audio/wav", "m4a": "audio/mp4",
}


class FileRef(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    storage_path: str
    original_filename: str
    content_type: str
    size: int
    kind: str = "scholarship_proof"
    created_at: str = Field(default_factory=now_iso)
    is_deleted: bool = False


@api_router.post("/upload/scholarship-proof")
async def upload_scholarship_proof(file: UploadFile = File(...)):
    """Public upload endpoint scoped to scholarship proof documents."""
    original = file.filename or "file"
    ext = original.rsplit(".", 1)[-1].lower() if "." in original else ""
    if ext not in ALLOWED_EXT:
        raise HTTPException(status_code=400, detail=f"Unsupported file type .{ext}. Allowed: {', '.join(sorted(ALLOWED_EXT))}")

    data = await file.read()
    if len(data) > MAX_UPLOAD_SIZE:
        raise HTTPException(status_code=400, detail="File larger than 10 MB")
    if len(data) == 0:
        raise HTTPException(status_code=400, detail="Empty file")

    content_type = file.content_type or MIME_BY_EXT.get(ext, "application/octet-stream")
    path = build_upload_path("scholarship", ext)
    try:
        result = put_object(path, data, content_type)
    except Exception as e:
        logger.error(f"Upload failed: {e}")
        raise HTTPException(status_code=503, detail="File storage unavailable. Please try again or paste a link in the text field.")

    ref = FileRef(
        storage_path=result["path"],
        original_filename=original,
        content_type=content_type,
        size=int(result.get("size") or len(data)),
        kind="scholarship_proof",
    )
    await db.file_refs.insert_one(ref.model_dump())
    return {"id": ref.id, "original_filename": original, "size": ref.size}


@api_router.get("/admin/files/{file_id}")
async def admin_download_file(file_id: str, _admin: dict = Depends(require_admin)):
    row = await db.file_refs.find_one({"id": file_id, "is_deleted": False}, {"_id": 0})
    if not row:
        raise HTTPException(status_code=404, detail="File not found")
    try:
        data, ctype = get_object(row["storage_path"])
    except Exception as e:
        logger.error(f"Download failed: {e}")
        raise HTTPException(status_code=503, detail="Storage unavailable")
    headers = {"Content-Disposition": f'inline; filename="{row["original_filename"]}"'}
    return Response(content=data, media_type=row.get("content_type") or ctype, headers=headers)


@api_router.get("/admin/files-meta/{file_id}")
async def admin_file_meta(file_id: str, _admin: dict = Depends(require_admin)):
    row = await db.file_refs.find_one({"id": file_id}, {"_id": 0})
    if not row:
        raise HTTPException(status_code=404, detail="File not found")
    return row


@api_router.get("/submissions")
async def list_submissions(_admin: dict = Depends(require_admin)):
    items = await db.submissions.find({}, {"_id": 0}).sort("created_at", -1).to_list(2000)
    return items


@api_router.delete("/submissions/{sid}")
async def delete_submission(sid: str, _admin: dict = Depends(require_admin)):
    await db.submissions.delete_one({"id": sid})
    return {"ok": True}


# ===================== Event materials + post-registration hub =====================
class EventMaterialLink(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    label: str
    url: str


class EventMaterialDocument(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    label: str  # human-friendly display name (admin overridable)
    file_id: str  # references file_refs.id
    filename: str
    content_type: str
    size: int = 0


class EventMaterials(BaseModel):
    notes: str = ""  # free-form instructions rendered as preserved-whitespace
    links: List[EventMaterialLink] = []
    documents: List[EventMaterialDocument] = []
    updated_at: str = Field(default_factory=now_iso)


class EventMaterialsUpdate(BaseModel):
    model_config = ConfigDict(extra="ignore")
    notes: Optional[str] = None
    links: Optional[List[EventMaterialLink]] = None
    documents: Optional[List[EventMaterialDocument]] = None


async def _require_paid_registration(event_id: str, reg_id: str) -> dict:
    """Gate helper: returns the paid registration for this event, else raises.
    Used to authorize student-facing access to post-registration materials."""
    if not reg_id:
        raise HTTPException(status_code=401, detail="Missing reg_id")
    reg = await db.registrations.find_one({"id": reg_id}, {"_id": 0})
    if not reg:
        raise HTTPException(status_code=404, detail="Registration not found")
    if reg.get("event_id") != event_id:
        raise HTTPException(status_code=403, detail="Registration does not belong to this event")
    if reg.get("payment_status") != "paid":
        raise HTTPException(
            status_code=402,  # Payment Required — frontend interprets this
            detail="Complete your payment to access event materials",
        )
    return reg


def _is_admin_request(authorization: str | None) -> bool:
    """Lightweight admin check for dual-gated endpoints (admin OR paid student)."""
    if not authorization or not authorization.startswith("Bearer "):
        return False
    token = authorization.split(" ", 1)[1]
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG])
        return payload.get("role") == "admin" or bool(payload.get("is_admin"))
    except Exception:
        return False


@api_router.get("/events/{event_id}/materials")
async def get_event_materials(event_id: str, reg_id: str | None = None, request: Request = None):
    """Gated read: admin OR paid registrant for this event can fetch materials."""
    if not _is_admin_request(request.headers.get("authorization") if request else None):
        await _require_paid_registration(event_id, reg_id or "")
    event = await db.events.find_one({"id": event_id}, {"_id": 0})
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    materials = event.get("materials") or {}
    # Normalise defaults so frontend can render without null-checks.
    return {
        "event_id": event_id,
        "event_title": event.get("title", ""),
        "event_date": event.get("date", ""),
        "event_location": event.get("location", ""),
        "event_description": event.get("description", ""),
        "notes": materials.get("notes", ""),
        "links": materials.get("links", []),
        "documents": materials.get("documents", []),
        "updated_at": materials.get("updated_at"),
    }


@api_router.put("/events/{event_id}/materials")
async def update_event_materials(
    event_id: str,
    body: EventMaterialsUpdate,
    _admin: dict = Depends(require_admin),
):
    event = await db.events.find_one({"id": event_id}, {"_id": 0})
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    current = event.get("materials") or {}
    patch = body.model_dump(exclude_unset=True)
    # Re-serialise nested pydantic models → dicts
    if "links" in patch and patch["links"] is not None:
        patch["links"] = [EventMaterialLink(**lk).model_dump() if not isinstance(lk, dict) else lk for lk in patch["links"]]
    if "documents" in patch and patch["documents"] is not None:
        patch["documents"] = [EventMaterialDocument(**d).model_dump() if not isinstance(d, dict) else d for d in patch["documents"]]
    next_materials = {**current, **patch, "updated_at": now_iso()}
    await db.events.update_one({"id": event_id}, {"$set": {"materials": next_materials}})
    return next_materials


@api_router.post("/events/{event_id}/files")
async def upload_event_file(
    event_id: str,
    file: UploadFile = File(...),
    _admin: dict = Depends(require_admin),
):
    """Admin-only upload for event material documents. Uses broader allowlist
    than scholarship proofs (25 MB cap, doc/ppt/video allowed)."""
    event = await db.events.find_one({"id": event_id}, {"_id": 0})
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    original = file.filename or "file"
    ext = original.rsplit(".", 1)[-1].lower() if "." in original else ""
    if ext not in ALLOWED_MATERIAL_EXT:
        raise HTTPException(status_code=400, detail=f"Unsupported file type .{ext}. Allowed: {', '.join(sorted(ALLOWED_MATERIAL_EXT))}")
    data = await file.read()
    if len(data) > MAX_EVENT_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File larger than 25 MB")
    if len(data) == 0:
        raise HTTPException(status_code=400, detail="Empty file")
    content_type = file.content_type or MIME_BY_EXT.get(ext, "application/octet-stream")
    path = build_upload_path(f"events/{event_id}/material", ext)
    try:
        result = put_object(path, data, content_type)
    except Exception as e:
        logger.error(f"Event file upload failed: {e}")
        raise HTTPException(status_code=503, detail="File storage unavailable")
    ref = FileRef(
        storage_path=result["path"],
        original_filename=original,
        content_type=content_type,
        size=int(result.get("size") or len(data)),
        kind="event_material",
    )
    await db.file_refs.insert_one(ref.model_dump())
    return {
        "id": ref.id,
        "file_id": ref.id,
        "filename": original,
        "content_type": content_type,
        "size": ref.size,
    }


@api_router.get("/events/{event_id}/files/{file_id}/download")
async def download_event_file(
    event_id: str,
    file_id: str,
    reg_id: str | None = None,
    request: Request = None,
):
    """Gated: admin OR paid registrant can download an event material file."""
    event = await db.events.find_one({"id": event_id}, {"_id": 0})
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    materials = event.get("materials") or {}
    document_ids = {d.get("file_id") for d in (materials.get("documents") or [])}
    if file_id not in document_ids:
        raise HTTPException(status_code=404, detail="File not attached to this event")
    if not _is_admin_request(request.headers.get("authorization") if request else None):
        await _require_paid_registration(event_id, reg_id or "")
    row = await db.file_refs.find_one({"id": file_id, "is_deleted": False}, {"_id": 0})
    if not row:
        raise HTTPException(status_code=404, detail="File not found")
    try:
        data, ctype = get_object(row["storage_path"])
    except Exception as e:
        logger.error(f"Event file download failed: {e}")
        raise HTTPException(status_code=503, detail="Storage unavailable")
    headers = {"Content-Disposition": f'inline; filename="{row["original_filename"]}"'}
    return Response(content=data, media_type=row.get("content_type") or ctype, headers=headers)


# ------ Student submissions ------
class EventSubmissionFile(BaseModel):
    file_id: str
    filename: str
    content_type: str = ""
    size: int = 0


class EventSubmissionIn(BaseModel):
    registration_id: str
    text_response: str = ""
    files: List[EventSubmissionFile] = []


class EventSubmission(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    event_id: str
    registration_id: str
    student_name: str = ""
    student_email: str = ""
    student_school: str = ""
    text_response: str = ""
    files: List[EventSubmissionFile] = []
    created_at: str = Field(default_factory=now_iso)
    updated_at: str = Field(default_factory=now_iso)


@api_router.post("/events/{event_id}/submission-files")
async def upload_submission_file(
    event_id: str,
    reg_id: str,
    file: UploadFile = File(...),
):
    """Student-facing upload, gated on paid registration. Returns a file_id the
    student then attaches when calling POST /events/{id}/submissions."""
    await _require_paid_registration(event_id, reg_id)
    original = file.filename or "file"
    ext = original.rsplit(".", 1)[-1].lower() if "." in original else ""
    if ext not in ALLOWED_MATERIAL_EXT:
        raise HTTPException(status_code=400, detail=f"Unsupported file type .{ext}. Allowed: {', '.join(sorted(ALLOWED_MATERIAL_EXT))}")
    data = await file.read()
    if len(data) > MAX_EVENT_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File larger than 25 MB")
    if len(data) == 0:
        raise HTTPException(status_code=400, detail="Empty file")
    content_type = file.content_type or MIME_BY_EXT.get(ext, "application/octet-stream")
    path = build_upload_path(f"events/{event_id}/submissions/{reg_id}", ext)
    try:
        result = put_object(path, data, content_type)
    except Exception as e:
        logger.error(f"Submission upload failed: {e}")
        raise HTTPException(status_code=503, detail="File storage unavailable")
    ref = FileRef(
        storage_path=result["path"],
        original_filename=original,
        content_type=content_type,
        size=int(result.get("size") or len(data)),
        kind="event_submission",
    )
    await db.file_refs.insert_one(ref.model_dump())
    return {
        "file_id": ref.id,
        "filename": original,
        "content_type": content_type,
        "size": ref.size,
    }


@api_router.post("/events/{event_id}/submissions")
async def submit_to_event(event_id: str, body: EventSubmissionIn):
    """Create-or-update a registrant's submission for this event. One submission
    per registration — subsequent posts overwrite the previous text + files."""
    reg = await _require_paid_registration(event_id, body.registration_id)
    existing = await db.event_submissions.find_one(
        {"event_id": event_id, "registration_id": body.registration_id},
        {"_id": 0},
    )
    now = now_iso()
    if existing:
        await db.event_submissions.update_one(
            {"id": existing["id"]},
            {"$set": {
                "text_response": body.text_response,
                "files": [f.model_dump() for f in body.files],
                "updated_at": now,
            }},
        )
        sub_id = existing["id"]
        action = "updated"
    else:
        sub = EventSubmission(
            event_id=event_id,
            registration_id=body.registration_id,
            student_name=reg.get("name", ""),
            student_email=reg.get("email", ""),
            student_school=reg.get("school", ""),
            text_response=body.text_response,
            files=[f.model_dump() for f in body.files],
        )
        await db.event_submissions.insert_one(sub.model_dump())
        sub_id = sub.id
        action = "created"
    # Notify admin
    try:
        event = await db.events.find_one({"id": event_id}, {"_id": 0})
        rows = [
            ("Event", event.get("title", "") if event else event_id),
            ("Student", reg.get("name", "")),
            ("Email", reg.get("email", "")),
            ("School", reg.get("school", "")),
            ("Action", action),
            ("Text", (body.text_response or "(none)")[:800]),
            ("Attachments", str(len(body.files))),
        ]
        notify_admin(
            f"SCALE — {action.title()} submission: {reg.get('name', '')} → {event.get('title', '') if event else event_id}",
            _email_html_table("Event Submission", rows),
            reply_to=reg.get("email"),
        )
    except Exception as e:
        logger.warning(f"Admin notify for submission failed: {e}")
    return {"ok": True, "id": sub_id, "action": action}


@api_router.get("/events/{event_id}/submissions/mine")
async def get_my_submission(event_id: str, reg_id: str):
    """Student fetches their own submission (if any)."""
    await _require_paid_registration(event_id, reg_id)
    sub = await db.event_submissions.find_one(
        {"event_id": event_id, "registration_id": reg_id},
        {"_id": 0},
    )
    return sub or {"exists": False}


@api_router.get("/admin/events/{event_id}/submissions")
async def admin_list_event_submissions(event_id: str, _admin: dict = Depends(require_admin)):
    items = await db.event_submissions.find({"event_id": event_id}, {"_id": 0}).sort("created_at", -1).to_list(5000)
    return items


@api_router.get("/admin/events/{event_id}/submissions/export")
async def admin_export_event_submissions(event_id: str, _admin: dict = Depends(require_admin)):
    """Stream a CSV of all submissions for this event. Includes file download
    URLs so admin can click through in Excel/Sheets."""
    items = await db.event_submissions.find({"event_id": event_id}, {"_id": 0}).sort("created_at", -1).to_list(5000)
    import csv as _csv
    import io as _io
    buf = _io.StringIO()
    w = _csv.writer(buf)
    w.writerow([
        "submission_id", "created_at", "updated_at",
        "student_name", "student_email", "student_school",
        "registration_id",
        "text_response", "file_count", "file_names", "file_ids",
    ])
    for it in items:
        files = it.get("files") or []
        w.writerow([
            it.get("id", ""), it.get("created_at", ""), it.get("updated_at", ""),
            it.get("student_name", ""), it.get("student_email", ""), it.get("student_school", ""),
            it.get("registration_id", ""),
            (it.get("text_response") or "").replace("\r", " ").replace("\n", " "),
            len(files),
            "; ".join(f.get("filename", "") for f in files),
            "; ".join(f.get("file_id", "") for f in files),
        ])
    csv_bytes = buf.getvalue().encode("utf-8-sig")
    return Response(
        content=csv_bytes,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="event-{event_id}-submissions.csv"'},
    )


# ===================== Cashfree payments =====================
# Cashfree Payment Gateway v3 (2023-08-01 API). UPI-first, supports cards,
# netbanking, wallets. Amounts sent in rupees (not paise) in API payloads; our
# internal bookkeeping still uses both.
#
# Flow:
#   1) Backend creates a Razorpay Order and returns the public key + order id.`r`n#   2) Frontend opens Razorpay Checkout via checkout.js.`r`n#   3) Frontend verifies the successful payment signature server-side.`r`n#   4) Frontend polls `GET /api/payments/status/{order_id}` for reconciliation.`r`n#   5) Webhook at `/api/webhook/razorpay` handles async reconciliation.
import hmac as _hmac
import hashlib as _hashlib


def _razorpay_auth() -> tuple[str, str]:
    key_id = (os.environ.get("RAZORPAY_KEY_ID") or "").strip()
    key_secret = (os.environ.get("RAZORPAY_KEY_SECRET") or "").strip()
    if not key_id or not key_secret:
        raise HTTPException(
            status_code=503,
            detail="Payment gateway not configured. Admin must set RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET.",
        )
    return key_id, key_secret


def _razorpay_headers() -> dict:
    return {"Content-Type": "application/json", "Accept": "application/json"}


def _razorpay_api_url(path: str) -> str:
    return f"https://api.razorpay.com/v1{path}"


class CreateOrderRequest(BaseModel):
    registration_id: str


@api_router.post("/payments/create-order")
async def create_payment_order(body: CreateOrderRequest, request: Request):
    """Create a Razorpay Order for a registration. Idempotent - if a
    created order already exists for this registration, return the same order."""
    _ = request
    reg = await db.registrations.find_one({"id": body.registration_id}, {"_id": 0})
    if not reg:
        raise HTTPException(status_code=404, detail="Registration not found")
    if reg.get("payment_status") == "paid":
        raise HTTPException(status_code=400, detail="Registration already paid")

    event = await db.events.find_one({"id": reg["event_id"]}, {"_id": 0})
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    amount_inr = float(event.get("price_inr", 500.0))
    amount_paise = int(round(amount_inr * 100))
    key_id, key_secret = _razorpay_auth()

    existing = await db.payment_transactions.find_one(
        {"registration_id": body.registration_id, "payment_status": {"$in": ["created", "initiated"]}},
        {"_id": 0},
    )
    if existing and existing.get("session_id"):
        return {
            "order_id": existing["session_id"],
            "key_id": key_id,
            "amount_paise": amount_paise,
            "amount_inr": amount_inr,
            "currency": "INR",
            "registration_id": body.registration_id,
            "customer_name": reg.get("name") or "SCALE Participant",
            "customer_email": reg.get("email") or "",
            "customer_phone": reg.get("phone") or "",
        }

    payload = {
        "amount": amount_paise,
        "currency": "INR",
        "receipt": f"scale_{body.registration_id[:30]}",
        "notes": {
            "registration_id": body.registration_id,
            "event_id": reg["event_id"],
        },
    }
    try:
        resp = requests.post(
            _razorpay_api_url("/orders"),
            json=payload,
            headers=_razorpay_headers(),
            auth=(key_id, key_secret),
            timeout=15,
        )
    except Exception as e:
        logger.error(f"Razorpay order create network error: {e}")
        raise HTTPException(status_code=502, detail="Payment gateway unreachable. Please try again.")
    if resp.status_code >= 400:
        logger.error(f"Razorpay order create failed [{resp.status_code}]: {resp.text[:400]}")
        raise HTTPException(status_code=502, detail="Could not create payment order.")
    data = resp.json()
    order_id = data.get("id")
    if not order_id:
        logger.error(f"Razorpay response missing order id: {data}")
        raise HTTPException(status_code=502, detail="Invalid gateway response.")

    tx = PaymentTransaction(
        session_id=order_id,
        registration_id=body.registration_id,
        event_id=reg["event_id"],
        amount=amount_inr,
        currency="inr",
        payment_status="created",
        metadata={
            "registration_id": body.registration_id,
            "event_id": reg["event_id"],
            "student_email": reg.get("email", ""),
            "razorpay_order_id": order_id,
            "amount_paise": amount_paise,
        },
    )
    await db.payment_transactions.insert_one(tx.model_dump())

    return {
        "order_id": order_id,
        "key_id": key_id,
        "amount_paise": amount_paise,
        "amount_inr": amount_inr,
        "currency": "INR",
        "registration_id": body.registration_id,
        "customer_name": reg.get("name") or "SCALE Participant",
        "customer_email": reg.get("email") or "",
        "customer_phone": reg.get("phone") or "",
    }


async def _mark_registration_paid(reg_id: str, amount_inr: float, payment_id: str) -> None:
    """Idempotent: mark registration paid + send confirmation emails."""
    reg = await db.registrations.find_one({"id": reg_id}, {"_id": 0})
    if not reg or reg.get("payment_status") == "paid":
        return
    await db.registrations.update_one(
        {"id": reg_id},
        {"$set": {"payment_status": "paid", "paid_at": now_iso(), "razorpay_payment_id": payment_id}},
    )
    event = await db.events.find_one({"id": reg.get("event_id")}, {"_id": 0})
    rows = [
        ("Event", event["title"] if event else "-"),
        ("Student", reg.get("name", "-")),
        ("Amount", f"INR {int(amount_inr)}"),
        ("Razorpay Payment ID", payment_id),
        ("Status", "PAID"),
    ]
    html = _email_html_table(
        "Payment Confirmed",
        rows,
        intro=f"Hi {reg.get('name', '')}, your payment for <strong>{event['title'] if event else ''}</strong> has been confirmed. We'll be in touch with event details closer to the date.",
    )
    if reg.get("email"):
        send_email(reg["email"], reg.get("name", ""), "SCALE - Payment Confirmed", html)
    if reg.get("parent_email"):
        send_email(reg["parent_email"], reg.get("parent_name", ""), f"SCALE - Payment Confirmed for {reg.get('name', '')}", html)
    notify_admin(f"PAID - {reg.get('name', '')} -> {event['title'] if event else ''}", html)


class VerifyPaymentRequest(BaseModel):
    razorpay_payment_id: str
    razorpay_order_id: str
    razorpay_signature: str


@api_router.post("/payments/verify")
async def verify_payment(body: VerifyPaymentRequest):
    _, key_secret = _razorpay_auth()
    signed = f"{body.razorpay_order_id}|{body.razorpay_payment_id}".encode("utf-8")
    expected = _hmac.new(key_secret.encode("utf-8"), signed, _hashlib.sha256).hexdigest()
    if not _hmac.compare_digest(expected, body.razorpay_signature):
        raise HTTPException(status_code=400, detail="Invalid payment signature")

    tx = await db.payment_transactions.find_one({"session_id": body.razorpay_order_id}, {"_id": 0})
    if not tx:
        raise HTTPException(status_code=404, detail="Order not found")

    await db.payment_transactions.update_one(
        {"session_id": body.razorpay_order_id},
        {"$set": {
            "payment_status": "paid",
            "status": "captured",
            "razorpay_payment_id": body.razorpay_payment_id,
            "updated_at": now_iso(),
        }},
    )
    if tx.get("registration_id"):
        await _mark_registration_paid(tx["registration_id"], float(tx.get("amount", 0.0)), body.razorpay_payment_id)

    return {
        "ok": True,
        "payment_status": "paid",
        "order_id": body.razorpay_order_id,
        "payment_id": body.razorpay_payment_id,
    }


@api_router.get("/payments/status/{order_id}")
async def get_payment_status(order_id: str):
    """Status check used by PaymentSuccessPage polling."""
    tx = await db.payment_transactions.find_one({"session_id": order_id}, {"_id": 0})
    if not tx:
        raise HTTPException(status_code=404, detail="Order not found")

    if tx.get("payment_status") == "paid":
        return {
            "payment_status": "paid",
            "status": "paid",
            "amount": tx.get("amount"),
            "currency": tx.get("currency", "inr"),
        }

    key_id, key_secret = _razorpay_auth()
    try:
        resp = requests.get(
            _razorpay_api_url(f"/orders/{order_id}"),
            headers=_razorpay_headers(),
            auth=(key_id, key_secret),
            timeout=10,
        )
    except Exception as e:
        logger.warning(f"Razorpay status fetch network error: {e}")
        return {
            "payment_status": tx.get("payment_status", "created"),
            "status": tx.get("status", "open"),
            "amount": tx.get("amount"),
            "currency": tx.get("currency", "inr"),
            "note": "pending_external_confirmation",
        }
    if resp.status_code == 404:
        raise HTTPException(status_code=404, detail="Order not found at gateway")
    if resp.status_code >= 400:
        logger.error(f"Razorpay status error [{resp.status_code}]: {resp.text[:300]}")
        return {
            "payment_status": tx.get("payment_status", "created"),
            "status": tx.get("status", "open"),
            "amount": tx.get("amount"),
            "currency": tx.get("currency", "inr"),
            "note": "pending_external_confirmation",
        }
    data = resp.json()
    order_status = (data.get("status") or "").lower()
    if order_status == "paid":
        new_payment_status, new_status = "paid", "captured"
    elif order_status in {"created", "attempted"}:
        new_payment_status, new_status = "created", "open"
    else:
        new_payment_status, new_status = tx.get("payment_status", "created"), tx.get("status", "open")

    razorpay_payment_id = None
    try:
        pays_resp = requests.get(
            _razorpay_api_url(f"/orders/{order_id}/payments"),
            headers=_razorpay_headers(),
            auth=(key_id, key_secret),
            timeout=10,
        )
        if pays_resp.status_code == 200:
            payments = pays_resp.json() or []
            for p in payments:
                if (p.get("status") or "").lower() == "captured":
                    razorpay_payment_id = p.get("id") or ""
                    new_payment_status, new_status = "paid", "captured"
                    break
    except Exception as e:
        logger.warning(f"Razorpay payments fetch failed (non-fatal): {e}")

    update = {"payment_status": new_payment_status, "status": new_status, "updated_at": now_iso()}
    if razorpay_payment_id:
        update["razorpay_payment_id"] = razorpay_payment_id
    await db.payment_transactions.update_one({"session_id": order_id}, {"$set": update})

    if new_payment_status == "paid" and tx.get("payment_status") != "paid" and tx.get("registration_id"):
        await _mark_registration_paid(tx["registration_id"], float(tx.get("amount", 0.0)), razorpay_payment_id or "")

    return {
        "payment_status": new_payment_status,
        "status": new_status,
        "amount": tx.get("amount"),
        "currency": tx.get("currency", "inr"),
    }


@api_router.post("/webhook/razorpay")
async def razorpay_webhook(request: Request):
    """Razorpay -> us. Signature = HMAC-SHA256 over raw_body using webhook secret."""
    raw = await request.body()
    signature = request.headers.get("x-razorpay-signature", "")
    secret = os.environ.get("RAZORPAY_WEBHOOK_SECRET")
    if not secret:
        logger.warning("Razorpay webhook received but RAZORPAY_WEBHOOK_SECRET not set; skipping.")
        return {"received": True}
    if not signature:
        logger.warning("Razorpay webhook missing signature header")
        raise HTTPException(status_code=400, detail="Missing signature header")

    expected = _hmac.new(secret.encode("utf-8"), raw, _hashlib.sha256).hexdigest()
    if not _hmac.compare_digest(expected, signature):
        logger.warning("Razorpay webhook: invalid signature")
        raise HTTPException(status_code=400, detail="Invalid webhook signature")

    import json as _json
    try:
        event = _json.loads(raw.decode("utf-8"))
    except Exception:
        return {"received": True}

    event_type = event.get("event") or event.get("type", "")
    payload = event.get("payload") or {}
    payment_entity = ((payload.get("payment") or {}).get("entity") or {})
    order_entity = ((payload.get("order") or {}).get("entity") or {})
    order_id = payment_entity.get("order_id") or order_entity.get("id")
    razorpay_payment_id = payment_entity.get("id") or ""
    amount = float((payment_entity.get("amount") or order_entity.get("amount") or 0) / 100.0)

    if not order_id:
        return {"received": True}

    if event_type in {"payment.captured", "order.paid"}:
        tx = await db.payment_transactions.find_one({"session_id": order_id}, {"_id": 0})
        if tx and tx.get("payment_status") != "paid":
            await db.payment_transactions.update_one(
                {"session_id": order_id},
                {"$set": {
                    "payment_status": "paid",
                    "status": "captured",
                    "razorpay_payment_id": razorpay_payment_id,
                    "updated_at": now_iso(),
                }},
            )
            if tx.get("registration_id"):
                await _mark_registration_paid(tx["registration_id"], amount or float(tx.get("amount", 0.0)), razorpay_payment_id)
    elif event_type == "payment.failed":
        await db.payment_transactions.update_one(
            {"session_id": order_id},
            {"$set": {"payment_status": "failed", "status": "failed", "updated_at": now_iso()}},
        )
    return {"received": True}
@api_router.get("/")
async def root():
    return {"message": "SCALE India API"}


app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get("CORS_ORIGINS", "*").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)


