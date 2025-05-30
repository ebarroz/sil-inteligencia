"""
Configuração de Banco de Dados - SIL Predictive System
-----------------------------------------------------
Este módulo define as configurações de conexão com o banco de dados
e fornece funções de utilidade para operações de banco de dados.
"""

import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Configurações do banco de dados
DB_USER = os.environ.get('DB_USER', 'sil_user')
DB_PASSWORD = os.environ.get('DB_PASSWORD', 'sil_password')
DB_HOST = os.environ.get('DB_HOST', 'localhost')
DB_PORT = os.environ.get('DB_PORT', '5432')
DB_NAME = os.environ.get('DB_NAME', 'sil_predictive')

# String de conexão
DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# Criação do engine SQLAlchemy
engine = create_engine(DATABASE_URL)

# Sessão para operações no banco
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base para modelos declarativos
Base = declarative_base()

def get_db():
    """Fornece uma sessão de banco de dados para operações."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
