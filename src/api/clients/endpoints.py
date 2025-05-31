"""
Endpoints REST para clientes no SIL Predictive System.

Este módulo fornece endpoints para gerenciamento de clientes com histórico de máquinas.
"""

import logging
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, Path, status
from fastapi.responses import JSONResponse

from ...models.clients.model import ClientCreate, ClientUpdate, ClientResponse, ClientStatus, ClientRiskLevel
from ...services.client_service import ClientService

# Configuração de logging
logger = logging.getLogger(__name__)

# Criar router
router = APIRouter(prefix="/clients", tags=["clients"])

# Dependência para obter o serviço de clientes
def get_client_service():
    """Dependência para obter o serviço de clientes."""
    from ...config.dependencies import get_db_manager
    from ...config.client_repository import ClientRepository
    
    db_manager = get_db_manager()
    client_repository = ClientRepository(db_manager)
    return ClientService(client_repository)

@router.post("/", response_model=ClientResponse, status_code=status.HTTP_201_CREATED)
async def create_client(
    client_data: ClientCreate,
    client_service: ClientService = Depends(get_client_service)
):
    """
    Cria um novo cliente.
    
    Args:
        client_data: Dados do cliente
        client_service: Serviço de clientes
        
    Returns:
        Cliente criado
    """
    try:
        client = client_service.create_client(client_data)
        
        if not client:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Falha ao criar cliente"
            )
        
        return client
    except Exception as e:
        logger.error(f"Erro ao criar cliente: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao criar cliente: {str(e)}"
        )

@router.get("/", response_model=Dict[str, Any])
async def list_clients(
    status: Optional[ClientStatus] = None,
    risk_level: Optional[ClientRiskLevel] = None,
    search: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    client_service: ClientService = Depends(get_client_service)
):
    """
    Lista clientes com filtros e paginação.
    
    Args:
        status: Status do cliente (opcional)
        risk_level: Nível de risco do cliente (opcional)
        search: Termo de busca para nome ou documento (opcional)
        page: Número da página
        page_size: Tamanho da página
        client_service: Serviço de clientes
        
    Returns:
        Lista paginada de clientes
    """
    try:
        clients, total_count = client_service.list_clients(
            status=status,
            risk_level=risk_level,
            search_term=search,
            page=page,
            page_size=page_size
        )
        
        # Calcular total de páginas
        total_pages = (total_count + page_size - 1) // page_size if total_count > 0 else 1
        
        return {
            "items": clients,
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total_items": total_count,
                "total_pages": total_pages
            }
        }
    except Exception as e:
        logger.error(f"Erro ao listar clientes: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao listar clientes: {str(e)}"
        )

@router.get("/{client_id}", response_model=ClientResponse)
async def get_client(
    client_id: str = Path(..., title="ID do cliente"),
    client_service: ClientService = Depends(get_client_service)
):
    """
    Obtém um cliente pelo ID.
    
    Args:
        client_id: ID do cliente
        client_service: Serviço de clientes
        
    Returns:
        Cliente
    """
    try:
        client = client_service.get_client(client_id)
        
        if not client:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Cliente {client_id} não encontrado"
            )
        
        return client
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao obter cliente {client_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao obter cliente {client_id}: {str(e)}"
        )

@router.put("/{client_id}", response_model=ClientResponse)
async def update_client(
    client_data: ClientUpdate,
    client_id: str = Path(..., title="ID do cliente"),
    client_service: ClientService = Depends(get_client_service)
):
    """
    Atualiza um cliente existente.
    
    Args:
        client_data: Dados atualizados do cliente
        client_id: ID do cliente
        client_service: Serviço de clientes
        
    Returns:
        Cliente atualizado
    """
    try:
        client = client_service.update_client(client_id, client_data)
        
        if not client:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Cliente {client_id} não encontrado"
            )
        
        return client
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao atualizar cliente {client_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao atualizar cliente {client_id}: {str(e)}"
        )

@router.delete("/{client_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_client(
    client_id: str = Path(..., title="ID do cliente"),
    client_service: ClientService = Depends(get_client_service)
):
    """
    Exclui um cliente.
    
    Args:
        client_id: ID do cliente
        client_service: Serviço de clientes
    """
    try:
        success = client_service.delete_client(client_id)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Cliente {client_id} não encontrado"
            )
        
        return JSONResponse(status_code=status.HTTP_204_NO_CONTENT, content={})
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao excluir cliente {client_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao excluir cliente {client_id}: {str(e)}"
        )

@router.patch("/{client_id}/status", response_model=Dict[str, Any])
async def update_client_status(
    status: ClientStatus,
    client_id: str = Path(..., title="ID do cliente"),
    client_service: ClientService = Depends(get_client_service)
):
    """
    Atualiza o status de um cliente.
    
    Args:
        status: Novo status
        client_id: ID do cliente
        client_service: Serviço de clientes
        
    Returns:
        Resultado da operação
    """
    try:
        success = client_service.update_client_status(client_id, status)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Cliente {client_id} não encontrado"
            )
        
        return {"success": True, "message": f"Status do cliente {client_id} atualizado para {status.value}"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao atualizar status do cliente {client_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao atualizar status do cliente {client_id}: {str(e)}"
        )

@router.patch("/{client_id}/risk-level", response_model=Dict[str, Any])
async def update_client_risk_level(
    risk_level: ClientRiskLevel,
    custom_risk_parameters: Optional[Dict[str, Any]] = None,
    client_id: str = Path(..., title="ID do cliente"),
    client_service: ClientService = Depends(get_client_service)
):
    """
    Atualiza o nível de risco de um cliente.
    
    Args:
        risk_level: Novo nível de risco
        custom_risk_parameters: Parâmetros de risco personalizados (opcional)
        client_id: ID do cliente
        client_service: Serviço de clientes
        
    Returns:
        Resultado da operação
    """
    try:
        success = client_service.update_client_risk_level(
            client_id,
            risk_level,
            custom_risk_parameters
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Cliente {client_id} não encontrado"
            )
        
        return {
            "success": True,
            "message": f"Nível de risco do cliente {client_id} atualizado para {risk_level.value}"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao atualizar nível de risco do cliente {client_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao atualizar nível de risco do cliente {client_id}: {str(e)}"
        )

@router.get("/{client_id}/equipment", response_model=Dict[str, Any])
async def get_client_equipment(
    client_id: str = Path(..., title="ID do cliente"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    client_service: ClientService = Depends(get_client_service)
):
    """
    Obtém equipamentos de um cliente específico.
    
    Args:
        client_id: ID do cliente
        page: Número da página
        page_size: Tamanho da página
        client_service: Serviço de clientes
        
    Returns:
        Lista paginada de equipamentos
    """
    try:
        equipment_list, total_count = client_service.get_client_equipment(
            client_id,
            page=page,
            page_size=page_size
        )
        
        if equipment_list is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Cliente {client_id} não encontrado"
            )
        
        # Calcular total de páginas
        total_pages = (total_count + page_size - 1) // page_size if total_count > 0 else 1
        
        return {
            "items": equipment_list,
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total_items": total_count,
                "total_pages": total_pages
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao obter equipamentos do cliente {client_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao obter equipamentos do cliente {client_id}: {str(e)}"
        )

@router.get("/{client_id}/alerts", response_model=Dict[str, Any])
async def get_client_alerts(
    client_id: str = Path(..., title="ID do cliente"),
    status: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    client_service: ClientService = Depends(get_client_service)
):
    """
    Obtém alertas de um cliente específico.
    
    Args:
        client_id: ID do cliente
        status: Status do alerta (opcional)
        page: Número da página
        page_size: Tamanho da página
        client_service: Serviço de clientes
        
    Returns:
        Lista paginada de alertas
    """
    try:
        alerts_list, total_count = client_service.get_client_alerts(
            client_id,
            status=status,
            page=page,
            page_size=page_size
        )
        
        if alerts_list is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Cliente {client_id} não encontrado"
            )
        
        # Calcular total de páginas
        total_pages = (total_count + page_size - 1) // page_size if total_count > 0 else 1
        
        return {
            "items": alerts_list,
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total_items": total_count,
                "total_pages": total_pages
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao obter alertas do cliente {client_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao obter alertas do cliente {client_id}: {str(e)}"
        )

@router.get("/{client_id}/statistics", response_model=Dict[str, Any])
async def get_client_statistics(
    client_id: str = Path(..., title="ID do cliente"),
    client_service: ClientService = Depends(get_client_service)
):
    """
    Obtém estatísticas de um cliente específico.
    
    Args:
        client_id: ID do cliente
        client_service: Serviço de clientes
        
    Returns:
        Estatísticas do cliente
    """
    try:
        statistics = client_service.get_client_statistics(client_id)
        
        if not statistics:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Cliente {client_id} não encontrado"
            )
        
        return statistics
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao obter estatísticas do cliente {client_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao obter estatísticas do cliente {client_id}: {str(e)}"
        )
