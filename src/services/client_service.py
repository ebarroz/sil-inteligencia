"""
Client service for the SIL Predictive System.

This module provides business logic for client management with machine history.
"""

import logging
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime

from ..models.clients.model import ClientBase, ClientCreate, ClientUpdate, ClientResponse, ClientStatus, ClientRiskLevel
from ..config.client_repository import ClientRepository

# Configuração de logging
logger = logging.getLogger(__name__)

class ClientService:
    """Serviço para gerenciamento de clientes."""
    
    def __init__(self, client_repository: ClientRepository):
        """
        Inicializa o serviço de clientes.
        
        Args:
            client_repository: Repositório de clientes
        """
        self.client_repository = client_repository
    
    def create_client(self, client_data: ClientCreate) -> Optional[ClientResponse]:
        """
        Cria um novo cliente.
        
        Args:
            client_data: Dados do cliente
            
        Returns:
            Cliente criado ou None se falhou
        """
        try:
            # Criar cliente
            client = ClientBase(**client_data.dict())
            
            # Salvar no repositório
            success = self.client_repository.save_client(client)
            
            if not success:
                logger.error(f"Falha ao salvar cliente {client.name}")
                return None
            
            # Obter cliente salvo
            client_dict = self.client_repository.get_client_by_id(client.id)
            
            if not client_dict:
                logger.error(f"Falha ao obter cliente salvo {client.id}")
                return None
            
            # Converter para modelo de resposta
            return ClientResponse(**client_dict)
        except Exception as e:
            logger.error(f"Erro ao criar cliente: {e}")
            return None
    
    def update_client(self, client_id: str, client_data: ClientUpdate) -> Optional[ClientResponse]:
        """
        Atualiza um cliente existente.
        
        Args:
            client_id: ID do cliente
            client_data: Dados atualizados do cliente
            
        Returns:
            Cliente atualizado ou None se falhou
        """
        try:
            # Obter cliente existente
            existing_client_dict = self.client_repository.get_client_by_id(client_id)
            
            if not existing_client_dict:
                logger.error(f"Cliente {client_id} não encontrado")
                return None
            
            # Mesclar dados existentes com atualizações
            updated_data = {**existing_client_dict}
            
            # Atualizar apenas campos não nulos
            update_dict = {k: v for k, v in client_data.dict().items() if v is not None}
            updated_data.update(update_dict)
            
            # Criar cliente atualizado
            client = ClientBase(**updated_data)
            
            # Salvar no repositório
            success = self.client_repository.save_client(client)
            
            if not success:
                logger.error(f"Falha ao atualizar cliente {client_id}")
                return None
            
            # Obter cliente atualizado
            client_dict = self.client_repository.get_client_by_id(client_id)
            
            if not client_dict:
                logger.error(f"Falha ao obter cliente atualizado {client_id}")
                return None
            
            # Converter para modelo de resposta
            return ClientResponse(**client_dict)
        except Exception as e:
            logger.error(f"Erro ao atualizar cliente {client_id}: {e}")
            return None
    
    def get_client(self, client_id: str) -> Optional[ClientResponse]:
        """
        Obtém um cliente pelo ID.
        
        Args:
            client_id: ID do cliente
            
        Returns:
            Cliente ou None se não encontrado
        """
        try:
            client_dict = self.client_repository.get_client_by_id(client_id)
            
            if not client_dict:
                logger.warning(f"Cliente {client_id} não encontrado")
                return None
            
            return ClientResponse(**client_dict)
        except Exception as e:
            logger.error(f"Erro ao obter cliente {client_id}: {e}")
            return None
    
    def list_clients(
        self,
        status: Optional[ClientStatus] = None,
        risk_level: Optional[ClientRiskLevel] = None,
        search_term: Optional[str] = None,
        page: int = 1,
        page_size: int = 20
    ) -> Tuple[List[ClientResponse], int]:
        """
        Lista clientes com filtros e paginação.
        
        Args:
            status: Status do cliente (opcional)
            risk_level: Nível de risco do cliente (opcional)
            search_term: Termo de busca para nome ou documento (opcional)
            page: Número da página
            page_size: Tamanho da página
            
        Returns:
            Tupla com lista de clientes e contagem total
        """
        try:
            # Calcular offset
            offset = (page - 1) * page_size
            
            # Obter clientes
            clients_dict = self.client_repository.get_clients(
                status=status,
                risk_level=risk_level,
                search_term=search_term,
                limit=page_size,
                offset=offset
            )
            
            # Obter contagem total
            total_count = self.client_repository.get_client_count(
                status=status,
                risk_level=risk_level,
                search_term=search_term
            )
            
            # Converter para modelo de resposta
            clients = [ClientResponse(**client_dict) for client_dict in clients_dict]
            
            return clients, total_count
        except Exception as e:
            logger.error(f"Erro ao listar clientes: {e}")
            return [], 0
    
    def delete_client(self, client_id: str) -> bool:
        """
        Exclui um cliente.
        
        Args:
            client_id: ID do cliente
            
        Returns:
            True se excluído com sucesso, False caso contrário
        """
        try:
            return self.client_repository.delete_client(client_id)
        except Exception as e:
            logger.error(f"Erro ao excluir cliente {client_id}: {e}")
            return False
    
    def update_client_status(self, client_id: str, status: ClientStatus) -> bool:
        """
        Atualiza o status de um cliente.
        
        Args:
            client_id: ID do cliente
            status: Novo status
            
        Returns:
            True se atualizado com sucesso, False caso contrário
        """
        try:
            return self.client_repository.update_client_status(client_id, status)
        except Exception as e:
            logger.error(f"Erro ao atualizar status do cliente {client_id}: {e}")
            return False
    
    def update_client_risk_level(
        self,
        client_id: str,
        risk_level: ClientRiskLevel,
        custom_risk_parameters: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Atualiza o nível de risco de um cliente.
        
        Args:
            client_id: ID do cliente
            risk_level: Novo nível de risco
            custom_risk_parameters: Parâmetros de risco personalizados (opcional)
            
        Returns:
            True se atualizado com sucesso, False caso contrário
        """
        try:
            return self.client_repository.update_client_risk_level(
                client_id,
                risk_level,
                custom_risk_parameters
            )
        except Exception as e:
            logger.error(f"Erro ao atualizar nível de risco do cliente {client_id}: {e}")
            return False
    
    def get_client_equipment(
        self,
        client_id: str,
        page: int = 1,
        page_size: int = 20
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        Obtém equipamentos de um cliente específico.
        
        Args:
            client_id: ID do cliente
            page: Número da página
            page_size: Tamanho da página
            
        Returns:
            Tupla com lista de equipamentos e contagem total
        """
        try:
            # Calcular offset
            offset = (page - 1) * page_size
            
            # Obter equipamentos
            equipment_list = self.client_repository.get_client_equipment(
                client_id,
                limit=page_size,
                offset=offset
            )
            
            # Obter contagem total
            total_count = self.client_repository.get_client_equipment_count(client_id)
            
            return equipment_list, total_count
        except Exception as e:
            logger.error(f"Erro ao obter equipamentos do cliente {client_id}: {e}")
            return [], 0
    
    def get_client_alerts(
        self,
        client_id: str,
        status: Optional[str] = None,
        page: int = 1,
        page_size: int = 20
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        Obtém alertas de um cliente específico.
        
        Args:
            client_id: ID do cliente
            status: Status do alerta (opcional)
            page: Número da página
            page_size: Tamanho da página
            
        Returns:
            Tupla com lista de alertas e contagem total
        """
        try:
            # Calcular offset
            offset = (page - 1) * page_size
            
            # Obter alertas
            alerts_list = self.client_repository.get_client_alerts(
                client_id,
                status=status,
                limit=page_size,
                offset=offset
            )
            
            # Obter contagem total
            total_count = self.client_repository.get_client_alerts_count(
                client_id,
                status=status
            )
            
            return alerts_list, total_count
        except Exception as e:
            logger.error(f"Erro ao obter alertas do cliente {client_id}: {e}")
            return [], 0
    
    def get_client_statistics(self, client_id: str) -> Dict[str, Any]:
        """
        Obtém estatísticas de um cliente específico.
        
        Args:
            client_id: ID do cliente
            
        Returns:
            Dicionário com estatísticas
        """
        try:
            # Obter cliente
            client_dict = self.client_repository.get_client_by_id(client_id)
            
            if not client_dict:
                logger.warning(f"Cliente {client_id} não encontrado")
                return {}
            
            # Obter contagem de equipamentos
            equipment_count = self.client_repository.get_client_equipment_count(client_id)
            
            # Obter contagem de alertas por status
            alerts_new = self.client_repository.get_client_alerts_count(client_id, status="NEW")
            alerts_acknowledged = self.client_repository.get_client_alerts_count(client_id, status="ACKNOWLEDGED")
            alerts_in_progress = self.client_repository.get_client_alerts_count(client_id, status="IN_PROGRESS")
            alerts_resolved = self.client_repository.get_client_alerts_count(client_id, status="RESOLVED")
            alerts_false = self.client_repository.get_client_alerts_count(client_id, status="FALSE_ALARM")
            
            return {
                "client_name": client_dict["name"],
                "risk_level": client_dict["risk_level"],
                "equipment_count": equipment_count,
                "alerts": {
                    "new": alerts_new,
                    "acknowledged": alerts_acknowledged,
                    "in_progress": alerts_in_progress,
                    "resolved": alerts_resolved,
                    "false_alarm": alerts_false,
                    "total": alerts_new + alerts_acknowledged + alerts_in_progress + alerts_resolved + alerts_false
                }
            }
        except Exception as e:
            logger.error(f"Erro ao obter estatísticas do cliente {client_id}: {e}")
            return {}
