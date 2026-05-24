import os
from logging.config import file_config
from sqlalchemy import engine_from_config
from sqlalchemy import pool
from alembic import context
from app.infrastructure.storage.postgres.models import Base

config = context.config

# Interpret the config file for Python logging.
if config.config_file_name is not None:
    file_config(config.config_file_name)

target_metadata = Base.metadata

def run_migrations_offline() -> None:
    url = os.getenv("DATABASE_URL", config.get_main_option("sqlalchemy.url"))
    # Convert asyncpg to psycopg2 for sync alembic
    url = url.replace("asyncpg", "psycopg2")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online() -> None:
    # Use sync driver for alembic migrations
    url = os.getenv("DATABASE_URL")
    if not url:
         url = config.get_main_option("sqlalchemy.url")
    
    sync_url = url.replace("asyncpg", "psycopg2")
    
    print(f"Running migrations on: {sync_url}")
    
    from sqlalchemy import create_engine
    connectable = create_engine(sync_url)

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

