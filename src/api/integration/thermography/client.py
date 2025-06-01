"""
Cliente específico para integração com APIs de termografia.

Este módulo implementa um cliente para consumo de APIs de termografia,
utilizando o cliente genérico como base e adicionando funcionalidades
específicas para este tipo de medição.
"""

import logging
import random
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Union
import uuid

from ..api_client import APIClient
from ....models.thermography.model import ThermographyMeasurement, ThermographyPoint
from ....models.base import MeasurementStatus, MeasurementSource, MeasurementThreshold

# Configuração de logging
logger = logging.getLogger(__name__)


class ThermographyAPIClient:
    """Cliente para APIs de termografia."""
    
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
        Inicializa o cliente de API de termografia.
        
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
        
        logger.info(f"ThermographyAPIClient inicializado. Modo simulação: {simulate}")
    
    def get_measurements(
        self,
        equipment_id: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100,
        status: Optional[str] = None
    ) -> List[ThermographyMeasurement]:
        """
        Obtém medições de termografia.
        
        Args:
            equipment_id: ID do equipamento (opcional)
            start_date: Data de início (opcional)
            end_date: Data de fim (opcional)
            limit: Limite de resultados
            status: Filtro por status (opcional)
            
        Returns:
            Lista de medições de termografia
        """
        if self.simulate:
            return self._simulate_measurements(
                equipment_id=equipment_id,
                start_date=start_date,
                end_date=end_date,
                limit=limit,
                status=status
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
        
        # Fazer requisição à API
        try:
            response = self.client.get(
                endpoint="thermography/readings",
                params=params
            )
            
            # Converter resposta para objetos do modelo
            measurements = []
            for item in response.get("data", []):
                try:
                    measurement = ThermographyMeasurement.from_dict(item)
                    measurements.append(measurement)
                except Exception as e:
                    logger.error(f"Erro ao converter medição: {e}")
            
            return measurements
            
        except Exception as e:
            logger.error(f"Erro ao obter medições de termografia: {e}")
            return []
    
    def get_measurement_by_id(self, measurement_id: str) -> Optional[ThermographyMeasurement]:
        """
        Obtém uma medição específica pelo ID.
        
        Args:
            measurement_id: ID da medição
            
        Returns:
            Medição de termografia ou None se não encontrada
        """
        if self.simulate:
            # Gerar uma medição simulada com o ID fornecido
            return self._simulate_measurement(measurement_id=measurement_id)
        
        try:
            response = self.client.get(
                endpoint=f"thermography/readings/{measurement_id}"
            )
            
            return ThermographyMeasurement.from_dict(response)
            
        except Exception as e:
            logger.error(f"Erro ao obter medição de termografia {measurement_id}: {e}")
            return None
    
    def get_measurements_since(
        self,
        since_datetime: datetime,
        equipment_id: Optional[str] = None,
        limit: int = 100
    ) -> List[ThermographyMeasurement]:
        """
        Obtém medições desde uma data específica.
        
        Args:
            since_datetime: Data a partir da qual obter medições
            equipment_id: ID do equipamento (opcional)
            limit: Limite de resultados
            
        Returns:
            Lista de medições de termografia
        """
        if self.simulate:
            return self._simulate_measurements(
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
                endpoint="thermography/readings",
                since_datetime=since_datetime,
                datetime_param="since",
                additional_params=params
            )
            
        except Exception as e:
            logger.error(f"Erro ao obter medições de termografia desde {since_datetime}: {e}")
            return []
    
    def _simulate_measurements(
        self,
        equipment_id: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 10,
        status: Optional[str] = None
    ) -> List[ThermographyMeasurement]:
        """
        Gera medições simuladas para testes.
        
        Args:
            equipment_id: ID do equipamento (opcional)
            start_date: Data de início (opcional)
            end_date: Data de fim (opcional)
            limit: Número de medições a gerar
            status: Status das medições (opcional)
            
        Returns:
            Lista de medições simuladas
        """
        if not start_date:
            start_date = datetime.utcnow() - timedelta(days=30)
            
        if not end_date:
            end_date = datetime.utcnow()
        
        # Gerar IDs de equipamento se não fornecido
        equipment_ids = [equipment_id] if equipment_id else [
            f"motor-{i:02d}" for i in range(1, 6)
        ]
        
        # Gerar medições simuladas
        measurements = []
        for _ in range(limit):
            # Selecionar um equipamento aleatório da lista
            eq_id = random.choice(equipment_ids)
            
            # Gerar timestamp aleatório entre start_date e end_date
            time_range = (end_date - start_date).total_seconds()
            random_seconds = random.randint(0, int(time_range))
            timestamp = start_date + timedelta(seconds=random_seconds)
            
            # Gerar medição
            measurement = self._simulate_measurement(
                equipment_id=eq_id,
                timestamp=timestamp,
                status_value=status
            )
            
            measurements.append(measurement)
        
        # Ordenar por timestamp (mais recente primeiro)
        measurements.sort(key=lambda m: m.timestamp, reverse=True)
        
        return measurements
    
    def _simulate_measurement(
        self,
        measurement_id: Optional[str] = None,
        equipment_id: Optional[str] = None,
        timestamp: Optional[datetime] = None,
        status_value: Optional[str] = None
    ) -> ThermographyMeasurement:
        """
        Gera uma medição simulada para testes.
        
        Args:
            measurement_id: ID da medição (opcional)
            equipment_id: ID do equipamento (opcional)
            timestamp: Timestamp da medição (opcional)
            status_value: Status da medição (opcional)
            
        Returns:
            Medição simulada
        """
        # Gerar valores padrão se não fornecidos
        if not measurement_id:
            measurement_id = f"thermo-{uuid.uuid4()}"
            
        if not equipment_id:
            equipment_id = f"motor-{random.randint(1, 5):02d}"
            
        if not timestamp:
            timestamp = datetime.utcnow() - timedelta(hours=random.randint(0, 720))
        
        # Gerar valores aleatórios para a medição
        ambient_temp = round(random.uniform(20.0, 30.0), 1)
        humidity = round(random.uniform(40.0, 80.0), 1)
        
        # Criar a medição
        measurement = ThermographyMeasurement(
            id=measurement_id,
            equipment_id=equipment_id,
            timestamp=timestamp,
            source=MeasurementSource.THERMOGRAPHY,
            image_url=f"https://storage.example.com/thermography/{measurement_id}.jpg",
            ambient_temperature=ambient_temp,
            humidity=humidity,
            camera_model="FLIR T540",
            distance=round(random.uniform(0.5, 3.0), 1)
        )
        
        # Adicionar pontos de medição
        num_points = random.randint(3, 8)
        for i in range(num_points):
            # Gerar temperatura com base no componente
            base_temp = 0
            if "motor" in equipment_id:
                base_temp = 65.0  # Motores tendem a ser mais quentes
            elif "pump" in equipment_id:
                base_temp = 55.0  # Bombas um pouco menos
            else:
                base_temp = 45.0  # Outros equipamentos
            
            # Adicionar variação aleatória
            variation = random.uniform(-15.0, 25.0)
            temperature = round(base_temp + variation, 1)
            
            # Determinar nome do ponto com base na temperatura
            if temperature > 85.0:
                point_name = f"Ponto crítico {i+1}"
            elif temperature > 75.0:
                point_name = f"Rolamento {i+1}"
            elif temperature > 65.0:
                point_name = f"Conexão elétrica {i+1}"
            else:
                point_name = f"Ponto de referência {i+1}"
            
            # Criar thresholds para o ponto
            thresholds = MeasurementThreshold(
                warning_high=70.0,
                alert_high=80.0,
                critical_high=90.0
            )
            
            # Criar o ponto
            point = ThermographyPoint(
                id=f"{measurement_id}-point-{i+1}",
                name=point_name,
                x=random.uniform(10.0, 640.0),
                y=random.uniform(10.0, 480.0),
                temperature=temperature,
                emissivity=0.95,
                thresholds=thresholds
            )
            
            # Avaliar status do ponto
            point.evaluate_status()
            
            # Adicionar à medição
            measurement.points.append(point)
        
        # Avaliar status geral da medição
        measurement.status = measurement.evaluate_status()
        
        # Sobrescrever status se fornecido
        if status_value:
            measurement.status = MeasurementStatus(status_value)
        
        return measurement
