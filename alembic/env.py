# alembic/env.py
from logging.config import fileConfig
from alembic import context
from sqlalchemy import engine_from_config, pool

# --- Load .env so we can read DB_URL
import os, sys
from pathlib import Path
from dotenv import load_dotenv

# Ensure project root is on sys.path (so "model" imports work when running alembic from repo root)
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Load .env at project root
load_dotenv(PROJECT_ROOT / ".env")

# Import your SQLAlchemy Base metadata
from model.base import Base  # <- make sure this is correct for your project

# Load all models so they're registered with Base.metadata
from model import load_all_models
load_all_models()

config = context.config

# Prefer DB_URL from env over alembic.ini
db_url = os.getenv("DB_URL")
if db_url:
    config.set_main_option("sqlalchemy.url", db_url)

# Logging config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        compare_type=True,
        compare_server_default=True,
    )
    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
        )
        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()