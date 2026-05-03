# SCALE India — Product Requirements Document

## Problem Statement
Multi-page website for SCALE — India's first national high-school student org for business, finance, marketing, leadership. Single-page anchor navigation + event detail pages + internal payment + admin CMS with inline-edit + admin-managed custom pages.

## Architecture
- **Backend**: FastAPI + MongoDB (motor), JWT auth, bcrypt, Brevo transactional email, Stripe Checkout (via emergentintegrations + stripe SDK fallback). Object storage via emergentintegrations.
- **Frontend**: React 19 + React Router + Tailwind + shadcn/ui, sonner toasts, Playfair Display + DM Sans.
- **Palette**: deep crimson #B01020, dark red #4A0008, cream #F4ECD8, off-white #FAF8F5, gold #C9931A, gold-light #F5C842.

## User Personas
- **Student visitor** — browses, registers for events (individual or team), submits scholarship applications.
- **Parent** — receives co-notification emails with payment + scholarship links.
- **Admin** — logs in, edits content/events/sessions/theme/**pages** via admin dashboard or inline on the live site, builds dynamic event registration forms, views registrations + form submissions.

## Core Requirements
- Home single-scroll: hero, fields strip, 4 pillars, upcoming event banner, about, events list, our story, contact.
- Event detail page `/events/:id` with mode-aware registration (individual or team of 2–N).
- After registration: Brevo emails parent + student/team with payment + scholarship links.
- Internal payment page `/payment/:registrationId` → Stripe Checkout (UPI + Cards).
- Scholarship-per-event form `/events/:id/scholarship` (financial proof file upload + why participate).
- Admin `/admin`: Content / Events / **Pages** / Sessions / Theme / Registrations / Submissions tabs.
- Admin inline edit: nav toggle → click any text to edit, saves to `/api/content`. Add/remove handles on pillars, why-scale, events.
- **Custom Pages CMS**: admin can create/edit/delete arbitrary pages (e.g. SCALE+, FAQ, Mentors). Each page is built from typed blocks (hero, section, cards, cta, image, richtext). Published pages with `show_in_nav` auto-appear in navbar.
- **Dynamic form builder**: per-event admin can add/edit/reorder/delete custom questions with 9 field types (text, textarea, email, number, yesno, select, radio, checkbox, file). Required flag + help text. For team events, each question has a scope: **team** (captain answers once) or **member** (each member answers individually).

## Implemented (updated 2026-02 — Iteration 9 through 12)
### Iteration 13 — Cashfree replaces Razorpay
- Cashfree Payment Gateway v3 (API version 2023-08-01) replaces Razorpay end-to-end. Flow: backend creates Order → returns `payment_session_id` → frontend opens `window.Cashfree({mode}).checkout({paymentSessionId, redirectTarget:'_self'})` → Cashfree redirects to `/payment-success?session_id=<order_id>&reg=<reg_id>` → `PaymentSuccessPage` polls `GET /api/payments/status/<order_id>` which calls Cashfree's `/pg/orders/{id}` to fetch authoritative status and (if PAID) marks the registration + sends confirmation emails.
- Backend routes: `POST /api/payments/create-order` (idempotent, reuses existing unpaid order), `GET /api/payments/status/{order_id}` (reads Cashfree's order + payments APIs, normalises status), `POST /api/webhook/cashfree` (HMAC-SHA256 over `timestamp + raw_body`, handles `PAYMENT_SUCCESS_WEBHOOK` / `PAYMENT_FAILED_WEBHOOK`).
- Env vars: `CASHFREE_APP_ID`, `CASHFREE_SECRET_KEY`, `CASHFREE_WEBHOOK_SECRET`, `CASHFREE_ENV=TEST|PROD` (base URL toggles between `sandbox.cashfree.com` and `api.cashfree.com`). Routes cleanly 503 with "Payment gateway not configured" until admin fills in APP_ID + SECRET_KEY.
- Razorpay SDK removed (`razorpay==2.0.1` uninstalled). Razorpay env vars dropped from `.env`.

### Iteration 12 — Post-Registration Event Hub
- **Route**: `/events/:id/registered?reg=<reg_id>` — gated by `registration.payment_status === "paid"`. 402 unpaid → "Complete payment" CTA; 404 → "Registration not found"; no `reg_id` → redirect to event page.
- **Backend routes**:
  - `GET /api/events/{id}/materials?reg_id=X` — dual gate (admin OR paid reg)
  - `PUT /api/events/{id}/materials` — admin; stores `{notes, links, documents}` on the event doc
  - `POST /api/events/{id}/files` — admin upload (25 MB cap, PDF/DOC/PPT/XLS/images/audio/video)
  - `GET /api/events/{id}/files/{file_id}/download?reg_id=X` — gated download
  - `POST /api/events/{id}/submission-files?reg_id=X` — paid-reg upload
  - `POST /api/events/{id}/submissions` — create-or-update submission (one per registration, idempotent)
  - `GET /api/events/{id}/submissions/mine?reg_id=X` — student's own submission
  - `GET /api/admin/events/{id}/submissions` — admin list
  - `GET /api/admin/events/{id}/submissions/export` — CSV download with UTF-8 BOM
- **Admin UI**: "Post-registration hub" collapsible section on each event row in `Admin → Events`, with Materials tab (notes/links/docs editor) + Submissions tab (listing + CSV export + per-file download).
- **Payment-success redirect**: On confirmed payment, `PaymentSuccessPage` shows "Go to Event Hub →" button linking to `/events/:id/registered?reg=<reg_id>`.

### Iteration 11 — Razorpay + inline page controls + email-link fix
- Swapped Stripe → Razorpay. Backend: `POST /api/payments/create-order`, `POST /api/payments/verify` (HMAC-SHA256 signature check), `POST /api/webhook/razorpay`. Frontend: Razorpay Checkout via `window.Razorpay`. Env: `RAZORPAY_KEY_ID`, `RAZORPAY_KEY_SECRET`, `RAZORPAY_WEBHOOK_SECRET` — currently unset; endpoints return 503 with clear message until admin fills them in.
- Email-link host fix: `_resolve_public_origin()` helper reads `PUBLIC_BASE_URL` env → `Origin` header → `Referer` → fallback. Fixed dead internal-pod URLs in confirmation emails.
- Inline hide-page toggle on `/p/:slug`: admin sees "Show in navbar" + "Published" checkboxes in the cream banner; flipping them propagates to the global navbar immediately via `refreshPages()`.
- Spam-folder hint on registration-success card.

### Iteration 10 — Form-builder fix
- `EventUpdate` and `PageUpdate` switched from `extra="forbid"` → `extra="ignore"` (fix for HTTP 422 on full round-trip saves).

### Iteration 9 — Pages CMS + extended ExtraField + Brevo sender fix
- Custom Pages CMS (hero/section/cards/cta/image/richtext blocks), admin tab, `/p/:slug` route.
- `ExtraField` extended to 9 types + scope (team/member) + help_text.
- Brevo sender switched to verified `scalesupportteam2@gmail.com`.

- All iterations: regression tests in `/app/backend/tests/` (iteration9, form-builder regression, iteration10-post-reg-hub from testing agent).

## Prioritised Backlog
- **P1**: Stripe webhook reconciliation — verify webhook URL reachable, test with Stripe CLI.
- **P2**: Split server.py into routers (payments, registrations, admin, content, pages) — currently ~1100 lines.
- **P2**: Migrate `@app.on_event` to FastAPI lifespan context manager.
- **P3**: SEO — meta tags / OG images / sitemap (especially for custom pages).
- **P3**: Analytics dashboard (admin) — registrations by event, conversion funnel, paid %.
- **P3**: Rich content blocks for pages — gallery / video / testimonial / pricing-table.
- **P3**: Mobile visual pass on EventDetailPage "Registration closed" card.

## Next Tasks
1. Mobile polish on registration-closed state.
2. Validate the "scale-plus" page content with the user; offer to seed a starter SCALE+ page on request.
3. Add gallery/video block types if user requests richer pages.
