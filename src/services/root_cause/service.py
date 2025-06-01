"""
Root cause analysis service for the SIL Predictive System.

This module implements analysis of repeated equipment failures to identify patterns and root causes.
"""

import logging
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, timedelta
import uuid
import json
from collections import Counter, defaultdict

from ..models.alerts.model import AlertBase, AlertGravity, AlertStatus
from ..models.equipment.equipment import EquipmentBase, MaintenanceRecord

# Configuração de logging
logger = logging.getLogger(__name__)

class RootCauseAnalysisService:
    """Serviço para análise de causa raiz de falhas recorrentes."""
    
    def __init__(self, db_manager, anthropic_service=None):
        """
        Inicializa o serviço de análise de causa raiz.
        
        Args:
            db_manager: Gerenciador de banco de dados
            anthropic_service: Serviço de integração com a API da Anthropic (opcional)
        """
        self.db_manager = db_manager
        self.anthropic_service = anthropic_service
        logger.info("Serviço de análise de causa raiz inicializado")
    
    def analyze_equipment_failures(
        self,
        equipment_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        min_occurrences: int = 2
    ) -> Dict[str, Any]:
        """
        Analisa falhas recorrentes em um equipamento específico.
        
        Args:
            equipment_id: ID do equipamento
            start_date: Data inicial para análise (opcional)
            end_date: Data final para análise (opcional)
            min_occurrences: Número mínimo de ocorrências para considerar um padrão
            
        Returns:
            Resultado da análise de causa raiz
        """
        try:
            # Definir período de análise se não fornecido
            if not end_date:
                end_date = datetime.now()
            if not start_date:
                start_date = end_date - timedelta(days=365)  # Último ano por padrão
            
            # Obter alertas do equipamento no período
            alerts = self._get_equipment_alerts(equipment_id, start_date, end_date)
            
            # Obter registros de manutenção no período
            maintenance_records = self._get_equipment_maintenance(equipment_id, start_date, end_date)
            
            # Obter medições no período
            measurements = self._get_equipment_measurements(equipment_id, start_date, end_date)
            
            # Identificar padrões de falha
            failure_patterns = self._identify_failure_patterns(alerts, min_occurrences)
            
            # Correlacionar com manutenções
            maintenance_correlation = self._correlate_with_maintenance(failure_patterns, maintenance_records)
            
            # Correlacionar com medições
            measurement_correlation = self._correlate_with_measurements(failure_patterns, measurements)
            
            # Gerar análise de causa raiz
            root_cause_analysis = self._generate_root_cause_analysis(
                failure_patterns,
                maintenance_correlation,
                measurement_correlation,
                equipment_id
            )
            
            return {
                "equipment_id": equipment_id,
                "analysis_period": {
                    "start_date": start_date,
                    "end_date": end_date
                },
                "alert_count": len(alerts),
                "maintenance_count": len(maintenance_records),
                "failure_patterns": failure_patterns,
                "maintenance_correlation": maintenance_correlation,
                "measurement_correlation": measurement_correlation,
                "root_cause_analysis": root_cause_analysis
            }
        except Exception as e:
            logger.error(f"Erro ao analisar falhas do equipamento {equipment_id}: {e}")
            return {
                "equipment_id": equipment_id,
                "error": str(e),
                "success": False
            }
    
    def analyze_client_equipment_failures(
        self,
        client_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        min_occurrences: int = 2
    ) -> Dict[str, Any]:
        """
        Analisa falhas recorrentes em todos os equipamentos de um cliente.
        
        Args:
            client_id: ID do cliente
            start_date: Data inicial para análise (opcional)
            end_date: Data final para análise (opcional)
            min_occurrences: Número mínimo de ocorrências para considerar um padrão
            
        Returns:
            Resultado da análise de causa raiz por equipamento
        """
        try:
            # Obter todos os equipamentos do cliente
            equipment_list = self._get_client_equipment(client_id)
            
            # Analisar cada equipamento
            equipment_analyses = {}
            for equipment in equipment_list:
                equipment_id = equipment["id"]
                analysis = self.analyze_equipment_failures(
                    equipment_id,
                    start_date,
                    end_date,
                    min_occurrences
                )
                equipment_analyses[equipment_id] = {
                    "equipment_name": equipment["name"],
                    "equipment_tag": equipment["tag"],
                    "analysis": analysis
                }
            
            # Identificar padrões comuns entre equipamentos
            common_patterns = self._identify_common_patterns(equipment_analyses)
            
            return {
                "client_id": client_id,
                "analysis_period": {
                    "start_date": start_date or (datetime.now() - timedelta(days=365)),
                    "end_date": end_date or datetime.now()
                },
                "equipment_count": len(equipment_list),
                "equipment_analyses": equipment_analyses,
                "common_patterns": common_patterns
            }
        except Exception as e:
            logger.error(f"Erro ao analisar falhas dos equipamentos do cliente {client_id}: {e}")
            return {
                "client_id": client_id,
                "error": str(e),
                "success": False
            }
    
    def _get_equipment_alerts(
        self,
        equipment_id: str,
        start_date: datetime,
        end_date: datetime
    ) -> List[Dict[str, Any]]:
        """
        Obtém alertas de um equipamento em um período.
        
        Args:
            equipment_id: ID do equipamento
            start_date: Data inicial
            end_date: Data final
            
        Returns:
            Lista de alertas
        """
        try:
            with self.db_manager.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        SELECT
                            id, timestamp, measurement_id, measurement_source,
                            description, gravity, criticality, status,
                            assigned_to, resolution_details, metadata
                        FROM alerts
                        WHERE equipment_id = %s
                        AND timestamp BETWEEN %s AND %s
                        ORDER BY timestamp
                        """,
                        (equipment_id, start_date, end_date)
                    )
                    
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
                            "status": row[7],
                            "assigned_to": row[8],
                            "resolution_details": row[9],
                            "metadata": row[10]
                        })
                    
                    return alerts
        except Exception as e:
            logger.error(f"Erro ao obter alertas do equipamento {equipment_id}: {e}")
            return []
    
    def _get_equipment_maintenance(
        self,
        equipment_id: str,
        start_date: datetime,
        end_date: datetime
    ) -> List[Dict[str, Any]]:
        """
        Obtém registros de manutenção de um equipamento em um período.
        
        Args:
            equipment_id: ID do equipamento
            start_date: Data inicial
            end_date: Data final
            
        Returns:
            Lista de registros de manutenção
        """
        try:
            with self.db_manager.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        SELECT maintenance_history
                        FROM equipment
                        WHERE id = %s
                        """,
                        (equipment_id,)
                    )
                    
                    row = cursor.fetchone()
                    if not row or not row[0]:
                        return []
                    
                    maintenance_history = row[0]
                    
                    # Filtrar por período
                    filtered_records = []
                    for record in maintenance_history:
                        record_date = datetime.fromisoformat(record["timestamp"])
                        if start_date <= record_date <= end_date:
                            filtered_records.append(record)
                    
                    return filtered_records
        except Exception as e:
            logger.error(f"Erro ao obter manutenções do equipamento {equipment_id}: {e}")
            return []
    
    def _get_equipment_measurements(
        self,
        equipment_id: str,
        start_date: datetime,
        end_date: datetime
    ) -> List[Dict[str, Any]]:
        """
        Obtém medições de um equipamento em um período.
        
        Args:
            equipment_id: ID do equipamento
            start_date: Data inicial
            end_date: Data final
            
        Returns:
            Lista de medições
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
                        return []
                    
                    measurement_history = row[0]
                    
                    # Filtrar por período
                    filtered_records = []
                    for record in measurement_history:
                        record_date = datetime.fromisoformat(record["timestamp"])
                        if start_date <= record_date <= end_date:
                            filtered_records.append(record)
                    
                    return filtered_records
        except Exception as e:
            logger.error(f"Erro ao obter medições do equipamento {equipment_id}: {e}")
            return []
    
    def _get_client_equipment(self, client_id: str) -> List[Dict[str, Any]]:
        """
        Obtém todos os equipamentos de um cliente.
        
        Args:
            client_id: ID do cliente
            
        Returns:
            Lista de equipamentos
        """
        try:
            with self.db_manager.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        SELECT id, tag, name, type, model, manufacturer
                        FROM equipment
                        WHERE client_id = %s
                        """,
                        (client_id,)
                    )
                    
                    equipment_list = []
                    for row in cursor.fetchall():
                        equipment_list.append({
                            "id": row[0],
                            "tag": row[1],
                            "name": row[2],
                            "type": row[3],
                            "model": row[4],
                            "manufacturer": row[5]
                        })
                    
                    return equipment_list
        except Exception as e:
            logger.error(f"Erro ao obter equipamentos do cliente {client_id}: {e}")
            return []
    
    def _identify_failure_patterns(
        self,
        alerts: List[Dict[str, Any]],
        min_occurrences: int
    ) -> List[Dict[str, Any]]:
        """
        Identifica padrões de falha nos alertas.
        
        Args:
            alerts: Lista de alertas
            min_occurrences: Número mínimo de ocorrências para considerar um padrão
            
        Returns:
            Lista de padrões de falha identificados
        """
        if not alerts:
            return []
        
        # Agrupar alertas por descrição
        description_groups = defaultdict(list)
        for alert in alerts:
            description_groups[alert["description"]].append(alert)
        
        # Filtrar grupos com ocorrências mínimas
        patterns = []
        for description, alert_group in description_groups.items():
            if len(alert_group) >= min_occurrences:
                # Calcular intervalo médio entre ocorrências
                timestamps = sorted([alert["timestamp"] for alert in alert_group])
                intervals = []
                for i in range(1, len(timestamps)):
                    interval = (timestamps[i] - timestamps[i-1]).total_seconds() / 3600  # Horas
                    intervals.append(interval)
                
                avg_interval = sum(intervals) / len(intervals) if intervals else 0
                
                # Calcular gravidade predominante
                gravity_counter = Counter([alert["gravity"] for alert in alert_group])
                predominant_gravity = gravity_counter.most_common(1)[0][0]
                
                patterns.append({
                    "description": description,
                    "occurrences": len(alert_group),
                    "first_occurrence": min(timestamps),
                    "last_occurrence": max(timestamps),
                    "average_interval_hours": avg_interval,
                    "predominant_gravity": predominant_gravity,
                    "alerts": [alert["id"] for alert in alert_group]
                })
        
        # Ordenar por número de ocorrências (decrescente)
        patterns.sort(key=lambda x: x["occurrences"], reverse=True)
        
        return patterns
    
    def _correlate_with_maintenance(
        self,
        failure_patterns: List[Dict[str, Any]],
        maintenance_records: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Correlaciona padrões de falha com registros de manutenção.
        
        Args:
            failure_patterns: Lista de padrões de falha
            maintenance_records: Lista de registros de manutenção
            
        Returns:
            Correlação entre falhas e manutenções
        """
        if not failure_patterns or not maintenance_records:
            return {"correlations": []}
        
        correlations = []
        
        # Ordenar manutenções por data
        maintenance_records.sort(key=lambda x: datetime.fromisoformat(x["timestamp"]))
        
        for pattern in failure_patterns:
            pattern_correlations = []
            
            # Para cada ocorrência de falha, verificar manutenções próximas
            for alert_id in pattern["alerts"]:
                # Obter timestamp do alerta
                alert_timestamp = None
                for alert in maintenance_records:
                    if alert.get("related_alert_id") == alert_id:
                        alert_timestamp = datetime.fromisoformat(alert["timestamp"])
                        break
                
                if not alert_timestamp:
                    continue
                
                # Procurar manutenções próximas (até 7 dias após o alerta)
                for record in maintenance_records:
                    record_timestamp = datetime.fromisoformat(record["timestamp"])
                    time_diff = (record_timestamp - alert_timestamp).total_seconds() / 3600  # Horas
                    
                    # Considerar manutenções até 7 dias após o alerta
                    if 0 <= time_diff <= 168:  # 7 dias * 24 horas
                        pattern_correlations.append({
                            "alert_id": alert_id,
                            "maintenance_id": record["id"],
                            "time_diff_hours": time_diff,
                            "maintenance_type": record["type"],
                            "maintenance_description": record["description"]
                        })
            
            if pattern_correlations:
                correlations.append({
                    "pattern_description": pattern["description"],
                    "maintenance_correlations": pattern_correlations,
                    "correlation_count": len(pattern_correlations)
                })
        
        return {
            "correlations": correlations,
            "total_correlations": sum(len(c["maintenance_correlations"]) for c in correlations)
        }
    
    def _correlate_with_measurements(
        self,
        failure_patterns: List[Dict[str, Any]],
        measurements: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Correlaciona padrões de falha com medições.
        
        Args:
            failure_patterns: Lista de padrões de falha
            measurements: Lista de medições
            
        Returns:
            Correlação entre falhas e medições
        """
        if not failure_patterns or not measurements:
            return {"correlations": []}
        
        correlations = []
        
        # Ordenar medições por data
        measurements.sort(key=lambda x: datetime.fromisoformat(x["timestamp"]))
        
        for pattern in failure_patterns:
            # Identificar medições anômalas próximas às falhas
            anomalous_measurements = []
            
            for alert_id in pattern["alerts"]:
                # Obter timestamp do alerta (aproximado, já que não temos o alerta completo aqui)
                alert_timestamp = pattern["first_occurrence"]
                
                # Procurar medições anômalas até 24 horas antes do alerta
                for measurement in measurements:
                    measurement_timestamp = datetime.fromisoformat(measurement["timestamp"])
                    time_diff = (alert_timestamp - measurement_timestamp).total_seconds() / 3600  # Horas
                    
                    # Considerar medições até 24 horas antes do alerta
                    if 0 <= time_diff <= 24 and measurement["status"] != "normal":
                        anomalous_measurements.append({
                            "measurement_id": measurement["id"],
                            "source": measurement["source"],
                            "timestamp": measurement_timestamp,
                            "time_before_alert_hours": time_diff,
                            "status": measurement["status"],
                            "values": measurement["values"]
                        })
            
            if anomalous_measurements:
                # Agrupar por fonte de medição
                sources = {}
                for measurement in anomalous_measurements:
                    source = measurement["source"]
                    if source not in sources:
                        sources[source] = []
                    sources[source].append(measurement)
                
                correlations.append({
                    "pattern_description": pattern["description"],
                    "anomalous_measurements": anomalous_measurements,
                    "measurement_count": len(anomalous_measurements),
                    "sources": [{"source": source, "count": len(measurements)} for source, measurements in sources.items()]
                })
        
        return {
            "correlations": correlations,
            "total_anomalous_measurements": sum(len(c["anomalous_measurements"]) for c in correlations)
        }
    
    def _generate_root_cause_analysis(
        self,
        failure_patterns: List[Dict[str, Any]],
        maintenance_correlation: Dict[str, Any],
        measurement_correlation: Dict[str, Any],
        equipment_id: str
    ) -> Dict[str, Any]:
        """
        Gera análise de causa raiz com base nos padrões e correlações.
        
        Args:
            failure_patterns: Lista de padrões de falha
            maintenance_correlation: Correlação com manutenções
            measurement_correlation: Correlação com medições
            equipment_id: ID do equipamento
            
        Returns:
            Análise de causa raiz
        """
        if not failure_patterns:
            return {
                "possible_causes": [],
                "recommendations": [],
                "confidence": 0
            }
        
        # Identificar possíveis causas com base nos padrões e correlações
        possible_causes = []
        recommendations = []
        
        # Analisar padrões de falha
        for pattern in failure_patterns:
            # Verificar se há correlações de manutenção para este padrão
            maintenance_corr = next((c for c in maintenance_correlation.get("correlations", []) 
                                    if c["pattern_description"] == pattern["description"]), None)
            
            # Verificar se há correlações de medição para este padrão
            measurement_corr = next((c for c in measurement_correlation.get("correlations", []) 
                                    if c["pattern_description"] == pattern["description"]), None)
            
            # Determinar possíveis causas com base nas correlações
            pattern_causes = []
            pattern_recommendations = []
            
            # Causas baseadas em manutenções
            if maintenance_corr:
                maintenance_types = Counter([mc["maintenance_type"] for mc in maintenance_corr["maintenance_correlations"]])
                most_common_type = maintenance_types.most_common(1)[0][0] if maintenance_types else None
                
                if most_common_type:
                    pattern_causes.append({
                        "description": f"Falha recorrente que requer manutenção do tipo {most_common_type}",
                        "confidence": 0.7,
                        "evidence": f"{len(maintenance_corr['maintenance_correlations'])} manutenções correlacionadas"
                    })
                    
                    pattern_recommendations.append({
                        "description": f"Implementar manutenção preventiva do tipo {most_common_type} com maior frequência",
                        "priority": "ALTA" if pattern["predominant_gravity"] in ["P1", "P2"] else "MÉDIA"
                    })
            
            # Causas baseadas em medições
            if measurement_corr:
                # Agrupar por fonte
                sources = defaultdict(list)
                for measurement in measurement_corr["anomalous_measurements"]:
                    sources[measurement["source"]].append(measurement)
                
                for source, measurements in sources.items():
                    # Analisar valores anômalos
                    anomalous_values = {}
                    for measurement in measurements:
                        for param, value in measurement["values"].items():
                            if param not in anomalous_values:
                                anomalous_values[param] = []
                            anomalous_values[param].append(value)
                    
                    # Identificar parâmetros com valores consistentemente anômalos
                    for param, values in anomalous_values.items():
                        if len(values) >= 2:  # Pelo menos 2 ocorrências
                            avg_value = sum(values) / len(values)
                            pattern_causes.append({
                                "description": f"Valores anômalos de {param} em medições de {source}",
                                "confidence": 0.8,
                                "evidence": f"Valor médio: {avg_value}, Ocorrências: {len(values)}"
                            })
                            
                            pattern_recommendations.append({
                                "description": f"Monitorar {param} em medições de {source} com maior frequência",
                                "priority": "ALTA" if pattern["predominant_gravity"] in ["P1", "P2"] else "MÉDIA"
                            })
            
            # Se não houver correlações específicas, usar informações do padrão
            if not pattern_causes:
                pattern_causes.append({
                    "description": f"Falha recorrente: {pattern['description']}",
                    "confidence": 0.5,
                    "evidence": f"{pattern['occurrences']} ocorrências, intervalo médio de {pattern['average_interval_hours']:.1f} horas"
                })
                
                pattern_recommendations.append({
                    "description": "Realizar inspeção detalhada para identificar causa raiz",
                    "priority": "ALTA" if pattern["predominant_gravity"] in ["P1", "P2"] else "MÉDIA"
                })
            
            # Adicionar causas e recomendações deste padrão
            possible_causes.extend(pattern_causes)
            recommendations.extend(pattern_recommendations)
        
        # Usar IA para análise avançada, se disponível
        ai_analysis = None
        if self.anthropic_service:
            try:
                ai_analysis = self._get_ai_analysis(
                    failure_patterns,
                    maintenance_correlation,
                    measurement_correlation,
                    equipment_id
                )
            except Exception as e:
                logger.error(f"Erro ao obter análise de IA para equipamento {equipment_id}: {e}")
        
        # Calcular confiança geral
        confidence = 0.0
        if possible_causes:
            confidence = sum(cause["confidence"] for cause in possible_causes) / len(possible_causes)
        
        return {
            "possible_causes": possible_causes,
            "recommendations": recommendations,
            "confidence": confidence,
            "ai_analysis": ai_analysis
        }
    
    def _get_ai_analysis(
        self,
        failure_patterns: List[Dict[str, Any]],
        maintenance_correlation: Dict[str, Any],
        measurement_correlation: Dict[str, Any],
        equipment_id: str
    ) -> Dict[str, Any]:
        """
        Obtém análise avançada usando IA (Anthropic API).
        
        Args:
            failure_patterns: Lista de padrões de falha
            maintenance_correlation: Correlação com manutenções
            measurement_correlation: Correlação com medições
            equipment_id: ID do equipamento
            
        Returns:
            Análise de IA
        """
        if not self.anthropic_service:
            return None
        
        try:
            # Obter informações do equipamento
            equipment_info = self._get_equipment_info(equipment_id)
            
            # Preparar prompt para a IA
            prompt = f"""
            Analise os seguintes dados de falhas recorrentes em um equipamento e identifique possíveis causas raiz e recomendações:
            
            Informações do Equipamento:
            - Tipo: {equipment_info.get('type', 'Desconhecido')}
            - Modelo: {equipment_info.get('model', 'Desconhecido')}
            - Fabricante: {equipment_info.get('manufacturer', 'Desconhecido')}
            
            Padrões de Falha:
            {json.dumps(failure_patterns, indent=2, default=str)}
            
            Correlações com Manutenções:
            {json.dumps(maintenance_correlation, indent=2, default=str)}
            
            Correlações com Medições:
            {json.dumps(measurement_correlation, indent=2, default=str)}
            
            Por favor, forneça:
            1. Uma análise detalhada das possíveis causas raiz
            2. Recomendações específicas para prevenir falhas futuras
            3. Sugestões de monitoramento adicional, se aplicável
            """
            
            # Obter resposta da IA
            response = self.anthropic_service.get_analysis(prompt)
            
            return {
                "analysis": response.get("analysis", ""),
                "causes": response.get("causes", []),
                "recommendations": response.get("recommendations", []),
                "monitoring_suggestions": response.get("monitoring_suggestions", [])
            }
        except Exception as e:
            logger.error(f"Erro ao obter análise de IA: {e}")
            return None
    
    def _get_equipment_info(self, equipment_id: str) -> Dict[str, Any]:
        """
        Obtém informações básicas de um equipamento.
        
        Args:
            equipment_id: ID do equipamento
            
        Returns:
            Informações do equipamento
        """
        try:
            with self.db_manager.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        SELECT type, model, manufacturer, tag, name
                        FROM equipment
                        WHERE id = %s
                        """,
                        (equipment_id,)
                    )
                    
                    row = cursor.fetchone()
                    if not row:
                        return {}
                    
                    return {
                        "type": row[0],
                        "model": row[1],
                        "manufacturer": row[2],
                        "tag": row[3],
                        "name": row[4]
                    }
        except Exception as e:
            logger.error(f"Erro ao obter informações do equipamento {equipment_id}: {e}")
            return {}
    
    def _identify_common_patterns(self, equipment_analyses: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Identifica padrões comuns entre diferentes equipamentos.
        
        Args:
            equipment_analyses: Análises por equipamento
            
        Returns:
            Lista de padrões comuns
        """
        if not equipment_analyses:
            return []
        
        # Agrupar descrições de falha por tipo de equipamento
        equipment_type_patterns = defaultdict(list)
        
        for equipment_id, analysis_data in equipment_analyses.items():
            equipment_type = analysis_data.get("analysis", {}).get("equipment_type", "unknown")
            patterns = analysis_data.get("analysis", {}).get("failure_patterns", [])
            
            for pattern in patterns:
                equipment_type_patterns[equipment_type].append({
                    "equipment_id": equipment_id,
                    "equipment_name": analysis_data.get("equipment_name", ""),
                    "pattern": pattern
                })
        
        # Identificar padrões comuns por tipo de equipamento
        common_patterns = []
        
        for equipment_type, patterns in equipment_type_patterns.items():
            # Agrupar por descrição
            description_groups = defaultdict(list)
            for pattern_data in patterns:
                description = pattern_data["pattern"]["description"]
                description_groups[description].append(pattern_data)
            
            # Identificar descrições que aparecem em múltiplos equipamentos
            for description, pattern_group in description_groups.items():
                equipment_ids = set(p["equipment_id"] for p in pattern_group)
                
                if len(equipment_ids) > 1:  # Aparece em mais de um equipamento
                    common_patterns.append({
                        "equipment_type": equipment_type,
                        "description": description,
                        "equipment_count": len(equipment_ids),
                        "total_occurrences": sum(p["pattern"]["occurrences"] for p in pattern_group),
                        "affected_equipment": [
                            {"id": p["equipment_id"], "name": p["equipment_name"]} 
                            for p in pattern_group
                        ]
                    })
        
        # Ordenar por número de equipamentos afetados (decrescente)
        common_patterns.sort(key=lambda x: x["equipment_count"], reverse=True)
        
        return common_patterns

logger.info("Root cause analysis service defined.")
"""
