# Archive & Deprecated Assets

This folder houses retired code, legacy components, and prior iterations that are **no longer in active production use** on the live website ([lucasgarage.uk](https://lucasgarage.uk)), preserved for historical auditability and version reference.

---

## Contents

### 1. `legacy_templates/`
* **What it contains**:
  - `index.html`
  - `about.html`
  - `pricing.html`
  - `cars.html`
  - `car_detail.html`
  - `booking_confirmed.html`
  - `404.html`
  - `500.html`
* **Reason for Archiving**:
  These represent the original single-directory templates that relied on client-side Google Translate widgets, cookie watchers, and DOM mutation observers.
* **Current Active Replacement**:
  All production user-facing pages now live in native, dedicated language subdirectories:
  - English: `templates/en/` (`/en/`, `/en/about`, `/en/pricing`, `/en/cars`, `/en/car/<id>`)
  - Spanish: `templates/es/` (`/es/`, `/es/about`, `/es/pricing`, `/es/cars`, `/es/car/<id>`)

---

## Active Project Structure Quick Reference

```text
├── app.py                      # Flask routes, context processors & i18n subdirectory routing
├── models.py                   # SQLAlchemy models (Car, Booking, StoredImage, AdminUser)
├── test_app.py                 # Automated verification test suite (15 passing tests)
├── requirements.txt            # Python dependencies (Flask, SQLAlchemy, Gunicorn, etc.)
├── render.yaml                 # Render cloud web service configuration
├── static/
│   ├── img/                    # Static image assets (logos, icons)
│   └── robots.txt              # Production search engine crawl directives
├── templates/
│   ├── en/                     # Active English subdirectory templates (/en/...)
│   ├── es/                     # Active Spanish subdirectory templates (/es/...)
│   ├── admin.html              # Workshop & mechanic management dashboard
│   ├── base.html               # Shared layout for admin & portal tools
│   ├── edit_car.html           # Vehicle editor modal & multi-image upload
│   └── login.html              # Secure mechanic portal login
└── archive/                    # Archived / deprecated historical assets
    ├── legacy_templates/       # Pre-i18n single-directory templates
    └── README.md               # This archive documentation guide
```
