"""
Database API integration service for the SIL Predictive System.

This module unifies data from multiple database sources into a single entity.
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import uuid
import json
import requests
import asyncio
import aiohttp
from concurrent.futures import ThreadPoolExecutor

from ..models.equipment.equipment import EquipmentBase, EquipmentStatus, TrackingStatus
from ..models.measurements.model import MeasurementBase, MeasurementSource

# Configuração de logging
logger = logging.getLogger(__name__)

class DatabaseIntegrationService:
    """Serviço para integração de múltiplas fontes de dados em uma entidade única."""
    
    def __init__(self, db_manager, config):
        """
        Inicializa o serviço de integração de banco de dados.
        
        Args:
            db_manager: Gerenciador de banco de dados
            config: Configurações do serviço
        """
        self.db_manager = db_manager
        self.config = config
        self.api_clients = {}
        
        # Inicializar clientes de API
        self._initialize_api_clients()
        
        logger.info("Serviço de integração de banco de dados inicializado")
    
    def _initialize_api_clients(self):
        """Inicializa os clientes de API para cada fonte de dados."""
        try:
            # Inicializar cliente de termografia
            if 'thermography' in self.config:
                from ..clients.thermography_client import ThermographyClient
                self.api_clients['thermography'] = ThermographyClient(self.config['thermography'])
                logger.info("Cliente de API de termografia inicializado")
            
            # Inicializar cliente de análise de óleo
            if 'oil' in self.config:
                from ..clients.oil_client import OilClient
                self.api_clients['oil'] = OilClient(self.config['oil'])
                logger.info("Cliente de API de análise de óleo inicializado")
            
            # Inicializar cliente de vibração
            if 'vibration' in self.config:
                from ..clients.vibration_client import VibrationClient
                self.api_clients['vibration'] = VibrationClient(self.config['vibration'])
                logger.info("Cliente de API de vibração inicializado")
            
            # Inicializar outros clientes conforme necessário
            # ...
            
        except Exception as e:
            logger.error(f"Erro ao inicializar clientes de API: {e}")
    
    async def sync_equipment_data(
        self,
        client_id: Optional[str] = None,
        equipment_id: Optional[str] = None,
        force_full_sync: bool = False
    ) -> Dict[str, Any]:
        """
        Sincroniza dados de equipamentos de todas as fontes.
        
        Args:
            client_id: ID do cliente para sincronização seletiva (opcional)
            equipment_id: ID do equipamento para sincronização seletiva (opcional)
            force_full_sync: Se deve forçar sincronização completa, ignorando última sincronização
            
        Returns:
            Resultado da sincronização
        """
        try:
            # Determinar equipamentos para sincronização
            equipment_list = await self._get_equipment_for_sync(client_id, equipment_id)
            
            if not equipment_list:
                logger.warning("Nenhum equipamento encontrado para sincronização")
                return {
                    "success": True,
                    "message": "Nenhum equipamento encontrado para sincronização",
                    "sync_count": 0,
                    "errors": []
                }
            
            # Determinar última sincronização
            last_sync = None
            if not force_full_sync:
                last_sync = await self._get_last_sync_timestamp()
            
            # Sincronizar dados para cada equipamento
            results = []
            errors = []
            
            # Usar asyncio para sincronização paralela
            tasks = []
            for equipment in equipment_list:
                task = self._sync_single_equipment(equipment, last_sync)
                tasks.append(task)
            
            # Executar tarefas em paralelo
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Processar resultados
            success_count = 0
            for result in results:
                if isinstance(result, Exception):
                    errors.append(str(result))
                elif result.get("success", False):
                    success_count += 1
                else:
                    errors.append(result.get("message", "Erro desconhecido"))
            
            # Registrar timestamp da sincronização
            await self._update_sync_timestamp()
            
            return {
                "success": True,
                "message": f"Sincronização concluída para {success_count} de {len(equipment_list)} equipamentos",
                "sync_count": success_count,
                "errors": errors
            }
        except Exception as e:
            logger.error(f"Erro na sincronização de dados de equipamentos: {e}")
            return {
                "success": False,
                "message": f"Erro na sincronização: {str(e)}",
                "sync_count": 0,
                "errors": [str(e)]
            }
    
    async def _get_equipment_for_sync(
        self,
        client_id: Optional[str] = None,
        equipment_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Obtém lista de equipamentos para sincronização.
        
        Args:
            client_id: ID do cliente para filtrar (opcional)
            equipment_id: ID do equipamento específico (opcional)
            
        Returns:
            Lista de equipamentos para sincronização
        """
        try:
            with self.db_manager.get_connection() as conn:
                with conn.cursor() as cursor:
                    # Construir consulta base
                    query = """
                    SELECT
                        e.id, e.tag, e.name, e.type, e.model, e.manufacturer,
                        e.serial_number, e.client_id, e.status, e.tracking_status,
                        e.external_ids
                    FROM equipment e
                    WHERE 1=1
                    """
                    
                    # Construir cláusulas WHERE
                    params = []
                    
                    if client_id:
                        query += " AND e.client_id = %s"
                        params.append(client_id)
                    
                    if equipment_id:
                        query += " AND e.id = %s"
                        params.append(equipment_id)
                    
                    # Adicionar ordenação
                    query += " ORDER BY e.client_id, e.name"
                    
                    cursor.execute(query, params)
                    
                    equipment_list = []
                    for row in cursor.fetchall():
                        equipment_list.append({
                            "id": row[0],
                            "tag": row[1],
                            "name": row[2],
                            "type": row[3],
                            "model": row[4],
                            "manufacturer": row[5],
                            "serial_number": row[6],
                            "client_id": row[7],
                            "status": row[8],
                            "tracking_status": row[9],
                            "external_ids": row[10] or {}
                        })
                    
                    return equipment_list
        except Exception as e:
            logger.error(f"Erro ao obter equipamentos para sincronização: {e}")
            return []
    
    async def _get_last_sync_timestamp(self) -> Optional[datetime]:
        """
        Obtém timestamp da última sincronização.
        
        Returns:
            Timestamp da última sincronização ou None se não houver
        """
        try:
            with self.db_manager.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        SELECT value
                        FROM system_settings
                        WHERE key = 'last_data_sync'
                        """
                    )
                    
                    row = cursor.fetchone()
                    if not row:
                        return None
                    
                    try:
                        return datetime.fromisoformat(row[0])
                    except (ValueError, TypeError):
                        return None
        except Exception as e:
            logger.error(f"Erro ao obter timestamp da última sincronização: {e}")
            return None
    
    async def _update_sync_timestamp(self) -> bool:
        """
        Atualiza timestamp da última sincronização.
        
        Returns:
            True se atualizado com sucesso, False caso contrário
        """
        try:
            now = datetime.now().isoformat()
            
            with self.db_manager.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        INSERT INTO system_settings (key, value)
                        VALUES ('last_data_sync', %s)
                        ON CONFLICT (key)
                        DO UPDATE SET value = %s
                        """,
                        (now, now)
                    )
                    
                    conn.commit()
                    return True
        except Exception as e:
            logger.error(f"Erro ao atualizar timestamp de sincronização: {e}")
            return False
    
    async def _sync_single_equipment(
        self,
        equipment: Dict[str, Any],
        last_sync: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Sincroniza dados de um único equipamento de todas as fontes.
        
        Args:
            equipment: Informações do equipamento
            last_sync: Timestamp da última sincronização (opcional)
            
        Returns:
            Resultado da sincronização
        """
        try:
            equipment_id = equipment["id"]
            
            # Inicializar resultado
            result = {
                "equipment_id": equipment_id,
                "equipment_name": equipment["name"],
                "success": True,
                "sources_synced": [],
                "measurements_count": 0,
                "errors": []
            }
            
            # Sincronizar dados de cada fonte
            tasks = []
            for source_name, api_client in self.api_clients.items():
                # Verificar se o equipamento tem ID externo para esta fonte
                external_id = equipment.get("external_ids", {}).get(source_name)
                
                if external_id:
                    task = self._sync_from_source(
                        source_name=source_name,
                        api_client=api_client,
                        equipment=equipment,
                        external_id=external_id,
                        last_sync=last_sync
                    )
                    tasks.append(task)
            
            # Executar tarefas em paralelo
            source_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Processar resultados
            for source_result in source_results:
                if isinstance(source_result, Exception):
                    result["errors"].append(str(source_result))
                else:
                    result["sources_synced"].append(source_result["source"])
                    result["measurements_count"] += source_result["measurements_count"]
                    
                    if not source_result["success"]:
                        result["errors"].append(f"{source_result['source']}: {source_result['message']}")
            
            # Atualizar status de rastreamento do equipamento
            await self._update_equipment_tracking_status(equipment_id, result["sources_synced"])
            
            # Determinar sucesso geral
            result["success"] = len(result["errors"]) == 0
            
            return result
        except Exception as e:
            logger.error(f"Erro ao sincronizar equipamento {equipment['id']}: {e}")
            return {
                "equipment_id": equipment["id"],
                "equipment_name": equipment["name"],
                "success": False,
                "message": str(e),
                "sources_synced": [],
                "measurements_count": 0,
                "errors": [str(e)]
            }
    
    async def _sync_from_source(
        self,
        source_name: str,
        api_client: Any,
        equipment: Dict[str, Any],
        external_id: str,
        last_sync: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Sincroniza dados de uma fonte específica para um equipamento.
        
        Args:
            source_name: Nome da fonte de dados
            api_client: Cliente de API para a fonte
            equipment: Informações do equipamento
            external_id: ID externo do equipamento na fonte
            last_sync: Timestamp da última sincronização (opcional)
            
        Returns:
            Resultado da sincronização
        """
        try:
            # Determinar período de sincronização
            start_date = last_sync if last_sync else datetime.now() - timedelta(days=90)
            end_date = datetime.now()
            
            # Obter medições da fonte
            measurements = await self._get_measurements_from_source(
                source_name=source_name,
                api_client=api_client,
                external_id=external_id,
                start_date=start_date,
                end_date=end_date
            )
            
            if not measurements:
                return {
                    "source": source_name,
                    "success": True,
                    "message": "Nenhuma medição encontrada",
                    "measurements_count": 0
                }
            
            # Salvar medições no banco de dados
            saved_count = await self._save_measurements(
                equipment_id=equipment["id"],
                source_name=source_name,
                measurements=measurements
            )
            
            return {
                "source": source_name,
                "success": True,
                "message": f"{saved_count} medições sincronizadas",
                "measurements_count": saved_count
            }
        except Exception as e:
            logger.error(f"Erro ao sincronizar fonte {source_name} para equipamento {equipment['id']}: {e}")
            return {
                "source": source_name,
                "success": False,
                "message": str(e),
                "measurements_count": 0
            }
    
    async def _get_measurements_from_source(
        self,
        source_name: str,
        api_client: Any,
        external_id: str,
        start_date: datetime,
        end_date: datetime
    ) -> List[Dict[str, Any]]:
        """
        Obtém medições de uma fonte específica.
        
        Args:
            source_name: Nome da fonte de dados
            api_client: Cliente de API para a fonte
            external_id: ID externo do equipamento na fonte
            start_date: Data inicial
            end_date: Data final
            
        Returns:
            Lista de medições
        """
        try:
            # Executar em thread separada para operações bloqueantes
            with ThreadPoolExecutor() as executor:
                future = executor.submit(
                    api_client.get_measurements,
                    external_id=external_id,
                    start_date=start_date,
                    end_date=end_date
                )
                return future.result()
        except Exception as e:
            logger.error(f"Erro ao obter medições da fonte {source_name}: {e}")
            raise
    
    async def _save_measurements(
        self,
        equipment_id: str,
        source_name: str,
        measurements: List[Dict[str, Any]]
    ) -> int:
        """
        Salva medições no banco de dados.
        
        Args:
            equipment_id: ID do equipamento
            source_name: Nome da fonte de dados
            measurements: Lista de medições
            
        Returns:
            Número de medições salvas
        """
        try:
            saved_count = 0
            
            with self.db_manager.get_connection() as conn:
                with conn.cursor() as cursor:
                    # Obter histórico de medições atual
                    cursor.execute(
                        """
                        SELECT measurement_history
                        FROM equipment
                        WHERE id = %s
                        """,
                        (equipment_id,)
                    )
                    
                    row = cursor.fetchone()
                    if not row:
                        logger.warning(f"Equipamento {equipment_id} não encontrado")
                        return 0
                    
                    measurement_history = row[0] or []
                    
                    # Filtrar medições existentes
                    existing_ids = set()
                    for measurement in measurement_history:
                        if measurement.get("source") == source_name:
                            existing_ids.add(measurement.get("id"))
                    
                    # Adicionar novas medições
                    new_measurements = []
                    for measurement in measurements:
                        if measurement.get("id") not in existing_ids:
                            # Adicionar fonte e timestamp de sincronização
                            measurement["source"] = source_name
                            measurement["synced_at"] = datetime.now().isoformat()
                            
                            new_measurements.append(measurement)
                            existing_ids.add(measurement.get("id"))
                    
                    # Atualizar histórico de medições
                    if new_measurements:
                        updated_history = measurement_history + new_measurements
                        
                        cursor.execute(
                            """
                            UPDATE equipment
                            SET measurement_history = %s,
                                updated_at = NOW()
                            WHERE id = %s
                            """,
                            (updated_history, equipment_id)
                        )
                        
                        conn.commit()
                        saved_count = len(new_measurements)
            
            return saved_count
        except Exception as e:
            logger.error(f"Erro ao salvar medições para equipamento {equipment_id}: {e}")
            raise
    
    async def _update_equipment_tracking_status(
        self,
        equipment_id: str,
        synced_sources: List[str]
    ) -> bool:
        """
        Atualiza o status de rastreamento do equipamento com base nas fontes sincronizadas.
        
        Args:
            equipment_id: ID do equipamento
            synced_sources: Lista de fontes sincronizadas
            
        Returns:
            True se atualizado com sucesso, False caso contrário
        """
        try:
            # Determinar status de rastreamento com base nas fontes
            tracking_status = TrackingStatus.NOT_TRACKED
            
            if len(synced_sources) >= 3:
                tracking_status = TrackingStatus.FULLY_TRACKED
            elif len(synced_sources) >= 1:
                tracking_status = TrackingStatus.MINIMALLY_TRACKED
            
            # Atualizar status no banco de dados
            with self.db_manager.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        UPDATE equipment
                        SET tracking_status = %s,
                            updated_at = NOW()
                        WHERE id = %s
                        """,
                        (tracking_status.value, equipment_id)
                    )
                    
                    conn.commit()
                    return True
        except Exception as e:
            logger.error(f"Erro ao atualizar status de rastreamento do equipamento {equipment_id}: {e}")
            return False
    
    async def get_unified_measurements(
        self,
        equipment_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        sources: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Obtém medições unificadas de um equipamento.
        
        Args:
            equipment_id: ID do equipamento
            start_date: Data inicial (opcional)
            end_date: Data final (opcional)
            sources: Lista de fontes para filtrar (opcional)
            
        Returns:
            Medições unificadas
        """
        try:
            # Obter informações do equipamento
            equipment = await self._get_equipment_info(equipment_id)
            if not equipment:
                return {
                    "equipment_id": equipment_id,
                    "success": False,
                    "message": "Equipamento não encontrado",
                    "measurements": {}
                }
            
            # Obter histórico de medições
            measurement_history = equipment.get("measurement_history", [])
            
            # Filtrar por período
            if start_date or end_date:
                filtered_history = []
                for measurement in measurement_history:
                    try:
                        timestamp = datetime.fromisoformat(measurement["timestamp"])
                        
                        if start_date and timestamp < start_date:
                            continue
                        
                        if end_date and timestamp > end_date:
                            continue
                        
                        filtered_history.append(measurement)
                    except (ValueError, KeyError):
                        continue
                
                measurement_history = filtered_history
            
            # Filtrar por fonte
            if sources:
                measurement_history = [m for m in measurement_history if m.get("source") in sources]
            
            # Agrupar por fonte
            measurements_by_source = {}
            for measurement in measurement_history:
                source = measurement.get("source", "unknown")
                if source not in measurements_by_source:
                    measurements_by_source[source] = []
                
                measurements_by_source[source].append(measurement)
            
            # Ordenar medições por timestamp
            for source, measurements in measurements_by_source.items():
                measurements_by_source[source] = sorted(
                    measurements,
                    key=lambda m: datetime.fromisoformat(m["timestamp"])
                )
            
            return {
                "equipment_id": equipment_id,
                "equipment_name": equipment.get("name"),
                "success": True,
                "measurements": measurements_by_source
            }
        except Exception as e:
            logger.error(f"Erro ao obter medições unificadas para equipamento {equipment_id}: {e}")
            return {
                "equipment_id": equipment_id,
                "success": False,
                "message": str(e),
                "measurements": {}
            }
    
    async def _get_equipment_info(self, equipment_id: str) -> Optional[Dict[str, Any]]:
        """
        Obtém informações detalhadas de um equipamento.
        
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
                            serial_number, client_id, status, tracking_status,
                            external_ids, measurement_history
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
                        "serial_number": row[6],
                        "client_id": row[7],
                        "status": row[8],
                        "tracking_status": row[9],
                        "external_ids": row[10] or {},
                        "measurement_history": row[11] or []
                    }
        except Exception as e:
            logger.error(f"Erro ao obter informações do equipamento {equipment_id}: {e}")
            return None
    
    async def register_external_equipment(
        self,
        source_name: str,
        external_data: Dict[str, Any],
        client_id: str
    ) -> Dict[str, Any]:
        """
        Registra um equipamento externo no sistema.
        
        Args:
            source_name: Nome da fonte de dados
            external_data: Dados do equipamento na fonte externa
            client_id: ID do cliente
            
        Returns:
            Resultado do registro
        """
        try:
            # Verificar se o equipamento já existe
            external_id = external_data.get("id")
            if not external_id:
                return {
                    "success": False,
                    "message": "ID externo não fornecido"
                }
            
            existing_equipment = await self._find_equipment_by_external_id(source_name, external_id)
            
            if existing_equipment:
                # Atualizar equipamento existente
                return await self._update_equipment_external_data(
                    equipment_id=existing_equipment["id"],
                    source_name=source_name,
                    external_data=external_data
                )
            else:
                # Criar novo equipamento
                return await self._create_equipment_from_external(
                    source_name=source_name,
                    external_data=external_data,
                    client_id=client_id
                )
        except Exception as e:
            logger.error(f"Erro ao registrar equipamento externo: {e}")
            return {
                "success": False,
                "message": f"Erro ao registrar equipamento: {str(e)}"
            }
    
    async def _find_equipment_by_external_id(
        self,
        source_name: str,
        external_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Busca um equipamento pelo ID externo.
        
        Args:
            source_name: Nome da fonte de dados
            external_id: ID externo do equipamento
            
        Returns:
            Equipamento encontrado ou None
        """
        try:
            with self.db_manager.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        SELECT
                            id, tag, name, type, model, manufacturer,
                            serial_number, client_id, status, tracking_status,
                            external_ids
                        FROM equipment
                        WHERE external_ids->>%s = %s
                        """,
                        (source_name, external_id)
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
                        "serial_number": row[6],
                        "client_id": row[7],
                        "status": row[8],
                        "tracking_status": row[9],
                        "external_ids": row[10] or {}
                    }
        except Exception as e:
            logger.error(f"Erro ao buscar equipamento por ID externo: {e}")
            return None
    
    async def _update_equipment_external_data(
        self,
        equipment_id: str,
        source_name: str,
        external_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Atualiza dados externos de um equipamento.
        
        Args:
            equipment_id: ID do equipamento
            source_name: Nome da fonte de dados
            external_data: Dados do equipamento na fonte externa
            
        Returns:
            Resultado da atualização
        """
        try:
            with self.db_manager.get_connection() as conn:
                with conn.cursor() as cursor:
                    # Obter dados atuais do equipamento
                    cursor.execute(
                        """
                        SELECT external_ids, metadata
                        FROM equipment
                        WHERE id = %s
                        """,
                        (equipment_id,)
                    )
                    
                    row = cursor.fetchone()
                    if not row:
                        return {
                            "success": False,
                            "message": f"Equipamento {equipment_id} não encontrado"
                        }
                    
                    external_ids = row[0] or {}
                    metadata = row[1] or {}
                    
                    # Atualizar ID externo
                    external_ids[source_name] = external_data.get("id")
                    
                    # Atualizar metadados
                    if source_name not in metadata:
                        metadata[source_name] = {}
                    
                    metadata[source_name].update({
                        "last_updated": datetime.now().isoformat(),
                        "data": external_data
                    })
                    
                    # Atualizar no banco de dados
                    cursor.execute(
                        """
                        UPDATE equipment
                        SET external_ids = %s,
                            metadata = %s,
                            updated_at = NOW()
                        WHERE id = %s
                        """,
                        (external_ids, metadata, equipment_id)
                    )
                    
                    conn.commit()
                    
                    return {
                        "success": True,
                        "message": "Dados externos atualizados com sucesso",
                        "equipment_id": equipment_id
                    }
        except Exception as e:
            logger.error(f"Erro ao atualizar dados externos do equipamento {equipment_id}: {e}")
            return {
                "success": False,
                "message": f"Erro ao atualizar dados externos: {str(e)}"
            }
    
    async def _create_equipment_from_external(
        self,
        source_name: str,
        external_data: Dict[str, Any],
        client_id: str
    ) -> Dict[str, Any]:
        """
        Cria um novo equipamento a partir de dados externos.
        
        Args:
            source_name: Nome da fonte de dados
            external_data: Dados do equipamento na fonte externa
            client_id: ID do cliente
            
        Returns:
            Resultado da criação
        """
        try:
            # Gerar ID para o novo equipamento
            equipment_id = str(uuid.uuid4())
            
            # Mapear dados externos para modelo de equipamento
            equipment_data = {
                "id": equipment_id,
                "tag": external_data.get("tag") or f"{source_name}_{external_data.get('id')}",
                "name": external_data.get("name") or f"Equipamento {external_data.get('id')}",
                "type": external_data.get("type") or "UNKNOWN",
                "model": external_data.get("model"),
                "manufacturer": external_data.get("manufacturer"),
                "serial_number": external_data.get("serial_number"),
                "client_id": client_id,
                "status": EquipmentStatus.ACTIVE.value,
                "tracking_status": TrackingStatus.MINIMALLY_TRACKED.value,
                "external_ids": {source_name: external_data.get("id")},
                "metadata": {
                    source_name: {
                        "created_at": datetime.now().isoformat(),
                        "last_updated": datetime.now().isoformat(),
                        "data": external_data
                    }
                },
                "measurement_history": [],
                "maintenance_history": []
            }
            
            # Inserir no banco de dados
            with self.db_manager.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        INSERT INTO equipment (
                            id, tag, name, type, model, manufacturer,
                            serial_number, client_id, status, tracking_status,
                            external_ids, metadata, measurement_history,
                            maintenance_history, created_at, updated_at
                        ) VALUES (
                            %s, %s, %s, %s, %s, %s,
                            %s, %s, %s, %s,
                            %s, %s, %s,
                            %s, NOW(), NOW()
                        )
                        """,
                        (
                            equipment_data["id"],
                            equipment_data["tag"],
                            equipment_data["name"],
                            equipment_data["type"],
                            equipment_data["model"],
                            equipment_data["manufacturer"],
                            equipment_data["serial_number"],
                            equipment_data["client_id"],
                            equipment_data["status"],
                            equipment_data["tracking_status"],
                            equipment_data["external_ids"],
                            equipment_data["metadata"],
                            equipment_data["measurement_history"],
                            equipment_data["maintenance_history"]
                        )
                    )
                    
                    conn.commit()
                    
                    return {
                        "success": True,
                        "message": "Equipamento criado com sucesso",
                        "equipment_id": equipment_id
                    }
        except Exception as e:
            logger.error(f"Erro ao criar equipamento a partir de dados externos: {e}")
            return {
                "success": False,
                "message": f"Erro ao criar equipamento: {str(e)}"
            }

logger.info("Database integration service defined.")
"""
