# Dummy & Seed Data

This directory houses mock and seed datasets used for local development, staging environments, and database bootstrapping for Lucas Garage.

---

## Contents

* **`cars.json`**: Structured JSON dataset containing realistic used vehicles, Copart salvage repair records, MOT dates, features, and specs (Ford Focus, VW Golf, Vauxhall Corsa).
* **`seed_data.py`**: Automated seeding script that parses `cars.json`, creates the initial admin user, and populates vehicle inventory.

---

## Usage

To populate your database with dummy data, run:

```bash
python dummy_data/seed_data.py
```

Or from Python:

```python
from dummy_data import seed_database
seed_database()
```
