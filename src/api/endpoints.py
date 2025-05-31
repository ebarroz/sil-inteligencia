"""
Endpoints REST para o SIL Predictive System.

Este módulo implementa os endpoints REST para acesso aos dados de medições
de termografia, óleo e vibração.
"""

import logging
from typing import List, Optional, Dict, Any, Union
from datetime import datetime, timedelta
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Path
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from ..config.database import DatabaseManager, MeasurementRepository
from ..models.base import MeasurementBase, MeasurementStatus, MeasurementSource
from ..models.thermography.model import ThermographyMeasurement, ThermographyPoint
from ..models.oil.model import OilAnalysisMeasurement, OilProperty, OilSampleType
from ..models.vibration.model import VibrationMeasurement, VibrationReading, FrequencySpectrum, VibrationAxis, VibrationUnit

# Configuração de logging
logger = logging.getLogger(__name__)

# Criar router
router = APIRouter(prefix="/api/v1", tags=["measurements"])

# Modelos Pydantic para API

class EquipmentBase(BaseModel):
    """Modelo base para equipamentos."""
    id: str
    name: str
    type: str
    location: Optional[str] = None
    manufacturer: Optional[str] = None
    model: Optional[str] = None
    serial_number: Optional[str] = None
    installation_date: Optional[datetime] = None
    last_maintenance: Optional[datetime] = None
    status: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

class EquipmentCreate(EquipmentBase):
    """Modelo para criação de equipamentos."""
    pass

class EquipmentResponse(EquipmentBase):
    """Modelo para resposta de equipamentos."""
    created_at: datetime
    updated_at: datetime

class MeasurementResponse(BaseModel):
    """Modelo base para resposta de medições."""
    id: str
    equipment_id: str
    timestamp: datetime
    source: str
    status: str
    metadata: Optional[Dict[str, Any]] = None

class ThermographyPointModel(BaseModel):
    """Modelo para pontos de termografia."""
    id: str
    name: str
    x: float
    y: float
    temperature: float
    emissivity: float
    status: Optional[str] = None
    thresholds: Optional[Dict[str, float]] = None
    metadata: Optional[Dict[str, Any]] = None

class ThermographyMeasurementResponse(MeasurementResponse):
    """Modelo para resposta de medições de termografia."""
    image_url: str
    ambient_temperature: float
    humidity: float
    camera_model: Optional[str] = None
    distance: Optional[float] = None
    points: List[ThermographyPointModel]

class OilPropertyModel(BaseModel):
    """Modelo para propriedades de óleo."""
    name: str
    value: float
    unit: str
    status: Optional[str] = None
    thresholds: Optional[Dict[str, float]] = None
    metadata: Optional[Dict[str, Any]] = None

class OilMeasurementResponse(MeasurementResponse):
    """Modelo para resposta de análises de óleo."""
    sample_id: str
    sample_type: Optional[str] = None
    oil_type: str
    oil_brand: Optional[str] = None
    hours_in_service: Optional[int] = None
    sample_date: Optional[datetime] = None
    analysis_date: Optional[datetime] = None
    laboratory: Optional[str] = None
    properties: List[OilPropertyModel]

class VibrationReadingModel(BaseModel):
    """Modelo para leituras de vibração."""
    axis: Optional[str] = None
    value: float
    unit: Optional[str] = None
    frequency: Optional[float] = None
    status: Optional[str] = None
    thresholds: Optional[Dict[str, float]] = None
    metadata: Optional[Dict[str, Any]] = None

class FrequencySpectrumModel(BaseModel):
    """Modelo para espectros de frequência."""
    axis: Optional[str] = None
    unit: Optional[str] = None
    frequencies: List[float]
    amplitudes: List[float]
    metadata: Optional[Dict[str, Any]] = None

class VibrationMeasurementResponse(MeasurementResponse):
    """Modelo para resposta de medições de vibração."""
    sensor_id: Optional[str] = None
    sensor_type: Optional[str] = None
    measurement_point: Optional[str] = None
    rpm: Optional[float] = None
    load: Optional[float] = None
    readings: List[VibrationReadingModel]
    spectra: List[FrequencySpectrumModel]

class ThermographyMeasurementCreate(BaseModel):
    """Modelo para criação de medições de termografia."""
    equipment_id: str
    timestamp: datetime = Field(default_factory=datetime.now)
    source: str = "thermography"
    status: str = "normal"
    metadata: Optional[Dict[str, Any]] = None
    image_url: str
    ambient_temperature: float
    humidity: float
    camera_model: Optional[str] = None
    distance: Optional[float] = None
    points: List[ThermographyPointModel]

class OilMeasurementCreate(BaseModel):
    """Modelo para criação de análises de óleo."""
    equipment_id: str
    timestamp: datetime = Field(default_factory=datetime.now)
    source: str = "oil_analysis"
    status: str = "normal"
    metadata: Optional[Dict[str, Any]] = None
    sample_id: str
    sample_type: Optional[str] = None
    oil_type: str
    oil_brand: Optional[str] = None
    hours_in_service: Optional[int] = None
    sample_date: Optional[datetime] = None
    analysis_date: Optional[datetime] = None
    laboratory: Optional[str] = None
    properties: List[OilPropertyModel]

class VibrationMeasurementCreate(BaseModel):
    """Modelo para criação de medições de vibração."""
    equipment_id: str
    timestamp: datetime = Field(default_factory=datetime.now)
    source: str = "vibration"
    status: str = "normal"
    metadata: Optional[Dict[str, Any]] = None
    sensor_id: Optional[str] = None
    sensor_type: Optional[str] = None
    measurement_point: Optional[str] = None
    rpm: Optional[float] = None
    load: Optional[float] = None
    readings: List[VibrationReadingModel]
    spectra: List[FrequencySpectrumModel] = []

class PaginatedResponse(BaseModel):
    """Modelo para resposta paginada."""
    items: List[Any]
    total: int
    page: int
    page_size: int
    pages: int

class ErrorResponse(BaseModel):
    """Modelo para resposta de erro."""
    detail: str

# Dependências

def get_repository():
    """
    Dependência para obter o repositório de medições.
    
    Returns:
        MeasurementRepository: Repositório de medições
    """
    db_manager = DatabaseManager()
    return MeasurementRepository(db_manager)

# Endpoints para equipamentos

@router.post("/equipment", response_model=EquipmentResponse, status_code=201, responses={400: {"model": ErrorResponse}})
def create_equipment(equipment: EquipmentCreate, repository: MeasurementRepository = Depends(get_repository)):
    """
    Cria um novo equipamento.
    
    Args:
        equipment: Dados do equipamento
        repository: Repositório de medições
        
    Returns:
        Equipamento criado
    """
    try:
        success = repository.save_equipment(
            equipment_id=equipment.id,
            name=equipment.name,
            equipment_type=equipment.type,
            location=equipment.location,
            manufacturer=equipment.manufacturer,
            model=equipment.model,
            serial_number=equipment.serial_number,
            installation_date=equipment.installation_date,
            last_maintenance=equipment.last_maintenance,
            status=equipment.status,
            metadata=equipment.metadata
        )
        
        if not success:
            raise HTTPException(status_code=400, detail="Falha ao criar equipamento")
        
        # Obter equipamento criado
        result = repository.get_equipment_by_id(equipment.id)
        
        if not result:
            raise HTTPException(status_code=404, detail="Equipamento não encontrado após criação")
        
        return result
    except Exception as e:
        logger.error(f"Erro ao criar equipamento: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/equipment", response_model=PaginatedResponse, responses={400: {"model": ErrorResponse}})
def get_equipment_list(
    type: Optional[str] = None,
    status: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    repository: MeasurementRepository = Depends(get_repository)
):
    """
    Obtém lista de equipamentos.
    
    Args:
        type: Tipo de equipamento (opcional)
        status: Status do equipamento (opcional)
        page: Número da página
        page_size: Tamanho da página
        repository: Repositório de medições
        
    Returns:
        Lista paginada de equipamentos
    """
    try:
        offset = (page - 1) * page_size
        
        # Obter equipamentos
        items = repository.get_equipment_list(
            equipment_type=type,
            status=status,
            limit=page_size,
            offset=offset
        )
        
        # Obter contagem total
        total = len(items)  # Simplificação - em produção, usar uma consulta COUNT
        
        # Calcular número de páginas
        pages = (total + page_size - 1) // page_size
        
        return {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
            "pages": pages
        }
    except Exception as e:
        logger.error(f"Erro ao obter lista de equipamentos: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/equipment/{equipment_id}", response_model=EquipmentResponse, responses={404: {"model": ErrorResponse}})
def get_equipment(
    equipment_id: str = Path(..., description="ID do equipamento"),
    repository: MeasurementRepository = Depends(get_repository)
):
    """
    Obtém um equipamento pelo ID.
    
    Args:
        equipment_id: ID do equipamento
        repository: Repositório de medições
        
    Returns:
        Equipamento
    """
    try:
        result = repository.get_equipment_by_id(equipment_id)
        
        if not result:
            raise HTTPException(status_code=404, detail="Equipamento não encontrado")
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao obter equipamento {equipment_id}: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@router.put("/equipment/{equipment_id}", response_model=EquipmentResponse, responses={404: {"model": ErrorResponse}})
def update_equipment(
    equipment: EquipmentCreate,
    equipment_id: str = Path(..., description="ID do equipamento"),
    repository: MeasurementRepository = Depends(get_repository)
):
    """
    Atualiza um equipamento.
    
    Args:
        equipment: Dados do equipamento
        equipment_id: ID do equipamento
        repository: Repositório de medições
        
    Returns:
        Equipamento atualizado
    """
    try:
        # Verificar se equipamento existe
        existing = repository.get_equipment_by_id(equipment_id)
        
        if not existing:
            raise HTTPException(status_code=404, detail="Equipamento não encontrado")
        
        # Atualizar equipamento
        success = repository.save_equipment(
            equipment_id=equipment_id,
            name=equipment.name,
            equipment_type=equipment.type,
            location=equipment.location,
            manufacturer=equipment.manufacturer,
            model=equipment.model,
            serial_number=equipment.serial_number,
            installation_date=equipment.installation_date,
            last_maintenance=equipment.last_maintenance,
            status=equipment.status,
            metadata=equipment.metadata
        )
        
        if not success:
            raise HTTPException(status_code=400, detail="Falha ao atualizar equipamento")
        
        # Obter equipamento atualizado
        result = repository.get_equipment_by_id(equipment_id)
        
        if not result:
            raise HTTPException(status_code=404, detail="Equipamento não encontrado após atualização")
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao atualizar equipamento {equipment_id}: {e}")
        raise HTTPException(status_code=400, detail=str(e))

# Endpoints para medições

@router.get("/measurements", response_model=PaginatedResponse, responses={400: {"model": ErrorResponse}})
def get_measurements(
    equipment_id: Optional[str] = None,
    source: Optional[str] = None,
    status: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    repository: MeasurementRepository = Depends(get_repository)
):
    """
    Obtém lista de medições.
    
    Args:
        equipment_id: ID do equipamento (opcional)
        source: Fonte da medição (opcional)
        status: Status da medição (opcional)
        start_date: Data de início (opcional)
        end_date: Data de fim (opcional)
        page: Número da página
        page_size: Tamanho da página
        repository: Repositório de medições
        
    Returns:
        Lista paginada de medições
    """
    try:
        offset = (page - 1) * page_size
        
        # Obter medições
        items = repository.get_measurements(
            equipment_id=equipment_id,
            source=source,
            status=status,
            start_date=start_date,
            end_date=end_date,
            limit=page_size,
            offset=offset
        )
        
        # Obter contagem total
        total = repository.get_measurement_count(
            equipment_id=equipment_id,
            source=source,
            status=status,
            start_date=start_date,
            end_date=end_date
        )
        
        # Calcular número de páginas
        pages = (total + page_size - 1) // page_size
        
        return {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
            "pages": pages
        }
    except Exception as e:
        logger.error(f"Erro ao obter lista de medições: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/measurements/{measurement_id}", responses={404: {"model": ErrorResponse}})
def get_measurement(
    measurement_id: str = Path(..., description="ID da medição"),
    repository: MeasurementRepository = Depends(get_repository)
):
    """
    Obtém uma medição pelo ID.
    
    Args:
        measurement_id: ID da medição
        repository: Repositório de medições
        
    Returns:
        Medição com detalhes específicos do tipo
    """
    try:
        # Obter informações básicas da medição
        basic_info = repository.get_measurement_by_id(measurement_id)
        
        if not basic_info:
            raise HTTPException(status_code=404, detail="Medição não encontrada")
        
        # Obter detalhes específicos com base no tipo
        source = basic_info["source"]
        
        if source == MeasurementSource.THERMOGRAPHY.value:
            measurement = repository.get_thermography_measurement(measurement_id)
            if not measurement:
                raise HTTPException(status_code=404, detail="Detalhes da medição de termografia não encontrados")
            
            # Converter para modelo de resposta
            points = []
            for point in measurement.points:
                points.append({
                    "id": point.id,
                    "name": point.name,
                    "x": point.x,
                    "y": point.y,
                    "temperature": point.temperature,
                    "emissivity": point.emissivity,
                    "status": point.status.value if point.status else None,
                    "thresholds": point.thresholds.to_dict() if point.thresholds else None,
                    "metadata": point.metadata
                })
            
            return {
                "id": measurement.id,
                "equipment_id": measurement.equipment_id,
                "timestamp": measurement.timestamp,
                "source": measurement.source.value,
                "status": measurement.status.value,
                "metadata": measurement.metadata,
                "image_url": measurement.image_url,
                "ambient_temperature": measurement.ambient_temperature,
                "humidity": measurement.humidity,
                "camera_model": measurement.camera_model,
                "distance": measurement.distance,
                "points": points
            }
            
        elif source == MeasurementSource.OIL_ANALYSIS.value:
            measurement = repository.get_oil_measurement(measurement_id)
            if not measurement:
                raise HTTPException(status_code=404, detail="Detalhes da análise de óleo não encontrados")
            
            # Converter para modelo de resposta
            properties = []
            for prop in measurement.properties:
                properties.append({
                    "name": prop.name,
                    "value": prop.value,
                    "unit": prop.unit,
                    "status": prop.status.value if prop.status else None,
                    "thresholds": prop.thresholds.to_dict() if prop.thresholds else None,
                    "metadata": prop.metadata
                })
            
            return {
                "id": measurement.id,
                "equipment_id": measurement.equipment_id,
                "timestamp": measurement.timestamp,
                "source": measurement.source.value,
                "status": measurement.status.value,
                "metadata": measurement.metadata,
                "sample_id": measurement.sample_id,
                "sample_type": measurement.sample_type.value if measurement.sample_type else None,
                "oil_type": measurement.oil_type,
                "oil_brand": measurement.oil_brand,
                "hours_in_service": measurement.hours_in_service,
                "sample_date": measurement.sample_date,
                "analysis_date": measurement.analysis_date,
                "laboratory": measurement.laboratory,
                "properties": properties
            }
            
        elif source == MeasurementSource.VIBRATION.value:
            measurement = repository.get_vibration_measurement(measurement_id)
            if not measurement:
                raise HTTPException(status_code=404, detail="Detalhes da medição de vibração não encontrados")
            
            # Converter para modelo de resposta
            readings = []
            for reading in measurement.readings:
                readings.append({
                    "axis": reading.axis.value if reading.axis else None,
                    "value": reading.value,
                    "unit": reading.unit.value if reading.unit else None,
                    "frequency": reading.frequency,
                    "status": reading.status.value if reading.status else None,
                    "thresholds": reading.thresholds.to_dict() if reading.thresholds else None,
                    "metadata": reading.metadata
                })
            
            spectra = []
            for spectrum in measurement.spectra:
                spectra.append({
                    "axis": spectrum.axis.value if spectrum.axis else None,
                    "unit": spectrum.unit.value if spectrum.unit else None,
                    "frequencies": spectrum.frequencies,
                    "amplitudes": spectrum.amplitudes,
                    "metadata": spectrum.metadata
                })
            
            return {
                "id": measurement.id,
                "equipment_id": measurement.equipment_id,
                "timestamp": measurement.timestamp,
                "source": measurement.source.value,
                "status": measurement.status.value,
                "metadata": measurement.metadata,
                "sensor_id": measurement.sensor_id,
                "sensor_type": measurement.sensor_type,
                "measurement_point": measurement.measurement_point,
                "rpm": measurement.rpm,
                "load": measurement.load,
                "readings": readings,
                "spectra": spectra
            }
            
        else:
            # Tipo desconhecido, retornar informações básicas
            return basic_info
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao obter medição {measurement_id}: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/measurements/{measurement_id}", status_code=204, responses={404: {"model": ErrorResponse}})
def delete_measurement(
    measurement_id: str = Path(..., description="ID da medição"),
    repository: MeasurementRepository = Depends(get_repository)
):
    """
    Exclui uma medição.
    
    Args:
        measurement_id: ID da medição
        repository: Repositório de medições
    """
    try:
        # Verificar se medição existe
        existing = repository.get_measurement_by_id(measurement_id)
        
        if not existing:
            raise HTTPException(status_code=404, detail="Medição não encontrada")
        
        # Excluir medição
        success = repository.delete_measurement(measurement_id)
        
        if not success:
            raise HTTPException(status_code=400, detail="Falha ao excluir medição")
        
        return JSONResponse(status_code=204, content={})
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao excluir medição {measurement_id}: {e}")
        raise HTTPException(status_code=400, detail=str(e))

# Endpoints para medições de termografia

@router.post("/thermography", response_model=ThermographyMeasurementResponse, status_code=201, responses={400: {"model": ErrorResponse}})
def create_thermography_measurement(
    measurement: ThermographyMeasurementCreate,
    repository: MeasurementRepository = Depends(get_repository)
):
    """
    Cria uma nova medição de termografia.
    
    Args:
        measurement: Dados da medição
        repository: Repositório de medições
        
    Returns:
        Medição criada
    """
    try:
        # Criar objeto de medição
        thermo_measurement = ThermographyMeasurement(
            id=str(uuid.uuid4()),
            equipment_id=measurement.equipment_id,
            timestamp=measurement.timestamp,
            source=MeasurementSource.THERMOGRAPHY,
            status=MeasurementStatus(measurement.status),
            image_url=measurement.image_url,
            ambient_temperature=measurement.ambient_temperature,
            humidity=measurement.humidity,
            camera_model=measurement.camera_model,
            distance=measurement.distance,
            metadata=measurement.metadata
        )
        
        # Adicionar pontos
        for point_data in measurement.points:
            point = ThermographyPoint(
                id=point_data.id or str(uuid.uuid4()),
                name=point_data.name,
                x=point_data.x,
                y=point_data.y,
                temperature=point_data.temperature,
                emissivity=point_data.emissivity,
                status=MeasurementStatus(point_data.status) if point_data.status else None,
                thresholds=None,  # Será definido abaixo
                metadata=point_data.metadata
            )
            
            # Definir thresholds
            if point_data.thresholds:
                from ..models.base import MeasurementThreshold
                point.thresholds = MeasurementThreshold.from_dict(point_data.thresholds)
            
            thermo_measurement.points.append(point)
        
        # Salvar medição
        success = repository.save_thermography_measurement(thermo_measurement)
        
        if not success:
            raise HTTPException(status_code=400, detail="Falha ao criar medição de termografia")
        
        # Obter medição criada
        result = repository.get_thermography_measurement(thermo_measurement.id)
        
        if not result:
            raise HTTPException(status_code=404, detail="Medição não encontrada após criação")
        
        # Converter para modelo de resposta
        points = []
        for point in result.points:
            points.append({
                "id": point.id,
                "name": point.name,
                "x": point.x,
                "y": point.y,
                "temperature": point.temperature,
                "emissivity": point.emissivity,
                "status": point.status.value if point.status else None,
                "thresholds": point.thresholds.to_dict() if point.thresholds else None,
                "metadata": point.metadata
            })
        
        return {
            "id": result.id,
            "equipment_id": result.equipment_id,
            "timestamp": result.timestamp,
            "source": result.source.value,
            "status": result.status.value,
            "metadata": result.metadata,
            "image_url": result.image_url,
            "ambient_temperature": result.ambient_temperature,
            "humidity": result.humidity,
            "camera_model": result.camera_model,
            "distance": result.distance,
            "points": points
        }
    except Exception as e:
        logger.error(f"Erro ao criar medição de termografia: {e}")
        raise HTTPException(status_code=400, detail=str(e))

# Endpoints para análises de óleo

@router.post("/oil", response_model=OilMeasurementResponse, status_code=201, responses={400: {"model": ErrorResponse}})
def create_oil_measurement(
    measurement: OilMeasurementCreate,
    repository: MeasurementRepository = Depends(get_repository)
):
    """
    Cria uma nova análise de óleo.
    
    Args:
        measurement: Dados da análise
        repository: Repositório de medições
        
    Returns:
        Análise criada
    """
    try:
        # Criar objeto de análise
        oil_measurement = OilAnalysisMeasurement(
            id=str(uuid.uuid4()),
            equipment_id=measurement.equipment_id,
            timestamp=measurement.timestamp,
            source=MeasurementSource.OIL_ANALYSIS,
            status=MeasurementStatus(measurement.status),
            sample_id=measurement.sample_id,
            sample_type=OilSampleType(measurement.sample_type) if measurement.sample_type else None,
            oil_type=measurement.oil_type,
            oil_brand=measurement.oil_brand,
            hours_in_service=measurement.hours_in_service,
            sample_date=measurement.sample_date,
            analysis_date=measurement.analysis_date,
            laboratory=measurement.laboratory,
            metadata=measurement.metadata
        )
        
        # Adicionar propriedades
        for prop_data in measurement.properties:
            prop = OilProperty(
                name=prop_data.name,
                value=prop_data.value,
                unit=prop_data.unit,
                status=MeasurementStatus(prop_data.status) if prop_data.status else None,
                thresholds=None,  # Será definido abaixo
                metadata=prop_data.metadata
            )
            
            # Definir thresholds
            if prop_data.thresholds:
                from ..models.base import MeasurementThreshold
                prop.thresholds = MeasurementThreshold.from_dict(prop_data.thresholds)
            
            oil_measurement.properties.append(prop)
        
        # Salvar análise
        success = repository.save_oil_measurement(oil_measurement)
        
        if not success:
            raise HTTPException(status_code=400, detail="Falha ao criar análise de óleo")
        
        # Obter análise criada
        result = repository.get_oil_measurement(oil_measurement.id)
        
        if not result:
            raise HTTPException(status_code=404, detail="Análise não encontrada após criação")
        
        # Converter para modelo de resposta
        properties = []
        for prop in result.properties:
            properties.append({
                "name": prop.name,
                "value": prop.value,
                "unit": prop.unit,
                "status": prop.status.value if prop.status else None,
                "thresholds": prop.thresholds.to_dict() if prop.thresholds else None,
                "metadata": prop.metadata
            })
        
        return {
            "id": result.id,
            "equipment_id": result.equipment_id,
            "timestamp": result.timestamp,
            "source": result.source.value,
            "status": result.status.value,
            "metadata": result.metadata,
            "sample_id": result.sample_id,
            "sample_type": result.sample_type.value if result.sample_type else None,
            "oil_type": result.oil_type,
            "oil_brand": result.oil_brand,
            "hours_in_service": result.hours_in_service,
            "sample_date": result.sample_date,
            "analysis_date": result.analysis_date,
            "laboratory": result.laboratory,
            "properties": properties
        }
    except Exception as e:
        logger.error(f"Erro ao criar análise de óleo: {e}")
        raise HTTPException(status_code=400, detail=str(e))

# Endpoints para medições de vibração

@router.post("/vibration", response_model=VibrationMeasurementResponse, status_code=201, responses={400: {"model": ErrorResponse}})
def create_vibration_measurement(
    measurement: VibrationMeasurementCreate,
    repository: MeasurementRepository = Depends(get_repository)
):
    """
    Cria uma nova medição de vibração.
    
    Args:
        measurement: Dados da medição
        repository: Repositório de medições
        
    Returns:
        Medição criada
    """
    try:
        # Criar objeto de medição
        vibration_measurement = VibrationMeasurement(
            id=str(uuid.uuid4()),
            equipment_id=measurement.equipment_id,
            timestamp=measurement.timestamp,
            source=MeasurementSource.VIBRATION,
            status=MeasurementStatus(measurement.status),
            sensor_id=measurement.sensor_id,
            sensor_type=measurement.sensor_type,
            measurement_point=measurement.measurement_point,
            rpm=measurement.rpm,
            load=measurement.load,
            metadata=measurement.metadata
        )
        
        # Adicionar leituras
        for reading_data in measurement.readings:
            reading = VibrationReading(
                axis=VibrationAxis(reading_data.axis) if reading_data.axis else None,
                value=reading_data.value,
                unit=VibrationUnit(reading_data.unit) if reading_data.unit else None,
                frequency=reading_data.frequency,
                status=MeasurementStatus(reading_data.status) if reading_data.status else None,
                thresholds=None,  # Será definido abaixo
                metadata=reading_data.metadata
            )
            
            # Definir thresholds
            if reading_data.thresholds:
                from ..models.base import MeasurementThreshold
                reading.thresholds = MeasurementThreshold.from_dict(reading_data.thresholds)
            
            vibration_measurement.readings.append(reading)
        
        # Adicionar espectros
        for spectrum_data in measurement.spectra:
            spectrum = FrequencySpectrum(
                axis=VibrationAxis(spectrum_data.axis) if spectrum_data.axis else None,
                unit=VibrationUnit(spectrum_data.unit) if spectrum_data.unit else None,
                frequencies=spectrum_data.frequencies,
                amplitudes=spectrum_data.amplitudes,
                metadata=spectrum_data.metadata
            )
            
            vibration_measurement.spectra.append(spectrum)
        
        # Salvar medição
        success = repository.save_vibration_measurement(vibration_measurement)
        
        if not success:
            raise HTTPException(status_code=400, detail="Falha ao criar medição de vibração")
        
        # Obter medição criada
        result = repository.get_vibration_measurement(vibration_measurement.id)
        
        if not result:
            raise HTTPException(status_code=404, detail="Medição não encontrada após criação")
        
        # Converter para modelo de resposta
        readings = []
        for reading in result.readings:
            readings.append({
                "axis": reading.axis.value if reading.axis else None,
                "value": reading.value,
                "unit": reading.unit.value if reading.unit else None,
                "frequency": reading.frequency,
                "status": reading.status.value if reading.status else None,
                "thresholds": reading.thresholds.to_dict() if reading.thresholds else None,
                "metadata": reading.metadata
            })
        
        spectra = []
        for spectrum in result.spectra:
            spectra.append({
                "axis": spectrum.axis.value if spectrum.axis else None,
                "unit": spectrum.unit.value if spectrum.unit else None,
                "frequencies": spectrum.frequencies,
                "amplitudes": spectrum.amplitudes,
                "metadata": spectrum.metadata
            })
        
        return {
            "id": result.id,
            "equipment_id": result.equipment_id,
            "timestamp": result.timestamp,
            "source": result.source.value,
            "status": result.status.value,
            "metadata": result.metadata,
            "sensor_id": result.sensor_id,
            "sensor_type": result.sensor_type,
            "measurement_point": result.measurement_point,
            "rpm": result.rpm,
            "load": result.load,
            "readings": readings,
            "spectra": spectra
        }
    except Exception as e:
        logger.error(f"Erro ao criar medição de vibração: {e}")
        raise HTTPException(status_code=400, detail=str(e))

# Endpoints para equipamentos específicos

@router.get("/equipment/{equipment_id}/measurements", response_model=PaginatedResponse, responses={404: {"model": ErrorResponse}})
def get_equipment_measurements(
    equipment_id: str = Path(..., description="ID do equipamento"),
    source: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    repository: MeasurementRepository = Depends(get_repository)
):
    """
    Obtém medições de um equipamento específico.
    
    Args:
        equipment_id: ID do equipamento
        source: Fonte da medição (opcional)
        start_date: Data de início (opcional)
        end_date: Data de fim (opcional)
        page: Número da página
        page_size: Tamanho da página
        repository: Repositório de medições
        
    Returns:
        Lista paginada de medições
    """
    try:
        # Verificar se equipamento existe
        equipment = repository.get_equipment_by_id(equipment_id)
        
        if not equipment:
            raise HTTPException(status_code=404, detail="Equipamento não encontrado")
        
        offset = (page - 1) * page_size
        
        # Obter medições
        items = repository.get_equipment_measurements(
            equipment_id=equipment_id,
            source=source,
            start_date=start_date,
            end_date=end_date,
            limit=page_size,
            offset=offset
        )
        
        # Obter contagem total
        total = repository.get_measurement_count(
            equipment_id=equipment_id,
            source=source,
            start_date=start_date,
            end_date=end_date
        )
        
        # Calcular número de páginas
        pages = (total + page_size - 1) // page_size
        
        return {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
            "pages": pages
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao obter medições do equipamento {equipment_id}: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/equipment/{equipment_id}/latest", responses={404: {"model": ErrorResponse}})
def get_equipment_latest_measurement(
    equipment_id: str = Path(..., description="ID do equipamento"),
    source: Optional[str] = None,
    repository: MeasurementRepository = Depends(get_repository)
):
    """
    Obtém a medição mais recente de um equipamento.
    
    Args:
        equipment_id: ID do equipamento
        source: Fonte da medição (opcional)
        repository: Repositório de medições
        
    Returns:
        Medição mais recente
    """
    try:
        # Verificar se equipamento existe
        equipment = repository.get_equipment_by_id(equipment_id)
        
        if not equipment:
            raise HTTPException(status_code=404, detail="Equipamento não encontrado")
        
        # Obter medição mais recente
        result = repository.get_latest_measurement(
            equipment_id=equipment_id,
            source=source
        )
        
        if not result:
            raise HTTPException(status_code=404, detail="Nenhuma medição encontrada para o equipamento")
        
        # Obter detalhes específicos
        measurement_id = result["id"]
        source_value = result["source"]
        
        if source_value == MeasurementSource.THERMOGRAPHY.value:
            measurement = repository.get_thermography_measurement(measurement_id)
            if not measurement:
                return result  # Retornar informações básicas se detalhes não estiverem disponíveis
            
            # Converter para modelo de resposta
            points = []
            for point in measurement.points:
                points.append({
                    "id": point.id,
                    "name": point.name,
                    "x": point.x,
                    "y": point.y,
                    "temperature": point.temperature,
                    "emissivity": point.emissivity,
                    "status": point.status.value if point.status else None,
                    "thresholds": point.thresholds.to_dict() if point.thresholds else None,
                    "metadata": point.metadata
                })
            
            return {
                "id": measurement.id,
                "equipment_id": measurement.equipment_id,
                "timestamp": measurement.timestamp,
                "source": measurement.source.value,
                "status": measurement.status.value,
                "metadata": measurement.metadata,
                "image_url": measurement.image_url,
                "ambient_temperature": measurement.ambient_temperature,
                "humidity": measurement.humidity,
                "camera_model": measurement.camera_model,
                "distance": measurement.distance,
                "points": points
            }
            
        elif source_value == MeasurementSource.OIL_ANALYSIS.value:
            measurement = repository.get_oil_measurement(measurement_id)
            if not measurement:
                return result  # Retornar informações básicas se detalhes não estiverem disponíveis
            
            # Converter para modelo de resposta
            properties = []
            for prop in measurement.properties:
                properties.append({
                    "name": prop.name,
                    "value": prop.value,
                    "unit": prop.unit,
                    "status": prop.status.value if prop.status else None,
                    "thresholds": prop.thresholds.to_dict() if prop.thresholds else None,
                    "metadata": prop.metadata
                })
            
            return {
                "id": measurement.id,
                "equipment_id": measurement.equipment_id,
                "timestamp": measurement.timestamp,
                "source": measurement.source.value,
                "status": measurement.status.value,
                "metadata": measurement.metadata,
                "sample_id": measurement.sample_id,
                "sample_type": measurement.sample_type.value if measurement.sample_type else None,
                "oil_type": measurement.oil_type,
                "oil_brand": measurement.oil_brand,
                "hours_in_service": measurement.hours_in_service,
                "sample_date": measurement.sample_date,
                "analysis_date": measurement.analysis_date,
                "laboratory": measurement.laboratory,
                "properties": properties
            }
            
        elif source_value == MeasurementSource.VIBRATION.value:
            measurement = repository.get_vibration_measurement(measurement_id)
            if not measurement:
                return result  # Retornar informações básicas se detalhes não estiverem disponíveis
            
            # Converter para modelo de resposta
            readings = []
            for reading in measurement.readings:
                readings.append({
                    "axis": reading.axis.value if reading.axis else None,
                    "value": reading.value,
                    "unit": reading.unit.value if reading.unit else None,
                    "frequency": reading.frequency,
                    "status": reading.status.value if reading.status else None,
                    "thresholds": reading.thresholds.to_dict() if reading.thresholds else None,
                    "metadata": reading.metadata
                })
            
            spectra = []
            for spectrum in measurement.spectra:
                spectra.append({
                    "axis": spectrum.axis.value if spectrum.axis else None,
                    "unit": spectrum.unit.value if spectrum.unit else None,
                    "frequencies": spectrum.frequencies,
                    "amplitudes": spectrum.amplitudes,
                    "metadata": spectrum.metadata
                })
            
            return {
                "id": measurement.id,
                "equipment_id": measurement.equipment_id,
                "timestamp": measurement.timestamp,
                "source": measurement.source.value,
                "status": measurement.status.value,
                "metadata": measurement.metadata,
                "sensor_id": measurement.sensor_id,
                "sensor_type": measurement.sensor_type,
                "measurement_point": measurement.measurement_point,
                "rpm": measurement.rpm,
                "load": measurement.load,
                "readings": readings,
                "spectra": spectra
            }
            
        else:
            # Tipo desconhecido, retornar informações básicas
            return result
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao obter medição mais recente do equipamento {equipment_id}: {e}")
        raise HTTPException(status_code=400, detail=str(e))

# Endpoints para status

@router.get("/status/alerts", response_model=PaginatedResponse, responses={400: {"model": ErrorResponse}})
def get_alerts(
    source: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    repository: MeasurementRepository = Depends(get_repository)
):
    """
    Obtém medições com status de alerta.
    
    Args:
        source: Fonte da medição (opcional)
        page: Número da página
        page_size: Tamanho da página
        repository: Repositório de medições
        
    Returns:
        Lista paginada de medições com status de alerta
    """
    try:
        offset = (page - 1) * page_size
        
        # Obter medições com status de alerta
        items = repository.get_measurements_by_status(
            status=MeasurementStatus.ALERT,
            source=source,
            limit=page_size,
            offset=offset
        )
        
        # Obter contagem total
        total = repository.get_measurement_count(
            source=source,
            status=MeasurementStatus.ALERT
        )
        
        # Calcular número de páginas
        pages = (total + page_size - 1) // page_size
        
        return {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
            "pages": pages
        }
    except Exception as e:
        logger.error(f"Erro ao obter medições com status de alerta: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/status/warnings", response_model=PaginatedResponse, responses={400: {"model": ErrorResponse}})
def get_warnings(
    source: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    repository: MeasurementRepository = Depends(get_repository)
):
    """
    Obtém medições com status de aviso.
    
    Args:
        source: Fonte da medição (opcional)
        page: Número da página
        page_size: Tamanho da página
        repository: Repositório de medições
        
    Returns:
        Lista paginada de medições com status de aviso
    """
    try:
        offset = (page - 1) * page_size
        
        # Obter medições com status de aviso
        items = repository.get_measurements_by_status(
            status=MeasurementStatus.WARNING,
            source=source,
            limit=page_size,
            offset=offset
        )
        
        # Obter contagem total
        total = repository.get_measurement_count(
            source=source,
            status=MeasurementStatus.WARNING
        )
        
        # Calcular número de páginas
        pages = (total + page_size - 1) // page_size
        
        return {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
            "pages": pages
        }
    except Exception as e:
        logger.error(f"Erro ao obter medições com status de aviso: {e}")
        raise HTTPException(status_code=400, detail=str(e))

# Endpoints para sincronização

@router.get("/sync", response_model=List[Dict[str, Any]], responses={400: {"model": ErrorResponse}})
def get_measurements_since(
    since: datetime = Query(..., description="Data a partir da qual obter medições"),
    equipment_id: Optional[str] = None,
    source: Optional[str] = None,
    limit: int = Query(100, ge=1, le=1000),
    repository: MeasurementRepository = Depends(get_repository)
):
    """
    Obtém medições desde uma data específica.
    
    Args:
        since: Data a partir da qual obter medições
        equipment_id: ID do equipamento (opcional)
        source: Fonte da medição (opcional)
        limit: Limite de resultados
        repository: Repositório de medições
        
    Returns:
        Lista de medições
    """
    try:
        # Obter medições desde a data especificada
        items = repository.get_measurements_since(
            since_datetime=since,
            equipment_id=equipment_id,
            source=source,
            limit=limit
        )
        
        return items
    except Exception as e:
        logger.error(f"Erro ao obter medições desde {since}: {e}")
        raise HTTPException(status_code=400, detail=str(e))
