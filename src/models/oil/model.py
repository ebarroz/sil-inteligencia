"""
Oil analysis measurement data models for SIL Predictive System.

This module provides data structures for representing oil analysis
measurement data from external systems.
"""

from datetime import datetime
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass, field
from enum import Enum

from .base import BaseMeasurement, MeasurementStatus, MeasurementSource, MeasurementThreshold


class OilSampleType(Enum):
    """Type of oil sample."""
    NEW = "new"
    IN_SERVICE = "in_service"
    FILTERED = "filtered"
    DRAIN = "drain"
    OTHER = "other"


@dataclass
class OilProperty:
    """Represents a specific property measured in an oil analysis."""
    name: str
    value: float
    unit: str
    status: MeasurementStatus = MeasurementStatus.UNKNOWN
    thresholds: Optional[MeasurementThreshold] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert property to dictionary."""
        return {
            "name": self.name,
            "value": self.value,
            "unit": self.unit,
            "status": self.status.value
        }
    
    def evaluate_status(self) -> MeasurementStatus:
        """Evaluate value against thresholds and update status."""
        if self.thresholds:
            self.status = self.thresholds.evaluate(self.value)
        return self.status


@dataclass
class OilAnalysisMeasurement(BaseMeasurement):
    """Represents an oil analysis measurement."""
    sample_id: str
    sample_type: OilSampleType = OilSampleType.IN_SERVICE
    oil_type: Optional[str] = None
    oil_brand: Optional[str] = None
    hours_in_service: Optional[int] = None
    sample_date: Optional[datetime] = None
    analysis_date: Optional[datetime] = None
    laboratory: Optional[str] = None
    properties: List[OilProperty] = field(default_factory=list)
    
    def __post_init__(self):
        """Set default source if not provided."""
        if not hasattr(self, 'source') or self.source is None:
            self.source = MeasurementSource.OIL_ANALYSIS
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert measurement to dictionary."""
        result = super().to_dict()
        
        result["sample_id"] = self.sample_id
        result["sample_type"] = self.sample_type.value
        
        if self.oil_type:
            result["oil_type"] = self.oil_type
            
        if self.oil_brand:
            result["oil_brand"] = self.oil_brand
            
        if self.hours_in_service is not None:
            result["hours_in_service"] = self.hours_in_service
            
        if self.sample_date:
            result["sample_date"] = self.sample_date.isoformat()
            
        if self.analysis_date:
            result["analysis_date"] = self.analysis_date.isoformat()
            
        if self.laboratory:
            result["laboratory"] = self.laboratory
            
        if self.properties:
            result["properties"] = [prop.to_dict() for prop in self.properties]
            
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'OilAnalysisMeasurement':
        """Create measurement from dictionary."""
        # First create the base measurement
        measurement = super().from_dict(data)
        
        # Convert string values to enums
        sample_type = OilSampleType(data.get("sample_type", "in_service"))
        
        # Convert ISO format strings to datetime objects
        sample_date = None
        if "sample_date" in data:
            sample_date = datetime.fromisoformat(data["sample_date"].replace("Z", "+00:00"))
            
        analysis_date = None
        if "analysis_date" in data:
            analysis_date = datetime.fromisoformat(data["analysis_date"].replace("Z", "+00:00"))
        
        # Add oil analysis-specific fields
        measurement.sample_id = data["sample_id"]
        measurement.sample_type = sample_type
        measurement.oil_type = data.get("oil_type")
        measurement.oil_brand = data.get("oil_brand")
        measurement.hours_in_service = data.get("hours_in_service")
        measurement.sample_date = sample_date
        measurement.analysis_date = analysis_date
        measurement.laboratory = data.get("laboratory")
        
        # Process properties if present
        if "properties" in data and isinstance(data["properties"], list):
            for prop_data in data["properties"]:
                prop = OilProperty(
                    name=prop_data["name"],
                    value=prop_data["value"],
                    unit=prop_data["unit"],
                    status=MeasurementStatus(prop_data.get("status", "unknown"))
                )
                measurement.properties.append(prop)
        
        return measurement
    
    def get_property(self, name: str) -> Optional[OilProperty]:
        """Get a specific property by name."""
        for prop in self.properties:
            if prop.name.lower() == name.lower():
                return prop
        return None
    
    def evaluate_status(self) -> MeasurementStatus:
        """Evaluate all properties and determine overall status."""
        if not self.properties:
            return MeasurementStatus.UNKNOWN
        
        # Evaluate each property
        for prop in self.properties:
            prop.evaluate_status()
        
        # Overall status is the most severe
        statuses = [prop.status for prop in self.properties]
        
        if MeasurementStatus.CRITICAL in statuses:
            return MeasurementStatus.CRITICAL
        elif MeasurementStatus.ALERT in statuses:
            return MeasurementStatus.ALERT
        elif MeasurementStatus.WARNING in statuses:
            return MeasurementStatus.WARNING
        elif MeasurementStatus.NORMAL in statuses:
            return MeasurementStatus.NORMAL
        else:
            return MeasurementStatus.UNKNOWN
