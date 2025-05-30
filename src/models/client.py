"""
Modelo de Cliente - SIL Predictive System
----------------------------------------
Este módulo define o modelo de dados para clientes no sistema.
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Text, JSON
from sqlalchemy.orm import relationship

from src.config.database import Base

class Client(Base):
    """Modelo de dados para clientes."""
    __tablename__ = "clients"
    
    id = Column(String(50), primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    description = Column(Text)
    
    # Informações de contato
    email = Column(String(100))
    phone = Column(String(50))
    address = Column(String(200))
    
    # Configurações de notificação
    notification_settings = Column(JSON, default={
        "email": True,
        "sms": False,
        "priority_threshold": "P3"  # Nível mínimo de prioridade para notificações
    })
    
    # Metadados
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relacionamentos
    equipment = relationship("Equipment", back_populates="client")
    alerts = relationship("Alert", back_populates="client")
    risk_profiles = relationship("RiskProfile", back_populates="client")
    
    def __repr__(self):
        return f"<Client(id={self.id}, name={self.name})>"
