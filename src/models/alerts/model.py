"""
Data models for Alerts in the SIL Predictive System.
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum
import uuid

from pydantic import BaseModel, Field

from .base import MeasurementBase, MeasurementStatus, MeasurementSource

# Configuração de logging
logger = logging.getLogger(__name__)

class AlertGravity(str, Enum):
    """Enumeração para a gravidade dos alertas."""
    P1 = "P1"  # Crítico
    P2 = "P2"  # Alto
    P3 = "P3"  # Médio
    P4 = "P4"  # Baixo (Opcional, se necessário)

class AlertCriticality(str, Enum):
    """Enumeração para a criticidade dos alertas (pode ser baseada no equipamento)."""
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"

class AlertStatus(str, Enum):
    """Enumeração para o status dos alertas."""
    NEW = "NEW"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    IN_PROGRESS = "IN_PROGRESS"
    RESOLVED = "RESOLVED"
    FALSE_POSITIVE = "FALSE_POSITIVE"

class AlertBase(BaseModel):
    """Modelo base para alertas."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    equipment_id: str
    timestamp: datetime = Field(default_factory=datetime.now)
    measurement_id: Optional[str] = None  # ID da medição que gerou o alerta
    measurement_source: Optional[MeasurementSource] = None
    description: str
    gravity: AlertGravity
    criticality: AlertCriticality
    status: AlertStatus = AlertStatus.NEW
    assigned_to: Optional[str] = None  # ID do engenheiro responsável (ex: Fernando)
    resolution_details: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

class AlertCreate(AlertBase):
    """Modelo para criação de alertas."""
    pass

class AlertUpdate(BaseModel):
    """Modelo para atualização de alertas."""
    status: Optional[AlertStatus] = None
    assigned_to: Optional[str] = None
    resolution_details: Optional[str] = None
    gravity: Optional[AlertGravity] = None
    criticality: Optional[AlertCriticality] = None
    metadata: Optional[Dict[str, Any]] = None

class AlertResponse(AlertBase):
    """Modelo para resposta de alertas."""
    created_at: datetime
    updated_at: datetime

logger.info("Alert models defined.")
