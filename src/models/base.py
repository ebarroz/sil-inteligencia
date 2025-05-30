"""
Base data models for SIL Predictive System measurements.

This module provides base classes and data structures for representing
measurement data from various sources (thermography, oil analysis, vibration).
"""

from datetime import datetime
from typing import Dict, Any, List, Optional, Union
from enum import Enum
from dataclasses import dataclass, field


class MeasurementStatus(Enum):
    """Status of a measurement."""
    NORMAL = "normal"
    WARNING = "warning"
    ALERT = "alert"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


class MeasurementSource(Enum):
    """Source of measurement data."""
    THERMOGRAPHY = "thermography"
    OIL_ANALYSIS = "oil_analysis"
    VIBRATION = "vibration"
    MANUAL = "manual"
    AUTOMATED = "automated"
    OTHER = "other"


@dataclass
class Equipment:
    """Represents equipment being monitored."""
    id: str
    name: str
    type: str
    location: str
    manufacturer: Optional[str] = None
    model: Optional[str] = None
    serial_number: Optional[str] = None
    installation_date: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class BaseMeasurement:
    """Base class for all measurement types."""
    id: str
    equipment_id: str
    timestamp: datetime
    source: MeasurementSource
    status: MeasurementStatus = MeasurementStatus.UNKNOWN
    notes: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert measurement to dictionary."""
        result = {
            "id": self.id,
            "equipment_id": self.equipment_id,
            "timestamp": self.timestamp.isoformat(),
            "source": self.source.value,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
        
        if self.notes:
            result["notes"] = self.notes
            
        if self.metadata:
            result["metadata"] = self.metadata
            
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BaseMeasurement':
        """Create measurement from dictionary."""
        # Convert string values to enums
        source = MeasurementSource(data.get("source", "other"))
        status = MeasurementStatus(data.get("status", "unknown"))
        
        # Convert ISO format strings to datetime objects
        timestamp = datetime.fromisoformat(data["timestamp"].replace("Z", "+00:00"))
        created_at = datetime.fromisoformat(data.get("created_at", datetime.utcnow().isoformat()).replace("Z", "+00:00"))
        updated_at = datetime.fromisoformat(data.get("updated_at", datetime.utcnow().isoformat()).replace("Z", "+00:00"))
        
        return cls(
            id=data["id"],
            equipment_id=data["equipment_id"],
            timestamp=timestamp,
            source=source,
            status=status,
            notes=data.get("notes"),
            created_at=created_at,
            updated_at=updated_at,
            metadata=data.get("metadata", {})
        )


@dataclass
class MeasurementThreshold:
    """Threshold values for measurement alerts."""
    warning_low: Optional[float] = None
    warning_high: Optional[float] = None
    alert_low: Optional[float] = None
    alert_high: Optional[float] = None
    critical_low: Optional[float] = None
    critical_high: Optional[float] = None
    
    def evaluate(self, value: float) -> MeasurementStatus:
        """Evaluate a value against thresholds and return appropriate status."""
        if self.critical_low is not None and value <= self.critical_low:
            return MeasurementStatus.CRITICAL
        if self.critical_high is not None and value >= self.critical_high:
            return MeasurementStatus.CRITICAL
        
        if self.alert_low is not None and value <= self.alert_low:
            return MeasurementStatus.ALERT
        if self.alert_high is not None and value >= self.alert_high:
            return MeasurementStatus.ALERT
        
        if self.warning_low is not None and value <= self.warning_low:
            return MeasurementStatus.WARNING
        if self.warning_high is not None and value >= self.warning_high:
            return MeasurementStatus.WARNING
        
        return MeasurementStatus.NORMAL
