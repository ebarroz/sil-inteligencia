"""
Sistema de Filtragem de Alarmes Falsos - SIL Predictive System
-------------------------------------------------------------
Este módulo implementa o sistema de filtragem de alarmes falsos para validação
e priorização de alertas, conforme requisito #7.
"""
import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
import numpy as np
from collections import defaultdict

# Configuração de logging
logger = logging.getLogger(__name__)

class AlarmFilter:
    """Serviço para filtragem e validação de alarmes."""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Inicializa o serviço de filtragem de alarmes.
        
        Args:
            config: Configurações do serviço
        """
        self.config = config
        self.anomaly_threshold = config.get("anomaly_threshold", 0.8)
        self.history_window_days = config.get("history_window_days", 30)
        self.min_samples = config.get("min_samples", 10)
        self.equipment_history = defaultdict(list)
        logger.info("Serviço de filtragem de alarmes inicializado")
    def validate_alarm(self, alert: Dict[str, Any], 
                      equipment_history: List[Dict[str, Any]],
                      measurement_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Valida um alarme para determinar se é um falso positivo.
        
        Args:
            alert: Dados do alerta
            equipment_history: Histórico de alertas do equipamento
            measurement_data: Dados de medição que geraram o alerta (opcional)
            
        Returns:
            Dict[str, Any]: Resultado da validação
        """
        equipment_id = alert.get("equipment_id")
        logger.info(f"Validando alarme para equipamento {equipment_id}")
        
        # Atualiza o histórico do equipamento
        self._update_equipment_history(equipment_id, equipment_history)
        
        # Aplica diferentes métodos de validação
        validation_results = {
            "statistical": self._statistical_validation(alert, measurement_data),
            "pattern_based": self._pattern_based_validation(alert, equipment_id),
            "rule_based": self._rule_based_validation(alert)
        }
        
        # Calcula o score de confiança combinado
        confidence_score = self._calculate_confidence_score(validation_results)
        
        # Determina se é um falso alarme com base no score de confiança
        is_false_alarm = confidence_score < self.anomaly_threshold
        
        result = {
            "alert_id": alert.get("id"),
            "equipment_id": equipment_id,
            "timestamp": datetime.utcnow().isoformat(),
            "is_false_alarm": is_false_alarm,
            "confidence_score": confidence_score,
            "validation_details": validation_results,
            "recommendation": self._generate_recommendation(is_false_alarm, confidence_score, alert)
        }
        
        logger.info(f"Validação de alarme concluída para {equipment_id}: falso alarme = {is_false_alarm}, confiança = {confidence_score:.2f}")
        return result
    def _update_equipment_history(self, equipment_id: str, equipment_history: List[Dict[str, Any]]) -> None:
        """
        Atualiza o histórico de alertas do equipamento.
        
        Args:
            equipment_id: ID do equipamento
            equipment_history: Histórico de alertas do equipamento
        """
        # Filtra alertas recentes dentro da janela de tempo
        cutoff_date = datetime.utcnow() - timedelta(days=self.history_window_days)
        
        # Atualiza o histórico mantendo apenas alertas recentes
        self.equipment_history[equipment_id] = [
            alert for alert in equipment_history 
            if alert.get("timestamp") and datetime.fromisoformat(alert["timestamp"]) > cutoff_date
        ]
    
    def _statistical_validation(self, alert: Dict[str, Any], 
                               measurement_data: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Aplica validação estatística ao alerta.
        
        Args:
            alert: Dados do alerta
            measurement_data: Dados de medição que geraram o alerta
            
        Returns:
            Dict[str, Any]: Resultado da validação estatística
        """
        # Se não há dados de medição, não é possível fazer validação estatística
        if not measurement_data:
            return {
                "method": "statistical",
                "confidence": 0.5,  # Neutro
                "details": "Sem dados de medição para validação estatística"
            }
        
        try:
            # Extrai valores numéricos dos dados de medição
            values = []
            for key, value in measurement_data.items():
                if isinstance(value, (int, float)) and key not in ["timestamp", "id"]:
                    values.append(value)
            
            if not values:
                return {
                    "method": "statistical",
                    "confidence": 0.5,  # Neutro
                    "details": "Sem valores numéricos nos dados de medição"
                }
            
            # Cálculo simples de Z-score para poucos dados
            mean = np.mean(values)
            std = np.std(values) or 1.0  # Evita divisão por zero
            z_scores = [(v - mean) / std for v in values]
            max_z = max(abs(z) for z in z_scores)
            
            # Z-score > 3 geralmente indica anomalia
            confidence = min(0.5 + (max_z / 6.0), 0.95)  # Mapeia para [0.5, 0.95]
            
            return {
                "method": "statistical",
                "confidence": confidence,
                "details": f"Z-score máximo = {max_z:.2f}"
            }
                
        except Exception as e:
            logger.error(f"Erro na validação estatística: {str(e)}")
            return {
                "method": "statistical",
                "confidence": 0.5,  # Neutro
                "details": f"Erro na validação estatística: {str(e)}"
            }
    def _pattern_based_validation(self, alert: Dict[str, Any], equipment_id: str) -> Dict[str, Any]:
        """
        Aplica validação baseada em padrões históricos.
        
        Args:
            alert: Dados do alerta
            equipment_id: ID do equipamento
            
        Returns:
            Dict[str, Any]: Resultado da validação baseada em padrões
        """
        equipment_alerts = self.equipment_history.get(equipment_id, [])
        
        if len(equipment_alerts) < self.min_samples:
            return {
                "method": "pattern_based",
                "confidence": 0.5,  # Neutro
                "details": "Histórico insuficiente para validação baseada em padrões"
            }
        
        # Conta ocorrências de alertas similares
        similar_count = 0
        total_count = len(equipment_alerts)
        
        for hist_alert in equipment_alerts:
            if self._are_alerts_similar(alert, hist_alert):
                similar_count += 1
        
        # Calcula proporção de alertas similares
        similarity_ratio = similar_count / total_count if total_count > 0 else 0
        
        # Se muitos alertas similares foram falsos alarmes no passado, aumenta a chance de ser falso alarme
        false_alarm_count = sum(1 for a in equipment_alerts if 
                               self._are_alerts_similar(alert, a) and 
                               a.get("status") == "FALSE_POSITIVE")
        
        false_alarm_ratio = false_alarm_count / similar_count if similar_count > 0 else 0
        
        # Calcula confiança baseada em padrões históricos
        pattern_confidence = 0.5 + (0.5 * (1.0 - false_alarm_ratio))
        
        return {
            "method": "pattern_based",
            "confidence": pattern_confidence,
            "details": f"Alertas similares: {similar_count}/{total_count}, falsos alarmes: {false_alarm_count}/{similar_count if similar_count > 0 else 1}"
        }
    
    def _rule_based_validation(self, alert: Dict[str, Any]) -> Dict[str, Any]:
        """
        Aplica validação baseada em regras predefinidas.
        
        Args:
            alert: Dados do alerta
            
        Returns:
            Dict[str, Any]: Resultado da validação baseada em regras
        """
        # Regras baseadas na gravidade e criticidade
        gravity = alert.get("gravity", "P3")
        criticality = alert.get("criticality", "LOW")
        
        # Alertas P1 em equipamentos críticos têm alta confiança
        if gravity == "P1" and criticality == "HIGH":
            return {
                "method": "rule_based",
                "confidence": 0.9,
                "details": "Alerta P1 em equipamento de alta criticidade"
            }
        
        # Alertas P3 em equipamentos de baixa criticidade têm menor confiança
        if gravity == "P3" and criticality == "LOW":
            return {
                "method": "rule_based",
                "confidence": 0.6,
                "details": "Alerta P3 em equipamento de baixa criticidade"
            }
        
        # Valor padrão para outras combinações
        return {
            "method": "rule_based",
            "confidence": 0.75,
            "details": f"Alerta {gravity} em equipamento de criticidade {criticality}"
        }
    def _are_alerts_similar(self, alert1: Dict[str, Any], alert2: Dict[str, Any]) -> bool:
        """
        Verifica se dois alertas são similares.
        
        Args:
            alert1: Primeiro alerta
            alert2: Segundo alerta
            
        Returns:
            bool: True se os alertas são similares, False caso contrário
        """
        # Compara campos relevantes
        similar_fields = 0
        total_fields = 3  # Número de campos a comparar
        
        # Compara gravidade
        if alert1.get("gravity") == alert2.get("gravity"):
            similar_fields += 1
        
        # Compara fonte de medição
        if alert1.get("measurement_source") == alert2.get("measurement_source"):
            similar_fields += 1
        
        # Compara descrição (simplificado)
        desc1 = alert1.get("description", "").lower()
        desc2 = alert2.get("description", "").lower()
        
        # Verifica palavras-chave comuns
        keywords1 = set(desc1.split())
        keywords2 = set(desc2.split())
        common_keywords = keywords1.intersection(keywords2)
        
        # Se pelo menos 30% das palavras são comuns
        if len(common_keywords) >= 0.3 * min(len(keywords1), len(keywords2)):
            similar_fields += 1
        
        # Alertas são similares se pelo menos 2 de 3 campos são similares
        return similar_fields >= 2
    
    def _calculate_confidence_score(self, validation_results: Dict[str, Dict[str, Any]]) -> float:
        """
        Calcula o score de confiança combinado.
        
        Args:
            validation_results: Resultados de diferentes métodos de validação
            
        Returns:
            float: Score de confiança combinado
        """
        # Pesos para cada método de validação
        weights = {
            "statistical": 0.4,
            "pattern_based": 0.4,
            "rule_based": 0.2
        }
        
        # Calcula média ponderada
        weighted_sum = 0.0
        total_weight = 0.0
        
        for method, result in validation_results.items():
            confidence = result.get("confidence", 0.5)
            weight = weights.get(method, 0.0)
            
            weighted_sum += confidence * weight
            total_weight += weight
        
        # Retorna média ponderada ou valor neutro se não há pesos
        return weighted_sum / total_weight if total_weight > 0 else 0.5
    def _generate_recommendation(self, is_false_alarm: bool, confidence_score: float, 
                               alert: Dict[str, Any]) -> Dict[str, Any]:
        """
        Gera recomendação com base no resultado da validação.
        
        Args:
            is_false_alarm: Indicador se é um falso alarme
            confidence_score: Score de confiança
            alert: Dados do alerta
            
        Returns:
            Dict[str, Any]: Recomendação gerada
        """
        if is_false_alarm:
            if confidence_score < 0.3:
                action = "IGNORAR"
                description = "Alta probabilidade de falso alarme, recomenda-se ignorar"
            else:
                action = "VERIFICAR_BAIXA"
                description = "Possível falso alarme, verificação de baixa prioridade recomendada"
        else:
            gravity = alert.get("gravity", "P3")
            
            if gravity == "P1" or confidence_score > 0.9:
                action = "ATENDER_URGENTE"
                description = "Alerta crítico validado, atendimento urgente necessário"
            elif gravity == "P2" or confidence_score > 0.7:
                action = "ATENDER_PRIORITARIO"
                description = "Alerta importante validado, atendimento prioritário recomendado"
            else:
                action = "ATENDER_NORMAL"
                description = "Alerta validado, atendimento normal recomendado"
        
        return {
            "action": action,
            "description": description,
            "confidence": confidence_score
        }
