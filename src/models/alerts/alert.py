"""
Modelo de Alerta - SIL Predictive System
----------------------------------------
Este módulo define o modelo de dados para alertas no sistema.
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Enum, Boolean, Text
from sqlalchemy.orm import relationship
import enum

from src.config.database import Base

class AlertSeverity(enum.Enum):
    """Classificação de gravidade dos alertas (requisito #13)."""
    P1 = "crítico"    # Crítico
    P2 = "alto"       # Alto
    P3 = "médio"      # Médio
    P4 = "baixo"      # Baixo (não mencionado no requisito, mas incluído para completude)


class AlertStatus(enum.Enum):
    """Status possíveis de um alerta."""
    NEW = "novo"
    VALIDATING = "validando"
    VALIDATED = "validado"
    FALSE_POSITIVE = "falso_positivo"
    RESOLVED = "resolvido"
    CLOSED = "fechado"


class Alert(Base):
    """Modelo de dados para alertas."""
    __tablename__ = "alerts"
    
    id = Column(Integer, primary_key=True, index=True)
    equipment_tag = Column(String(50), ForeignKey("equipment.tag"), nullable=False)
    client_id = Column(String(50), ForeignKey("clients.id"), nullable=False)
    
    # Informações do alerta
    title = Column(String(200), nullable=False)
    description = Column(Text)
    severity = Column(Enum(AlertSeverity), nullable=False)
    status = Column(Enum(AlertStatus), default=AlertStatus.NEW, nullable=False)
    
    # Dados de medição que geraram o alerta
    measurement_type = Column(String(50))  # vibração, temperatura, óleo, etc.
    measurement_value = Column(Float)
    measurement_unit = Column(String(20))
    threshold_value = Column(Float)
    
    # Metadados
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    validated_at = Column(DateTime)
    validated_by = Column(String(100))
    
    # Análise de causa raiz (requisito #5)
    root_cause = Column(Text)
    ai_analysis = Column(Text)
    is_false_positive = Column(Boolean, default=False)
    
    # Relacionamentos
    equipment = relationship("Equipment", back_populates="alerts")
    client = relationship("Client", back_populates="alerts")
    
    def __repr__(self):
        return f"<Alert(id={self.id}, equipment_tag={self.equipment_tag}, severity={self.severity})>"
