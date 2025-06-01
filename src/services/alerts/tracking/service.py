"""
Alert tracking service for the SIL Predictive System.

This module implements map and list views for tracking alerts.
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import json
import uuid

# Configuração de logging
logger = logging.getLogger(__name__)

class AlertTrackingService:
    """Serviço para rastreamento de alertas por mapa e lista."""
    
    def __init__(self, db_manager):
        """
        Inicializa o serviço de rastreamento de alertas.
        
        Args:
            db_manager: Gerenciador de banco de dados
        """
        self.db_manager = db_manager
        logger.info("Serviço de rastreamento de alertas inicializado")
    
    def get_alerts_for_map(
        self,
        client_id: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        gravity: Optional[List[str]] = None,
        status: Optional[List[str]] = None,
        include_false_positives: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Obtém alertas com informações de localização para exibição em mapa.
        
        Args:
            client_id: ID do cliente (opcional)
            start_date: Data inicial (opcional)
            end_date: Data final (opcional)
            gravity: Lista de gravidades para filtrar (opcional)
            status: Lista de status para filtrar (opcional)
            include_false_positives: Se deve incluir falsos positivos
            
        Returns:
            Lista de alertas com informações de localização
        """
        try:
            with self.db_manager.get_connection() as conn:
                with conn.cursor() as cursor:
                    # Construir consulta base
                    query = """
                    SELECT
                        a.id, a.equipment_id, a.timestamp, a.description,
                        a.gravity, a.criticality, a.status,
                        e.name as equipment_name, e.tag as equipment_tag,
                        e.location as equipment_location,
                        c.id as client_id, c.name as client_name,
                        c.address->>'latitude' as latitude,
                        c.address->>'longitude' as longitude
                    FROM alerts a
                    JOIN equipment e ON a.equipment_id = e.id
                    JOIN clients c ON e.client_id = c.id
                    WHERE (c.address->>'latitude' IS NOT NULL AND c.address->>'longitude' IS NOT NULL)
                    """
                    
                    # Construir cláusulas WHERE
                    params = []
                    
                    if client_id:
                        query += " AND c.id = %s"
                        params.append(client_id)
                    
                    if start_date:
                        query += " AND a.timestamp >= %s"
                        params.append(start_date)
                    
                    if end_date:
                        query += " AND a.timestamp <= %s"
                        params.append(end_date)
                    
                    if gravity and len(gravity) > 0:
                        placeholders = ",".join(["%s"] * len(gravity))
                        query += f" AND a.gravity IN ({placeholders})"
                        params.extend(gravity)
                    
                    if status and len(status) > 0:
                        placeholders = ",".join(["%s"] * len(status))
                        query += f" AND a.status IN ({placeholders})"
                        params.extend(status)
                    
                    if not include_false_positives:
                        query += " AND (a.is_valid = TRUE OR a.is_valid IS NULL)"
                    
                    # Adicionar ordenação
                    query += " ORDER BY a.timestamp DESC"
                    
                    cursor.execute(query, params)
                    
                    alerts = []
                    for row in cursor.fetchall():
                        try:
                            latitude = float(row[12]) if row[12] else None
                            longitude = float(row[13]) if row[13] else None
                        except (ValueError, TypeError):
                            latitude = None
                            longitude = None
                        
                        if latitude is not None and longitude is not None:
                            alerts.append({
                                "id": row[0],
                                "equipment_id": row[1],
                                "timestamp": row[2],
                                "description": row[3],
                                "gravity": row[4],
                                "criticality": row[5],
                                "status": row[6],
                                "equipment_name": row[7],
                                "equipment_tag": row[8],
                                "equipment_location": row[9],
                                "client_id": row[10],
                                "client_name": row[11],
                                "location": {
                                    "latitude": latitude,
                                    "longitude": longitude
                                }
                            })
                    
                    return alerts
        except Exception as e:
            logger.error(f"Erro ao obter alertas para mapa: {e}")
            return []
    
    def get_alerts_for_list(
        self,
        client_id: Optional[str] = None,
        equipment_id: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        gravity: Optional[List[str]] = None,
        status: Optional[List[str]] = None,
        include_false_positives: bool = False,
        sort_by: str = "timestamp",
        sort_order: str = "desc",
        limit: int = 100,
        offset: int = 0
    ) -> Dict[str, Any]:
        """
        Obtém alertas para exibição em lista com paginação e ordenação.
        
        Args:
            client_id: ID do cliente (opcional)
            equipment_id: ID do equipamento (opcional)
            start_date: Data inicial (opcional)
            end_date: Data final (opcional)
            gravity: Lista de gravidades para filtrar (opcional)
            status: Lista de status para filtrar (opcional)
            include_false_positives: Se deve incluir falsos positivos
            sort_by: Campo para ordenação
            sort_order: Ordem de classificação (asc/desc)
            limit: Limite de resultados
            offset: Deslocamento para paginação
            
        Returns:
            Dicionário com alertas e informações de paginação
        """
        try:
            with self.db_manager.get_connection() as conn:
                with conn.cursor() as cursor:
                    # Validar parâmetros de ordenação
                    valid_sort_fields = ["timestamp", "gravity", "status", "equipment_name", "client_name"]
                    if sort_by not in valid_sort_fields:
                        sort_by = "timestamp"
                    
                    sort_order = sort_order.lower()
                    if sort_order not in ["asc", "desc"]:
                        sort_order = "desc"
                    
                    # Construir consulta base
                    query = """
                    SELECT
                        a.id, a.equipment_id, a.timestamp, a.measurement_id,
                        a.measurement_source, a.description, a.gravity,
                        a.criticality, a.status, a.assigned_to,
                        a.resolution_details, a.is_valid, a.filter_result,
                        e.name as equipment_name, e.tag as equipment_tag,
                        e.location as equipment_location,
                        c.id as client_id, c.name as client_name
                    FROM alerts a
                    JOIN equipment e ON a.equipment_id = e.id
                    JOIN clients c ON e.client_id = c.id
                    WHERE 1=1
                    """
                    
                    # Construir cláusulas WHERE
                    params = []
                    
                    if client_id:
                        query += " AND c.id = %s"
                        params.append(client_id)
                    
                    if equipment_id:
                        query += " AND e.id = %s"
                        params.append(equipment_id)
                    
                    if start_date:
                        query += " AND a.timestamp >= %s"
                        params.append(start_date)
                    
                    if end_date:
                        query += " AND a.timestamp <= %s"
                        params.append(end_date)
                    
                    if gravity and len(gravity) > 0:
                        placeholders = ",".join(["%s"] * len(gravity))
                        query += f" AND a.gravity IN ({placeholders})"
                        params.extend(gravity)
                    
                    if status and len(status) > 0:
                        placeholders = ",".join(["%s"] * len(status))
                        query += f" AND a.status IN ({placeholders})"
                        params.extend(status)
                    
                    if not include_false_positives:
                        query += " AND (a.is_valid = TRUE OR a.is_valid IS NULL)"
                    
                    # Consulta para contagem total
                    count_query = f"""
                    SELECT COUNT(*)
                    FROM ({query}) as subquery
                    """
                    
                    cursor.execute(count_query, params)
                    total_count = cursor.fetchone()[0]
                    
                    # Adicionar ordenação, limite e deslocamento
                    sort_field_map = {
                        "timestamp": "a.timestamp",
                        "gravity": "a.gravity",
                        "status": "a.status",
                        "equipment_name": "e.name",
                        "client_name": "c.name"
                    }
                    
                    query += f" ORDER BY {sort_field_map[sort_by]} {sort_order.upper()}"
                    query += " LIMIT %s OFFSET %s"
                    params.extend([limit, offset])
                    
                    cursor.execute(query, params)
                    
                    alerts = []
                    for row in cursor.fetchall():
                        alerts.append({
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
                            "is_valid": row[11],
                            "filter_result": row[12],
                            "equipment_name": row[13],
                            "equipment_tag": row[14],
                            "equipment_location": row[15],
                            "client_id": row[16],
                            "client_name": row[17]
                        })
                    
                    # Calcular informações de paginação
                    total_pages = (total_count + limit - 1) // limit if limit > 0 else 1
                    current_page = (offset // limit) + 1 if limit > 0 else 1
                    
                    return {
                        "alerts": alerts,
                        "pagination": {
                            "total_count": total_count,
                            "total_pages": total_pages,
                            "current_page": current_page,
                            "limit": limit,
                            "offset": offset
                        }
                    }
        except Exception as e:
            logger.error(f"Erro ao obter alertas para lista: {e}")
            return {"alerts": [], "pagination": {"total_count": 0, "total_pages": 0, "current_page": 1, "limit": limit, "offset": offset}}
    
    def get_alert_clusters(
        self,
        client_id: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        min_cluster_size: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Obtém clusters de alertas para visualização em mapa.
        
        Args:
            client_id: ID do cliente (opcional)
            start_date: Data inicial (opcional)
            end_date: Data final (opcional)
            min_cluster_size: Tamanho mínimo para considerar um cluster
            
        Returns:
            Lista de clusters de alertas
        """
        try:
            # Obter alertas para mapa
            alerts = self.get_alerts_for_map(
                client_id=client_id,
                start_date=start_date,
                end_date=end_date,
                include_false_positives=False
            )
            
            if not alerts:
                return []
            
            # Agrupar alertas por localização (arredondando coordenadas para criar clusters)
            clusters = {}
            for alert in alerts:
                lat = alert["location"]["latitude"]
                lng = alert["location"]["longitude"]
                
                # Arredondar para 2 casas decimais (aproximadamente 1.1km de precisão)
                cluster_key = f"{round(lat, 2)},{round(lng, 2)}"
                
                if cluster_key not in clusters:
                    clusters[cluster_key] = {
                        "center": {"latitude": lat, "longitude": lng},
                        "alerts": []
                    }
                
                clusters[cluster_key]["alerts"].append(alert)
            
            # Filtrar clusters com tamanho mínimo
            result = []
            for key, cluster in clusters.items():
                if len(cluster["alerts"]) >= min_cluster_size:
                    # Calcular centro real do cluster (média das coordenadas)
                    lats = [a["location"]["latitude"] for a in cluster["alerts"]]
                    lngs = [a["location"]["longitude"] for a in cluster["alerts"]]
                    center_lat = sum(lats) / len(lats)
                    center_lng = sum(lngs) / len(lngs)
                    
                    # Contar alertas por gravidade
                    gravity_counts = {}
                    for alert in cluster["alerts"]:
                        gravity = alert["gravity"]
                        if gravity not in gravity_counts:
                            gravity_counts[gravity] = 0
                        gravity_counts[gravity] += 1
                    
                    result.append({
                        "id": str(uuid.uuid4()),
                        "center": {"latitude": center_lat, "longitude": center_lng},
                        "alert_count": len(cluster["alerts"]),
                        "gravity_counts": gravity_counts,
                        "alerts": [a["id"] for a in cluster["alerts"]],
                        "clients": list(set([a["client_id"] for a in cluster["alerts"]]))
                    })
            
            # Ordenar por contagem de alertas (decrescente)
            result.sort(key=lambda x: x["alert_count"], reverse=True)
            
            return result
        except Exception as e:
            logger.error(f"Erro ao obter clusters de alertas: {e}")
            return []
    
    def get_alert_summary_by_client(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """
        Obtém resumo de alertas agrupados por cliente.
        
        Args:
            start_date: Data inicial (opcional)
            end_date: Data final (opcional)
            
        Returns:
            Lista de resumos de alertas por cliente
        """
        try:
            with self.db_manager.get_connection() as conn:
                with conn.cursor() as cursor:
                    # Construir consulta base
                    query = """
                    SELECT
                        c.id as client_id,
                        c.name as client_name,
                        COUNT(a.id) as total_alerts,
                        COUNT(CASE WHEN a.gravity = 'P1' THEN 1 END) as p1_count,
                        COUNT(CASE WHEN a.gravity = 'P2' THEN 1 END) as p2_count,
                        COUNT(CASE WHEN a.gravity = 'P3' THEN 1 END) as p3_count,
                        COUNT(CASE WHEN a.gravity = 'P4' THEN 1 END) as p4_count,
                        COUNT(CASE WHEN a.status = 'NEW' THEN 1 END) as new_count,
                        COUNT(CASE WHEN a.status = 'ACKNOWLEDGED' THEN 1 END) as acknowledged_count,
                        COUNT(CASE WHEN a.status = 'IN_PROGRESS' THEN 1 END) as in_progress_count,
                        COUNT(CASE WHEN a.status = 'RESOLVED' THEN 1 END) as resolved_count,
                        COUNT(CASE WHEN a.status = 'FALSE_POSITIVE' THEN 1 END) as false_positive_count,
                        c.address->>'latitude' as latitude,
                        c.address->>'longitude' as longitude
                    FROM clients c
                    LEFT JOIN equipment e ON e.client_id = c.id
                    LEFT JOIN alerts a ON a.equipment_id = e.id
                    """
                    
                    # Construir cláusulas WHERE
                    params = []
                    where_clauses = []
                    
                    if start_date:
                        where_clauses.append("a.timestamp >= %s")
                        params.append(start_date)
                    
                    if end_date:
                        where_clauses.append("a.timestamp <= %s")
                        params.append(end_date)
                    
                    if where_clauses:
                        query += " WHERE " + " AND ".join(where_clauses)
                    
                    # Adicionar agrupamento e ordenação
                    query += " GROUP BY c.id, c.name, c.address->>'latitude', c.address->>'longitude'"
                    query += " ORDER BY total_alerts DESC"
                    
                    cursor.execute(query, params)
                    
                    summaries = []
                    for row in cursor.fetchall():
                        try:
                            latitude = float(row[12]) if row[12] else None
                            longitude = float(row[13]) if row[13] else None
                        except (ValueError, TypeError):
                            latitude = None
                            longitude = None
                        
                        location = None
                        if latitude is not None and longitude is not None:
                            location = {"latitude": latitude, "longitude": longitude}
                        
                        summaries.append({
                            "client_id": row[0],
                            "client_name": row[1],
                            "total_alerts": row[2],
                            "gravity_counts": {
                                "P1": row[3],
                                "P2": row[4],
                                "P3": row[5],
                                "P4": row[6]
                            },
                            "status_counts": {
                                "NEW": row[7],
                                "ACKNOWLEDGED": row[8],
                                "IN_PROGRESS": row[9],
                                "RESOLVED": row[10],
                                "FALSE_POSITIVE": row[11]
                            },
                            "location": location
                        })
                    
                    return summaries
        except Exception as e:
            logger.error(f"Erro ao obter resumo de alertas por cliente: {e}")
            return []
    
    def get_alert_timeline(
        self,
        client_id: Optional[str] = None,
        equipment_id: Optional[str] = None,
        days: int = 30,
        interval: str = "day"
    ) -> Dict[str, Any]:
        """
        Obtém dados de linha do tempo de alertas para visualização.
        
        Args:
            client_id: ID do cliente (opcional)
            equipment_id: ID do equipamento (opcional)
            days: Número de dias para incluir
            interval: Intervalo de agrupamento ('hour', 'day', 'week', 'month')
            
        Returns:
            Dados de linha do tempo de alertas
        """
        try:
            # Validar intervalo
            valid_intervals = ["hour", "day", "week", "month"]
            if interval not in valid_intervals:
                interval = "day"
            
            # Mapear intervalo para formato PostgreSQL
            interval_format = {
                "hour": "YYYY-MM-DD HH24",
                "day": "YYYY-MM-DD",
                "week": "YYYY-WW",
                "month": "YYYY-MM"
            }
            
            with self.db_manager.get_connection() as conn:
                with conn.cursor() as cursor:
                    # Construir consulta base
                    query = """
                    SELECT
                        TO_CHAR(a.timestamp, %s) as time_bucket,
                        COUNT(a.id) as total_alerts,
                        COUNT(CASE WHEN a.gravity = 'P1' THEN 1 END) as p1_count,
                        COUNT(CASE WHEN a.gravity = 'P2' THEN 1 END) as p2_count,
                        COUNT(CASE WHEN a.gravity = 'P3' THEN 1 END) as p3_count,
                        COUNT(CASE WHEN a.gravity = 'P4' THEN 1 END) as p4_count
                    FROM alerts a
                    JOIN equipment e ON a.equipment_id = e.id
                    JOIN clients c ON e.client_id = c.id
                    WHERE a.timestamp >= %s
                    """
                    
                    # Parâmetros base
                    params = [interval_format[interval], datetime.now() - timedelta(days=days)]
                    
                    # Adicionar filtros
                    if client_id:
                        query += " AND c.id = %s"
                        params.append(client_id)
                    
                    if equipment_id:
                        query += " AND e.id = %s"
                        params.append(equipment_id)
                    
                    # Adicionar agrupamento e ordenação
                    query += " GROUP BY time_bucket ORDER BY time_bucket"
                    
                    cursor.execute(query, params)
                    
                    timeline_data = []
                    for row in cursor.fetchall():
                        timeline_data.append({
                            "time_bucket": row[0],
                            "total_alerts": row[1],
                            "gravity_counts": {
                                "P1": row[2],
                                "P2": row[3],
                                "P3": row[4],
                                "P4": row[5]
                            }
                        })
                    
                    return {
                        "interval": interval,
                        "days": days,
                        "data": timeline_data
                    }
        except Exception as e:
            logger.error(f"Erro ao obter linha do tempo de alertas: {e}")
            return {"interval": interval, "days": days, "data": []}

logger.info("Alert tracking service defined.")
"""
