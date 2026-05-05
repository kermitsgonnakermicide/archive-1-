# SCALE India — Test Credentials

## Admin Account
- Email: `scalesupportteam2@gmail.com`
- Password: `SCALEdaddySALLU67`
- Access: `/admin` (Content, Events, Pages, Sessions, Theme, Registrations, Submissions)

## User Accounts
No pre-seeded user accounts. Sign up via `/signup`.

## Brevo (Email)
- API key in backend `.env` as `BREVO_API_KEY`.
- **Sender (validated)**: `scalesupportteam2@gmail.com` (verified in Brevo dashboard 2026-02). Backup validated sender: `veer.sahni01@gmail.com`.
- Reply-to / admin notify recipient: `scalesupportteam2@gmail.com`.
- Verify deliveries: `curl https://api.brevo.com/v3/smtp/statistics/events?limit=10 -H "api-key: $BREVO_API_KEY"`. Look for `event=delivered`.

## Razorpay
- Add your test `RAZORPAY_KEY_ID`, `RAZORPAY_KEY_SECRET`, and `RAZORPAY_WEBHOOK_SECRET` in backend `.env` or `.env.casaos`.
- Payment flow: `/payment/{registration_id}` -> Razorpay Checkout -> `/payment-success?session_id=...&reg=...`.
