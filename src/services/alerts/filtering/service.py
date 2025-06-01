"""
Alarm filtering service for the SIL Predictive System.

This module implements logic to filter false alarms and prioritize valid ones.
"""

import logging
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, timedelta
import uuid
from collections import defaultdict

from ..models.alerts.model import AlertBase, AlertGravity, AlertStatus, AlertCriticality
from ..models.equipment.equipment import EquipmentBase, TrackingStatus

# Configuração de logging
logger = logging.getLogger(__name__)

class AlarmFilteringService:
    """Serviço para filtragem de alarmes falsos e priorização de alarmes válidos."""
    
    def __init__(self, db_manager):
        """
        Inicializa o serviço de filtragem de alarmes.
        
        Args:
            db_manager: Gerenciador de banco de dados
        """
        self.db_manager = db_manager
        logger.info("Serviço de filtragem de alarmes inicializado")
    
    def filter_alarm(self, alert: AlertBase) -> Tuple[bool, Dict[str, Any]]:
        """
        Filtra um alarme para determinar se é válido ou falso.
        
        Args:
            alert: Alerta a ser filtrado
            
        Returns:
            Tupla com (is_valid, filter_result)
        """
        try:
            # Obter informações do equipamento
            equipment = self._get_equipment_info(alert.equipment_id)
            if not equipment:
                logger.warning(f"Equipamento {alert.equipment_id} não encontrado para alerta {alert.id}")
                return False, {"reason": "Equipamento não encontrado", "confidence": 1.0}
            
            # Obter histórico recente de alertas do equipamento
            recent_alerts = self._get_recent_alerts(alert.equipment_id, alert.id, hours=24)
            
            # Obter medições recentes do equipamento
            recent_measurements = self._get_recent_measurements(alert.equipment_id, hours=24)
            
            # Aplicar regras de filtragem
            filter_result = self._apply_filter_rules(alert, equipment, recent_alerts, recent_measurements)
            
            # Determinar se o alerta é válido com base no resultado da filtragem
            is_valid = filter_result["confidence"] < 0.7  # Se a confiança de que é falso for menor que 70%, consideramos válido
            
            # Registrar resultado da filtragem
            self._log_filter_result(alert.id, is_valid, filter_result)
            
            return is_valid, filter_result
        except Exception as e:
            logger.error(f"Erro ao filtrar alerta {alert.id}: {e}")
            # Em caso de erro, consideramos o alerta como válido para evitar perder alertas importantes
            return True, {"reason": f"Erro na filtragem: {str(e)}", "confidence": 0.0}
    
    def filter_alerts_batch(self, alerts: List[AlertBase]) -> List[Tuple[AlertBase, bool, Dict[str, Any]]]:
        """
        Filtra um lote de alertas.
        
        Args:
            alerts: Lista de alertas a serem filtrados
            
        Returns:
            Lista de tuplas (alerta, is_valid, filter_result)
        """
        results = []
        
        # Agrupar alertas por equipamento para otimizar consultas
        equipment_alerts = defaultdict(list)
        for alert in alerts:
            equipment_alerts[alert.equipment_id].append(alert)
        
        # Processar alertas por equipamento
        for equipment_id, equipment_alerts_list in equipment_alerts.items():
            # Obter informações do equipamento uma única vez
            equipment = self._get_equipment_info(equipment_id)
            if not equipment:
                logger.warning(f"Equipamento {equipment_id} não encontrado")
                # Marcar todos os alertas deste equipamento como válidos (para evitar perder alertas importantes)
                for alert in equipment_alerts_list:
                    results.append((alert, True, {"reason": "Equipamento não encontrado", "confidence": 0.0}))
                continue
            
            # Obter histórico recente de alertas do equipamento
            all_recent_alerts = self._get_recent_alerts(equipment_id, None, hours=24)
            
            # Obter medições recentes do equipamento
            recent_measurements = self._get_recent_measurements(equipment_id, hours=24)
            
            # Processar cada alerta deste equipamento
            for alert in equipment_alerts_list:
                # Filtrar alertas recentes para excluir o alerta atual
                recent_alerts = [a for a in all_recent_alerts if a["id"] != alert.id]
                
                # Aplicar regras de filtragem
                filter_result = self._apply_filter_rules(alert, equipment, recent_alerts, recent_measurements)
                
                # Determinar se o alerta é válido com base no resultado da filtragem
                is_valid = filter_result["confidence"] < 0.7
                
                # Registrar resultado da filtragem
                self._log_filter_result(alert.id, is_valid, filter_result)
                
                results.append((alert, is_valid, filter_result))
        
        return results
    
    def _get_equipment_info(self, equipment_id: str) -> Optional[Dict[str, Any]]:
        """
        Obtém informações do equipamento.
        
        Args:
            equipment_id: ID do equipamento
            
        Returns:
            Informações do equipamento ou None se não encontrado
        """
        try:
            with self.db_manager.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        SELECT
                            id, tag, name, type, model, manufacturer,
                            status, tracking_status, client_id
                        FROM equipment
                        WHERE id = %s
                        """,
                        (equipment_id,)
                    )
                    
                    row = cursor.fetchone()
                    if not row:
                        return None
                    
                    return {
                        "id": row[0],
                        "tag": row[1],
                        "name": row[2],
                        "type": row[3],
                        "model": row[4],
                        "manufacturer": row[5],
                        "status": row[6],
                        "tracking_status": row[7],
                        "client_id": row[8]
                    }
        except Exception as e:
            logger.error(f"Erro ao obter informações do equipamento {equipment_id}: {e}")
            return None
    
    def _get_recent_alerts(
        self,
        equipment_id: str,
        exclude_alert_id: Optional[str] = None,
        hours: int = 24
    ) -> List[Dict[str, Any]]:
        """
        Obtém alertas recentes de um equipamento.
        
        Args:
            equipment_id: ID do equipamento
            exclude_alert_id: ID do alerta a ser excluído (opcional)
            hours: Número de horas para considerar
            
        Returns:
            Lista de alertas recentes
        """
        try:
            with self.db_manager.get_connection() as conn:
                with conn.cursor() as cursor:
                    query = """
                    SELECT
                        id, timestamp, measurement_id, measurement_source,
                        description, gravity, criticality, status
                    FROM alerts
                    WHERE equipment_id = %s
                    AND timestamp >= %s
                    """
                    
                    params = [equipment_id, datetime.now() - timedelta(hours=hours)]
                    
                    if exclude_alert_id:
                        query += " AND id != %s"
                        params.append(exclude_alert_id)
                    
                    query += " ORDER BY timestamp DESC"
                    
                    cursor.execute(query, params)
                    
                    alerts = []
                    for row in cursor.fetchall():
                        alerts.append({
                            "id": row[0],
                            "timestamp": row[1],
                            "measurement_id": row[2],
                            "measurement_source": row[3],
                            "description": row[4],
                            "gravity": row[5],
                            "criticality": row[6],
                            "status": row[7]
                        })
                    
                    return alerts
        except Exception as e:
            logger.error(f"Erro ao obter alertas recentes do equipamento {equipment_id}: {e}")
            return []
    
    def _get_recent_measurements(
        self,
        equipment_id: str,
        hours: int = 24
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Obtém medições recentes de um equipamento.
        
        Args:
            equipment_id: ID do equipamento
            hours: Número de horas para considerar
            
        Returns:
            Dicionário com medições recentes agrupadas por fonte
        """
        try:
            with self.db_manager.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        SELECT measurement_history
                        FROM equipment
                        WHERE id = %s
                        """,
                        (equipment_id,)
                    )
                    
                    row = cursor.fetchone()
                    if not row or not row[0]:
                        return {}
                    
                    measurement_history = row[0]
                    
                    # Filtrar por período e agrupar por fonte
                    cutoff_time = datetime.now() - timedelta(hours=hours)
                    recent_measurements = defaultdict(list)
                    
                    for record in measurement_history:
                        record_time = datetime.fromisoformat(record["timestamp"])
                        if record_time >= cutoff_time:
                            source = record["source"]
                            recent_measurements[source].append(record)
                    
                    return dict(recent_measurements)
        except Exception as e:
            logger.error(f"Erro ao obter medições recentes do equipamento {equipment_id}: {e}")
            return {}
    
    def _apply_filter_rules(
        self,
        alert: AlertBase,
        equipment: Dict[str, Any],
        recent_alerts: List[Dict[str, Any]],
        recent_measurements: Dict[str, List[Dict[str, Any]]]
    ) -> Dict[str, Any]:
        """
        Aplica regras de filtragem para determinar se um alerta é falso.
        
        Args:
            alert: Alerta a ser filtrado
            equipment: Informações do equipamento
            recent_alerts: Alertas recentes do equipamento
            recent_measurements: Medições recentes do equipamento
            
        Returns:
            Resultado da filtragem
        """
        # Inicializar resultado
        result = {
            "is_false_positive": False,
            "confidence": 0.0,
            "reason": "",
            "rules_applied": []
        }
        
        # Regra 1: Verificar duplicação de alertas recentes (mesmo tipo/descrição)
        duplicate_alerts = [a for a in recent_alerts if a["description"] == alert.description]
        if duplicate_alerts:
            # Se houver alertas duplicados recentes, aumentar a confiança de que é falso
            duplicate_count = len(duplicate_alerts)
            if duplicate_count >= 3:
                result["rules_applied"].append({
                    "rule": "duplicate_alerts",
                    "description": f"Alerta duplicado {duplicate_count} vezes nas últimas 24 horas",
                    "confidence": 0.8
                })
                result["confidence"] = max(result["confidence"], 0.8)
                result["reason"] = "Alerta duplicado múltiplas vezes"
        
        # Regra 2: Verificar se há medições recentes que contradizem o alerta
        if alert.measurement_source and alert.measurement_source in recent_measurements:
            source_measurements = recent_measurements[alert.measurement_source]
            
            # Verificar se há medições normais após a medição que gerou o alerta
            if alert.measurement_id:
                # Encontrar a medição que gerou o alerta
                alert_measurement = None
                for measurement in source_measurements:
                    if measurement["id"] == alert.measurement_id:
                        alert_measurement = measurement
                        break
                
                if alert_measurement:
                    alert_time = datetime.fromisoformat(alert_measurement["timestamp"])
                    
                    # Verificar se há medições normais posteriores
                    normal_after = [m for m in source_measurements 
                                   if datetime.fromisoformat(m["timestamp"]) > alert_time 
                                   and m["status"] == "normal"]
                    
                    if normal_after:
                        # Se houver medições normais após o alerta, aumentar a confiança de que é falso
                        normal_count = len(normal_after)
                        confidence = min(0.5 + (normal_count * 0.1), 0.9)  # Máximo de 90% de confiança
                        
                        result["rules_applied"].append({
                            "rule": "normal_measurements_after_alert",
                            "description": f"{normal_count} medições normais após o alerta",
                            "confidence": confidence
                        })
                        
                        if confidence > result["confidence"]:
                            result["confidence"] = confidence
                            result["reason"] = "Medições normais após o alerta"
        
        # Regra 3: Verificar status de monitoramento do equipamento
        if equipment["tracking_status"] == "MINIMALLY_TRACKED":
            # Equipamentos com monitoramento mínimo têm maior chance de gerar falsos positivos
            result["rules_applied"].append({
                "rule": "minimally_tracked_equipment",
                "description": "Equipamento com monitoramento mínimo",
                "confidence": 0.4
            })
            
            if result["confidence"] < 0.4:
                result["confidence"] = 0.4
                result["reason"] = "Equipamento com monitoramento mínimo"
        
        # Regra 4: Verificar histórico de falsos positivos para este tipo de alerta
        false_positive_rate = self._get_false_positive_rate(equipment["id"], alert.description)
        if false_positive_rate > 0.7:  # Se mais de 70% dos alertas similares foram falsos positivos
            result["rules_applied"].append({
                "rule": "high_false_positive_history",
                "description": f"Taxa histórica de falsos positivos: {false_positive_rate:.1%}",
                "confidence": false_positive_rate
            })
            
            if false_positive_rate > result["confidence"]:
                result["confidence"] = false_positive_rate
                result["reason"] = "Alto histórico de falsos positivos"
        
        # Regra 5: Verificar gravidade e criticidade
        # Alertas P1 e P2 em equipamentos críticos têm menor probabilidade de serem falsos
        if alert.gravity in [AlertGravity.P1, AlertGravity.P2] and alert.criticality == AlertCriticality.HIGH:
            # Reduzir a confiança de que é falso
            result["rules_applied"].append({
                "rule": "high_severity_critical_equipment",
                "description": f"Alerta {alert.gravity} em equipamento de criticidade {alert.criticality}",
                "confidence": -0.3  # Valor negativo para reduzir a confiança
            })
            
            # Reduzir a confiança, mas não abaixo de 0
            result["confidence"] = max(0, result["confidence"] - 0.3)
        
        # Determinar resultado final
        result["is_false_positive"] = result["confidence"] >= 0.7
        
        # Se nenhuma regra foi aplicada com confiança suficiente, considerar como válido
        if not result["reason"]:
            result["reason"] = "Nenhuma regra de filtragem aplicável"
        
        return result
    
    def _get_false_positive_rate(self, equipment_id: str, alert_description: str) -> float:
        """
        Obtém a taxa histórica de falsos positivos para um tipo de alerta em um equipamento.
        
        Args:
            equipment_id: ID do equipamento
            alert_description: Descrição do alerta
            
        Returns:
            Taxa de falsos positivos (0.0 a 1.0)
        """
        try:
            with self.db_manager.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        SELECT
                            COUNT(*) as total,
                            COUNT(CASE WHEN status = 'FALSE_POSITIVE' THEN 1 END) as false_positives
                        FROM alerts
                        WHERE equipment_id = %s
                        AND description = %s
                        AND timestamp >= %s
                        """,
                        (equipment_id, alert_description, datetime.now() - timedelta(days=90))  # Últimos 90 dias
                    )
                    
                    row = cursor.fetchone()
                    if not row or row[0] == 0:
                        return 0.0
                    
                    total = row[0]
                    false_positives = row[1]
                    
                    return false_positives / total
        except Exception as e:
            logger.error(f"Erro ao obter taxa de falsos positivos para equipamento {equipment_id}: {e}")
            return 0.0
    
    def _log_filter_result(self, alert_id: str, is_valid: bool, filter_result: Dict[str, Any]) -> None:
        """
        Registra o resultado da filtragem de um alerta.
        
        Args:
            alert_id: ID do alerta
            is_valid: Se o alerta é válido
            filter_result: Resultado da filtragem
        """
        try:
            with self.db_manager.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        UPDATE alerts
                        SET filter_result = %s,
                            is_valid = %s,
                            updated_at = NOW()
                        WHERE id = %s
                        """,
                        (filter_result, is_valid, alert_id)
                    )
                    
                    conn.commit()
        except Exception as e:
            logger.error(f"Erro ao registrar resultado de filtragem para alerta {alert_id}: {e}")
    
    def get_filtered_alerts(
        self,
        client_id: Optional[str] = None,
        equipment_id: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        include_false_positives: bool = False,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Obtém alertas filtrados com base em critérios.
        
        Args:
            client_id: ID do cliente (opcional)
            equipment_id: ID do equipamento (opcional)
            start_date: Data inicial (opcional)
            end_date: Data final (opcional)
            include_false_positives: Se deve incluir falsos positivos
            limit: Limite de resultados
            offset: Deslocamento para paginação
            
        Returns:
            Lista de alertas filtrados
        """
        try:
            with self.db_manager.get_connection() as conn:
                with conn.cursor() as cursor:
                    # Construir consulta base
                    query = """
                    SELECT
                        a.id, a.equipment_id, a.timestamp, a.measurement_id,
                        a.measurement_source, a.description, a.gravity,
                        a.criticality, a.status, a.assigned_to,
                        a.resolution_details, a.is_valid, a.filter_result,
                        e.name as equipment_name, e.tag as equipment_tag,
                        c.name as client_name
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
                    
                    if not include_false_positives:
                        query += " AND (a.is_valid = TRUE OR a.is_valid IS NULL)"
                    
                    # Adicionar ordenação, limite e deslocamento
                    query += " ORDER BY a.timestamp DESC LIMIT %s OFFSET %s"
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
                            "client_name": row[15]
                        })
                    
                    return alerts
        except Exception as e:
            logger.error(f"Erro ao obter alertas filtrados: {e}")
            return []

logger.info("Alarm filtering service defined.")
"""
