"""
Modelo de Perfil de Risco - SIL Predictive System
------------------------------------------------
Este módulo define o modelo de dados para perfis de risco no sistema,
implementando o Grau de Risco Personalizado (requisito #2).
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, JSON, Text
from sqlalchemy.orm import relationship

from src.config.database import Base

class RiskProfile(Base):
    """Modelo de dados para perfis de risco personalizados por cliente."""
    __tablename__ = "risk_profiles"
    
    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(String(50), ForeignKey("clients.id"), nullable=False)
    equipment_tag = Column(String(50), ForeignKey("equipment.tag"), nullable=False)
    
    # Parâmetros de risco personalizados (requisito #2)
    high_threshold = Column(Float, default=0.8)
    medium_threshold = Column(Float, default=0.5)
    low_threshold = Column(Float, default=0.3)
    
    # Configurações adicionais de risco
    parameters = Column(JSON)  # Armazena configurações específicas em formato JSON
    description = Column(Text)
    
    # Metadados
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    last_calculation = Column(DateTime)
    current_risk_level = Column(Float)
    
    # Relacionamentos
    client = relationship("Client", back_populates="risk_profiles")
    equipment = relationship("Equipment", back_populates="risk_profiles")
    
    def __repr__(self):
        return f"<RiskProfile(id={self.id}, client_id={self.client_id}, equipment_tag={self.equipment_tag})>"
