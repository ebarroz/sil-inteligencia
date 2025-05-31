"""
Data models for Clients in the SIL Predictive System.
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum
import uuid

from pydantic import BaseModel, Field, EmailStr

# Configuração de logging
logger = logging.getLogger(__name__)

class ClientStatus(str, Enum):
    """Enumeração para o status dos clientes."""
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    PENDING = "PENDING"

class ClientRiskLevel(str, Enum):
    """Enumeração para o nível de risco dos clientes."""
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    CUSTOM = "CUSTOM"  # Para clientes com parâmetros de risco personalizados

class ContactType(str, Enum):
    """Enumeração para o tipo de contato."""
    PRIMARY = "PRIMARY"
    TECHNICAL = "TECHNICAL"
    BILLING = "BILLING"
    EMERGENCY = "EMERGENCY"

class NotificationPreference(str, Enum):
    """Enumeração para preferências de notificação."""
    EMAIL = "EMAIL"
    SMS = "SMS"
    BOTH = "BOTH"
    NONE = "NONE"

class ContactInfo(BaseModel):
    """Modelo para informações de contato."""
    name: str
    email: EmailStr
    phone: Optional[str] = None
    position: Optional[str] = None
    type: ContactType
    notification_preference: NotificationPreference = NotificationPreference.EMAIL

class Address(BaseModel):
    """Modelo para endereço."""
    street: str
    number: str
    complement: Optional[str] = None
    city: str
    state: str
    zip_code: str
    country: str = "Brasil"
    latitude: Optional[float] = None
    longitude: Optional[float] = None

class ClientBase(BaseModel):
    """Modelo base para clientes."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    document: str  # CNPJ ou outro documento
    status: ClientStatus = ClientStatus.ACTIVE
    risk_level: ClientRiskLevel = ClientRiskLevel.MEDIUM
    address: Address
    contacts: List[ContactInfo]
    custom_risk_parameters: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None

class ClientCreate(ClientBase):
    """Modelo para criação de clientes."""
    pass

class ClientUpdate(BaseModel):
    """Modelo para atualização de clientes."""
    name: Optional[str] = None
    document: Optional[str] = None
    status: Optional[ClientStatus] = None
    risk_level: Optional[ClientRiskLevel] = None
    address: Optional[Address] = None
    contacts: Optional[List[ContactInfo]] = None
    custom_risk_parameters: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None

class ClientResponse(ClientBase):
    """Modelo para resposta de clientes."""
    created_at: datetime
    updated_at: datetime
    equipment_count: int = 0
    active_alerts_count: int = 0

logger.info("Client models defined.")
