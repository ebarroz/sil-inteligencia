"""
Thermography measurement data models for SIL Predictive System.

This module provides data structures for representing thermography
measurement data from external systems.
"""

from datetime import datetime
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass, field

from .base import BaseMeasurement, MeasurementStatus, MeasurementSource, MeasurementThreshold


@dataclass
class ThermographyPoint:
    """Represents a specific measurement point in a thermographic image."""
    id: str
    name: str
    x: float  # X coordinate in the image
    y: float  # Y coordinate in the image
    temperature: float  # Temperature in Celsius
    emissivity: Optional[float] = None
    reference_temperature: Optional[float] = None
    status: MeasurementStatus = MeasurementStatus.UNKNOWN
    thresholds: Optional[MeasurementThreshold] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert point to dictionary."""
        result = {
            "id": self.id,
            "name": self.name,
            "x": self.x,
            "y": self.y,
            "temperature": self.temperature,
            "status": self.status.value,
        }
        
        if self.emissivity is not None:
            result["emissivity"] = self.emissivity
            
        if self.reference_temperature is not None:
            result["reference_temperature"] = self.reference_temperature
            
        return result
    
    def evaluate_status(self) -> MeasurementStatus:
        """Evaluate temperature against thresholds and update status."""
        if self.thresholds:
            self.status = self.thresholds.evaluate(self.temperature)
        return self.status


@dataclass
class ThermographyMeasurement(BaseMeasurement):
    """Represents a thermography measurement session."""
    image_url: Optional[str] = None
    image_path: Optional[str] = None
    ambient_temperature: Optional[float] = None
    humidity: Optional[float] = None
    distance: Optional[float] = None
    camera_model: Optional[str] = None
    points: List[ThermographyPoint] = field(default_factory=list)
    
    def __post_init__(self):
        """Set default source if not provided."""
        if not hasattr(self, 'source') or self.source is None:
            self.source = MeasurementSource.THERMOGRAPHY
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert measurement to dictionary."""
        result = super().to_dict()
        
        if self.image_url:
            result["image_url"] = self.image_url
            
        if self.image_path:
            result["image_path"] = self.image_path
            
        if self.ambient_temperature is not None:
            result["ambient_temperature"] = self.ambient_temperature
            
        if self.humidity is not None:
            result["humidity"] = self.humidity
            
        if self.distance is not None:
            result["distance"] = self.distance
            
        if self.camera_model:
            result["camera_model"] = self.camera_model
            
        if self.points:
            result["points"] = [point.to_dict() for point in self.points]
            
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ThermographyMeasurement':
        """Create measurement from dictionary."""
        # First create the base measurement
        measurement = super().from_dict(data)
        
        # Add thermography-specific fields
        measurement.image_url = data.get("image_url")
        measurement.image_path = data.get("image_path")
        measurement.ambient_temperature = data.get("ambient_temperature")
        measurement.humidity = data.get("humidity")
        measurement.distance = data.get("distance")
        measurement.camera_model = data.get("camera_model")
        
        # Process points if present
        if "points" in data and isinstance(data["points"], list):
            for point_data in data["points"]:
                point = ThermographyPoint(
                    id=point_data["id"],
                    name=point_data["name"],
                    x=point_data["x"],
                    y=point_data["y"],
                    temperature=point_data["temperature"],
                    emissivity=point_data.get("emissivity"),
                    reference_temperature=point_data.get("reference_temperature"),
                    status=MeasurementStatus(point_data.get("status", "unknown"))
                )
                measurement.points.append(point)
        
        return measurement
    
    def get_max_temperature(self) -> Optional[float]:
        """Get the maximum temperature from all points."""
        if not self.points:
            return None
        return max(point.temperature for point in self.points)
    
    def get_min_temperature(self) -> Optional[float]:
        """Get the minimum temperature from all points."""
        if not self.points:
            return None
        return min(point.temperature for point in self.points)
    
    def get_avg_temperature(self) -> Optional[float]:
        """Get the average temperature from all points."""
        if not self.points:
            return None
        return sum(point.temperature for point in self.points) / len(self.points)
    
    def evaluate_status(self) -> MeasurementStatus:
        """Evaluate all points and determine overall status."""
        if not self.points:
            return MeasurementStatus.UNKNOWN
        
        # Evaluate each point
        for point in self.points:
            point.evaluate_status()
        
        # Overall status is the most severe
        statuses = [point.status for point in self.points]
        
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
