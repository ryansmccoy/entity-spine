# Entity Spine Backend

FastAPI backend for Entity Spine - Financial Data & Knowledge Graph Platform.

## Features

- **Company Profiles**: Comprehensive company data with financial metrics
- **SEC Filings**: Search, browse, and analyze SEC filings
- **Knowledge Graph**: Entity extraction and relationship mapping
- **Universal Search**: Search across companies, filings, and entities
- **Watchlists**: Track companies and receive alerts

## Setup

### Prerequisites

- Python 3.11+
- PostgreSQL 15+
- Redis (optional, for caching)
- Elasticsearch (optional, for enhanced search)

### Installation

1. Create virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Configure environment:
```bash
cp .env.example .env
# Edit .env with your database credentials
```

4. Initialize database:
```bash
# Apply schema
psql -d entityspine -f ../db/schema.sql
```

5. Run development server:
```bash
uvicorn app.main:app --reload
```

## API Documentation

Once running, visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Project Structure

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI application
│   ├── api/
│   │   └── v1/
│   │       ├── router.py    # API router
│   │       └── endpoints/   # API endpoint modules
│   │           ├── companies.py
│   │           ├── filings.py
│   │           ├── entities.py
│   │           ├── search.py
│   │           └── watchlists.py
│   ├── core/
│   │   ├── config.py        # Settings & configuration
│   │   └── logging.py       # Logging setup
│   ├── db/
│   │   ├── session.py       # Database session
│   │   └── migrations/      # Alembic migrations
│   ├── models/              # SQLAlchemy models
│   │   ├── company.py
│   │   ├── filing.py
│   │   └── entity.py
│   ├── schemas/             # Pydantic schemas
│   │   ├── company.py
│   │   └── filing.py
│   └── services/            # Business logic
├── tests/
│   ├── conftest.py
│   ├── unit/
│   ├── integration/
│   └── e2e/
├── requirements.txt
├── requirements-dev.txt
└── README.md
```

## Configuration

Environment variables (`.env`):

```env
# Database
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/entityspine

# Redis
REDIS_URL=redis://localhost:6379/0

# Security
SECRET_KEY=your-secret-key
ACCESS_TOKEN_EXPIRE_MINUTES=30

# SEC Edgar
SEC_EDGAR_USER_AGENT=Your Company your@email.com

# Features
ENABLE_AI_SUMMARIES=false
ENABLE_KNOWLEDGE_GRAPH=true
```

## Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app

# Run specific test file
pytest tests/unit/test_companies.py
```

## License

MIT
