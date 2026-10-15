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
- `app.py` - main Flask app, routes, startup bootstrap
- `models.py` - SQLAlchemy models (Car, Booking, StoredImage, AdminUser)
- `services/` - production WhatsApp link integration (`services/whatsapp.py`)
- `dummy_data/` - organized seed datasets & seeder script (`dummy_data/seed_data.py`)
- `tests/` - automated verification test suite (`tests/test_app.py`)
- `templates/` - UI templates (`/en/`, `/es/`, and admin views)
- `archive/` - retired legacy templates and services (`archive/services/`)

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
- `ADMIN_USER`
- `ADMIN_PASSWORD`

At startup, `app.py` auto-creates the admin user if missing.
In production, both variables are required and must be provided through secure environment variables (for example, Render dashboard secret env vars).

### Messaging & WhatsApp
- `GARAGE_MOBILE` - Luca's phone number with country code (default `447535321145`).
- `CALLMEBOT_API_KEY` - Optional CallMeBot WhatsApp alert key.

## Database notes
- Tables are created automatically at app startup (`db.create_all()` in `app.py`).
- Local default DB file is `garage.db` in project root.
- To seed sample data:
  ```bash
  python dummy_data/seed_data.py
  # or: python seed_data.py
  ```

## Running verification tests
Run:
```bash
python tests/test_app.py
# or: python test_app.py
```

The script exercises homepage rendering, inventory/detail pages, booking API/business rules, admin login, editing flows, image serving, and security headers.

## Docker
Docker instructions are in:
- `/home/runner/work/Lucas-garage-landingpage/Lucas-garage-landingpage/README.Docker.md`

## Developer documentation
For maintenance workflows and common fixes, see:
- `/home/runner/work/Lucas-garage-landingpage/Lucas-garage-landingpage/docs/DEVELOPER_GUIDE.md`
