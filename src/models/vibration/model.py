"""
Vibration measurement data models for SIL Predictive System.

This module provides data structures for representing vibration
measurement data from external systems.
"""

from datetime import datetime
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass, field
from enum import Enum

from .base import BaseMeasurement, MeasurementStatus, MeasurementSource, MeasurementThreshold


class VibrationAxis(Enum):
    """Measurement axis for vibration data."""
    X = "x"
    Y = "y"
    Z = "z"
    RADIAL = "radial"
    AXIAL = "axial"
    VERTICAL = "vertical"
    HORIZONTAL = "horizontal"
    OTHER = "other"


class VibrationUnit(Enum):
    """Units for vibration measurements."""
    ACCELERATION = "g"           # Acceleration in g
    VELOCITY = "mm/s"            # Velocity in mm/s
    DISPLACEMENT = "μm"          # Displacement in micrometers
    FREQUENCY = "Hz"             # Frequency in Hertz
    OTHER = "other"


@dataclass
class VibrationReading:
    """Represents a single vibration reading."""
    axis: VibrationAxis
    value: float
    unit: VibrationUnit
    frequency: Optional[float] = None  # Frequency in Hz
    status: MeasurementStatus = MeasurementStatus.UNKNOWN
    thresholds: Optional[MeasurementThreshold] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert reading to dictionary."""
        result = {
            "axis": self.axis.value,
            "value": self.value,
            "unit": self.unit.value,
            "status": self.status.value
        }
        
        if self.frequency is not None:
            result["frequency"] = self.frequency
            
        return result
    
    def evaluate_status(self) -> MeasurementStatus:
        """Evaluate value against thresholds and update status."""
        if self.thresholds:
            self.status = self.thresholds.evaluate(self.value)
        return self.status


@dataclass
class FrequencySpectrum:
    """Represents a frequency spectrum for vibration analysis."""
    frequencies: List[float]
    amplitudes: List[float]
    unit: VibrationUnit
    axis: VibrationAxis
    max_amplitude: Optional[float] = None
    dominant_frequency: Optional[float] = None
    
    def __post_init__(self):
        """Calculate derived values if not provided."""
        if self.max_amplitude is None and self.amplitudes:
            self.max_amplitude = max(self.amplitudes)
            
        if self.dominant_frequency is None and self.frequencies and self.amplitudes:
            max_index = self.amplitudes.index(max(self.amplitudes))
            self.dominant_frequency = self.frequencies[max_index]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert spectrum to dictionary."""
        return {
            "frequencies": self.frequencies,
            "amplitudes": self.amplitudes,
            "unit": self.unit.value,
            "axis": self.axis.value,
            "max_amplitude": self.max_amplitude,
            "dominant_frequency": self.dominant_frequency
        }


@dataclass
class VibrationMeasurement(BaseMeasurement):
    """Represents a vibration measurement session."""
    sensor_id: Optional[str] = None
    sensor_type: Optional[str] = None
    measurement_point: Optional[str] = None
    rpm: Optional[float] = None
    load: Optional[float] = None
    readings: List[VibrationReading] = field(default_factory=list)
    spectra: List[FrequencySpectrum] = field(default_factory=list)
    
    def __post_init__(self):
        """Set default source if not provided."""
        if not hasattr(self, 'source') or self.source is None:
            self.source = MeasurementSource.VIBRATION
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert measurement to dictionary."""
        result = super().to_dict()
        
        if self.sensor_id:
            result["sensor_id"] = self.sensor_id
            
        if self.sensor_type:
            result["sensor_type"] = self.sensor_type
            
        if self.measurement_point:
            result["measurement_point"] = self.measurement_point
            
        if self.rpm is not None:
            result["rpm"] = self.rpm
            
        if self.load is not None:
            result["load"] = self.load
            
        if self.readings:
            result["readings"] = [reading.to_dict() for reading in self.readings]
            
        if self.spectra:
            result["spectra"] = [spectrum.to_dict() for spectrum in self.spectra]
            
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'VibrationMeasurement':
        """Create measurement from dictionary."""
        # First create the base measurement
        measurement = super().from_dict(data)
        
        # Add vibration-specific fields
        measurement.sensor_id = data.get("sensor_id")
        measurement.sensor_type = data.get("sensor_type")
        measurement.measurement_point = data.get("measurement_point")
        measurement.rpm = data.get("rpm")
        measurement.load = data.get("load")
        
        # Process readings if present
        if "readings" in data and isinstance(data["readings"], list):
            for reading_data in data["readings"]:
                reading = VibrationReading(
                    axis=VibrationAxis(reading_data["axis"]),
                    value=reading_data["value"],
                    unit=VibrationUnit(reading_data["unit"]),
                    frequency=reading_data.get("frequency"),
                    status=MeasurementStatus(reading_data.get("status", "unknown"))
                )
                measurement.readings.append(reading)
        
        # Process spectra if present
        if "spectra" in data and isinstance(data["spectra"], list):
            for spectrum_data in data["spectra"]:
                spectrum = FrequencySpectrum(
                    frequencies=spectrum_data["frequencies"],
                    amplitudes=spectrum_data["amplitudes"],
                    unit=VibrationUnit(spectrum_data["unit"]),
                    axis=VibrationAxis(spectrum_data["axis"]),
                    max_amplitude=spectrum_data.get("max_amplitude"),
                    dominant_frequency=spectrum_data.get("dominant_frequency")
                )
                measurement.spectra.append(spectrum)
        
        return measurement
    
    def get_overall_values(self) -> Dict[str, Dict[str, float]]:
        """Get overall values by axis and unit."""
        result = {}
        
        for reading in self.readings:
            axis = reading.axis.value
            unit = reading.unit.value
            
            if axis not in result:
                result[axis] = {}
                
            if unit not in result[axis]:
                result[axis][unit] = reading.value
            else:
                # If multiple readings for same axis/unit, use the highest
                result[axis][unit] = max(result[axis][unit], reading.value)
                
        return result
    
    def evaluate_status(self) -> MeasurementStatus:
        """Evaluate all readings and determine overall status."""
        if not self.readings:
            return MeasurementStatus.UNKNOWN
        
        # Evaluate each reading
        for reading in self.readings:
            reading.evaluate_status()
        
        # Overall status is the most severe
        statuses = [reading.status for reading in self.readings]
        
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
