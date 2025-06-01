"""
Risk parameters model for the SIL Predictive System.

This module defines the risk parameters model for customization per company.
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum
import uuid

from pydantic import BaseModel, Field, validator

# Configuração de logging
logger = logging.getLogger(__name__)

class MeasurementType(str, Enum):
    """Enumeração para o tipo de medição."""
    THERMOGRAPHY = "THERMOGRAPHY"
    OIL = "OIL"
    VIBRATION = "VIBRATION"
    ACOUSTIC = "ACOUSTIC"
    ELECTRICAL = "ELECTRICAL"
    OTHER = "OTHER"

class EquipmentCategory(str, Enum):
    """Enumeração para a categoria de equipamento."""
    CRITICAL = "CRITICAL"
    IMPORTANT = "IMPORTANT"
    STANDARD = "STANDARD"
    AUXILIARY = "AUXILIARY"

class ThresholdType(str, Enum):
    """Enumeração para o tipo de limite."""
    ABSOLUTE = "ABSOLUTE"
    PERCENTAGE = "PERCENTAGE"
    RATE_OF_CHANGE = "RATE_OF_CHANGE"
    STATISTICAL = "STATISTICAL"

class AlertTrigger(str, Enum):
    """Enumeração para o gatilho de alerta."""
    SINGLE_READING = "SINGLE_READING"
    CONSECUTIVE_READINGS = "CONSECUTIVE_READINGS"
    AVERAGE_READINGS = "AVERAGE_READINGS"
    TREND_ANALYSIS = "TREND_ANALYSIS"

class ThresholdDefinition(BaseModel):
    """Modelo para definição de limites."""
    type: ThresholdType
    warning_value: float
    critical_value: float
    unit: Optional[str] = None
    time_window_minutes: Optional[int] = None  # Para limites baseados em tempo
    consecutive_readings: Optional[int] = None  # Para gatilhos de leituras consecutivas
    statistical_parameters: Optional[Dict[str, Any]] = None  # Para limites estatísticos

class MeasurementThreshold(BaseModel):
    """Modelo para limites de medição."""
    measurement_type: MeasurementType
    parameter_name: str  # Ex: "temperature", "vibration_velocity", "oil_moisture"
    thresholds: ThresholdDefinition
    alert_trigger: AlertTrigger = AlertTrigger.SINGLE_READING
    enabled: bool = True
    metadata: Optional[Dict[str, Any]] = None

class EquipmentTypeRiskParameters(BaseModel):
    """Modelo para parâmetros de risco por tipo de equipamento."""
    equipment_type: str  # Ex: "MOTOR", "PUMP", "COMPRESSOR"
    category: EquipmentCategory = EquipmentCategory.STANDARD
    measurement_thresholds: List[MeasurementThreshold]
    maintenance_interval_days: Optional[int] = None
    criticality_factor: float = 1.0  # Multiplicador para ajustar a criticidade
    metadata: Optional[Dict[str, Any]] = None

class RiskParameterBase(BaseModel):
    """Modelo base para parâmetros de risco."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    client_id: str
    name: str
    description: Optional[str] = None
    equipment_type_parameters: List[EquipmentTypeRiskParameters]
    global_criticality_factor: float = 1.0  # Multiplicador global para todos os equipamentos
    is_default: bool = False
    created_by: Optional[str] = None  # ID do usuário que criou
    metadata: Optional[Dict[str, Any]] = None

    @validator('equipment_type_parameters')
    def validate_equipment_types(cls, v):
        """Valida que há pelo menos um tipo de equipamento definido."""
        if not v:
            raise ValueError("Pelo menos um tipo de equipamento deve ser definido")
        return v

class RiskParameterCreate(RiskParameterBase):
    """Modelo para criação de parâmetros de risco."""
    pass

class RiskParameterUpdate(BaseModel):
    """Modelo para atualização de parâmetros de risco."""
    name: Optional[str] = None
    description: Optional[str] = None
    equipment_type_parameters: Optional[List[EquipmentTypeRiskParameters]] = None
    global_criticality_factor: Optional[float] = None
    is_default: Optional[bool] = None
    metadata: Optional[Dict[str, Any]] = None

class RiskParameterResponse(RiskParameterBase):
    """Modelo para resposta de parâmetros de risco."""
    created_at: datetime
    updated_at: datetime
    equipment_count: int = 0  # Número de equipamentos usando este perfil

logger.info("Risk parameters models defined.")
"""
