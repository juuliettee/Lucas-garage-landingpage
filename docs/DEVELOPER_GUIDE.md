# Developer Guide

This guide is for developers maintaining the Lucas Garage app.

## 1) Quick start checklist
1. Install deps: `pip install -r requirements.txt`
2. Start app: `python app.py`
3. Run regression checks: `python test_app.py`
4. Log in admin at `/login` using `ADMIN_USER` / `ADMIN_PASSWORD`

## 2) Core architecture map
- **Entry point:** `app.py`
- **Data models:** `models.py`
- **Notifications:** `services/notifications.py`
- **WhatsApp links/alerts:** `services/whatsapp.py`
- **Booking verification token logic:** `services/verification.py`
- **Calendar invite generation:** `services/calendar_service.py`
- **AI assistant fallback + Gemini integration:** `services/ai_assistant.py`

## 3) Key business flows

### Vehicle listing flow
- Add/edit vehicles through admin routes in `app.py` (`/admin/add`, `/admin/car/edit/<id>`).
- Primary image is stored on `Car.image_filename`; extra images in `CarImage`.
- Uploaded files are cached on disk under `static/uploads` and also persisted in `StoredImage`.

### Viewing booking flow
- Public API endpoint: `/api/book-viewing`.
- Booking is created in `Pending_Verification` state with signed token.
- Confirmation route validates token and transitions to `Confirmed`.
- Confirmation dispatches email + calendar + optional Telegram alert.

### Image serving resiliency
- Route: `/static/uploads/<filename>`.
- Order of resolution:
  1. Serve from `static/uploads` if present.
  2. Rehydrate from `StoredImage` DB binary if missing on disk.
  3. Fallback to known default images.

## 4) Common maintenance tasks

### Change opening-hour validation
- Update booking-hour rules in `app.py` booking logic.
- Re-run `python test_app.py` (tests include opening-hours assertions).

### Update admin credentials
- Prefer setting `ADMIN_USER` and `ADMIN_PASSWORD` in environment.
- On fresh DB, startup bootstrap creates the configured admin user.
- For existing users, update via DB (passwords are hashed).

### Diagnose failed customer emails
1. Check if `RESEND_API_KEY` is set (Resend path is attempted first).
2. If not using Resend, ensure `SMTP_USER` + `SMTP_PASS` are set.
3. Use `/admin/test-email` after logging in to validate dispatch path.
4. Review server logs for `[RESEND ERROR]` / `[SMTP ERROR]` messages.

### Diagnose missing vehicle images
1. Verify filename exists in `Car.image_filename` or related `CarImage` records.
2. Check file presence under `static/uploads`.
3. If missing from disk, confirm `StoredImage` contains the same filename.
4. If neither exists, re-upload the image from admin edit page.

### Diagnose login failures
1. Confirm `.env` (or deploy env) has intended `ADMIN_USER`/`ADMIN_PASSWORD`.
2. Confirm matching `admin_users.username` exists in DB.
3. If needed, reset password hash directly in DB using Werkzeug hash function.

## 5) Testing expectations before merging
- Minimum verification for feature/bugfix work:
  - `python test_app.py`
- If change touches notifications, manually validate at least one path (e.g., `/admin/test-email`).
- If change touches templates, check both `/en/*` and `/es/*` routes for affected pages.

## 6) Security and operational notes
- Keep `SECRET_KEY` private and unique per environment.
- Do not commit API keys or mail credentials.
- Uploaded files are restricted by extension and size checks; keep these checks intact.
- Security headers are applied globally in `app.py` via `@app.after_request`.

## 7) Known quirks to be aware of
- `seed_data.py` uses sample credentials and data intended for local bootstrapping only.
- `services/ai_assistant.py` contains garage hours text independent of booking validation logic; if business hours change, update both areas.
- Test script reads admin defaults from env with fallback values, so env mismatch can cause login test failures.
