# CrimeMind AI — Backend

FastAPI backend for the CrimeMind AI investigation copilot.

## Tech Stack

- **Python 3.12** + **FastAPI 0.115** + **Uvicorn**
- **SQLAlchemy 2** (async via asyncpg) + **Alembic** migrations
- **Pydantic v2** + **pydantic-settings**
- **PostgreSQL** (target DB)

## Quick Start

### 1. PostgreSQL setup

```sql
CREATE USER crimemind_user WITH PASSWORD 'changeme';
CREATE DATABASE crimemind OWNER crimemind_user;
```

### 2. Python environment

```bash
cd backend/
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 3. Environment variables

```bash
cp .env.example .env
# Edit .env with your real credentials
```

### 4. Run Alembic migrations

```bash
alembic upgrade head
```

### 5. Start the development server

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/health` | Health check |
| GET | `/docs` | Swagger UI (dev only) |
| GET | `/redoc` | ReDoc (dev only) |

## Project Structure

```
backend/
├── app/
│   ├── api/v1/          # Route handlers
│   ├── config/          # pydantic-settings
│   ├── core/            # Logging, exceptions
│   ├── db/              # Engine, session, init
│   ├── models/          # SQLAlchemy ORM models
│   ├── schemas/         # Pydantic request/response schemas
│   ├── services/        # Business logic (future)
│   ├── utils/           # Shared utilities (future)
│   └── main.py          # Application factory
├── alembic/             # Migration scripts
├── alembic.ini
├── requirements.txt
├── .env.example
└── .gitignore
```
