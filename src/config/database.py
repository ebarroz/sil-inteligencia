"""
Camada de persistência para o SIL Predictive System.

Este módulo implementa a interface com o banco de dados PostgreSQL/TimescaleDB
para armazenamento e recuperação de medições de termografia, óleo e vibração.
"""

import logging
from typing import List, Optional, Dict, Any, Union, Type
from datetime import datetime, timedelta
import json

import psycopg2
from psycopg2.extras import RealDictCursor, Json
from psycopg2 import pool

from ..models.base import MeasurementBase, MeasurementStatus, MeasurementSource
from ..models.thermography.model import ThermographyMeasurement, ThermographyPoint
from ..models.oil.model import OilAnalysisMeasurement, OilProperty
from ..models.vibration.model import VibrationMeasurement, VibrationReading, FrequencySpectrum

# Configuração de logging
logger = logging.getLogger(__name__)


class DatabaseManager:
    """Gerenciador de conexão com o banco de dados."""
    
    _instance = None
    
    def __new__(cls, *args, **kwargs):
        """Implementa padrão Singleton para garantir uma única instância."""
        if cls._instance is None:
            cls._instance = super(DatabaseManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(
        self,
        host: str = "localhost",
        port: int = 5432,
        database: str = "sil_predictive",
        user: str = "postgres",
        password: str = "postgres",
        min_connections: int = 1,
        max_connections: int = 10
    ):
        """
        Inicializa o gerenciador de banco de dados.
        
        Args:
            host: Host do banco de dados
            port: Porta do banco de dados
            database: Nome do banco de dados
            user: Usuário do banco de dados
            password: Senha do banco de dados
            min_connections: Número mínimo de conexões no pool
            max_connections: Número máximo de conexões no pool
        """
        if self._initialized:
            return
            
        self.connection_params = {
            "host": host,
            "port": port,
            "database": database,
            "user": user,
            "password": password
        }
        
        # Criar pool de conexões
        try:
            self.connection_pool = pool.ThreadedConnectionPool(
                min_connections,
                max_connections,
                **self.connection_params
            )
            logger.info(f"Pool de conexões criado com sucesso: {min_connections}-{max_connections} conexões")
        except Exception as e:
            logger.error(f"Erro ao criar pool de conexões: {e}")
            raise
            
        self._initialized = True
    
    def get_connection(self):
        """
        Obtém uma conexão do pool.
        
        Returns:
            Conexão com o banco de dados
        """
        try:
            connection = self.connection_pool.getconn()
            logger.debug("Conexão obtida do pool")
            return connection
        except Exception as e:
            logger.error(f"Erro ao obter conexão do pool: {e}")
            raise
    
    def release_connection(self, connection):
        """
        Devolve uma conexão ao pool.
        
        Args:
            connection: Conexão a ser devolvida
        """
        try:
            self.connection_pool.putconn(connection)
            logger.debug("Conexão devolvida ao pool")
        except Exception as e:
            logger.error(f"Erro ao devolver conexão ao pool: {e}")
            raise
    
    def close_all_connections(self):
        """Fecha todas as conexões no pool."""
        try:
            self.connection_pool.closeall()
            logger.info("Todas as conexões fechadas")
        except Exception as e:
            logger.error(f"Erro ao fechar conexões: {e}")
            raise
    
    def initialize_schema(self):
        """
        Inicializa o esquema do banco de dados.
        
        Cria as tabelas necessárias para o funcionamento do sistema.
        """
        connection = None
        try:
            connection = self.get_connection()
            cursor = connection.cursor()
            
            # Criar extensão TimescaleDB se não existir
            cursor.execute("CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;")
            
            # Criar tabela de equipamentos
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS equipment (
                    id VARCHAR(50) PRIMARY KEY,
                    name VARCHAR(100) NOT NULL,
                    type VARCHAR(50) NOT NULL,
                    location VARCHAR(100),
                    manufacturer VARCHAR(100),
                    model VARCHAR(100),
                    serial_number VARCHAR(100),
                    installation_date TIMESTAMP,
                    last_maintenance TIMESTAMP,
                    status VARCHAR(20),
                    metadata JSONB,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            
            # Criar tabela de medições (tabela base para hypertable)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS measurements (
                    id VARCHAR(50) PRIMARY KEY,
                    equipment_id VARCHAR(50) NOT NULL REFERENCES equipment(id),
                    timestamp TIMESTAMP NOT NULL,
                    source VARCHAR(20) NOT NULL,
                    status VARCHAR(20) NOT NULL,
                    metadata JSONB,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            
            # Converter para hypertable do TimescaleDB
            try:
                cursor.execute("""
                    SELECT create_hypertable('measurements', 'timestamp', 
                                            if_not_exists => TRUE);
                """)
            except Exception as e:
                logger.warning(f"Aviso ao criar hypertable: {e}")
            
            # Criar tabela de medições de termografia
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS thermography_measurements (
                    id VARCHAR(50) PRIMARY KEY REFERENCES measurements(id),
                    image_url VARCHAR(255),
                    ambient_temperature FLOAT,
                    humidity FLOAT,
                    camera_model VARCHAR(100),
                    distance FLOAT,
                    metadata JSONB
                );
            """)
            
            # Criar tabela de pontos de termografia
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS thermography_points (
                    id VARCHAR(50) PRIMARY KEY,
                    measurement_id VARCHAR(50) REFERENCES thermography_measurements(id),
                    name VARCHAR(100),
                    x FLOAT,
                    y FLOAT,
                    temperature FLOAT,
                    emissivity FLOAT,
                    status VARCHAR(20),
                    thresholds JSONB,
                    metadata JSONB
                );
            """)
            
            # Criar tabela de análises de óleo
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS oil_measurements (
                    id VARCHAR(50) PRIMARY KEY REFERENCES measurements(id),
                    sample_id VARCHAR(50),
                    sample_type VARCHAR(20),
                    oil_type VARCHAR(50),
                    oil_brand VARCHAR(100),
                    hours_in_service INTEGER,
                    sample_date TIMESTAMP,
                    analysis_date TIMESTAMP,
                    laboratory VARCHAR(100),
                    metadata JSONB
                );
            """)
            
            # Criar tabela de propriedades de óleo
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS oil_properties (
                    id SERIAL PRIMARY KEY,
                    measurement_id VARCHAR(50) REFERENCES oil_measurements(id),
                    name VARCHAR(100),
                    value FLOAT,
                    unit VARCHAR(20),
                    status VARCHAR(20),
                    thresholds JSONB,
                    metadata JSONB
                );
            """)
            
            # Criar tabela de medições de vibração
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS vibration_measurements (
                    id VARCHAR(50) PRIMARY KEY REFERENCES measurements(id),
                    sensor_id VARCHAR(50),
                    sensor_type VARCHAR(50),
                    measurement_point VARCHAR(20),
                    rpm FLOAT,
                    load FLOAT,
                    metadata JSONB
                );
            """)
            
            # Criar tabela de leituras de vibração
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS vibration_readings (
                    id SERIAL PRIMARY KEY,
                    measurement_id VARCHAR(50) REFERENCES vibration_measurements(id),
                    axis VARCHAR(20),
                    value FLOAT,
                    unit VARCHAR(20),
                    frequency FLOAT,
                    status VARCHAR(20),
                    thresholds JSONB,
                    metadata JSONB
                );
            """)
            
            # Criar tabela de espectros de frequência
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS frequency_spectra (
                    id SERIAL PRIMARY KEY,
                    measurement_id VARCHAR(50) REFERENCES vibration_measurements(id),
                    axis VARCHAR(20),
                    unit VARCHAR(20),
                    frequencies FLOAT[],
                    amplitudes FLOAT[],
                    metadata JSONB
                );
            """)
            
            # Criar índices para melhorar performance
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_measurements_equipment_id ON measurements(equipment_id);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_measurements_source ON measurements(source);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_measurements_status ON measurements(status);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_thermography_points_measurement_id ON thermography_points(measurement_id);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_oil_properties_measurement_id ON oil_properties(measurement_id);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_vibration_readings_measurement_id ON vibration_readings(measurement_id);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_frequency_spectra_measurement_id ON frequency_spectra(measurement_id);")
            
            connection.commit()
            logger.info("Esquema do banco de dados inicializado com sucesso")
            
        except Exception as e:
            if connection:
                connection.rollback()
            logger.error(f"Erro ao inicializar esquema do banco de dados: {e}")
            raise
        finally:
            if connection:
                self.release_connection(connection)


class MeasurementRepository:
    """Repositório para operações com medições."""
    
    def __init__(self, db_manager: Optional[DatabaseManager] = None):
        """
        Inicializa o repositório de medições.
        
        Args:
            db_manager: Gerenciador de banco de dados
        """
        self.db_manager = db_manager or DatabaseManager()
    
    def save_equipment(self, equipment_id: str, name: str, equipment_type: str, **kwargs) -> bool:
        """
        Salva ou atualiza informações de um equipamento.
        
        Args:
            equipment_id: ID do equipamento
            name: Nome do equipamento
            equipment_type: Tipo do equipamento
            **kwargs: Campos adicionais (location, manufacturer, model, etc.)
            
        Returns:
            True se a operação foi bem-sucedida, False caso contrário
        """
        connection = None
        try:
            connection = self.db_manager.get_connection()
            cursor = connection.cursor()
            
            # Verificar se o equipamento já existe
            cursor.execute(
                "SELECT id FROM equipment WHERE id = %s",
                (equipment_id,)
            )
            
            exists = cursor.fetchone() is not None
            
            # Preparar campos adicionais
            metadata = kwargs.pop("metadata", {})
            
            if exists:
                # Atualizar equipamento existente
                query = """
                    UPDATE equipment
                    SET name = %s,
                        type = %s,
                        updated_at = CURRENT_TIMESTAMP
                """
                
                params = [name, equipment_type]
                
                # Adicionar campos opcionais
                for key, value in kwargs.items():
                    if value is not None:
                        query += f", {key} = %s"
                        params.append(value)
                
                # Adicionar metadata
                if metadata:
                    query += ", metadata = %s"
                    params.append(Json(metadata))
                
                query += " WHERE id = %s"
                params.append(equipment_id)
                
                cursor.execute(query, params)
                
            else:
                # Inserir novo equipamento
                fields = ["id", "name", "type"]
                values = [equipment_id, name, equipment_type]
                
                # Adicionar campos opcionais
                for key, value in kwargs.items():
                    if value is not None:
                        fields.append(key)
                        values.append(value)
                
                # Adicionar metadata
                if metadata:
                    fields.append("metadata")
                    values.append(Json(metadata))
                
                placeholders = ", ".join(["%s"] * len(values))
                query = f"""
                    INSERT INTO equipment ({', '.join(fields)})
                    VALUES ({placeholders})
                """
                
                cursor.execute(query, values)
            
            connection.commit()
            logger.info(f"Equipamento {equipment_id} salvo com sucesso")
            return True
            
        except Exception as e:
            if connection:
                connection.rollback()
            logger.error(f"Erro ao salvar equipamento {equipment_id}: {e}")
            return False
        finally:
            if connection:
                self.db_manager.release_connection(connection)
    
    def save_thermography_measurement(self, measurement: ThermographyMeasurement) -> bool:
        """
        Salva uma medição de termografia no banco de dados.
        
        Args:
            measurement: Medição de termografia
            
        Returns:
            True se a operação foi bem-sucedida, False caso contrário
        """
        connection = None
        try:
            connection = self.db_manager.get_connection()
            cursor = connection.cursor()
            
            # Iniciar transação
            cursor.execute("BEGIN;")
            
            # Inserir na tabela base de medições
            cursor.execute("""
                INSERT INTO measurements (id, equipment_id, timestamp, source, status, metadata)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (id) DO UPDATE
                SET equipment_id = EXCLUDED.equipment_id,
                    timestamp = EXCLUDED.timestamp,
                    source = EXCLUDED.source,
                    status = EXCLUDED.status,
                    metadata = EXCLUDED.metadata
            """, (
                measurement.id,
                measurement.equipment_id,
                measurement.timestamp,
                measurement.source.value,
                measurement.status.value,
                Json(measurement.metadata) if measurement.metadata else None
            ))
            
            # Inserir na tabela de medições de termografia
            cursor.execute("""
                INSERT INTO thermography_measurements (
                    id, image_url, ambient_temperature, humidity, camera_model, distance, metadata
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (id) DO UPDATE
                SET image_url = EXCLUDED.image_url,
                    ambient_temperature = EXCLUDED.ambient_temperature,
                    humidity = EXCLUDED.humidity,
                    camera_model = EXCLUDED.camera_model,
                    distance = EXCLUDED.distance,
                    metadata = EXCLUDED.metadata
            """, (
                measurement.id,
                measurement.image_url,
                measurement.ambient_temperature,
                measurement.humidity,
                measurement.camera_model,
                measurement.distance,
                Json(measurement.metadata) if measurement.metadata else None
            ))
            
            # Remover pontos existentes para evitar duplicação
            cursor.execute("""
                DELETE FROM thermography_points
                WHERE measurement_id = %s
            """, (measurement.id,))
            
            # Inserir pontos de termografia
            for point in measurement.points:
                cursor.execute("""
                    INSERT INTO thermography_points (
                        id, measurement_id, name, x, y, temperature, emissivity, status, thresholds, metadata
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    point.id,
                    measurement.id,
                    point.name,
                    point.x,
                    point.y,
                    point.temperature,
                    point.emissivity,
                    point.status.value if point.status else None,
                    Json(point.thresholds.to_dict()) if point.thresholds else None,
                    Json(point.metadata) if point.metadata else None
                ))
            
            # Finalizar transação
            cursor.execute("COMMIT;")
            
            logger.info(f"Medição de termografia {measurement.id} salva com sucesso")
            return True
            
        except Exception as e:
            if connection:
                cursor.execute("ROLLBACK;")
            logger.error(f"Erro ao salvar medição de termografia {measurement.id}: {e}")
            return False
        finally:
            if connection:
                self.db_manager.release_connection(connection)
    
    def save_oil_measurement(self, measurement: OilAnalysisMeasurement) -> bool:
        """
        Salva uma análise de óleo no banco de dados.
        
        Args:
            measurement: Análise de óleo
            
        Returns:
            True se a operação foi bem-sucedida, False caso contrário
        """
        connection = None
        try:
            connection = self.db_manager.get_connection()
            cursor = connection.cursor()
            
            # Iniciar transação
            cursor.execute("BEGIN;")
            
            # Inserir na tabela base de medições
            cursor.execute("""
                INSERT INTO measurements (id, equipment_id, timestamp, source, status, metadata)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (id) DO UPDATE
                SET equipment_id = EXCLUDED.equipment_id,
                    timestamp = EXCLUDED.timestamp,
                    source = EXCLUDED.source,
                    status = EXCLUDED.status,
                    metadata = EXCLUDED.metadata
            """, (
                measurement.id,
                measurement.equipment_id,
                measurement.timestamp,
                measurement.source.value,
                measurement.status.value,
                Json(measurement.metadata) if measurement.metadata else None
            ))
            
            # Inserir na tabela de análises de óleo
            cursor.execute("""
                INSERT INTO oil_measurements (
                    id, sample_id, sample_type, oil_type, oil_brand, hours_in_service,
                    sample_date, analysis_date, laboratory, metadata
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (id) DO UPDATE
                SET sample_id = EXCLUDED.sample_id,
                    sample_type = EXCLUDED.sample_type,
                    oil_type = EXCLUDED.oil_type,
                    oil_brand = EXCLUDED.oil_brand,
                    hours_in_service = EXCLUDED.hours_in_service,
                    sample_date = EXCLUDED.sample_date,
                    analysis_date = EXCLUDED.analysis_date,
                    laboratory = EXCLUDED.laboratory,
                    metadata = EXCLUDED.metadata
            """, (
                measurement.id,
                measurement.sample_id,
                measurement.sample_type.value if measurement.sample_type else None,
                measurement.oil_type,
                measurement.oil_brand,
                measurement.hours_in_service,
                measurement.sample_date,
                measurement.analysis_date,
                measurement.laboratory,
                Json(measurement.metadata) if measurement.metadata else None
            ))
            
            # Remover propriedades existentes para evitar duplicação
            cursor.execute("""
                DELETE FROM oil_properties
                WHERE measurement_id = %s
            """, (measurement.id,))
            
            # Inserir propriedades de óleo
            for prop in measurement.properties:
                cursor.execute("""
                    INSERT INTO oil_properties (
                        measurement_id, name, value, unit, status, thresholds, metadata
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (
                    measurement.id,
                    prop.name,
                    prop.value,
                    prop.unit,
                    prop.status.value if prop.status else None,
                    Json(prop.thresholds.to_dict()) if prop.thresholds else None,
                    Json(prop.metadata) if prop.metadata else None
                ))
            
            # Finalizar transação
            cursor.execute("COMMIT;")
            
            logger.info(f"Análise de óleo {measurement.id} salva com sucesso")
            return True
            
        except Exception as e:
            if connection:
                cursor.execute("ROLLBACK;")
            logger.error(f"Erro ao salvar análise de óleo {measurement.id}: {e}")
            return False
        finally:
            if connection:
                self.db_manager.release_connection(connection)
    
    def save_vibration_measurement(self, measurement: VibrationMeasurement) -> bool:
        """
        Salva uma medição de vibração no banco de dados.
        
        Args:
            measurement: Medição de vibração
            
        Returns:
            True se a operação foi bem-sucedida, False caso contrário
        """
        connection = None
        try:
            connection = self.db_manager.get_connection()
            cursor = connection.cursor()
            
            # Iniciar transação
            cursor.execute("BEGIN;")
            
            # Inserir na tabela base de medições
            cursor.execute("""
                INSERT INTO measurements (id, equipment_id, timestamp, source, status, metadata)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (id) DO UPDATE
                SET equipment_id = EXCLUDED.equipment_id,
                    timestamp = EXCLUDED.timestamp,
                    source = EXCLUDED.source,
                    status = EXCLUDED.status,
                    metadata = EXCLUDED.metadata
            """, (
                measurement.id,
                measurement.equipment_id,
                measurement.timestamp,
                measurement.source.value,
                measurement.status.value,
                Json(measurement.metadata) if measurement.metadata else None
            ))
            
            # Inserir na tabela de medições de vibração
            cursor.execute("""
                INSERT INTO vibration_measurements (
                    id, sensor_id, sensor_type, measurement_point, rpm, load, metadata
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (id) DO UPDATE
                SET sensor_id = EXCLUDED.sensor_id,
                    sensor_type = EXCLUDED.sensor_type,
                    measurement_point = EXCLUDED.measurement_point,
                    rpm = EXCLUDED.rpm,
                    load = EXCLUDED.load,
                    metadata = EXCLUDED.metadata
            """, (
                measurement.id,
                measurement.sensor_id,
                measurement.sensor_type,
                measurement.measurement_point,
                measurement.rpm,
                measurement.load,
                Json(measurement.metadata) if measurement.metadata else None
            ))
            
            # Remover leituras existentes para evitar duplicação
            cursor.execute("""
                DELETE FROM vibration_readings
                WHERE measurement_id = %s
            """, (measurement.id,))
            
            # Inserir leituras de vibração
            for reading in measurement.readings:
                cursor.execute("""
                    INSERT INTO vibration_readings (
                        measurement_id, axis, value, unit, frequency, status, thresholds, metadata
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    measurement.id,
                    reading.axis.value if reading.axis else None,
                    reading.value,
                    reading.unit.value if reading.unit else None,
                    reading.frequency,
                    reading.status.value if reading.status else None,
                    Json(reading.thresholds.to_dict()) if reading.thresholds else None,
                    Json(reading.metadata) if reading.metadata else None
                ))
            
            # Remover espectros existentes para evitar duplicação
            cursor.execute("""
                DELETE FROM frequency_spectra
                WHERE measurement_id = %s
            """, (measurement.id,))
            
            # Inserir espectros de frequência
            for spectrum in measurement.spectra:
                cursor.execute("""
                    INSERT INTO frequency_spectra (
                        measurement_id, axis, unit, frequencies, amplitudes, metadata
                    )
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (
                    measurement.id,
                    spectrum.axis.value if spectrum.axis else None,
                    spectrum.unit.value if spectrum.unit else None,
                    spectrum.frequencies,
                    spectrum.amplitudes,
                    Json(spectrum.metadata) if spectrum.metadata else None
                ))
            
            # Finalizar transação
            cursor.execute("COMMIT;")
            
            logger.info(f"Medição de vibração {measurement.id} salva com sucesso")
            return True
            
        except Exception as e:
            if connection:
                cursor.execute("ROLLBACK;")
            logger.error(f"Erro ao salvar medição de vibração {measurement.id}: {e}")
            return False
        finally:
            if connection:
                self.db_manager.release_connection(connection)
    
    def get_thermography_measurement(self, measurement_id: str) -> Optional[ThermographyMeasurement]:
        """
        Obtém uma medição de termografia pelo ID.
        
        Args:
            measurement_id: ID da medição
            
        Returns:
            Medição de termografia ou None se não encontrada
        """
        connection = None
        try:
            connection = self.db_manager.get_connection()
            cursor = connection.cursor(cursor_factory=RealDictCursor)
            
            # Obter dados da medição
            cursor.execute("""
                SELECT m.id, m.equipment_id, m.timestamp, m.source, m.status, m.metadata as m_metadata,
                       t.image_url, t.ambient_temperature, t.humidity, t.camera_model, t.distance, t.metadata as t_metadata
                FROM measurements m
                JOIN thermography_measurements t ON m.id = t.id
                WHERE m.id = %s
            """, (measurement_id,))
            
            result = cursor.fetchone()
            
            if not result:
                return None
            
            # Criar objeto de medição
            measurement = ThermographyMeasurement(
                id=result["id"],
                equipment_id=result["equipment_id"],
                timestamp=result["timestamp"],
                source=MeasurementSource(result["source"]),
                status=MeasurementStatus(result["status"]),
                image_url=result["image_url"],
                ambient_temperature=result["ambient_temperature"],
                humidity=result["humidity"],
                camera_model=result["camera_model"],
                distance=result["distance"],
                metadata=result["m_metadata"] if result["m_metadata"] else {}
            )
            
            # Obter pontos de termografia
            cursor.execute("""
                SELECT id, name, x, y, temperature, emissivity, status, thresholds, metadata
                FROM thermography_points
                WHERE measurement_id = %s
            """, (measurement_id,))
            
            points = cursor.fetchall()
            
            for point_data in points:
                point = ThermographyPoint(
                    id=point_data["id"],
                    name=point_data["name"],
                    x=point_data["x"],
                    y=point_data["y"],
                    temperature=point_data["temperature"],
                    emissivity=point_data["emissivity"],
                    status=MeasurementStatus(point_data["status"]) if point_data["status"] else None,
                    thresholds=None,  # Será definido abaixo
                    metadata=point_data["metadata"] if point_data["metadata"] else {}
                )
                
                # Definir thresholds
                if point_data["thresholds"]:
                    point.thresholds = MeasurementThreshold.from_dict(point_data["thresholds"])
                
                measurement.points.append(point)
            
            return measurement
            
        except Exception as e:
            logger.error(f"Erro ao obter medição de termografia {measurement_id}: {e}")
            return None
        finally:
            if connection:
                self.db_manager.release_connection(connection)
    
    def get_oil_measurement(self, measurement_id: str) -> Optional[OilAnalysisMeasurement]:
        """
        Obtém uma análise de óleo pelo ID.
        
        Args:
            measurement_id: ID da análise
            
        Returns:
            Análise de óleo ou None se não encontrada
        """
        connection = None
        try:
            connection = self.db_manager.get_connection()
            cursor = connection.cursor(cursor_factory=RealDictCursor)
            
            # Obter dados da análise
            cursor.execute("""
                SELECT m.id, m.equipment_id, m.timestamp, m.source, m.status, m.metadata as m_metadata,
                       o.sample_id, o.sample_type, o.oil_type, o.oil_brand, o.hours_in_service,
                       o.sample_date, o.analysis_date, o.laboratory, o.metadata as o_metadata
                FROM measurements m
                JOIN oil_measurements o ON m.id = o.id
                WHERE m.id = %s
            """, (measurement_id,))
            
            result = cursor.fetchone()
            
            if not result:
                return None
            
            # Criar objeto de análise
            from ..models.oil.model import OilSampleType
            
            measurement = OilAnalysisMeasurement(
                id=result["id"],
                equipment_id=result["equipment_id"],
                timestamp=result["timestamp"],
                source=MeasurementSource(result["source"]),
                status=MeasurementStatus(result["status"]),
                sample_id=result["sample_id"],
                sample_type=OilSampleType(result["sample_type"]) if result["sample_type"] else None,
                oil_type=result["oil_type"],
                oil_brand=result["oil_brand"],
                hours_in_service=result["hours_in_service"],
                sample_date=result["sample_date"],
                analysis_date=result["analysis_date"],
                laboratory=result["laboratory"],
                metadata=result["m_metadata"] if result["m_metadata"] else {}
            )
            
            # Obter propriedades de óleo
            cursor.execute("""
                SELECT name, value, unit, status, thresholds, metadata
                FROM oil_properties
                WHERE measurement_id = %s
            """, (measurement_id,))
            
            properties = cursor.fetchall()
            
            for prop_data in properties:
                prop = OilProperty(
                    name=prop_data["name"],
                    value=prop_data["value"],
                    unit=prop_data["unit"],
                    status=MeasurementStatus(prop_data["status"]) if prop_data["status"] else None,
                    thresholds=None,  # Será definido abaixo
                    metadata=prop_data["metadata"] if prop_data["metadata"] else {}
                )
                
                # Definir thresholds
                if prop_data["thresholds"]:
                    prop.thresholds = MeasurementThreshold.from_dict(prop_data["thresholds"])
                
                measurement.properties.append(prop)
            
            return measurement
            
        except Exception as e:
            logger.error(f"Erro ao obter análise de óleo {measurement_id}: {e}")
            return None
        finally:
            if connection:
                self.db_manager.release_connection(connection)
    
    def get_vibration_measurement(self, measurement_id: str) -> Optional[VibrationMeasurement]:
        """
        Obtém uma medição de vibração pelo ID.
        
        Args:
            measurement_id: ID da medição
            
        Returns:
            Medição de vibração ou None se não encontrada
        """
        connection = None
        try:
            connection = self.db_manager.get_connection()
            cursor = connection.cursor(cursor_factory=RealDictCursor)
            
            # Obter dados da medição
            cursor.execute("""
                SELECT m.id, m.equipment_id, m.timestamp, m.source, m.status, m.metadata as m_metadata,
                       v.sensor_id, v.sensor_type, v.measurement_point, v.rpm, v.load, v.metadata as v_metadata
                FROM measurements m
                JOIN vibration_measurements v ON m.id = v.id
                WHERE m.id = %s
            """, (measurement_id,))
            
            result = cursor.fetchone()
            
            if not result:
                return None
            
            # Criar objeto de medição
            measurement = VibrationMeasurement(
                id=result["id"],
                equipment_id=result["equipment_id"],
                timestamp=result["timestamp"],
                source=MeasurementSource(result["source"]),
                status=MeasurementStatus(result["status"]),
                sensor_id=result["sensor_id"],
                sensor_type=result["sensor_type"],
                measurement_point=result["measurement_point"],
                rpm=result["rpm"],
                load=result["load"],
                metadata=result["m_metadata"] if result["m_metadata"] else {}
            )
            
            # Obter leituras de vibração
            cursor.execute("""
                SELECT axis, value, unit, frequency, status, thresholds, metadata
                FROM vibration_readings
                WHERE measurement_id = %s
            """, (measurement_id,))
            
            readings = cursor.fetchall()
            
            from ..models.vibration.model import VibrationAxis, VibrationUnit
            
            for reading_data in readings:
                reading = VibrationReading(
                    axis=VibrationAxis(reading_data["axis"]) if reading_data["axis"] else None,
                    value=reading_data["value"],
                    unit=VibrationUnit(reading_data["unit"]) if reading_data["unit"] else None,
                    frequency=reading_data["frequency"],
                    status=MeasurementStatus(reading_data["status"]) if reading_data["status"] else None,
                    thresholds=None,  # Será definido abaixo
                    metadata=reading_data["metadata"] if reading_data["metadata"] else {}
                )
                
                # Definir thresholds
                if reading_data["thresholds"]:
                    reading.thresholds = MeasurementThreshold.from_dict(reading_data["thresholds"])
                
                measurement.readings.append(reading)
            
            # Obter espectros de frequência
            cursor.execute("""
                SELECT axis, unit, frequencies, amplitudes, metadata
                FROM frequency_spectra
                WHERE measurement_id = %s
            """, (measurement_id,))
            
            spectra = cursor.fetchall()
            
            for spectrum_data in spectra:
                spectrum = FrequencySpectrum(
                    axis=VibrationAxis(spectrum_data["axis"]) if spectrum_data["axis"] else None,
                    unit=VibrationUnit(spectrum_data["unit"]) if spectrum_data["unit"] else None,
                    frequencies=spectrum_data["frequencies"],
                    amplitudes=spectrum_data["amplitudes"],
                    metadata=spectrum_data["metadata"] if spectrum_data["metadata"] else {}
                )
                
                measurement.spectra.append(spectrum)
            
            return measurement
            
        except Exception as e:
            logger.error(f"Erro ao obter medição de vibração {measurement_id}: {e}")
            return None
        finally:
            if connection:
                self.db_manager.release_connection(connection)
    
    def get_measurements(
        self,
        equipment_id: Optional[str] = None,
        source: Optional[Union[str, MeasurementSource]] = None,
        status: Optional[Union[str, MeasurementStatus]] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Obtém medições com base em filtros.
        
        Args:
            equipment_id: ID do equipamento (opcional)
            source: Fonte da medição (opcional)
            status: Status da medição (opcional)
            start_date: Data de início (opcional)
            end_date: Data de fim (opcional)
            limit: Limite de resultados
            offset: Deslocamento para paginação
            
        Returns:
            Lista de medições
        """
        connection = None
        try:
            connection = self.db_manager.get_connection()
            cursor = connection.cursor(cursor_factory=RealDictCursor)
            
            # Construir consulta
            query = """
                SELECT id, equipment_id, timestamp, source, status, metadata
                FROM measurements
                WHERE 1=1
            """
            
            params = []
            
            if equipment_id:
                query += " AND equipment_id = %s"
                params.append(equipment_id)
            
            if source:
                source_value = source.value if isinstance(source, MeasurementSource) else source
                query += " AND source = %s"
                params.append(source_value)
            
            if status:
                status_value = status.value if isinstance(status, MeasurementStatus) else status
                query += " AND status = %s"
                params.append(status_value)
            
            if start_date:
                query += " AND timestamp >= %s"
                params.append(start_date)
            
            if end_date:
                query += " AND timestamp <= %s"
                params.append(end_date)
            
            # Ordenar por timestamp (mais recente primeiro)
            query += " ORDER BY timestamp DESC"
            
            # Adicionar limite e offset
            query += " LIMIT %s OFFSET %s"
            params.extend([limit, offset])
            
            cursor.execute(query, params)
            
            return cursor.fetchall()
            
        except Exception as e:
            logger.error(f"Erro ao obter medições: {e}")
            return []
        finally:
            if connection:
                self.db_manager.release_connection(connection)
    
    def get_measurement_by_id(self, measurement_id: str) -> Optional[Dict[str, Any]]:
        """
        Obtém uma medição pelo ID.
        
        Args:
            measurement_id: ID da medição
            
        Returns:
            Medição ou None se não encontrada
        """
        connection = None
        try:
            connection = self.db_manager.get_connection()
            cursor = connection.cursor(cursor_factory=RealDictCursor)
            
            cursor.execute("""
                SELECT id, equipment_id, timestamp, source, status, metadata
                FROM measurements
                WHERE id = %s
            """, (measurement_id,))
            
            return cursor.fetchone()
            
        except Exception as e:
            logger.error(f"Erro ao obter medição {measurement_id}: {e}")
            return None
        finally:
            if connection:
                self.db_manager.release_connection(connection)
    
    def get_measurement_details(self, measurement_id: str) -> Optional[MeasurementBase]:
        """
        Obtém detalhes de uma medição pelo ID.
        
        Args:
            measurement_id: ID da medição
            
        Returns:
            Objeto de medição específico (ThermographyMeasurement, OilAnalysisMeasurement, VibrationMeasurement)
            ou None se não encontrada
        """
        # Primeiro, obter o tipo de medição
        basic_info = self.get_measurement_by_id(measurement_id)
        
        if not basic_info:
            return None
        
        source = basic_info["source"]
        
        # Obter detalhes específicos com base no tipo
        if source == MeasurementSource.THERMOGRAPHY.value:
            return self.get_thermography_measurement(measurement_id)
        elif source == MeasurementSource.OIL_ANALYSIS.value:
            return self.get_oil_measurement(measurement_id)
        elif source == MeasurementSource.VIBRATION.value:
            return self.get_vibration_measurement(measurement_id)
        else:
            logger.warning(f"Tipo de medição desconhecido: {source}")
            return None
    
    def delete_measurement(self, measurement_id: str) -> bool:
        """
        Exclui uma medição pelo ID.
        
        Args:
            measurement_id: ID da medição
            
        Returns:
            True se a operação foi bem-sucedida, False caso contrário
        """
        connection = None
        try:
            connection = self.db_manager.get_connection()
            cursor = connection.cursor()
            
            # Obter o tipo de medição
            cursor.execute("""
                SELECT source
                FROM measurements
                WHERE id = %s
            """, (measurement_id,))
            
            result = cursor.fetchone()
            
            if not result:
                logger.warning(f"Medição {measurement_id} não encontrada")
                return False
            
            source = result[0]
            
            # Iniciar transação
            cursor.execute("BEGIN;")
            
            # Excluir registros específicos com base no tipo
            if source == MeasurementSource.THERMOGRAPHY.value:
                cursor.execute("DELETE FROM thermography_points WHERE measurement_id = %s", (measurement_id,))
                cursor.execute("DELETE FROM thermography_measurements WHERE id = %s", (measurement_id,))
            elif source == MeasurementSource.OIL_ANALYSIS.value:
                cursor.execute("DELETE FROM oil_properties WHERE measurement_id = %s", (measurement_id,))
                cursor.execute("DELETE FROM oil_measurements WHERE id = %s", (measurement_id,))
            elif source == MeasurementSource.VIBRATION.value:
                cursor.execute("DELETE FROM frequency_spectra WHERE measurement_id = %s", (measurement_id,))
                cursor.execute("DELETE FROM vibration_readings WHERE measurement_id = %s", (measurement_id,))
                cursor.execute("DELETE FROM vibration_measurements WHERE id = %s", (measurement_id,))
            
            # Excluir da tabela base
            cursor.execute("DELETE FROM measurements WHERE id = %s", (measurement_id,))
            
            # Finalizar transação
            cursor.execute("COMMIT;")
            
            logger.info(f"Medição {measurement_id} excluída com sucesso")
            return True
            
        except Exception as e:
            if connection:
                cursor.execute("ROLLBACK;")
            logger.error(f"Erro ao excluir medição {measurement_id}: {e}")
            return False
        finally:
            if connection:
                self.db_manager.release_connection(connection)
    
    def get_equipment_list(
        self,
        equipment_type: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Obtém lista de equipamentos.
        
        Args:
            equipment_type: Tipo de equipamento (opcional)
            status: Status do equipamento (opcional)
            limit: Limite de resultados
            offset: Deslocamento para paginação
            
        Returns:
            Lista de equipamentos
        """
        connection = None
        try:
            connection = self.db_manager.get_connection()
            cursor = connection.cursor(cursor_factory=RealDictCursor)
            
            # Construir consulta
            query = """
                SELECT id, name, type, location, manufacturer, model, status, created_at, updated_at
                FROM equipment
                WHERE 1=1
            """
            
            params = []
            
            if equipment_type:
                query += " AND type = %s"
                params.append(equipment_type)
            
            if status:
                query += " AND status = %s"
                params.append(status)
            
            # Ordenar por nome
            query += " ORDER BY name"
            
            # Adicionar limite e offset
            query += " LIMIT %s OFFSET %s"
            params.extend([limit, offset])
            
            cursor.execute(query, params)
            
            return cursor.fetchall()
            
        except Exception as e:
            logger.error(f"Erro ao obter lista de equipamentos: {e}")
            return []
        finally:
            if connection:
                self.db_manager.release_connection(connection)
    
    def get_equipment_by_id(self, equipment_id: str) -> Optional[Dict[str, Any]]:
        """
        Obtém um equipamento pelo ID.
        
        Args:
            equipment_id: ID do equipamento
            
        Returns:
            Equipamento ou None se não encontrado
        """
        connection = None
        try:
            connection = self.db_manager.get_connection()
            cursor = connection.cursor(cursor_factory=RealDictCursor)
            
            cursor.execute("""
                SELECT *
                FROM equipment
                WHERE id = %s
            """, (equipment_id,))
            
            return cursor.fetchone()
            
        except Exception as e:
            logger.error(f"Erro ao obter equipamento {equipment_id}: {e}")
            return None
        finally:
            if connection:
                self.db_manager.release_connection(connection)
    
    def get_equipment_measurements(
        self,
        equipment_id: str,
        source: Optional[Union[str, MeasurementSource]] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Obtém medições de um equipamento específico.
        
        Args:
            equipment_id: ID do equipamento
            source: Fonte da medição (opcional)
            start_date: Data de início (opcional)
            end_date: Data de fim (opcional)
            limit: Limite de resultados
            offset: Deslocamento para paginação
            
        Returns:
            Lista de medições
        """
        return self.get_measurements(
            equipment_id=equipment_id,
            source=source,
            start_date=start_date,
            end_date=end_date,
            limit=limit,
            offset=offset
        )
    
    def get_latest_measurement(
        self,
        equipment_id: str,
        source: Optional[Union[str, MeasurementSource]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Obtém a medição mais recente de um equipamento.
        
        Args:
            equipment_id: ID do equipamento
            source: Fonte da medição (opcional)
            
        Returns:
            Medição mais recente ou None se não encontrada
        """
        measurements = self.get_measurements(
            equipment_id=equipment_id,
            source=source,
            limit=1
        )
        
        return measurements[0] if measurements else None
    
    def get_measurement_count(
        self,
        equipment_id: Optional[str] = None,
        source: Optional[Union[str, MeasurementSource]] = None,
        status: Optional[Union[str, MeasurementStatus]] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> int:
        """
        Obtém o número de medições com base em filtros.
        
        Args:
            equipment_id: ID do equipamento (opcional)
            source: Fonte da medição (opcional)
            status: Status da medição (opcional)
            start_date: Data de início (opcional)
            end_date: Data de fim (opcional)
            
        Returns:
            Número de medições
        """
        connection = None
        try:
            connection = self.db_manager.get_connection()
            cursor = connection.cursor()
            
            # Construir consulta
            query = """
                SELECT COUNT(*)
                FROM measurements
                WHERE 1=1
            """
            
            params = []
            
            if equipment_id:
                query += " AND equipment_id = %s"
                params.append(equipment_id)
            
            if source:
                source_value = source.value if isinstance(source, MeasurementSource) else source
                query += " AND source = %s"
                params.append(source_value)
            
            if status:
                status_value = status.value if isinstance(status, MeasurementStatus) else status
                query += " AND status = %s"
                params.append(status_value)
            
            if start_date:
                query += " AND timestamp >= %s"
                params.append(start_date)
            
            if end_date:
                query += " AND timestamp <= %s"
                params.append(end_date)
            
            cursor.execute(query, params)
            
            return cursor.fetchone()[0]
            
        except Exception as e:
            logger.error(f"Erro ao obter contagem de medições: {e}")
            return 0
        finally:
            if connection:
                self.db_manager.release_connection(connection)
    
    def get_measurements_by_status(
        self,
        status: Union[str, MeasurementStatus],
        source: Optional[Union[str, MeasurementSource]] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Obtém medições por status.
        
        Args:
            status: Status da medição
            source: Fonte da medição (opcional)
            limit: Limite de resultados
            offset: Deslocamento para paginação
            
        Returns:
            Lista de medições
        """
        return self.get_measurements(
            source=source,
            status=status,
            limit=limit,
            offset=offset
        )
    
    def get_measurements_since(
        self,
        since_datetime: datetime,
        equipment_id: Optional[str] = None,
        source: Optional[Union[str, MeasurementSource]] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Obtém medições desde uma data específica.
        
        Args:
            since_datetime: Data a partir da qual obter medições
            equipment_id: ID do equipamento (opcional)
            source: Fonte da medição (opcional)
            limit: Limite de resultados
            
        Returns:
            Lista de medições
        """
        return self.get_measurements(
            equipment_id=equipment_id,
            source=source,
            start_date=since_datetime,
            limit=limit
        )
