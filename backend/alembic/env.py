# backend/alembic/env.py

from logging.config import fileConfig
import sys
import os
from dotenv import load_dotenv

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

# Carregar variáveis de ambiente do arquivo .env
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '..', '.env'))

# Adicionar o diretório src ao sys.path para permitir importações corretas
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

# Importações corrigidas com os caminhos corretos
from models.database import Base
import models


config = context.config

# Substituir a URL do banco de dados se não estiver configurada
if not config.get_main_option("sqlalchemy.url"):
    config.set_main_option("sqlalchemy.url", os.getenv("DATABASE_URL"))

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Aponte o target_metadata para a Base dos seus modelos
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    # ... (o resto do arquivo pode continuar como o original)
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    # ... (o resto do arquivo pode continuar como o original)
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

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
