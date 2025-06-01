"""
Cliente específico para integração com APIs de vibração.

Este módulo implementa um cliente para consumo de APIs de vibração,
utilizando o cliente genérico como base e adicionando funcionalidades
específicas para este tipo de medição.
"""

import logging
import random
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Union
import uuid
import math

from ..api_client import APIClient
from ....models.vibration.model import (
    VibrationMeasurement, VibrationReading, FrequencySpectrum,
    VibrationAxis, VibrationUnit
)
from ....models.base import MeasurementStatus, MeasurementSource, MeasurementThreshold

# Configuração de logging
logger = logging.getLogger(__name__)


class VibrationAPIClient:
    """Cliente para APIs de vibração."""
    
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
        Inicializa o cliente de API de vibração.
        
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
        
        logger.info(f"VibrationAPIClient inicializado. Modo simulação: {simulate}")
    
    def get_measurements(
        self,
        equipment_id: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100,
        status: Optional[str] = None,
        measurement_point: Optional[str] = None
    ) -> List[VibrationMeasurement]:
        """
        Obtém medições de vibração.
        
        Args:
            equipment_id: ID do equipamento (opcional)
            start_date: Data de início (opcional)
            end_date: Data de fim (opcional)
            limit: Limite de resultados
            status: Filtro por status (opcional)
            measurement_point: Ponto de medição (opcional)
            
        Returns:
            Lista de medições de vibração
        """
        if self.simulate:
            return self._simulate_measurements(
                equipment_id=equipment_id,
                start_date=start_date,
                end_date=end_date,
                limit=limit,
                status=status,
                measurement_point=measurement_point
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
            
        if measurement_point:
            params["measurement_point"] = measurement_point
        
        # Fazer requisição à API
        try:
            response = self.client.get(
                endpoint="vibration/data",
                params=params
            )
            
            # Converter resposta para objetos do modelo
            measurements = []
            for item in response.get("data", []):
                try:
                    measurement = VibrationMeasurement.from_dict(item)
                    measurements.append(measurement)
                except Exception as e:
                    logger.error(f"Erro ao converter medição de vibração: {e}")
            
            return measurements
            
        except Exception as e:
            logger.error(f"Erro ao obter medições de vibração: {e}")
            return []
    
    def get_measurement_by_id(self, measurement_id: str) -> Optional[VibrationMeasurement]:
        """
        Obtém uma medição específica pelo ID.
        
        Args:
            measurement_id: ID da medição
            
        Returns:
            Medição de vibração ou None se não encontrada
        """
        if self.simulate:
            # Gerar uma medição simulada com o ID fornecido
            return self._simulate_measurement(measurement_id=measurement_id)
        
        try:
            response = self.client.get(
                endpoint=f"vibration/data/{measurement_id}"
            )
            
            return VibrationMeasurement.from_dict(response)
            
        except Exception as e:
            logger.error(f"Erro ao obter medição de vibração {measurement_id}: {e}")
            return None
    
    def get_measurements_since(
        self,
        since_datetime: datetime,
        equipment_id: Optional[str] = None,
        limit: int = 100
    ) -> List[VibrationMeasurement]:
        """
        Obtém medições desde uma data específica.
        
        Args:
            since_datetime: Data a partir da qual obter medições
            equipment_id: ID do equipamento (opcional)
            limit: Limite de resultados
            
        Returns:
            Lista de medições de vibração
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
                endpoint="vibration/data",
                since_datetime=since_datetime,
                datetime_param="since",
                additional_params=params
            )
            
        except Exception as e:
            logger.error(f"Erro ao obter medições de vibração desde {since_datetime}: {e}")
            return []
    
    def _simulate_measurements(
        self,
        equipment_id: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 10,
        status: Optional[str] = None,
        measurement_point: Optional[str] = None
    ) -> List[VibrationMeasurement]:
        """
        Gera medições simuladas para testes.
        
        Args:
            equipment_id: ID do equipamento (opcional)
            start_date: Data de início (opcional)
            end_date: Data de fim (opcional)
            limit: Número de medições a gerar
            status: Status das medições (opcional)
            measurement_point: Ponto de medição (opcional)
            
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
        ] + [
            f"pump-{i:02d}" for i in range(1, 4)
        ] + [
            f"fan-{i:02d}" for i in range(1, 3)
        ]
        
        # Gerar pontos de medição se não fornecido
        measurement_points = [measurement_point] if measurement_point else [
            "DE-H", "DE-V", "DE-A",  # Drive End (Horizontal, Vertical, Axial)
            "NDE-H", "NDE-V", "NDE-A"  # Non-Drive End
        ]
        
        # Gerar medições simuladas
        measurements = []
        for _ in range(limit):
            # Selecionar um equipamento aleatório da lista
            eq_id = random.choice(equipment_ids)
            
            # Selecionar um ponto de medição aleatório
            meas_point = random.choice(measurement_points)
            
            # Gerar timestamp aleatório entre start_date e end_date
            time_range = (end_date - start_date).total_seconds()
            random_seconds = random.randint(0, int(time_range))
            timestamp = start_date + timedelta(seconds=random_seconds)
            
            # Gerar medição
            measurement = self._simulate_measurement(
                equipment_id=eq_id,
                timestamp=timestamp,
                status_value=status,
                measurement_point=meas_point
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
        status_value: Optional[str] = None,
        measurement_point: Optional[str] = None
    ) -> VibrationMeasurement:
        """
        Gera uma medição simulada para testes.
        
        Args:
            measurement_id: ID da medição (opcional)
            equipment_id: ID do equipamento (opcional)
            timestamp: Timestamp da medição (opcional)
            status_value: Status da medição (opcional)
            measurement_point: Ponto de medição (opcional)
            
        Returns:
            Medição simulada
        """
        # Gerar valores padrão se não fornecidos
        if not measurement_id:
            measurement_id = f"vib-{uuid.uuid4()}"
            
        if not equipment_id:
            equipment_id = f"motor-{random.randint(1, 5):02d}"
            
        if not timestamp:
            timestamp = datetime.utcnow() - timedelta(hours=random.randint(0, 720))
            
        if not measurement_point:
            measurement_point = random.choice(["DE-H", "DE-V", "DE-A", "NDE-H", "NDE-V", "NDE-A"])
        
        # Determinar RPM com base no tipo de equipamento
        rpm = 1800.0  # Padrão para motores de 4 polos
        
        if "pump" in equipment_id:
            rpm = 3600.0  # Bombas de alta velocidade
        elif "fan" in equipment_id:
            rpm = 1200.0  # Ventiladores de baixa velocidade
        
        # Adicionar variação aleatória ao RPM
        rpm_variation = random.uniform(-50.0, 50.0)
        rpm += rpm_variation
        
        # Determinar carga
        load = random.uniform(60.0, 95.0)
        
        # Criar a medição
        measurement = VibrationMeasurement(
            id=measurement_id,
            equipment_id=equipment_id,
            timestamp=timestamp,
            source=MeasurementSource.VIBRATION,
            sensor_id=f"accel-{random.randint(1000, 9999)}",
            sensor_type="Acelerômetro Piezoelétrico",
            measurement_point=measurement_point,
            rpm=round(rpm, 1),
            load=round(load, 1)
        )
        
        # Adicionar leituras de vibração
        self._add_vibration_readings(measurement, equipment_id, measurement_point)
        
        # Adicionar espectros de frequência
        self._add_frequency_spectra(measurement, equipment_id, measurement_point)
        
        # Avaliar status geral da medição
        measurement.status = measurement.evaluate_status()
        
        # Sobrescrever status se fornecido
        if status_value:
            measurement.status = MeasurementStatus(status_value)
        
        return measurement
    
    def _add_vibration_readings(
        self,
        measurement: VibrationMeasurement,
        equipment_id: str,
        measurement_point: str
    ) -> None:
        """
        Adiciona leituras de vibração à medição.
        
        Args:
            measurement: Medição de vibração
            equipment_id: ID do equipamento
            measurement_point: Ponto de medição
        """
        # Determinar eixos com base no ponto de medição
        axes = []
        if "H" in measurement_point:
            axes.append(VibrationAxis.HORIZONTAL)
        elif "V" in measurement_point:
            axes.append(VibrationAxis.VERTICAL)
        elif "A" in measurement_point:
            axes.append(VibrationAxis.AXIAL)
        else:
            # Se não especificado, incluir todos os eixos
            axes = [VibrationAxis.HORIZONTAL, VibrationAxis.VERTICAL, VibrationAxis.AXIAL]
        
        # Determinar valores base com base no tipo de equipamento e ponto de medição
        base_values = {
            "acceleration": 0.5,  # g
            "velocity": 3.0,      # mm/s
            "displacement": 20.0  # μm
        }
        
        # Ajustar valores base para diferentes tipos de equipamento
        if "pump" in equipment_id:
            base_values["acceleration"] = 0.8
            base_values["velocity"] = 4.0
            base_values["displacement"] = 25.0
        elif "fan" in equipment_id:
            base_values["acceleration"] = 0.6
            base_values["velocity"] = 5.0
            base_values["displacement"] = 30.0
        
        # Ajustar valores base para diferentes pontos de medição
        if "NDE" in measurement_point:  # Non-Drive End geralmente tem menos vibração
            base_values["acceleration"] *= 0.8
            base_values["velocity"] *= 0.8
            base_values["displacement"] *= 0.8
        
        # Adicionar leituras para cada eixo
        for axis in axes:
            # Aceleração
            accel_value = base_values["acceleration"] * random.uniform(0.7, 1.5)
            accel_thresholds = MeasurementThreshold(
                warning_high=1.0,
                alert_high=2.0,
                critical_high=4.0
            )
            
            accel_reading = VibrationReading(
                axis=axis,
                value=round(accel_value, 2),
                unit=VibrationUnit.ACCELERATION,
                frequency=None,  # Valor global
                thresholds=accel_thresholds
            )
            accel_reading.evaluate_status()
            measurement.readings.append(accel_reading)
            
            # Velocidade
            vel_value = base_values["velocity"] * random.uniform(0.7, 1.5)
            vel_thresholds = MeasurementThreshold(
                warning_high=4.5,
                alert_high=7.1,
                critical_high=11.0
            )
            
            vel_reading = VibrationReading(
                axis=axis,
                value=round(vel_value, 2),
                unit=VibrationUnit.VELOCITY,
                frequency=None,  # Valor global
                thresholds=vel_thresholds
            )
            vel_reading.evaluate_status()
            measurement.readings.append(vel_reading)
            
            # Deslocamento
            disp_value = base_values["displacement"] * random.uniform(0.7, 1.5)
            disp_thresholds = MeasurementThreshold(
                warning_high=40.0,
                alert_high=65.0,
                critical_high=100.0
            )
            
            disp_reading = VibrationReading(
                axis=axis,
                value=round(disp_value, 2),
                unit=VibrationUnit.DISPLACEMENT,
                frequency=None,  # Valor global
                thresholds=disp_thresholds
            )
            disp_reading.evaluate_status()
            measurement.readings.append(disp_reading)
    
    def _add_frequency_spectra(
        self,
        measurement: VibrationMeasurement,
        equipment_id: str,
        measurement_point: str
    ) -> None:
        """
        Adiciona espectros de frequência à medição.
        
        Args:
            measurement: Medição de vibração
            equipment_id: ID do equipamento
            measurement_point: Ponto de medição
        """
        # Determinar eixos com base no ponto de medição
        axes = []
        if "H" in measurement_point:
            axes.append(VibrationAxis.HORIZONTAL)
        elif "V" in measurement_point:
            axes.append(VibrationAxis.VERTICAL)
        elif "A" in measurement_point:
            axes.append(VibrationAxis.AXIAL)
        else:
            # Se não especificado, incluir todos os eixos
            axes = [VibrationAxis.HORIZONTAL, VibrationAxis.VERTICAL, VibrationAxis.AXIAL]
        
        # Frequência de rotação em Hz
        if measurement.rpm:
            rotation_freq = measurement.rpm / 60.0
        else:
            rotation_freq = 30.0  # Padrão: 1800 RPM = 30 Hz
        
        # Gerar espectro para cada eixo
        for axis in axes:
            # Gerar frequências de 0 a 1000 Hz com incremento de 0.5 Hz
            frequencies = [i * 0.5 for i in range(2001)]  # 0 a 1000 Hz
            
            # Inicializar amplitudes com ruído de fundo
            amplitudes = [random.uniform(0.01, 0.05) for _ in frequencies]
            
            # Adicionar picos nas frequências características
            self._add_characteristic_peaks(
                frequencies, amplitudes, rotation_freq, equipment_id, axis
            )
            
            # Criar o espectro
            spectrum = FrequencySpectrum(
                frequencies=frequencies,
                amplitudes=amplitudes,
                unit=VibrationUnit.VELOCITY,  # Espectros geralmente em velocidade
                axis=axis
            )
            
            # Adicionar à medição
            measurement.spectra.append(spectrum)
    
    def _add_characteristic_peaks(
        self,
        frequencies: List[float],
        amplitudes: List[float],
        rotation_freq: float,
        equipment_id: str,
        axis: VibrationAxis
    ) -> None:
        """
        Adiciona picos característicos ao espectro de frequência.
        
        Args:
            frequencies: Lista de frequências
            amplitudes: Lista de amplitudes
            rotation_freq: Frequência de rotação em Hz
            equipment_id: ID do equipamento
            axis: Eixo de medição
        """
        # Função para adicionar um pico gaussiano
        def add_peak(center_freq, amplitude, width=1.0):
            for i, freq in enumerate(frequencies):
                # Distância da frequência central
                dist = abs(freq - center_freq)
                # Aplicar função gaussiana
                if dist < width * 5:  # Limitar o cálculo para otimização
                    amplitudes[i] += amplitude * math.exp(-(dist**2) / (2 * width**2))
        
        # Adicionar pico na frequência de rotação (1x RPM)
        rpm_amplitude = random.uniform(0.5, 2.0)
        add_peak(rotation_freq, rpm_amplitude, 0.5)
        
        # Adicionar harmônicos (2x, 3x, 4x RPM)
        for harmonic in range(2, 5):
            harmonic_freq = rotation_freq * harmonic
            harmonic_amplitude = rpm_amplitude / harmonic * random.uniform(0.5, 1.5)
            add_peak(harmonic_freq, harmonic_amplitude, 0.5)
        
        # Adicionar picos específicos com base no tipo de equipamento
        if "motor" in equipment_id:
            # Frequência de linha (60 Hz) para motores elétricos
            line_freq = 60.0
            line_amplitude = random.uniform(0.3, 1.0)
            add_peak(line_freq, line_amplitude, 0.5)
            
            # Frequência de passagem de polos (para motores de indução)
            pole_pass_freq = line_freq * (1 - 0.03)  # 3% de escorregamento
            pole_amplitude = random.uniform(0.2, 0.8)
            add_peak(pole_pass_freq, pole_amplitude, 0.5)
            
        elif "pump" in equipment_id:
            # Frequência de passagem de pás (BPF)
            # Assumindo 5 pás
            blade_pass_freq = rotation_freq * 5
            blade_amplitude = random.uniform(0.8, 2.5)
            add_peak(blade_pass_freq, blade_amplitude, 1.0)
            
        elif "fan" in equipment_id:
            # Frequência de passagem de pás (BPF)
            # Assumindo 8 pás
            blade_pass_freq = rotation_freq * 8
            blade_amplitude = random.uniform(1.0, 3.0)
            add_peak(blade_pass_freq, blade_amplitude, 1.0)
        
        # Adicionar picos de rolamento (BPFI, BPFO, BSF, FTF)
        # Valores típicos para rolamentos
        bpfi_factor = 5.4  # Inner race defect
        bpfo_factor = 3.6  # Outer race defect
        bsf_factor = 2.8   # Ball defect
        ftf_factor = 0.4   # Cage defect
        
        # Adicionar com amplitudes baixas (falhas incipientes)
        if random.random() < 0.3:  # 30% de chance de ter algum defeito
            defect_type = random.choice(["bpfi", "bpfo", "bsf", "ftf"])
            
            if defect_type == "bpfi":
                add_peak(rotation_freq * bpfi_factor, random.uniform(0.2, 0.8), 0.5)
            elif defect_type == "bpfo":
                add_peak(rotation_freq * bpfo_factor, random.uniform(0.3, 1.0), 0.5)
            elif defect_type == "bsf":
                add_peak(rotation_freq * bsf_factor, random.uniform(0.2, 0.7), 0.5)
            elif defect_type == "ftf":
                add_peak(rotation_freq * ftf_factor, random.uniform(0.1, 0.5), 0.3)
        
        # Adicionar picos de ressonância estrutural
        resonance_freq = random.uniform(100, 500)
        resonance_amplitude = random.uniform(0.5, 3.0)
        add_peak(resonance_freq, resonance_amplitude, 2.0)
        
        # Adicionar picos específicos para cada eixo
        if axis == VibrationAxis.HORIZONTAL:
            # Desbalanceamento é mais pronunciado no plano horizontal
            add_peak(rotation_freq, rpm_amplitude * 1.5, 0.5)
        elif axis == VibrationAxis.VERTICAL:
            # Folga estrutural é mais pronunciada no plano vertical
            add_peak(rotation_freq * 2, rpm_amplitude * 1.2, 0.5)
        elif axis == VibrationAxis.AXIAL:
            # Desalinhamento é mais pronunciado no eixo axial
            add_peak(rotation_freq, rpm_amplitude * 0.8, 0.5)
            add_peak(rotation_freq * 2, rpm_amplitude * 1.0, 0.5)
