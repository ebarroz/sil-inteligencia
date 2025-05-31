"""
Client repository for the SIL Predictive System.

This module extends the database functionality to handle clients with machine history.
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime
import uuid

from ..models.clients.model import ClientBase, ClientStatus, ClientRiskLevel

# Configuração de logging
logger = logging.getLogger(__name__)

class ClientRepository:
    """Repositório para operações com clientes."""
    
    def __init__(self, db_manager):
        """
        Inicializa o repositório de clientes.
        
        Args:
            db_manager: Gerenciador de banco de dados
        """
        self.db_manager = db_manager
    
    def save_client(self, client: ClientBase) -> bool:
        """
        Salva um cliente no banco de dados.
        
        Args:
            client: Cliente a ser salvo
            
        Returns:
            bool: True se o cliente foi salvo com sucesso, False caso contrário
        """
        try:
            with self.db_manager.get_connection() as conn:
                with conn.cursor() as cursor:
                    # Verificar se o cliente já existe
                    cursor.execute(
                        """
                        SELECT id FROM clients WHERE id = %s
                        """,
                        (client.id,)
                    )
                    
                    exists = cursor.fetchone() is not None
                    
                    if exists:
                        # Atualizar cliente existente
                        cursor.execute(
                            """
                            UPDATE clients
                            SET name = %s,
                                document = %s,
                                status = %s,
                                risk_level = %s,
                                address = %s,
                                contacts = %s,
                                custom_risk_parameters = %s,
                                metadata = %s,
                                updated_at = NOW()
                            WHERE id = %s
                            """,
                            (
                                client.name,
                                client.document,
                                client.status.value,
                                client.risk_level.value,
                                client.address.dict(),
                                [contact.dict() for contact in client.contacts],
                                client.custom_risk_parameters,
                                client.metadata,
                                client.id
                            )
                        )
                    else:
                        # Inserir novo cliente
                        cursor.execute(
                            """
                            INSERT INTO clients (
                                id, name, document, status, risk_level,
                                address, contacts, custom_risk_parameters, metadata,
                                created_at, updated_at
                            ) VALUES (
                                %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW()
                            )
                            """,
                            (
                                client.id,
                                client.name,
                                client.document,
                                client.status.value,
                                client.risk_level.value,
                                client.address.dict(),
                                [contact.dict() for contact in client.contacts],
                                client.custom_risk_parameters,
                                client.metadata
                            )
                        )
                    
                    conn.commit()
                    return True
        except Exception as e:
            logger.error(f"Erro ao salvar cliente: {e}")
            return False
    
    def get_client_by_id(self, client_id: str) -> Optional[Dict[str, Any]]:
        """
        Obtém um cliente pelo ID.
        
        Args:
            client_id: ID do cliente
            
        Returns:
            Cliente ou None se não encontrado
        """
        try:
            with self.db_manager.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        SELECT
                            c.id, c.name, c.document, c.status, c.risk_level,
                            c.address, c.contacts, c.custom_risk_parameters, c.metadata,
                            c.created_at, c.updated_at,
                            COUNT(DISTINCT e.id) as equipment_count,
                            COUNT(DISTINCT CASE WHEN a.status IN ('NEW', 'ACKNOWLEDGED', 'IN_PROGRESS') THEN a.id END) as active_alerts_count
                        FROM clients c
                        LEFT JOIN equipment e ON e.client_id = c.id
                        LEFT JOIN alerts a ON a.equipment_id = e.id AND a.status IN ('NEW', 'ACKNOWLEDGED', 'IN_PROGRESS')
                        WHERE c.id = %s
                        GROUP BY c.id
                        """,
                        (client_id,)
                    )
                    
                    row = cursor.fetchone()
                    
                    if not row:
                        return None
                    
                    return {
                        "id": row[0],
                        "name": row[1],
                        "document": row[2],
                        "status": row[3],
                        "risk_level": row[4],
                        "address": row[5],
                        "contacts": row[6],
                        "custom_risk_parameters": row[7],
                        "metadata": row[8],
                        "created_at": row[9],
                        "updated_at": row[10],
                        "equipment_count": row[11],
                        "active_alerts_count": row[12]
                    }
        except Exception as e:
            logger.error(f"Erro ao obter cliente {client_id}: {e}")
            return None
    
    def get_clients(
        self,
        status: Optional[ClientStatus] = None,
        risk_level: Optional[ClientRiskLevel] = None,
        search_term: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Obtém lista de clientes com filtros.
        
        Args:
            status: Status do cliente (opcional)
            risk_level: Nível de risco do cliente (opcional)
            search_term: Termo de busca para nome ou documento (opcional)
            limit: Limite de resultados
            offset: Deslocamento para paginação
            
        Returns:
            Lista de clientes
        """
        try:
            with self.db_manager.get_connection() as conn:
                with conn.cursor() as cursor:
                    # Construir consulta com filtros
                    query = """
                    SELECT
                        c.id, c.name, c.document, c.status, c.risk_level,
                        c.address, c.contacts, c.custom_risk_parameters, c.metadata,
                        c.created_at, c.updated_at,
                        COUNT(DISTINCT e.id) as equipment_count,
                        COUNT(DISTINCT CASE WHEN a.status IN ('NEW', 'ACKNOWLEDGED', 'IN_PROGRESS') THEN a.id END) as active_alerts_count
                    FROM clients c
                    LEFT JOIN equipment e ON e.client_id = c.id
                    LEFT JOIN alerts a ON a.equipment_id = e.id AND a.status IN ('NEW', 'ACKNOWLEDGED', 'IN_PROGRESS')
                    """
                    
                    # Construir cláusula WHERE
                    conditions = []
                    params = []
                    
                    if status:
                        status_value = status.value if isinstance(status, ClientStatus) else status
                        conditions.append("c.status = %s")
                        params.append(status_value)
                    
                    if risk_level:
                        risk_level_value = risk_level.value if isinstance(risk_level, ClientRiskLevel) else risk_level
                        conditions.append("c.risk_level = %s")
                        params.append(risk_level_value)
                    
                    if search_term:
                        conditions.append("(c.name ILIKE %s OR c.document ILIKE %s)")
                        search_pattern = f"%{search_term}%"
                        params.extend([search_pattern, search_pattern])
                    
                    if conditions:
                        query += " WHERE " + " AND ".join(conditions)
                    
                    # Adicionar agrupamento, ordenação, limite e deslocamento
                    query += " GROUP BY c.id ORDER BY c.name LIMIT %s OFFSET %s"
                    params.extend([limit, offset])
                    
                    cursor.execute(query, params)
                    
                    rows = cursor.fetchall()
                    
                    result = []
                    for row in rows:
                        result.append({
                            "id": row[0],
                            "name": row[1],
                            "document": row[2],
                            "status": row[3],
                            "risk_level": row[4],
                            "address": row[5],
                            "contacts": row[6],
                            "custom_risk_parameters": row[7],
                            "metadata": row[8],
                            "created_at": row[9],
                            "updated_at": row[10],
                            "equipment_count": row[11],
                            "active_alerts_count": row[12]
                        })
                    
                    return result
        except Exception as e:
            logger.error(f"Erro ao obter clientes: {e}")
            return []
    
    def get_client_count(
        self,
        status: Optional[ClientStatus] = None,
        risk_level: Optional[ClientRiskLevel] = None,
        search_term: Optional[str] = None
    ) -> int:
        """
        Obtém contagem de clientes com filtros.
        
        Args:
            status: Status do cliente (opcional)
            risk_level: Nível de risco do cliente (opcional)
            search_term: Termo de busca para nome ou documento (opcional)
            
        Returns:
            Contagem de clientes
        """
        try:
            with self.db_manager.get_connection() as conn:
                with conn.cursor() as cursor:
                    # Construir consulta com filtros
                    query = "SELECT COUNT(*) FROM clients c"
                    
                    # Construir cláusula WHERE
                    conditions = []
                    params = []
                    
                    if status:
                        status_value = status.value if isinstance(status, ClientStatus) else status
                        conditions.append("c.status = %s")
                        params.append(status_value)
                    
                    if risk_level:
                        risk_level_value = risk_level.value if isinstance(risk_level, ClientRiskLevel) else risk_level
                        conditions.append("c.risk_level = %s")
                        params.append(risk_level_value)
                    
                    if search_term:
                        conditions.append("(c.name ILIKE %s OR c.document ILIKE %s)")
                        search_pattern = f"%{search_term}%"
                        params.extend([search_pattern, search_pattern])
                    
                    if conditions:
                        query += " WHERE " + " AND ".join(conditions)
                    
                    cursor.execute(query, params)
                    
                    row = cursor.fetchone()
                    
                    return row[0] if row else 0
        except Exception as e:
            logger.error(f"Erro ao obter contagem de clientes: {e}")
            return 0
    
    def update_client_status(
        self,
        client_id: str,
        status: ClientStatus
    ) -> bool:
        """
        Atualiza o status de um cliente.
        
        Args:
            client_id: ID do cliente
            status: Novo status
            
        Returns:
            bool: True se o cliente foi atualizado com sucesso, False caso contrário
        """
        try:
            with self.db_manager.get_connection() as conn:
                with conn.cursor() as cursor:
                    # Verificar se o cliente existe
                    cursor.execute(
                        "SELECT id FROM clients WHERE id = %s",
                        (client_id,)
                    )
                    
                    if not cursor.fetchone():
                        logger.warning(f"Cliente {client_id} não encontrado")
                        return False
                    
                    # Atualizar status
                    cursor.execute(
                        """
                        UPDATE clients
                        SET status = %s,
                            updated_at = NOW()
                        WHERE id = %s
                        """,
                        (status.value, client_id)
                    )
                    
                    conn.commit()
                    return True
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
            bool: True se o cliente foi atualizado com sucesso, False caso contrário
        """
        try:
            with self.db_manager.get_connection() as conn:
                with conn.cursor() as cursor:
                    # Verificar se o cliente existe
                    cursor.execute(
                        "SELECT id FROM clients WHERE id = %s",
                        (client_id,)
                    )
                    
                    if not cursor.fetchone():
                        logger.warning(f"Cliente {client_id} não encontrado")
                        return False
                    
                    # Atualizar nível de risco
                    if custom_risk_parameters is not None:
                        cursor.execute(
                            """
                            UPDATE clients
                            SET risk_level = %s,
                                custom_risk_parameters = %s,
                                updated_at = NOW()
                            WHERE id = %s
                            """,
                            (risk_level.value, custom_risk_parameters, client_id)
                        )
                    else:
                        cursor.execute(
                            """
                            UPDATE clients
                            SET risk_level = %s,
                                updated_at = NOW()
                            WHERE id = %s
                            """,
                            (risk_level.value, client_id)
                        )
                    
                    conn.commit()
                    return True
        except Exception as e:
            logger.error(f"Erro ao atualizar nível de risco do cliente {client_id}: {e}")
            return False
    
    def delete_client(self, client_id: str) -> bool:
        """
        Exclui um cliente.
        
        Args:
            client_id: ID do cliente
            
        Returns:
            bool: True se o cliente foi excluído com sucesso, False caso contrário
        """
        try:
            with self.db_manager.get_connection() as conn:
                with conn.cursor() as cursor:
                    # Verificar se o cliente existe
                    cursor.execute(
                        "SELECT id FROM clients WHERE id = %s",
                        (client_id,)
                    )
                    
                    if not cursor.fetchone():
                        logger.warning(f"Cliente {client_id} não encontrado")
                        return False
                    
                    # Excluir cliente
                    cursor.execute(
                        "DELETE FROM clients WHERE id = %s",
                        (client_id,)
                    )
                    
                    conn.commit()
                    return True
        except Exception as e:
            logger.error(f"Erro ao excluir cliente {client_id}: {e}")
            return False
    
    def get_client_equipment(
        self,
        client_id: str,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Obtém equipamentos de um cliente específico.
        
        Args:
            client_id: ID do cliente
            limit: Limite de resultados
            offset: Deslocamento para paginação
            
        Returns:
            Lista de equipamentos
        """
        try:
            with self.db_manager.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        SELECT
                            e.id, e.tag, e.name, e.type, e.status,
                            e.location, e.metadata, e.created_at, e.updated_at,
                            COUNT(DISTINCT CASE WHEN a.status IN ('NEW', 'ACKNOWLEDGED', 'IN_PROGRESS') THEN a.id END) as active_alerts_count
                        FROM equipment e
                        LEFT JOIN alerts a ON a.equipment_id = e.id AND a.status IN ('NEW', 'ACKNOWLEDGED', 'IN_PROGRESS')
                        WHERE e.client_id = %s
                        GROUP BY e.id
                        ORDER BY e.name
                        LIMIT %s OFFSET %s
                        """,
                        (client_id, limit, offset)
                    )
                    
                    rows = cursor.fetchall()
                    
                    result = []
                    for row in rows:
                        result.append({
                            "id": row[0],
                            "tag": row[1],
                            "name": row[2],
                            "type": row[3],
                            "status": row[4],
                            "location": row[5],
                            "metadata": row[6],
                            "created_at": row[7],
                            "updated_at": row[8],
                            "active_alerts_count": row[9]
                        })
                    
                    return result
        except Exception as e:
            logger.error(f"Erro ao obter equipamentos do cliente {client_id}: {e}")
            return []
    
    def get_client_equipment_count(self, client_id: str) -> int:
        """
        Obtém contagem de equipamentos de um cliente específico.
        
        Args:
            client_id: ID do cliente
            
        Returns:
            Contagem de equipamentos
        """
        try:
            with self.db_manager.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        SELECT COUNT(*)
                        FROM equipment
                        WHERE client_id = %s
                        """,
                        (client_id,)
                    )
                    
                    row = cursor.fetchone()
                    
                    return row[0] if row else 0
        except Exception as e:
            logger.error(f"Erro ao obter contagem de equipamentos do cliente {client_id}: {e}")
            return 0
    
    def get_client_alerts(
        self,
        client_id: str,
        status: Optional[str] = None,
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
        try:
            with self.db_manager.get_connection() as conn:
                with conn.cursor() as cursor:
                    # Construir consulta com filtros
                    query = """
                    SELECT
                        a.id, a.equipment_id, a.timestamp, a.measurement_id, a.measurement_source,
                        a.description, a.gravity, a.criticality, a.status, a.assigned_to,
                        a.resolution_details, a.metadata, a.created_at, a.updated_at,
                        e.tag, e.name
                    FROM alerts a
                    JOIN equipment e ON a.equipment_id = e.id
                    WHERE e.client_id = %s
                    """
                    
                    params = [client_id]
                    
                    if status:
                        query += " AND a.status = %s"
                        params.append(status)
                    
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
                            "updated_at": row[13],
                            "equipment_tag": row[14],
                            "equipment_name": row[15]
                        })
                    
                    return result
        except Exception as e:
            logger.error(f"Erro ao obter alertas do cliente {client_id}: {e}")
            return []
    
    def get_client_alerts_count(
        self,
        client_id: str,
        status: Optional[str] = None
    ) -> int:
        """
        Obtém contagem de alertas de um cliente específico.
        
        Args:
            client_id: ID do cliente
            status: Status do alerta (opcional)
            
        Returns:
            Contagem de alertas
        """
        try:
            with self.db_manager.get_connection() as conn:
                with conn.cursor() as cursor:
                    # Construir consulta com filtros
                    query = """
                    SELECT COUNT(*)
                    FROM alerts a
                    JOIN equipment e ON a.equipment_id = e.id
                    WHERE e.client_id = %s
                    """
                    
                    params = [client_id]
                    
                    if status:
                        query += " AND a.status = %s"
                        params.append(status)
                    
                    cursor.execute(query, params)
                    
                    row = cursor.fetchone()
                    
                    return row[0] if row else 0
        except Exception as e:
            logger.error(f"Erro ao obter contagem de alertas do cliente {client_id}: {e}")
            return 0
    
    def initialize_schema(self):
        """
        Inicializa o esquema do banco de dados para clientes.
        """
        try:
            with self.db_manager.get_connection() as conn:
                with conn.cursor() as cursor:
                    # Criar tabela de clientes
                    cursor.execute(
                        """
                        CREATE TABLE IF NOT EXISTS clients (
                            id VARCHAR(36) PRIMARY KEY,
                            name VARCHAR(255) NOT NULL,
                            document VARCHAR(50) NOT NULL,
                            status VARCHAR(20) NOT NULL,
                            risk_level VARCHAR(20) NOT NULL,
                            address JSONB NOT NULL,
                            contacts JSONB NOT NULL,
                            custom_risk_parameters JSONB,
                            metadata JSONB,
                            created_at TIMESTAMP NOT NULL,
                            updated_at TIMESTAMP NOT NULL
                        )
                        """
                    )
                    
                    # Criar índices
                    cursor.execute(
                        """
                        CREATE INDEX IF NOT EXISTS idx_clients_name ON clients (name)
                        """
                    )
                    
                    cursor.execute(
                        """
                        CREATE INDEX IF NOT EXISTS idx_clients_document ON clients (document)
                        """
                    )
                    
                    cursor.execute(
                        """
                        CREATE INDEX IF NOT EXISTS idx_clients_status ON clients (status)
                        """
                    )
                    
                    cursor.execute(
                        """
                        CREATE INDEX IF NOT EXISTS idx_clients_risk_level ON clients (risk_level)
                        """
                    )
                    
                    conn.commit()
                    logger.info("Esquema de clientes inicializado com sucesso")
        except Exception as e:
            logger.error(f"Erro ao inicializar esquema de clientes: {e}")
            raise
