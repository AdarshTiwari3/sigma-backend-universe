# Food Delivery Stream: Professional Setup Guide

This project is a high-performance, event-driven food delivery backend built with **FastAPI**, **Kafka**, and **PostgreSQL**, following **Clean Architecture** principles.

---

## 🏗️ 1. Project Architecture
We maintain a strict separation of concerns to ensure the "Business Brain" is never tightly coupled to the "Database/Kafka Tools."

```text
food-delivery-stream/
├── migrations/             # Alembic database migration versions
├── src/
│   └── app/
│       ├── main.py         # App Entry Point & Lifespan Management
│       ├── api/            # API Controllers (FastAPI Routes)
│       ├── core/           # Config (Pydantic Settings) & Constants
│       ├── models/         # SQLAlchemy Domain Entities (Tables)
│       ├── schemas/        # Pydantic DTOs (Data Validation)
│       ├── services/       # Business Logic (The Brain)
│       ├── repositories/   # DB Queries (CRUD Operations)
│       └── infrastructure/ # External Adapters
│           ├── database/   # Connection & Session Setup
│           └── kafka/      # Producer & Consumer Logic
├── tests/                  # Test Suite
│   ├── __init__.py
│   ├── conftest.py         # Pytest fixtures (DB session, Kafka mock)
│   ├── unit/               # Logic tests (no DB/Kafka)
│   │   └── services/
│   ├── integration/        # Component tests (DB/Kafka involved)
│   │   ├── api/
│   │   └── repositories/
│   └── e2e/                # Full flow tests (Docker required)
├── .env
├── alembic.ini             # Migration Configuration
├── docker-compose.yml      # Infrastructure Orchestration
├── pyproject.toml          # UV Project & Tooling Config
└── README.md
```

## 🛠️ 2. Development Environment Setup
- 2.1 Initialize with uv

    ```bash
    # Initialize the application structure
    uv init --app

    # Add Core Production Dependencies
    uv add "fastapi[standard]" aiokafka pydantic-settings sqlalchemy asyncpg aiomysql

    # Add Development & Quality Tooling
    uv add --dev ruff mypy bandit pylint pytest alembic

    # Run the app in debug mode
    uv run uvicorn src.app.main:app --reload
    # or
    uv run uvicorn src.app.main:app --reload --host 0.0.0.0 --port 8000

    ```
- 2.2 Directory setup:

    Run this to create the full package structure with __init__.py files:

    ```bash
    mkdir -p src/app/{api,core,models,schemas,services,repositories,infrastructure/database,infrastructure/kafka}

    mv main.py src/app/main.py


    ```

## 📜 3. Database Migration Strategy (Alembic)

In a PBC, we never use ```Base.metadata.create_all()```. We version control the schema.

1. Initialize: ```uv run alembic init migrations```

2. Setup: Ensure migrations/env.py imports your Base and models.

3. Generate: ```uv run alembic revision --autogenerate -m "Initial Schema"```

4. Deploy: ```uv run alembic upgrade head``` - this will create the table if not present

## 4. Code Quality Guardrails
Configure these in pyproject.toml to maintain a high "Industry Standard" score.

```bash 


# black formatter related configuration

[tool.black]
line-length = 100
target-version = ["py311"]
skip-string-normalization = false

# ruff related configuration

[tool.ruff]
line-length = 100
target-version = "py311"

[tool.ruff.lint]
select = [
    "E",   # pycodestyle errors
    "F",   # pyflakes
    "I",   # import sorting
    "B",   # flake8-bugbear
    "UP",  # pyupgrade
    "C4",  # comprehensions
]
ignore = ["E501"]  # line too long handled by black

[tool.ruff.format]
quote-style = "double"
indent-style = "space"

# mypy related configuration

[tool.mypy]
python_version = "3.11"
strict = true

warn_unused_configs = true
warn_unused_ignores = true
warn_return_any = true

disallow_untyped_defs = true
disallow_incomplete_defs = true
check_untyped_defs = true
no_implicit_optional = true

ignore_missing_imports = true


# bandit related configuration

[tool.bandit]
exclude_dirs = ["tests"]
skips = ["B101"]

#pytest setup

[tool.pytest.ini_options]
pythonpath = ["."]

```