"""
Modelo de Equipamento - SIL Predictive System
--------------------------------------------
Este módulo define o modelo de dados para equipamentos no sistema,
implementando o sistema de TAG como "RG" do Equipamento (requisito #6).
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Enum, Boolean, Text
from sqlalchemy.orm import relationship
import enum

from src.config.database import Base

class EquipmentType(enum.Enum):
    """Tipos de equipamentos suportados pelo sistema."""
    MOTOR = "motor"
    PUMP = "bomba"
    COMPRESSOR = "compressor"
    TURBINE = "turbina"
    FAN = "ventilador"
    GEARBOX = "redutor"
    OTHER = "outro"

class EquipmentStatus(enum.Enum):
    """Status possíveis de um equipamento."""
    OPERATIONAL = "operacional"
    MAINTENANCE = "em_manutenção"
    FAILURE = "falha"
    INACTIVE = "inativo"
    VULNERABLE = "vulnerável"  # Para equipamentos marcados como vulneráveis (requisito #12)

class Equipment(Base):
    """Modelo de dados para equipamentos."""
    __tablename__ = "equipment"
    
    # TAG como identificador único (requisito #6)
    tag = Column(String(50), primary_key=True, index=True)
    client_id = Column(String(50), ForeignKey("clients.id"), nullable=False)
    
    # Informações do equipamento
    name = Column(String(200), nullable=False)
    description = Column(Text)
    type = Column(Enum(EquipmentType), nullable=False)
    model = Column(String(100))
    manufacturer = Column(String(100))
    status = Column(Enum(EquipmentStatus), default=EquipmentStatus.OPERATIONAL, nullable=False)
    
    # Localização
    location = Column(String(200))
    latitude = Column(Float)
    longitude = Column(Float)
    
    # Metadados
    installation_date = Column(DateTime)
    last_maintenance = Column(DateTime)
    next_maintenance = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Vulnerabilidades (requisito #12)
    is_vulnerable = Column(Boolean, default=False)
    vulnerability_reason = Column(Text)
    monitoring_level = Column(String(50))  # online, offline, nenhum
    
    # Relacionamentos
    client = relationship("Client", back_populates="equipment")
    alerts = relationship("Alert", back_populates="equipment")
    risk_profiles = relationship("RiskProfile", back_populates="equipment")
    
    def __repr__(self):
        return f"<Equipment(tag={self.tag}, name={self.name}, status={self.status})>"
