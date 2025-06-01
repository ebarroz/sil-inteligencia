"""
Cliente específico para integração com APIs de análise de óleo.

Este módulo implementa um cliente para consumo de APIs de análise de óleo,
utilizando o cliente genérico como base e adicionando funcionalidades
específicas para este tipo de medição.
"""

import logging
import random
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Union
import uuid

from ..api_client import APIClient
from ....models.oil.model import OilAnalysisMeasurement, OilProperty, OilSampleType
from ....models.base import MeasurementStatus, MeasurementSource, MeasurementThreshold

# Configuração de logging
logger = logging.getLogger(__name__)


class OilAnalysisAPIClient:
    """Cliente para APIs de análise de óleo."""
    
    def __init__(
        self,
        base_url: str = "https://api.example.com/v1",
        auth_type: str = "api_key",
        auth_credentials: Dict[str, str] = None,
        max_retries: int = 3,
        timeout: int = 30,
        simulate: bool = False
    ):
        """
        Inicializa o cliente de API de análise de óleo.
        
        Args:
            base_url: URL base da API
            auth_type: Tipo de autenticação ('api_key', 'bearer', 'oauth2')
            auth_credentials: Credenciais de autenticação
            max_retries: Número máximo de tentativas em caso de falha
            timeout: Tempo limite para requisições em segundos
            simulate: Se True, gera dados simulados em vez de fazer requisições reais
        """
        self.simulate = simulate
        
        if not simulate:
            self.client = APIClient(
                base_url=base_url,
                auth_type=auth_type,
                auth_credentials=auth_credentials or {},
                max_retries=max_retries,
                timeout=timeout
            )
        
        logger.info(f"OilAnalysisAPIClient inicializado. Modo simulação: {simulate}")
    
    def get_analyses(
        self,
        equipment_id: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100,
        status: Optional[str] = None,
        sample_type: Optional[str] = None
    ) -> List[OilAnalysisMeasurement]:
        """
        Obtém análises de óleo.
        
        Args:
            equipment_id: ID do equipamento (opcional)
            start_date: Data de início (opcional)
            end_date: Data de fim (opcional)
            limit: Limite de resultados
            status: Filtro por status (opcional)
            sample_type: Tipo de amostra (opcional)
            
        Returns:
            Lista de análises de óleo
        """
        if self.simulate:
            return self._simulate_analyses(
                equipment_id=equipment_id,
                start_date=start_date,
                end_date=end_date,
                limit=limit,
                status=status,
                sample_type=sample_type
            )
        
        # Preparar parâmetros para a requisição
        params = {"limit": limit}
        
        if equipment_id:
            params["equipment_id"] = equipment_id
            
        if start_date:
            params["start_date"] = start_date.isoformat()
            
        if end_date:
            params["end_date"] = end_date.isoformat()
            
        if status:
            params["status"] = status
            
        if sample_type:
            params["sample_type"] = sample_type
        
        # Fazer requisição à API
        try:
            response = self.client.get(
                endpoint="oil/analysis",
                params=params
            )
            
            # Converter resposta para objetos do modelo
            analyses = []
            for item in response.get("data", []):
                try:
                    analysis = OilAnalysisMeasurement.from_dict(item)
                    analyses.append(analysis)
                except Exception as e:
                    logger.error(f"Erro ao converter análise de óleo: {e}")
            
            return analyses
            
        except Exception as e:
            logger.error(f"Erro ao obter análises de óleo: {e}")
            return []
    
    def get_analysis_by_id(self, analysis_id: str) -> Optional[OilAnalysisMeasurement]:
        """
        Obtém uma análise específica pelo ID.
        
        Args:
            analysis_id: ID da análise
            
        Returns:
            Análise de óleo ou None se não encontrada
        """
        if self.simulate:
            # Gerar uma análise simulada com o ID fornecido
            return self._simulate_analysis(analysis_id=analysis_id)
        
        try:
            response = self.client.get(
                endpoint=f"oil/analysis/{analysis_id}"
            )
            
            return OilAnalysisMeasurement.from_dict(response)
            
        except Exception as e:
            logger.error(f"Erro ao obter análise de óleo {analysis_id}: {e}")
            return None
    
    def get_analyses_since(
        self,
        since_datetime: datetime,
        equipment_id: Optional[str] = None,
        limit: int = 100
    ) -> List[OilAnalysisMeasurement]:
        """
        Obtém análises desde uma data específica.
        
        Args:
            since_datetime: Data a partir da qual obter análises
            equipment_id: ID do equipamento (opcional)
            limit: Limite de resultados
            
        Returns:
            Lista de análises de óleo
        """
        if self.simulate:
            return self._simulate_analyses(
                equipment_id=equipment_id,
                start_date=since_datetime,
                end_date=datetime.utcnow(),
                limit=limit
            )
        
        params = {
            "since": since_datetime.isoformat(),
            "limit": limit
        }
        
        if equipment_id:
            params["equipment_id"] = equipment_id
        
        try:
            return self.client.get_since(
                endpoint="oil/analysis",
                since_datetime=since_datetime,
                datetime_param="since",
                additional_params=params
            )
            
        except Exception as e:
            logger.error(f"Erro ao obter análises de óleo desde {since_datetime}: {e}")
            return []
    
    def _simulate_analyses(
        self,
        equipment_id: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 10,
        status: Optional[str] = None,
        sample_type: Optional[str] = None
    ) -> List[OilAnalysisMeasurement]:
        """
        Gera análises simuladas para testes.
        
        Args:
            equipment_id: ID do equipamento (opcional)
            start_date: Data de início (opcional)
            end_date: Data de fim (opcional)
            limit: Número de análises a gerar
            status: Status das análises (opcional)
            sample_type: Tipo de amostra (opcional)
            
        Returns:
            Lista de análises simuladas
        """
        if not start_date:
            start_date = datetime.utcnow() - timedelta(days=365)  # Análises de óleo são menos frequentes
            
        if not end_date:
            end_date = datetime.utcnow()
        
        # Gerar IDs de equipamento se não fornecido
        equipment_ids = [equipment_id] if equipment_id else [
            f"motor-{i:02d}" for i in range(1, 6)
        ] + [
            f"gearbox-{i:02d}" for i in range(1, 4)
        ] + [
            f"hydraulic-{i:02d}" for i in range(1, 3)
        ]
        
        # Gerar análises simuladas
        analyses = []
        for _ in range(limit):
            # Selecionar um equipamento aleatório da lista
            eq_id = random.choice(equipment_ids)
            
            # Gerar timestamp aleatório entre start_date e end_date
            time_range = (end_date - start_date).total_seconds()
            random_seconds = random.randint(0, int(time_range))
            timestamp = start_date + timedelta(seconds=random_seconds)
            
            # Gerar análise
            analysis = self._simulate_analysis(
                equipment_id=eq_id,
                timestamp=timestamp,
                status_value=status,
                sample_type_value=sample_type
            )
            
            analyses.append(analysis)
        
        # Ordenar por timestamp (mais recente primeiro)
        analyses.sort(key=lambda a: a.timestamp, reverse=True)
        
        return analyses
    
    def _simulate_analysis(
        self,
        analysis_id: Optional[str] = None,
        equipment_id: Optional[str] = None,
        timestamp: Optional[datetime] = None,
        status_value: Optional[str] = None,
        sample_type_value: Optional[str] = None
    ) -> OilAnalysisMeasurement:
        """
        Gera uma análise simulada para testes.
        
        Args:
            analysis_id: ID da análise (opcional)
            equipment_id: ID do equipamento (opcional)
            timestamp: Timestamp da análise (opcional)
            status_value: Status da análise (opcional)
            sample_type_value: Tipo de amostra (opcional)
            
        Returns:
            Análise simulada
        """
        # Gerar valores padrão se não fornecidos
        if not analysis_id:
            analysis_id = f"oil-{uuid.uuid4()}"
            
        if not equipment_id:
            equipment_id = f"motor-{random.randint(1, 5):02d}"
            
        if not timestamp:
            timestamp = datetime.utcnow() - timedelta(days=random.randint(0, 365))
        
        # Determinar tipo de óleo com base no equipamento
        oil_type = "Mineral"
        oil_brand = "Petrobras Lubrax"
        
        if "hydraulic" in equipment_id:
            oil_type = "Hidráulico"
            oil_brand = "Shell Tellus"
        elif "gearbox" in equipment_id:
            oil_type = "Sintético"
            oil_brand = "Mobil SHC"
        
        # Determinar tipo de amostra
        if sample_type_value:
            sample_type = OilSampleType(sample_type_value)
        else:
            sample_type = random.choice([
                OilSampleType.IN_SERVICE,
                OilSampleType.IN_SERVICE,
                OilSampleType.IN_SERVICE,  # Mais comum
                OilSampleType.NEW,
                OilSampleType.FILTERED
            ])
        
        # Gerar horas em serviço
        hours_in_service = None
        if sample_type == OilSampleType.IN_SERVICE:
            hours_in_service = random.randint(500, 8000)
        
        # Criar a análise
        sample_date = timestamp - timedelta(days=random.randint(1, 5))
        analysis_date = timestamp
        
        analysis = OilAnalysisMeasurement(
            id=analysis_id,
            equipment_id=equipment_id,
            timestamp=timestamp,
            source=MeasurementSource.OIL_ANALYSIS,
            sample_id=f"S{random.randint(10000, 99999)}",
            sample_type=sample_type,
            oil_type=oil_type,
            oil_brand=oil_brand,
            hours_in_service=hours_in_service,
            sample_date=sample_date,
            analysis_date=analysis_date,
            laboratory="LabTech Análises"
        )
        
        # Adicionar propriedades da análise
        self._add_oil_properties(analysis, equipment_id, sample_type)
        
        # Avaliar status geral da análise
        analysis.status = analysis.evaluate_status()
        
        # Sobrescrever status se fornecido
        if status_value:
            analysis.status = MeasurementStatus(status_value)
        
        return analysis
    
    def _add_oil_properties(
        self,
        analysis: OilAnalysisMeasurement,
        equipment_id: str,
        sample_type: OilSampleType
    ) -> None:
        """
        Adiciona propriedades à análise de óleo.
        
        Args:
            analysis: Análise de óleo
            equipment_id: ID do equipamento
            sample_type: Tipo de amostra
        """
        # Definir propriedades comuns para análise de óleo
        properties = [
            # Viscosidade
            {
                "name": "Viscosidade a 40°C",
                "unit": "cSt",
                "base_value": 100.0,
                "variation": 20.0,
                "thresholds": MeasurementThreshold(
                    warning_low=85.0,
                    alert_low=80.0,
                    critical_low=75.0,
                    warning_high=115.0,
                    alert_high=120.0,
                    critical_high=125.0
                )
            },
            # TAN (Número de Acidez Total)
            {
                "name": "TAN",
                "unit": "mgKOH/g",
                "base_value": 0.5,
                "variation": 0.3,
                "thresholds": MeasurementThreshold(
                    warning_high=0.8,
                    alert_high=1.0,
                    critical_high=1.2
                )
            },
            # Água
            {
                "name": "Água",
                "unit": "ppm",
                "base_value": 150.0,
                "variation": 100.0,
                "thresholds": MeasurementThreshold(
                    warning_high=300.0,
                    alert_high=500.0,
                    critical_high=1000.0
                )
            },
            # Partículas
            {
                "name": "ISO 4406",
                "unit": "código",
                "base_value": 18.0,
                "variation": 3.0,
                "thresholds": MeasurementThreshold(
                    warning_high=20.0,
                    alert_high=22.0,
                    critical_high=24.0
                )
            }
        ]
        
        # Adicionar propriedades específicas com base no tipo de equipamento
        if "motor" in equipment_id:
            properties.extend([
                # Fuligem
                {
                    "name": "Fuligem",
                    "unit": "%",
                    "base_value": 0.2,
                    "variation": 0.3,
                    "thresholds": MeasurementThreshold(
                        warning_high=0.5,
                        alert_high=0.8,
                        critical_high=1.2
                    )
                },
                # Oxidação
                {
                    "name": "Oxidação",
                    "unit": "Abs/cm",
                    "base_value": 10.0,
                    "variation": 5.0,
                    "thresholds": MeasurementThreshold(
                        warning_high=15.0,
                        alert_high=20.0,
                        critical_high=25.0
                    )
                }
            ])
        elif "gearbox" in equipment_id:
            properties.extend([
                # Ferro (desgaste)
                {
                    "name": "Ferro",
                    "unit": "ppm",
                    "base_value": 15.0,
                    "variation": 10.0,
                    "thresholds": MeasurementThreshold(
                        warning_high=25.0,
                        alert_high=40.0,
                        critical_high=60.0
                    )
                },
                # Cobre (desgaste)
                {
                    "name": "Cobre",
                    "unit": "ppm",
                    "base_value": 8.0,
                    "variation": 5.0,
                    "thresholds": MeasurementThreshold(
                        warning_high=15.0,
                        alert_high=25.0,
                        critical_high=40.0
                    )
                }
            ])
        elif "hydraulic" in equipment_id:
            properties.extend([
                # Limpeza
                {
                    "name": "NAS 1638",
                    "unit": "classe",
                    "base_value": 7.0,
                    "variation": 2.0,
                    "thresholds": MeasurementThreshold(
                        warning_high=9.0,
                        alert_high=10.0,
                        critical_high=12.0
                    )
                }
            ])
        
        # Ajustar valores com base no tipo de amostra
        for prop_def in properties:
            base_value = prop_def["base_value"]
            variation = prop_def["variation"]
            
            # Óleo novo tem valores mais próximos do ideal
            if sample_type == OilSampleType.NEW:
                value = base_value + random.uniform(-variation * 0.2, variation * 0.2)
            # Óleo filtrado tem valores melhores que em serviço
            elif sample_type == OilSampleType.FILTERED:
                value = base_value + random.uniform(-variation * 0.5, variation * 0.3)
            # Óleo em serviço pode ter valores mais degradados
            else:
                value = base_value + random.uniform(-variation * 0.3, variation * 1.0)
            
            # Criar a propriedade
            prop = OilProperty(
                name=prop_def["name"],
                value=round(value, 2),
                unit=prop_def["unit"],
                thresholds=prop_def["thresholds"]
            )
            
            # Avaliar status da propriedade
            prop.evaluate_status()
            
            # Adicionar à análise
            analysis.properties.append(prop)
