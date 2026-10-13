# Lucas Garage Landing Page

Flask-based website and admin portal for Lucas Garage vehicle listings, viewing bookings, and customer communications.

## What this project does
- Public pages for inventory, vehicle details, pricing, and about information (English + Spanish routes).
- Booking flow with email verification and booking status management.
- Admin dashboard for vehicle CRUD, booking updates, and marketplace ad text generation.
- Notification integrations for email, Telegram, and WhatsApp helper links.
- Persistent image serving with DB fallback when local upload files are missing.

## Tech stack
- Python 3 + Flask
- Flask-SQLAlchemy + Flask-Login
- SQLite (default local) or PostgreSQL via `DATABASE_URL`
- Jinja templates in `/templates`, static files in `/static`

## Repository structure
- `/home/runner/work/Lucas-garage-landingpage/Lucas-garage-landingpage/app.py` - main Flask app, routes, startup bootstrap
- `/home/runner/work/Lucas-garage-landingpage/Lucas-garage-landingpage/models.py` - SQLAlchemy models
- `/home/runner/work/Lucas-garage-landingpage/Lucas-garage-landingpage/services/` - integrations/utilities (notifications, WhatsApp, calendar, verification, AI assistant)
- `/home/runner/work/Lucas-garage-landingpage/Lucas-garage-landingpage/templates/` - UI templates
- `/home/runner/work/Lucas-garage-landingpage/Lucas-garage-landingpage/test_app.py` - regression verification script
- `/home/runner/work/Lucas-garage-landingpage/Lucas-garage-landingpage/seed_data.py` - sample data seeding script

## Local development setup
1. Create and activate a virtual environment.
2. Install dependencies:
   ```bash
   pip install -r /home/runner/work/Lucas-garage-landingpage/Lucas-garage-landingpage/requirements.txt
   ```
3. (Optional) create a `.env` file in repository root.
4. Run the app:
   ```bash
   python /home/runner/work/Lucas-garage-landingpage/Lucas-garage-landingpage/app.py
   ```
5. Open `http://localhost:5000`.

## Environment variables
Only set what you need; sane defaults exist for local development.

### Core app
- `SECRET_KEY` - signing/session secret.
- `DATABASE_URL` - SQLAlchemy DB URI (default `sqlite:///garage.db`).
- `FLASK_DEBUG` - set to `1`/`true` for debug mode.
- `FLASK_ENV` / `RENDER` - influence secure cookie + HSTS behavior.

### Admin login bootstrap
- `ADMIN_USER` (default `luca`)
- `ADMIN_PASSWORD` (default `lucasgarage2026`)

At startup, `app.py` auto-creates the admin user if missing.

### Messaging/notifications
- Email (SMTP): `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASS`, `FROM_EMAIL`, `LUCA_EMAIL`
- Email (Resend): `RESEND_API_KEY`
- Telegram: `TELEGRAM_BOT_TOKEN`, `TELEGRAM_LUCA_CHAT_ID`
- WhatsApp helper: `GARAGE_MOBILE`, `CALLMEBOT_API_KEY`

### Optional AI assistant
- `GEMINI_API_KEY`

## Database notes
- Tables are created automatically at app startup (`db.create_all()` in `app.py`).
- Local default DB file is `garage.db` in project root.
- To seed sample data:
  ```bash
  python /home/runner/work/Lucas-garage-landingpage/Lucas-garage-landingpage/seed_data.py
  ```

## Running verification tests
Run:
```bash
python /home/runner/work/Lucas-garage-landingpage/Lucas-garage-landingpage/test_app.py
```

The script exercises homepage rendering, inventory/detail pages, booking API/business rules, admin login, editing flows, image serving, and security headers.

## Docker
Docker instructions are in:
- `/home/runner/work/Lucas-garage-landingpage/Lucas-garage-landingpage/README.Docker.md`

## Developer documentation
For maintenance workflows and common fixes, see:
- `/home/runner/work/Lucas-garage-landingpage/Lucas-garage-landingpage/docs/DEVELOPER_GUIDE.md`
