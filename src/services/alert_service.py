"""
Alert service for the SIL Predictive System.

This module implements the business logic for alert management, including
alert generation, filtering, and notification.
"""

import logging
from typing import List, Optional, Dict, Any, Union
from datetime import datetime
import uuid

from ..models.alerts.model import AlertBase, AlertStatus, AlertGravity, AlertCriticality
from ..models.base import MeasurementStatus, MeasurementSource
from ..config.database import DatabaseManager
from ..config.alert_repository import AlertRepository

# Configuração de logging
logger = logging.getLogger(__name__)

class AlertService:
    """Serviço para gerenciamento de alertas."""
    
    def __init__(self, db_manager: DatabaseManager):
        """
        Inicializa o serviço de alertas.
        
        Args:
            db_manager: Gerenciador de banco de dados
        """
        self.db_manager = db_manager
        self.alert_repository = AlertRepository(db_manager)
    
    def generate_alert_from_measurement(
        self,
        measurement_id: str,
        equipment_id: str,
        source: MeasurementSource,
        status: MeasurementStatus,
        description: str,
        timestamp: datetime,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[str]:
        """
        Gera um alerta a partir de uma medição.
        
        Args:
            measurement_id: ID da medição
            equipment_id: ID do equipamento
            source: Fonte da medição
            status: Status da medição
            description: Descrição do alerta
            timestamp: Timestamp da medição
            metadata: Metadados adicionais (opcional)
            
        Returns:
            ID do alerta gerado ou None se não foi possível gerar
        """
        try:
            # Determinar gravidade com base no status da medição
            gravity = AlertGravity.P1
            if status == MeasurementStatus.WARNING:
                gravity = AlertGravity.P2
            elif status == MeasurementStatus.ALERT:
                gravity = AlertGravity.P1
            else:
                gravity = AlertGravity.P3
            
            # Determinar criticidade com base no equipamento
            # Em uma implementação real, isso seria obtido do equipamento
            criticality = AlertCriticality.MEDIUM
            
            # Criar alerta
            alert = AlertBase(
                id=str(uuid.uuid4()),
                equipment_id=equipment_id,
                timestamp=timestamp,
                measurement_id=measurement_id,
                measurement_source=source,
                description=description,
                gravity=gravity,
                criticality=criticality,
                status=AlertStatus.NEW,
                metadata=metadata
            )
            
            # Salvar alerta
            success = self.alert_repository.save_alert(alert)
            
            if success:
                logger.info(f"Alerta gerado com sucesso: {alert.id}")
                return alert.id
            else:
                logger.error("Falha ao gerar alerta")
                return None
        except Exception as e:
            logger.error(f"Erro ao gerar alerta: {e}")
            return None
    
    def get_alert(self, alert_id: str) -> Optional[Dict[str, Any]]:
        """
        Obtém um alerta pelo ID.
        
        Args:
            alert_id: ID do alerta
            
        Returns:
            Alerta ou None se não encontrado
        """
        return self.alert_repository.get_alert_by_id(alert_id)
    
    def get_alerts(
        self,
        equipment_id: Optional[str] = None,
        client_id: Optional[str] = None,
        status: Optional[Union[AlertStatus, str]] = None,
        gravity: Optional[Union[AlertGravity, str]] = None,
        criticality: Optional[Union[AlertCriticality, str]] = None,
        assigned_to: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
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
            limit: Limite de resultados
            offset: Deslocamento para paginação
            
        Returns:
            Lista de alertas
        """
        return self.alert_repository.get_alerts(
            equipment_id=equipment_id,
            client_id=client_id,
            status=status,
            gravity=gravity,
            criticality=criticality,
            assigned_to=assigned_to,
            start_date=start_date,
            end_date=end_date,
            limit=limit,
            offset=offset
        )
    
    def update_alert_status(
        self,
        alert_id: str,
        status: AlertStatus,
        resolution_details: Optional[str] = None,
        assigned_to: Optional[str] = None
    ) -> bool:
        """
        Atualiza o status de um alerta.
        
        Args:
            alert_id: ID do alerta
            status: Novo status
            resolution_details: Detalhes da resolução (opcional)
            assigned_to: ID do responsável (opcional)
            
        Returns:
            bool: True se o alerta foi atualizado com sucesso, False caso contrário
        """
        return self.alert_repository.update_alert_status(
            alert_id=alert_id,
            status=status,
            resolution_details=resolution_details,
            assigned_to=assigned_to
        )
    
    def mark_as_false_positive(
        self,
        alert_id: str,
        resolution_details: str,
        assigned_to: Optional[str] = None
    ) -> bool:
        """
        Marca um alerta como falso positivo.
        
        Args:
            alert_id: ID do alerta
            resolution_details: Detalhes da resolução
            assigned_to: ID do responsável (opcional)
            
        Returns:
            bool: True se o alerta foi marcado com sucesso, False caso contrário
        """
        return self.alert_repository.update_alert_status(
            alert_id=alert_id,
            status=AlertStatus.FALSE_POSITIVE,
            resolution_details=resolution_details,
            assigned_to=assigned_to
        )
    
    def resolve_alert(
        self,
        alert_id: str,
        resolution_details: str,
        assigned_to: Optional[str] = None
    ) -> bool:
        """
        Resolve um alerta.
        
        Args:
            alert_id: ID do alerta
            resolution_details: Detalhes da resolução
            assigned_to: ID do responsável (opcional)
            
        Returns:
            bool: True se o alerta foi resolvido com sucesso, False caso contrário
        """
        return self.alert_repository.update_alert_status(
            alert_id=alert_id,
            status=AlertStatus.RESOLVED,
            resolution_details=resolution_details,
            assigned_to=assigned_to
        )
    
    def assign_alert(
        self,
        alert_id: str,
        assigned_to: str
    ) -> bool:
        """
        Atribui um alerta a um responsável.
        
        Args:
            alert_id: ID do alerta
            assigned_to: ID do responsável
            
        Returns:
            bool: True se o alerta foi atribuído com sucesso, False caso contrário
        """
        # Obter alerta atual
        alert = self.alert_repository.get_alert_by_id(alert_id)
        
        if not alert:
            logger.warning(f"Alerta {alert_id} não encontrado")
            return False
        
        # Atualizar status para ACKNOWLEDGED se estiver NEW
        status = AlertStatus(alert["status"])
        if status == AlertStatus.NEW:
            status = AlertStatus.ACKNOWLEDGED
        
        return self.alert_repository.update_alert_status(
            alert_id=alert_id,
            status=status,
            assigned_to=assigned_to
        )
    
    def get_alerts_by_equipment(
        self,
        equipment_id: str,
        status: Optional[Union[AlertStatus, str]] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Obtém alertas de um equipamento específico.
        
        Args:
            equipment_id: ID do equipamento
            status: Status do alerta (opcional)
            limit: Limite de resultados
            offset: Deslocamento para paginação
            
        Returns:
            Lista de alertas
        """
        return self.alert_repository.get_alerts_by_equipment(
            equipment_id=equipment_id,
            status=status,
            limit=limit,
            offset=offset
        )
    
    def get_alerts_by_client(
        self,
        client_id: str,
        status: Optional[Union[AlertStatus, str]] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Obtém alertas de um cliente específico.
        
        Args:
            client_id: ID do cliente
            status: Status do alerta (opcional)
            limit: Limite de resultados
            offset: Deslocamento para paginação
            
        Returns:
            Lista de alertas
        """
        return self.alert_repository.get_alerts_by_client(
            client_id=client_id,
            status=status,
            limit=limit,
            offset=offset
        )
    
    def filter_false_alarms(self, alert_id: str) -> bool:
        """
        Filtra alarmes falsos com base em critérios predefinidos.
        
        Args:
            alert_id: ID do alerta a ser verificado
            
        Returns:
            bool: True se o alerta é considerado válido, False se for um falso alarme
        """
        # Em uma implementação real, aqui seriam aplicados algoritmos de filtragem
        # baseados em histórico, padrões, etc.
        # Por enquanto, retornamos True para todos os alertas
        return True
    
    def get_alert_count(
        self,
        equipment_id: Optional[str] = None,
        client_id: Optional[str] = None,
        status: Optional[Union[AlertStatus, str]] = None,
        gravity: Optional[Union[AlertGravity, str]] = None,
        criticality: Optional[Union[AlertCriticality, str]] = None,
        assigned_to: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> int:
        """
        Obtém contagem de alertas com filtros.
        
        Args:
            equipment_id: ID do equipamento (opcional)
            client_id: ID do cliente (opcional)
            status: Status do alerta (opcional)
            gravity: Gravidade do alerta (opcional)
            criticality: Criticidade do alerta (opcional)
            assigned_to: ID do responsável (opcional)
            start_date: Data de início (opcional)
            end_date: Data de fim (opcional)
            
        Returns:
            Contagem de alertas
        """
        return self.alert_repository.get_alert_count(
            equipment_id=equipment_id,
            client_id=client_id,
            status=status,
            gravity=gravity,
            criticality=criticality,
            assigned_to=assigned_to,
            start_date=start_date,
            end_date=end_date
        )
    
    def delete_alert(self, alert_id: str) -> bool:
        """
        Exclui um alerta.
        
        Args:
            alert_id: ID do alerta
            
        Returns:
            bool: True se o alerta foi excluído com sucesso, False caso contrário
        """
        return self.alert_repository.delete_alert(alert_id)
