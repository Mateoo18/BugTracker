# BugTracker Django

A complete Django + Django REST Framework bug tracking system using SQLite and a Django-friendly clean architecture split:

- `domain` - pure domain logic, including priority scoring.
- `application` - use-case services for creating bugs, assignment, status changes, and priority handling.
- `infrastructure` - Django models, admin, migrations, and demo seed data.
- `presentation/api` - DRF serializers, permissions, viewsets, and business endpoints.
- `presentation/web` - server-rendered Django Templates UI.
- `shared_kernel` - shared role constants and small helpers.

## Run locally

```bash
python -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt
python manage.py migrate
python manage.py seed_demo
python manage.py runserver
```

Web UI: <http://127.0.0.1:8000/>

API: <http://127.0.0.1:8000/api/>

Admin: <http://127.0.0.1:8000/admin/>

## Demo accounts

Password for every demo account: `demo1234`

| Login | Name | Role |
| --- | --- | --- |
| `reporter` | Olivia Reporter | Reporter |
| `admin` | Ava Admin | Admin / superuser |
| `po.acme` | Emma Carter | Product Owner |
| `dev.acme.james` | James Wilson | Developer |
| `dev.acme.sophia` | Sophia Martin | Developer |
| `po.northwind` | Liam Anderson | Product Owner |
| `dev.northwind.noah` | Noah Brown | Developer |
| `dev.northwind.mia` | Mia Davis | Developer |
| `po.globex` | Charlotte Miller | Product Owner |
| `dev.globex.ethan` | Ethan Moore | Developer |
| `dev.globex.amelia` | Amelia Taylor | Developer |
| `po.initech` | Benjamin Thomas | Product Owner |
| `dev.initech.harper` | Harper Jackson | Developer |
| `dev.initech.lucas` | Lucas White | Developer |

## Product Owner workflow

Admins create and manage Product Owner accounts. A Product Owner belongs to a company and can create teams and developer accounts for that company from the staff dashboard. When a developer account is created, BugTracker emails a temporary first-login password. After the developer logs in with that temporary password, the app forces them to set a personal password before they can continue.

## Main API endpoints

- `POST /api/bugs/create/` - create a bug with an optional image.
- `POST /api/bugs/{id}/assign/` - assign a bug to a team and user.
- `POST /api/bugs/{id}/status/` - change bug status.
- `GET /api/bugs/my/` - bugs reported by the current user.
- `GET /api/bugs/assigned/` - bugs assigned to the current user.
- `GET /api/bugs/company-board/` - company bug board.
- `GET /api/bugs/public-resolved/` - resolved public board.
- `POST /api/bugs/{id}/priority/recalculate/` - recalculate priority or apply a manual override.

CRUD endpoints are available through the DRF router for companies, teams, users, bugs, comments, assignments, attachments, status history, and priority history.

## Logging

Django logging writes:

- daily application logs to `logs/bugtracker.log`, rotated at midnight,
- error logs to `logs/errors.log`, rotated separately.

## Tests

```bash
python manage.py test
```
