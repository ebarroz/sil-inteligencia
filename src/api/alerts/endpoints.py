"""
Endpoints REST para alertas no SIL Predictive System.

Este módulo implementa os endpoints REST para gerenciamento de alertas,
incluindo criação, consulta, atualização e exclusão.
"""

import logging
from typing import List, Optional, Dict, Any, Union
from datetime import datetime, timedelta
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Path
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from ..models.alerts.model import AlertBase, AlertStatus, AlertGravity, AlertCriticality
from ..config.database import DatabaseManager
from ..services.alert_service import AlertService

# Configuração de logging
logger = logging.getLogger(__name__)

# Criar router
router = APIRouter(prefix="/api/v1/alerts", tags=["alerts"])

# Modelos Pydantic para API

class AlertCreateRequest(BaseModel):
    """Modelo para criação de alertas."""
    equipment_id: str
    description: str
    measurement_id: Optional[str] = None
    measurement_source: Optional[str] = None
    gravity: AlertGravity
    criticality: AlertCriticality
    timestamp: datetime = Field(default_factory=datetime.now)
    metadata: Optional[Dict[str, Any]] = None

class AlertUpdateRequest(BaseModel):
    """Modelo para atualização de alertas."""
    status: Optional[AlertStatus] = None
    assigned_to: Optional[str] = None
    resolution_details: Optional[str] = None
    gravity: Optional[AlertGravity] = None
    criticality: Optional[AlertCriticality] = None
    metadata: Optional[Dict[str, Any]] = None

class AlertResponse(BaseModel):
    """Modelo para resposta de alertas."""
    id: str
    equipment_id: str
    timestamp: datetime
    measurement_id: Optional[str] = None
    measurement_source: Optional[str] = None
    description: str
    gravity: str
    criticality: str
    status: str
    assigned_to: Optional[str] = None
    resolution_details: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime

class PaginatedAlertResponse(BaseModel):
    """Modelo para resposta paginada de alertas."""
    items: List[AlertResponse]
    total: int
    page: int
    page_size: int
    pages: int

class ErrorResponse(BaseModel):
    """Modelo para resposta de erro."""
    detail: str

# Dependências

def get_alert_service():
    """
    Dependência para obter o serviço de alertas.
    
    Returns:
        AlertService: Serviço de alertas
    """
    db_manager = DatabaseManager()
    return AlertService(db_manager)

# Endpoints

@router.post("", response_model=AlertResponse, status_code=201, responses={400: {"model": ErrorResponse}})
def create_alert(alert: AlertCreateRequest, service: AlertService = Depends(get_alert_service)):
    """
    Cria um novo alerta.
    
    Args:
        alert: Dados do alerta
        service: Serviço de alertas
        
    Returns:
        Alerta criado
    """
    try:
        # Criar objeto de alerta
        alert_obj = AlertBase(
            id=str(uuid.uuid4()),
            equipment_id=alert.equipment_id,
            timestamp=alert.timestamp,
            measurement_id=alert.measurement_id,
            measurement_source=alert.measurement_source,
            description=alert.description,
            gravity=alert.gravity,
            criticality=alert.criticality,
            status=AlertStatus.NEW,
            metadata=alert.metadata
        )
        
        # Salvar alerta
        success = service.alert_repository.save_alert(alert_obj)
        
        if not success:
            raise HTTPException(status_code=400, detail="Falha ao criar alerta")
        
        # Obter alerta criado
        result = service.get_alert(alert_obj.id)
        
        if not result:
            raise HTTPException(status_code=404, detail="Alerta não encontrado após criação")
        
        return result
    except Exception as e:
        logger.error(f"Erro ao criar alerta: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@router.get("", response_model=PaginatedAlertResponse, responses={400: {"model": ErrorResponse}})
def get_alerts(
    equipment_id: Optional[str] = None,
    client_id: Optional[str] = None,
    status: Optional[str] = None,
    gravity: Optional[str] = None,
    criticality: Optional[str] = None,
    assigned_to: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    service: AlertService = Depends(get_alert_service)
):
    """
    Obtém lista de alertas com filtros.
    
    Args:
        equipment_id: ID do equipamento (opcional)
        client_id: ID do cliente (opcional)
        status: Status do alerta (opcional)
        gravity: Gravidade do alerta (opcional)
        criticality: Criticidade do alerta (opcional)
        assigned_to: ID do responsável (opcional)
        start_date: Data de início (opcional)
        end_date: Data de fim (opcional)
        page: Número da página
        page_size: Tamanho da página
        service: Serviço de alertas
        
    Returns:
        Lista paginada de alertas
    """
    try:
        offset = (page - 1) * page_size
        
        # Obter alertas
        items = service.get_alerts(
            equipment_id=equipment_id,
            client_id=client_id,
            status=status,
            gravity=gravity,
            criticality=criticality,
            assigned_to=assigned_to,
            start_date=start_date,
            end_date=end_date,
            limit=page_size,
            offset=offset
        )
        
        # Obter contagem total
        total = service.get_alert_count(
            equipment_id=equipment_id,
            client_id=client_id,
            status=status,
            gravity=gravity,
            criticality=criticality,
            assigned_to=assigned_to,
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
        logger.error(f"Erro ao obter alertas: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{alert_id}", response_model=AlertResponse, responses={404: {"model": ErrorResponse}})
def get_alert(
    alert_id: str = Path(..., description="ID do alerta"),
    service: AlertService = Depends(get_alert_service)
):
    """
    Obtém um alerta pelo ID.
    
    Args:
        alert_id: ID do alerta
        service: Serviço de alertas
        
    Returns:
        Alerta
    """
    try:
        result = service.get_alert(alert_id)
        
        if not result:
            raise HTTPException(status_code=404, detail="Alerta não encontrado")
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao obter alerta {alert_id}: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@router.put("/{alert_id}", response_model=AlertResponse, responses={404: {"model": ErrorResponse}})
def update_alert(
    alert: AlertUpdateRequest,
    alert_id: str = Path(..., description="ID do alerta"),
    service: AlertService = Depends(get_alert_service)
):
    """
    Atualiza um alerta.
    
    Args:
        alert: Dados do alerta
        alert_id: ID do alerta
        service: Serviço de alertas
        
    Returns:
        Alerta atualizado
    """
    try:
        # Verificar se alerta existe
        existing = service.get_alert(alert_id)
        
        if not existing:
            raise HTTPException(status_code=404, detail="Alerta não encontrado")
        
        # Atualizar campos
        if alert.status is not None:
            service.update_alert_status(
                alert_id=alert_id,
                status=alert.status,
                resolution_details=alert.resolution_details,
                assigned_to=alert.assigned_to
            )
        
        # Obter alerta atualizado
        result = service.get_alert(alert_id)
        
        if not result:
            raise HTTPException(status_code=404, detail="Alerta não encontrado após atualização")
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao atualizar alerta {alert_id}: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/{alert_id}", status_code=204, responses={404: {"model": ErrorResponse}})
def delete_alert(
    alert_id: str = Path(..., description="ID do alerta"),
    service: AlertService = Depends(get_alert_service)
):
    """
    Exclui um alerta.
    
    Args:
        alert_id: ID do alerta
        service: Serviço de alertas
    """
    try:
        # Verificar se alerta existe
        existing = service.get_alert(alert_id)
        
        if not existing:
            raise HTTPException(status_code=404, detail="Alerta não encontrado")
        
        # Excluir alerta
        success = service.delete_alert(alert_id)
        
        if not success:
            raise HTTPException(status_code=400, detail="Falha ao excluir alerta")
        
        return JSONResponse(status_code=204, content={})
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao excluir alerta {alert_id}: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/{alert_id}/assign", response_model=AlertResponse, responses={404: {"model": ErrorResponse}})
def assign_alert(
    assigned_to: str = Query(..., description="ID do responsável"),
    alert_id: str = Path(..., description="ID do alerta"),
    service: AlertService = Depends(get_alert_service)
):
    """
    Atribui um alerta a um responsável.
    
    Args:
        assigned_to: ID do responsável
        alert_id: ID do alerta
        service: Serviço de alertas
        
    Returns:
        Alerta atualizado
    """
    try:
        # Verificar se alerta existe
        existing = service.get_alert(alert_id)
        
        if not existing:
            raise HTTPException(status_code=404, detail="Alerta não encontrado")
        
        # Atribuir alerta
        success = service.assign_alert(
            alert_id=alert_id,
            assigned_to=assigned_to
        )
        
        if not success:
            raise HTTPException(status_code=400, detail="Falha ao atribuir alerta")
        
        # Obter alerta atualizado
        result = service.get_alert(alert_id)
        
        if not result:
            raise HTTPException(status_code=404, detail="Alerta não encontrado após atribuição")
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao atribuir alerta {alert_id}: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/{alert_id}/resolve", response_model=AlertResponse, responses={404: {"model": ErrorResponse}})
def resolve_alert(
    resolution_details: str = Query(..., description="Detalhes da resolução"),
    alert_id: str = Path(..., description="ID do alerta"),
    service: AlertService = Depends(get_alert_service)
):
    """
    Resolve um alerta.
    
    Args:
        resolution_details: Detalhes da resolução
        alert_id: ID do alerta
        service: Serviço de alertas
        
    Returns:
        Alerta atualizado
    """
    try:
        # Verificar se alerta existe
        existing = service.get_alert(alert_id)
        
        if not existing:
            raise HTTPException(status_code=404, detail="Alerta não encontrado")
        
        # Resolver alerta
        success = service.resolve_alert(
            alert_id=alert_id,
            resolution_details=resolution_details
        )
        
        if not success:
            raise HTTPException(status_code=400, detail="Falha ao resolver alerta")
        
        # Obter alerta atualizado
        result = service.get_alert(alert_id)
        
        if not result:
            raise HTTPException(status_code=404, detail="Alerta não encontrado após resolução")
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao resolver alerta {alert_id}: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/{alert_id}/false-positive", response_model=AlertResponse, responses={404: {"model": ErrorResponse}})
def mark_as_false_positive(
    resolution_details: str = Query(..., description="Detalhes da resolução"),
    alert_id: str = Path(..., description="ID do alerta"),
    service: AlertService = Depends(get_alert_service)
):
    """
    Marca um alerta como falso positivo.
    
    Args:
        resolution_details: Detalhes da resolução
        alert_id: ID do alerta
        service: Serviço de alertas
        
    Returns:
        Alerta atualizado
    """
    try:
        # Verificar se alerta existe
        existing = service.get_alert(alert_id)
        
        if not existing:
            raise HTTPException(status_code=404, detail="Alerta não encontrado")
        
        # Marcar como falso positivo
        success = service.mark_as_false_positive(
            alert_id=alert_id,
            resolution_details=resolution_details
        )
        
        if not success:
            raise HTTPException(status_code=400, detail="Falha ao marcar alerta como falso positivo")
        
        # Obter alerta atualizado
        result = service.get_alert(alert_id)
        
        if not result:
            raise HTTPException(status_code=404, detail="Alerta não encontrado após marcação")
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao marcar alerta {alert_id} como falso positivo: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/equipment/{equipment_id}", response_model=PaginatedAlertResponse, responses={404: {"model": ErrorResponse}})
def get_equipment_alerts(
    equipment_id: str = Path(..., description="ID do equipamento"),
    status: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    service: AlertService = Depends(get_alert_service)
):
    """
    Obtém alertas de um equipamento específico.
    
    Args:
        equipment_id: ID do equipamento
        status: Status do alerta (opcional)
        page: Número da página
        page_size: Tamanho da página
        service: Serviço de alertas
        
    Returns:
        Lista paginada de alertas
    """
    try:
        offset = (page - 1) * page_size
        
        # Obter alertas
        items = service.get_alerts_by_equipment(
            equipment_id=equipment_id,
            status=status,
            limit=page_size,
            offset=offset
        )
        
        # Obter contagem total
        total = service.get_alert_count(
            equipment_id=equipment_id,
            status=status
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
        logger.error(f"Erro ao obter alertas do equipamento {equipment_id}: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/client/{client_id}", response_model=PaginatedAlertResponse, responses={404: {"model": ErrorResponse}})
def get_client_alerts(
    client_id: str = Path(..., description="ID do cliente"),
    status: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    service: AlertService = Depends(get_alert_service)
):
    """
    Obtém alertas de um cliente específico.
    
    Args:
        client_id: ID do cliente
        status: Status do alerta (opcional)
        page: Número da página
        page_size: Tamanho da página
        service: Serviço de alertas
        
    Returns:
        Lista paginada de alertas
    """
    try:
        offset = (page - 1) * page_size
        
        # Obter alertas
        items = service.get_alerts_by_client(
            client_id=client_id,
            status=status,
            limit=page_size,
            offset=offset
        )
        
        # Obter contagem total
        total = service.get_alert_count(
            client_id=client_id,
            status=status
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
        logger.error(f"Erro ao obter alertas do cliente {client_id}: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/status/new", response_model=PaginatedAlertResponse, responses={400: {"model": ErrorResponse}})
def get_new_alerts(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    service: AlertService = Depends(get_alert_service)
):
    """
    Obtém alertas com status NEW.
    
    Args:
        page: Número da página
        page_size: Tamanho da página
        service: Serviço de alertas
        
    Returns:
        Lista paginada de alertas
    """
    try:
        offset = (page - 1) * page_size
        
        # Obter alertas
        items = service.get_alerts(
            status=AlertStatus.NEW,
            limit=page_size,
            offset=offset
        )
        
        # Obter contagem total
        total = service.get_alert_count(
            status=AlertStatus.NEW
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
        logger.error(f"Erro ao obter alertas novos: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/status/in-progress", response_model=PaginatedAlertResponse, responses={400: {"model": ErrorResponse}})
def get_in_progress_alerts(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    service: AlertService = Depends(get_alert_service)
):
    """
    Obtém alertas com status IN_PROGRESS.
    
    Args:
        page: Número da página
        page_size: Tamanho da página
        service: Serviço de alertas
        
    Returns:
        Lista paginada de alertas
    """
    try:
        offset = (page - 1) * page_size
        
        # Obter alertas
        items = service.get_alerts(
            status=AlertStatus.IN_PROGRESS,
            limit=page_size,
            offset=offset
        )
        
        # Obter contagem total
        total = service.get_alert_count(
            status=AlertStatus.IN_PROGRESS
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
        logger.error(f"Erro ao obter alertas em andamento: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/gravity/{gravity}", response_model=PaginatedAlertResponse, responses={400: {"model": ErrorResponse}})
def get_alerts_by_gravity(
    gravity: str = Path(..., description="Gravidade do alerta (P1, P2, P3)"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    service: AlertService = Depends(get_alert_service)
):
    """
    Obtém alertas por gravidade.
    
    Args:
        gravity: Gravidade do alerta
        page: Número da página
        page_size: Tamanho da página
        service: Serviço de alertas
        
    Returns:
        Lista paginada de alertas
    """
    try:
        offset = (page - 1) * page_size
        
        # Obter alertas
        items = service.get_alerts(
            gravity=gravity,
            limit=page_size,
            offset=offset
        )
        
        # Obter contagem total
        total = service.get_alert_count(
            gravity=gravity
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
        logger.error(f"Erro ao obter alertas por gravidade {gravity}: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/criticality/{criticality}", response_model=PaginatedAlertResponse, responses={400: {"model": ErrorResponse}})
def get_alerts_by_criticality(
    criticality: str = Path(..., description="Criticidade do alerta (HIGH, MEDIUM, LOW)"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    service: AlertService = Depends(get_alert_service)
):
    """
    Obtém alertas por criticidade.
    
    Args:
        criticality: Criticidade do alerta
        page: Número da página
        page_size: Tamanho da página
        service: Serviço de alertas
        
    Returns:
        Lista paginada de alertas
    """
    try:
        offset = (page - 1) * page_size
        
        # Obter alertas
        items = service.get_alerts(
            criticality=criticality,
            limit=page_size,
            offset=offset
        )
        
        # Obter contagem total
        total = service.get_alert_count(
            criticality=criticality
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
        logger.error(f"Erro ao obter alertas por criticidade {criticality}: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/assigned/{user_id}", response_model=PaginatedAlertResponse, responses={400: {"model": ErrorResponse}})
def get_alerts_by_assigned_user(
    user_id: str = Path(..., description="ID do usuário responsável"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    service: AlertService = Depends(get_alert_service)
):
    """
    Obtém alertas atribuídos a um usuário específico.
    
    Args:
        user_id: ID do usuário
        page: Número da página
        page_size: Tamanho da página
        service: Serviço de alertas
        
    Returns:
        Lista paginada de alertas
    """
    try:
        offset = (page - 1) * page_size
        
        # Obter alertas
        items = service.get_alerts(
            assigned_to=user_id,
            limit=page_size,
            offset=offset
        )
        
        # Obter contagem total
        total = service.get_alert_count(
            assigned_to=user_id
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
        logger.error(f"Erro ao obter alertas atribuídos ao usuário {user_id}: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/summary", responses={400: {"model": ErrorResponse}})
def get_alert_summary(service: AlertService = Depends(get_alert_service)):
    """
    Obtém resumo de alertas por status, gravidade e criticidade.
    
    Args:
        service: Serviço de alertas
        
    Returns:
        Resumo de alertas
    """
    try:
        # Obter contagens por status
        new_count = service.get_alert_count(status=AlertStatus.NEW)
        acknowledged_count = service.get_alert_count(status=AlertStatus.ACKNOWLEDGED)
        in_progress_count = service.get_alert_count(status=AlertStatus.IN_PROGRESS)
        resolved_count = service.get_alert_count(status=AlertStatus.RESOLVED)
        false_positive_count = service.get_alert_count(status=AlertStatus.FALSE_POSITIVE)
        
        # Obter contagens por gravidade
        p1_count = service.get_alert_count(gravity=AlertGravity.P1)
        p2_count = service.get_alert_count(gravity=AlertGravity.P2)
        p3_count = service.get_alert_count(gravity=AlertGravity.P3)
        
        # Obter contagens por criticidade
        high_count = service.get_alert_count(criticality=AlertCriticality.HIGH)
        medium_count = service.get_alert_count(criticality=AlertCriticality.MEDIUM)
        low_count = service.get_alert_count(criticality=AlertCriticality.LOW)
        
        return {
            "status": {
                "new": new_count,
                "acknowledged": acknowledged_count,
                "in_progress": in_progress_count,
                "resolved": resolved_count,
                "false_positive": false_positive_count
            },
            "gravity": {
                "p1": p1_count,
                "p2": p2_count,
                "p3": p3_count
            },
            "criticality": {
                "high": high_count,
                "medium": medium_count,
                "low": low_count
            },
            "total": new_count + acknowledged_count + in_progress_count + resolved_count + false_positive_count
        }
    except Exception as e:
        logger.error(f"Erro ao obter resumo de alertas: {e}")
        raise HTTPException(status_code=400, detail=str(e))
