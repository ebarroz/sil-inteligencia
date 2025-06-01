"""
Data models for Equipment in the SIL Predictive System.

This module defines the equipment model with support for machine history.
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum
import uuid

from pydantic import BaseModel, Field

# Configuração de logging
logger = logging.getLogger(__name__)

class EquipmentStatus(str, Enum):
    """Enumeração para o status dos equipamentos."""
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    MAINTENANCE = "MAINTENANCE"
    DECOMMISSIONED = "DECOMMISSIONED"

class EquipmentType(str, Enum):
    """Enumeração para o tipo de equipamento."""
    MOTOR = "MOTOR"
    PUMP = "PUMP"
    COMPRESSOR = "COMPRESSOR"
    GENERATOR = "GENERATOR"
    TRANSFORMER = "TRANSFORMER"
    HVAC = "HVAC"
    OTHER = "OTHER"

class MaintenanceType(str, Enum):
    """Enumeração para o tipo de manutenção."""
    PREVENTIVE = "PREVENTIVE"
    CORRECTIVE = "CORRECTIVE"
    PREDICTIVE = "PREDICTIVE"
    CONDITION_BASED = "CONDITION_BASED"

class TrackingStatus(str, Enum):
    """Enumeração para o status de monitoramento do equipamento."""
    FULLY_TRACKED = "FULLY_TRACKED"  # Monitoramento completo (online e offline)
    PARTIALLY_TRACKED = "PARTIALLY_TRACKED"  # Monitoramento parcial
    MINIMALLY_TRACKED = "MINIMALLY_TRACKED"  # Monitoramento mínimo
    NOT_TRACKED = "NOT_TRACKED"  # Sem monitoramento (vulnerável)

class MaintenanceRecord(BaseModel):
    """Modelo para registro de manutenção."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = Field(default_factory=datetime.now)
    type: MaintenanceType
    description: str
    technician: str
    parts_replaced: Optional[List[str]] = None
    cost: Optional[float] = None
    downtime_hours: Optional[float] = None
    resolution: Optional[str] = None
    related_alert_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

class MeasurementRecord(BaseModel):
    """Modelo para registro de medição."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = Field(default_factory=datetime.now)
    source: str  # termografia, óleo, vibração, etc.
    values: Dict[str, Any]  # Valores medidos
    status: str  # normal, alerta, crítico
    metadata: Optional[Dict[str, Any]] = None

class EquipmentBase(BaseModel):
    """Modelo base para equipamentos."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tag: str  # RG do equipamento
    name: str
    type: EquipmentType
    model: str
    manufacturer: str
    serial_number: str
    installation_date: datetime
    status: EquipmentStatus = EquipmentStatus.ACTIVE
    location: str
    client_id: str  # ID do cliente proprietário
    tracking_status: TrackingStatus = TrackingStatus.FULLY_TRACKED
    last_maintenance_date: Optional[datetime] = None
    next_maintenance_date: Optional[datetime] = None
    maintenance_history: List[MaintenanceRecord] = []
    measurement_history: List[MeasurementRecord] = []
    metadata: Optional[Dict[str, Any]] = None

class EquipmentCreate(EquipmentBase):
    """Modelo para criação de equipamentos."""
    pass

class EquipmentUpdate(BaseModel):
    """Modelo para atualização de equipamentos."""
    name: Optional[str] = None
    type: Optional[EquipmentType] = None
    model: Optional[str] = None
    manufacturer: Optional[str] = None
    serial_number: Optional[str] = None
    status: Optional[EquipmentStatus] = None
    location: Optional[str] = None
    tracking_status: Optional[TrackingStatus] = None
    last_maintenance_date: Optional[datetime] = None
    next_maintenance_date: Optional[datetime] = None
    metadata: Optional[Dict[str, Any]] = None

class EquipmentResponse(EquipmentBase):
    """Modelo para resposta de equipamentos."""
    created_at: datetime
    updated_at: datetime
    alert_count: int = 0
    active_alert_count: int = 0

class EquipmentHistory(BaseModel):
    """Modelo para histórico completo de um equipamento."""
    equipment: EquipmentResponse
    maintenance_records: List[MaintenanceRecord]
    measurement_records: List[MeasurementRecord]
    alerts: List[Dict[str, Any]]  # Lista simplificada de alertas

logger.info("Equipment models defined.")
