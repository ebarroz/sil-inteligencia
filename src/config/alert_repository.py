"""
Alert repository for the SIL Predictive System.

This module extends the database functionality to handle alerts with gravity and criticality.
"""

import logging
from typing import List, Optional, Dict, Any, Union
from datetime import datetime
import uuid

from ..models.alerts.model import AlertBase, AlertStatus, AlertGravity, AlertCriticality

# Configuração de logging
logger = logging.getLogger(__name__)

class AlertRepository:
    """Repositório para operações com alertas."""
    
    def __init__(self, db_manager):
        """
        Inicializa o repositório de alertas.
        
        Args:
            db_manager: Gerenciador de banco de dados
        """
        self.db_manager = db_manager
    
    def save_alert(self, alert: AlertBase) -> bool:
        """
        Salva um alerta no banco de dados.
        
        Args:
            alert: Alerta a ser salvo
            
        Returns:
            bool: True se o alerta foi salvo com sucesso, False caso contrário
        """
        try:
            with self.db_manager.get_connection() as conn:
                with conn.cursor() as cursor:
                    # Verificar se o alerta já existe
                    cursor.execute(
                        """
                        SELECT id FROM alerts WHERE id = %s
                        """,
                        (alert.id,)
                    )
                    
                    exists = cursor.fetchone() is not None
                    
                    if exists:
                        # Atualizar alerta existente
                        cursor.execute(
                            """
                            UPDATE alerts
                            SET equipment_id = %s,
                                timestamp = %s,
                                measurement_id = %s,
                                measurement_source = %s,
                                description = %s,
                                gravity = %s,
                                criticality = %s,
                                status = %s,
                                assigned_to = %s,
                                resolution_details = %s,
                                metadata = %s,
                                updated_at = NOW()
                            WHERE id = %s
                            """,
                            (
                                alert.equipment_id,
                                alert.timestamp,
                                alert.measurement_id,
                                alert.measurement_source.value if alert.measurement_source else None,
                                alert.description,
                                alert.gravity.value,
                                alert.criticality.value,
                                alert.status.value,
                                alert.assigned_to,
                                alert.resolution_details,
                                alert.metadata,
                                alert.id
                            )
                        )
                    else:
                        # Inserir novo alerta
                        cursor.execute(
                            """
                            INSERT INTO alerts (
                                id, equipment_id, timestamp, measurement_id, measurement_source,
                                description, gravity, criticality, status, assigned_to,
                                resolution_details, metadata, created_at, updated_at
                            ) VALUES (
                                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW()
                            )
                            """,
                            (
                                alert.id,
                                alert.equipment_id,
                                alert.timestamp,
                                alert.measurement_id,
                                alert.measurement_source.value if alert.measurement_source else None,
                                alert.description,
                                alert.gravity.value,
                                alert.criticality.value,
                                alert.status.value,
                                alert.assigned_to,
                                alert.resolution_details,
                                alert.metadata
                            )
                        )
                    
                    conn.commit()
                    return True
        except Exception as e:
            logger.error(f"Erro ao salvar alerta: {e}")
            return False
    
    def get_alert_by_id(self, alert_id: str) -> Optional[Dict[str, Any]]:
        """
        Obtém um alerta pelo ID.
        
        Args:
            alert_id: ID do alerta
            
        Returns:
            Alerta ou None se não encontrado
        """
        try:
            with self.db_manager.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        SELECT
                            id, equipment_id, timestamp, measurement_id, measurement_source,
                            description, gravity, criticality, status, assigned_to,
                            resolution_details, metadata, created_at, updated_at
                        FROM alerts
                        WHERE id = %s
                        """,
                        (alert_id,)
                    )
                    
                    row = cursor.fetchone()
                    
                    if not row:
                        return None
                    
                    return {
                        "id": row[0],
                        "equipment_id": row[1],
                        "timestamp": row[2],
                        "measurement_id": row[3],
                        "measurement_source": row[4],
                        "description": row[5],
                        "gravity": row[6],
                        "criticality": row[7],
                        "status": row[8],
                        "assigned_to": row[9],
                        "resolution_details": row[10],
                        "metadata": row[11],
                        "created_at": row[12],
                        "updated_at": row[13]
                    }
        except Exception as e:
            logger.error(f"Erro ao obter alerta {alert_id}: {e}")
            return None
    
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
        try:
            with self.db_manager.get_connection() as conn:
                with conn.cursor() as cursor:
                    # Construir consulta com filtros
                    query = """
                    SELECT
                        a.id, a.equipment_id, a.timestamp, a.measurement_id, a.measurement_source,
                        a.description, a.gravity, a.criticality, a.status, a.assigned_to,
                        a.resolution_details, a.metadata, a.created_at, a.updated_at
                    FROM alerts a
                    """
                    
                    # Adicionar join com equipamentos se client_id for fornecido
                    if client_id:
                        query += " JOIN equipment e ON a.equipment_id = e.id"
                    
                    # Construir cláusula WHERE
                    conditions = []
                    params = []
                    
                    if equipment_id:
                        conditions.append("a.equipment_id = %s")
                        params.append(equipment_id)
                    
                    if client_id:
                        conditions.append("e.client_id = %s")
                        params.append(client_id)
                    
                    if status:
                        status_value = status.value if isinstance(status, AlertStatus) else status
                        conditions.append("a.status = %s")
                        params.append(status_value)
                    
                    if gravity:
                        gravity_value = gravity.value if isinstance(gravity, AlertGravity) else gravity
                        conditions.append("a.gravity = %s")
                        params.append(gravity_value)
                    
                    if criticality:
                        criticality_value = criticality.value if isinstance(criticality, AlertCriticality) else criticality
                        conditions.append("a.criticality = %s")
                        params.append(criticality_value)
                    
                    if assigned_to:
                        conditions.append("a.assigned_to = %s")
                        params.append(assigned_to)
                    
                    if start_date:
                        conditions.append("a.timestamp >= %s")
                        params.append(start_date)
                    
                    if end_date:
                        conditions.append("a.timestamp <= %s")
                        params.append(end_date)
                    
                    if conditions:
                        query += " WHERE " + " AND ".join(conditions)
                    
                    # Adicionar ordenação, limite e deslocamento
                    query += " ORDER BY a.timestamp DESC LIMIT %s OFFSET %s"
                    params.extend([limit, offset])
                    
                    cursor.execute(query, params)
                    
                    rows = cursor.fetchall()
                    
                    result = []
                    for row in rows:
                        result.append({
                            "id": row[0],
                            "equipment_id": row[1],
                            "timestamp": row[2],
                            "measurement_id": row[3],
                            "measurement_source": row[4],
                            "description": row[5],
                            "gravity": row[6],
                            "criticality": row[7],
                            "status": row[8],
                            "assigned_to": row[9],
                            "resolution_details": row[10],
                            "metadata": row[11],
                            "created_at": row[12],
                            "updated_at": row[13]
                        })
                    
                    return result
        except Exception as e:
            logger.error(f"Erro ao obter alertas: {e}")
            return []
    
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
        try:
            with self.db_manager.get_connection() as conn:
                with conn.cursor() as cursor:
                    # Construir consulta com filtros
                    query = "SELECT COUNT(*) FROM alerts a"
                    
                    # Adicionar join com equipamentos se client_id for fornecido
                    if client_id:
                        query += " JOIN equipment e ON a.equipment_id = e.id"
                    
                    # Construir cláusula WHERE
                    conditions = []
                    params = []
                    
                    if equipment_id:
                        conditions.append("a.equipment_id = %s")
                        params.append(equipment_id)
                    
                    if client_id:
                        conditions.append("e.client_id = %s")
                        params.append(client_id)
                    
                    if status:
                        status_value = status.value if isinstance(status, AlertStatus) else status
                        conditions.append("a.status = %s")
                        params.append(status_value)
                    
                    if gravity:
                        gravity_value = gravity.value if isinstance(gravity, AlertGravity) else gravity
                        conditions.append("a.gravity = %s")
                        params.append(gravity_value)
                    
                    if criticality:
                        criticality_value = criticality.value if isinstance(criticality, AlertCriticality) else criticality
                        conditions.append("a.criticality = %s")
                        params.append(criticality_value)
                    
                    if assigned_to:
                        conditions.append("a.assigned_to = %s")
                        params.append(assigned_to)
                    
                    if start_date:
                        conditions.append("a.timestamp >= %s")
                        params.append(start_date)
                    
                    if end_date:
                        conditions.append("a.timestamp <= %s")
                        params.append(end_date)
                    
                    if conditions:
                        query += " WHERE " + " AND ".join(conditions)
                    
                    cursor.execute(query, params)
                    
                    row = cursor.fetchone()
                    
                    return row[0] if row else 0
        except Exception as e:
            logger.error(f"Erro ao obter contagem de alertas: {e}")
            return 0
    
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
        try:
            with self.db_manager.get_connection() as conn:
                with conn.cursor() as cursor:
                    # Verificar se o alerta existe
                    cursor.execute(
                        "SELECT id FROM alerts WHERE id = %s",
                        (alert_id,)
                    )
                    
                    if not cursor.fetchone():
                        logger.warning(f"Alerta {alert_id} não encontrado")
                        return False
                    
                    # Atualizar status
                    cursor.execute(
                        """
                        UPDATE alerts
                        SET status = %s,
                            resolution_details = COALESCE(%s, resolution_details),
                            assigned_to = COALESCE(%s, assigned_to),
                            updated_at = NOW()
                        WHERE id = %s
                        """,
                        (status.value, resolution_details, assigned_to, alert_id)
                    )
                    
                    conn.commit()
                    return True
        except Exception as e:
            logger.error(f"Erro ao atualizar status do alerta {alert_id}: {e}")
            return False
    
    def delete_alert(self, alert_id: str) -> bool:
        """
        Exclui um alerta.
        
        Args:
            alert_id: ID do alerta
            
        Returns:
            bool: True se o alerta foi excluído com sucesso, False caso contrário
        """
        try:
            with self.db_manager.get_connection() as conn:
                with conn.cursor() as cursor:
                    # Verificar se o alerta existe
                    cursor.execute(
                        "SELECT id FROM alerts WHERE id = %s",
                        (alert_id,)
                    )
                    
                    if not cursor.fetchone():
                        logger.warning(f"Alerta {alert_id} não encontrado")
                        return False
                    
                    # Excluir alerta
                    cursor.execute(
                        "DELETE FROM alerts WHERE id = %s",
                        (alert_id,)
                    )
                    
                    conn.commit()
                    return True
        except Exception as e:
            logger.error(f"Erro ao excluir alerta {alert_id}: {e}")
            return False
    
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
        return self.get_alerts(
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
        return self.get_alerts(
            client_id=client_id,
            status=status,
            limit=limit,
            offset=offset
        )
    
    def initialize_schema(self):
        """
        Inicializa o esquema do banco de dados para alertas.
        """
        try:
            with self.db_manager.get_connection() as conn:
                with conn.cursor() as cursor:
                    # Criar tabela de alertas
                    cursor.execute(
                        """
                        CREATE TABLE IF NOT EXISTS alerts (
                            id VARCHAR(36) PRIMARY KEY,
                            equipment_id VARCHAR(36) NOT NULL,
                            timestamp TIMESTAMP NOT NULL,
                            measurement_id VARCHAR(36),
                            measurement_source VARCHAR(50),
                            description TEXT NOT NULL,
                            gravity VARCHAR(10) NOT NULL,
                            criticality VARCHAR(10) NOT NULL,
                            status VARCHAR(20) NOT NULL,
                            assigned_to VARCHAR(36),
                            resolution_details TEXT,
                            metadata JSONB,
                            created_at TIMESTAMP NOT NULL,
                            updated_at TIMESTAMP NOT NULL
                        )
                        """
                    )
                    
                    # Criar índices
                    cursor.execute(
                        """
                        CREATE INDEX IF NOT EXISTS idx_alerts_equipment_id ON alerts (equipment_id)
                        """
                    )
                    
                    cursor.execute(
                        """
                        CREATE INDEX IF NOT EXISTS idx_alerts_timestamp ON alerts (timestamp)
                        """
                    )
                    
                    cursor.execute(
                        """
                        CREATE INDEX IF NOT EXISTS idx_alerts_status ON alerts (status)
                        """
                    )
                    
                    cursor.execute(
                        """
                        CREATE INDEX IF NOT EXISTS idx_alerts_gravity ON alerts (gravity)
                        """
                    )
                    
                    cursor.execute(
                        """
                        CREATE INDEX IF NOT EXISTS idx_alerts_criticality ON alerts (criticality)
                        """
                    )
                    
                    cursor.execute(
                        """
                        CREATE INDEX IF NOT EXISTS idx_alerts_assigned_to ON alerts (assigned_to)
                        """
                    )
                    
                    # Adicionar restrição de chave estrangeira para equipamentos
                    cursor.execute(
                        """
                        DO $$
                        BEGIN
                            IF NOT EXISTS (
                                SELECT 1 FROM pg_constraint WHERE conname = 'fk_alerts_equipment_id'
                            ) THEN
                                ALTER TABLE alerts
                                ADD CONSTRAINT fk_alerts_equipment_id
                                FOREIGN KEY (equipment_id)
                                REFERENCES equipment (id)
                                ON DELETE CASCADE;
                            END IF;
                        END
                        $$;
                        """
                    )
                    
                    conn.commit()
                    logger.info("Esquema de alertas inicializado com sucesso")
        except Exception as e:
            logger.error(f"Erro ao inicializar esquema de alertas: {e}")
            raise
