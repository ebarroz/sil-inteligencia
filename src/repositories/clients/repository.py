"""
Client repository for the SIL Predictive System.

This module extends the database functionality to handle clients with machine history.
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime
import uuid

from ..models.clients.model import ClientBase, ClientStatus, ClientRiskLevel
from ..models.equipment.equipment import EquipmentBase, EquipmentStatus, TrackingStatus

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
    
    def get_client_equipment_history(
        self,
        client_id: str,
        equipment_id: Optional[str] = None,
        equipment_tag: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0
    ) -> Dict[str, Any]:
        """
        Obtém o histórico de máquinas de um cliente.
        
        Args:
            client_id: ID do cliente
            equipment_id: ID do equipamento específico (opcional)
            equipment_tag: TAG do equipamento específico (opcional)
            start_date: Data inicial para filtro (opcional)
            end_date: Data final para filtro (opcional)
            limit: Limite de resultados
            offset: Deslocamento para paginação
            
        Returns:
            Dicionário com cliente e histórico de máquinas
        """
        try:
            with self.db_manager.get_connection() as conn:
                with conn.cursor() as cursor:
                    # Obter informações do cliente
                    cursor.execute(
                        """
                        SELECT
                            c.id, c.name, c.document, c.status, c.risk_level,
                            c.address, c.contacts, c.custom_risk_parameters, c.metadata,
                            c.created_at, c.updated_at
                        FROM clients c
                        WHERE c.id = %s
                        """,
                        (client_id,)
                    )
                    
                    client_row = cursor.fetchone()
                    
                    if not client_row:
                        logger.warning(f"Cliente {client_id} não encontrado")
                        return {"client": None, "equipment": []}
                    
                    client = {
                        "id": client_row[0],
                        "name": client_row[1],
                        "document": client_row[2],
                        "status": client_row[3],
                        "risk_level": client_row[4],
                        "address": client_row[5],
                        "contacts": client_row[6],
                        "custom_risk_parameters": client_row[7],
                        "metadata": client_row[8],
                        "created_at": client_row[9],
                        "updated_at": client_row[10]
                    }
                    
                    # Construir consulta para equipamentos
                    query = """
                    SELECT
                        e.id, e.tag, e.name, e.type, e.model, e.manufacturer, e.serial_number,
                        e.installation_date, e.status, e.location, e.tracking_status,
                        e.last_maintenance_date, e.next_maintenance_date,
                        e.maintenance_history, e.measurement_history, e.metadata,
                        e.created_at, e.updated_at,
                        COUNT(DISTINCT a.id) as alert_count,
                        COUNT(DISTINCT CASE WHEN a.status IN ('NEW', 'ACKNOWLEDGED', 'IN_PROGRESS') THEN a.id END) as active_alert_count
                    FROM equipment e
                    LEFT JOIN alerts a ON a.equipment_id = e.id
                    WHERE e.client_id = %s
                    """
                    
                    # Construir cláusula WHERE adicional
                    conditions = ["e.client_id = %s"]
                    params = [client_id]
                    
                    if equipment_id:
                        conditions.append("e.id = %s")
                        params.append(equipment_id)
                    
                    if equipment_tag:
                        conditions.append("e.tag = %s")
                        params.append(equipment_tag)
                    
                    if start_date:
                        conditions.append("e.created_at >= %s")
                        params.append(start_date)
                    
                    if end_date:
                        conditions.append("e.created_at <= %s")
                        params.append(end_date)
                    
                    # Atualizar a consulta com as condições
                    query = """
                    SELECT
                        e.id, e.tag, e.name, e.type, e.model, e.manufacturer, e.serial_number,
                        e.installation_date, e.status, e.location, e.tracking_status,
                        e.last_maintenance_date, e.next_maintenance_date,
                        e.maintenance_history, e.measurement_history, e.metadata,
                        e.created_at, e.updated_at,
                        COUNT(DISTINCT a.id) as alert_count,
                        COUNT(DISTINCT CASE WHEN a.status IN ('NEW', 'ACKNOWLEDGED', 'IN_PROGRESS') THEN a.id END) as active_alert_count
                    FROM equipment e
                    LEFT JOIN alerts a ON a.equipment_id = e.id
                    WHERE """ + " AND ".join(conditions) + """
                    GROUP BY e.id
                    ORDER BY e.name
                    LIMIT %s OFFSET %s
                    """
                    
                    params.extend([limit, offset])
                    
                    cursor.execute(query, params)
                    
                    equipment_rows = cursor.fetchall()
                    
                    equipment = []
                    for row in equipment_rows:
                        equipment.append({
                            "id": row[0],
                            "tag": row[1],
                            "name": row[2],
                            "type": row[3],
                            "model": row[4],
                            "manufacturer": row[5],
                            "serial_number": row[6],
                            "installation_date": row[7],
                            "status": row[8],
                            "location": row[9],
                            "tracking_status": row[10],
                            "last_maintenance_date": row[11],
                            "next_maintenance_date": row[12],
                            "maintenance_history": row[13],
                            "measurement_history": row[14],
                            "metadata": row[15],
                            "created_at": row[16],
                            "updated_at": row[17],
                            "alert_count": row[18],
                            "active_alert_count": row[19]
                        })
                    
                    return {
                        "client": client,
                        "equipment": equipment
                    }
        except Exception as e:
            logger.error(f"Erro ao obter histórico de máquinas do cliente {client_id}: {e}")
            return {"client": None, "equipment": []}
    
    def get_clients_with_vulnerable_equipment(self) -> List[Dict[str, Any]]:
        """
        Obtém lista de clientes com equipamentos vulneráveis.
        
        Returns:
            Lista de clientes com equipamentos vulneráveis
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
                            COUNT(DISTINCT CASE WHEN e.tracking_status IN ('NOT_TRACKED', 'MINIMALLY_TRACKED') THEN e.id END) as vulnerable_equipment_count
                        FROM clients c
                        JOIN equipment e ON e.client_id = c.id
                        WHERE e.tracking_status IN ('NOT_TRACKED', 'MINIMALLY_TRACKED')
                        GROUP BY c.id
                        HAVING COUNT(DISTINCT CASE WHEN e.tracking_status IN ('NOT_TRACKED', 'MINIMALLY_TRACKED') THEN e.id END) > 0
                        ORDER BY vulnerable_equipment_count DESC
                        """
                    )
                    
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
                            "vulnerable_equipment_count": row[12]
                        })
                    
                    return result
        except Exception as e:
            logger.error(f"Erro ao obter clientes com equipamentos vulneráveis: {e}")
            return []

logger.info("Client repository defined.")
"""
