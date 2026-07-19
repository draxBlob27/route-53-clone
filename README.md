# AWS Route 53 Clone

A small full-stack clone of the AWS Route 53 console. The aim of this project was to reproduce the main Route 53 workflow—managing hosted zones and DNS records—without implementing real DNS resolution or AWS account integration.

## Live demo

The application is deployed here: [http://34.87.172.133:3000/](http://34.87.172.133:3000/)

Authentication is mocked for the demo. Enter any valid email address on the sign-in screen to access the console.

## What is included

- Mocked sign-in and sign-out with a persistent browser session
- Create, view, edit, search, and delete hosted zones
- Create, view, edit, search, and delete DNS records within a hosted zone
- Support for A, AAAA, CNAME, TXT, MX, NS, PTR, SRV, and CAA record types
- SQLite-backed persistence
- Route 53-inspired navigation, hosted-zone table, record table, forms, modals, filters, notifications, and empty states
- Placeholder pages for Dashboard, Traffic Policies, Health Checks, Resolver, and Profiles

## Tech stack

- Frontend: Next.js with TypeScript
- Backend: FastAPI
- Database: SQLite with SQLAlchemy

## Project structure

```text
.
├── frontend/             # Next.js application and Route 53-style UI
│   └── app/
├── backend/              # FastAPI application
│   ├── main.py           # API routes, models, and SQLite setup
│   └── requirements.txt
└── README.md
```

## Running the project locally

Start the API first:

```bash
cd backend
python3 -m venv .venv
PIP_CACHE_DIR=.pip-cache .venv/bin/pip install -r requirements.txt
.venv/bin/uvicorn main:app --reload --port 8000
```

Then, in a second terminal, start the frontend:

```bash
cd frontend
npm install --cache .npm-cache
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) in the browser.

## Architecture

The frontend is a single-page console built with Next.js. It talks to the FastAPI backend through JSON REST endpoints. The backend creates a local SQLite file (`backend/route53.db`) on first start, so hosted zones and records remain available after a server restart.

The sign-in flow is intentionally simple: the backend stores the supplied email address in a cookie and uses it to protect the application endpoints. AWS IAM and account-management features are outside this project’s scope.

## Database design

There are two main tables:

| Table | Purpose |
| --- | --- |
| `hosted_zones` | Stores the zone ID, domain name, optional comment, zone type, and creation time. |
| `dns_records` | Stores each record’s ID, parent hosted-zone ID, name, type, value, TTL, and routing policy. |

A hosted zone owns its DNS records. Removing a hosted zone also removes its associated records.

## API summary

| Area | Endpoints |
| --- | --- |
| Authentication | `POST /api/auth/login`, `POST /api/auth/logout`, `GET /api/auth/me` |
| Hosted zones | `GET`, `POST /api/zones`; `GET`, `PUT`, `DELETE /api/zones/{id}` |
| DNS records | `GET`, `POST /api/zones/{id}/records`; `PUT`, `DELETE /api/records/{id}` |

The list endpoints support search. Record listing also supports filtering by record type.

## Notes

This is a UI and workflow clone, not a DNS server. Creating or changing a record in this application only updates its local SQLite database; it does not modify live DNS records.
