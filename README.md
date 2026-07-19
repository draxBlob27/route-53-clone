# AWS Route 53 Clone

A Route 53-style DNS management console built with Next.js, FastAPI, and SQLite. It provides a mocked sign-in flow, persistent hosted-zone CRUD, and CRUD for A, AAAA, CNAME, TXT, MX, NS, PTR, SRV, and CAA records.

## Run locally

All dependencies are installed inside their respective project folders:

```bash
cd backend
python -m venv .venv
PIP_CACHE_DIR=.pip-cache .venv/bin/pip install -r requirements.txt
.venv/bin/uvicorn main:app --reload --port 8000
```

In another terminal:

```bash
cd frontend
npm install --cache .npm-cache
npm run dev
```

Open `http://localhost:3000`. The app accepts any valid email address for its local mocked session.

## Architecture

- `frontend/`: single-page Next.js TypeScript console, styled to mirror Route 53 navigation, tables, filters, forms, modals, notifications, and placeholder sections.
- `backend/main.py`: FastAPI REST API with cookie-backed mock authentication.
- `backend/route53.db`: SQLite database, generated automatically on first server start and intentionally ignored from source control.

## Database schema

`hosted_zones` stores UUID, domain name, comment, public/private flag, and timestamp. `dns_records` stores UUID, owning zone UUID, name, type, value, TTL, and routing policy. Deleting a hosted zone cascades to its records.

## API overview

Authentication: `POST /api/auth/login`, `POST /api/auth/logout`, `GET /api/auth/me`.

Hosted zones: `GET/POST /api/zones`, `GET/PUT/DELETE /api/zones/{id}`.

Records: `GET/POST /api/zones/{id}/records`, `PUT/DELETE /api/records/{id}`. List endpoints support text filters; record lists can also filter by `type`.

## Deployment

Build the frontend with `npm run build`, serve it with `npm start`, and run the FastAPI service behind an HTTPS reverse proxy. Set the frontend API base URL to the deployed backend origin before publishing.
