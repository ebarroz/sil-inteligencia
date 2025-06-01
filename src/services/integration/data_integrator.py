"""
Integração de Múltiplas Fontes de Dados - SIL Predictive System
-------------------------------------------------------------
Este módulo implementa a integração unificada de múltiplas fontes de dados,
conforme requisito de "pegar as APIs dos banco de dados diferentes e colocar em uma entidade única
dentro do nosso banco de dados pessoal".
"""
import logging
from typing import List, Dict, Any, Optional, Union
from datetime import datetime, timedelta
import json
import requests
import pandas as pd
import numpy as np
import sqlite3
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

# Configuração de logging
logger = logging.getLogger(__name__)

class DataIntegrator:
    """Serviço para integração de múltiplas fontes de dados."""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Inicializa o serviço de integração de dados.
        
        Args:
            config: Configurações do serviço
        """
        self.config = config
        self.db_path = config.get("db_path", "data/sil_integrated.db")
        self.api_configs = config.get("api_configs", {})
        self.sync_interval = config.get("sync_interval", 3600)  # Padrão: 1 hora
        self.max_workers = config.get("max_workers", 5)
        self.last_sync = {}
        
        # Garante que o diretório do banco de dados existe
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        # Inicializa conexão com o banco de dados
        self._init_database()
        
        logger.info("Serviço de integração de dados inicializado")
    def _init_database(self):
        """Inicializa o banco de dados com as tabelas necessárias."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Tabela para armazenar metadados de sincronização
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS sync_metadata (
                source_id TEXT PRIMARY KEY,
                last_sync TIMESTAMP,
                status TEXT,
                records_processed INTEGER,
                error_message TEXT
            )
            ''')
            
            # Tabela unificada de equipamentos
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS unified_equipment (
                id TEXT PRIMARY KEY,
                source_id TEXT,
                source_system TEXT,
                tag TEXT,
                name TEXT,
                type TEXT,
                model TEXT,
                manufacturer TEXT,
                serial_number TEXT,
                installation_date TIMESTAMP,
                location TEXT,
                latitude REAL,
                longitude REAL,
                client_id TEXT,
                status TEXT,
                last_maintenance TIMESTAMP,
                next_maintenance TIMESTAMP,
                metadata TEXT,
                created_at TIMESTAMP,
                updated_at TIMESTAMP,
                UNIQUE(source_system, source_id)
            )
            ''')
            
            # Tabela unificada de medições
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS unified_measurements (
                id TEXT PRIMARY KEY,
                equipment_id TEXT,
                source_id TEXT,
                source_system TEXT,
                measurement_type TEXT,
                timestamp TIMESTAMP,
                value REAL,
                unit TEXT,
                status TEXT,
                metadata TEXT,
                created_at TIMESTAMP,
                FOREIGN KEY (equipment_id) REFERENCES unified_equipment (id)
            )
            ''')
            
            # Tabela unificada de alertas
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS unified_alerts (
                id TEXT PRIMARY KEY,
                equipment_id TEXT,
                source_id TEXT,
                source_system TEXT,
                timestamp TIMESTAMP,
                gravity TEXT,
                status TEXT,
                description TEXT,
                measurement_id TEXT,
                metadata TEXT,
                created_at TIMESTAMP,
                updated_at TIMESTAMP,
                FOREIGN KEY (equipment_id) REFERENCES unified_equipment (id)
            )
            ''')
            
            # Tabela unificada de clientes
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS unified_clients (
                id TEXT PRIMARY KEY,
                source_id TEXT,
                source_system TEXT,
                name TEXT,
                contact_name TEXT,
                contact_email TEXT,
                contact_phone TEXT,
                address TEXT,
                city TEXT,
                state TEXT,
                country TEXT,
                metadata TEXT,
                created_at TIMESTAMP,
                updated_at TIMESTAMP,
                UNIQUE(source_system, source_id)
            )
            ''')
            
            conn.commit()
            conn.close()
            
            logger.info("Banco de dados inicializado com sucesso")
            
        except Exception as e:
            logger.error(f"Erro ao inicializar banco de dados: {str(e)}")
            raise
    def sync_all_sources(self) -> Dict[str, Any]:
        """
        Sincroniza dados de todas as fontes configuradas.
        
        Returns:
            Dict[str, Any]: Resultados da sincronização
        """
        logger.info("Iniciando sincronização de todas as fontes")
        
        results = {}
        
        # Executa sincronização em paralelo
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_source = {
                executor.submit(self.sync_source, source_id): source_id
                for source_id in self.api_configs.keys()
            }
            
            for future in as_completed(future_to_source):
                source_id = future_to_source[future]
                try:
                    result = future.result()
                    results[source_id] = result
                except Exception as e:
                    logger.error(f"Erro ao sincronizar fonte {source_id}: {str(e)}")
                    results[source_id] = {
                        "status": "error",
                        "error": str(e),
                        "timestamp": datetime.utcnow().isoformat()
                    }
        
        logger.info(f"Sincronização de todas as fontes concluída: {len(results)} fontes processadas")
        return results
    def sync_source(self, source_id: str) -> Dict[str, Any]:
        """
        Sincroniza dados de uma fonte específica.
        
        Args:
            source_id: Identificador da fonte
            
        Returns:
            Dict[str, Any]: Resultados da sincronização
        """
        if source_id not in self.api_configs:
            raise ValueError(f"Fonte não configurada: {source_id}")
        
        source_config = self.api_configs[source_id]
        logger.info(f"Iniciando sincronização da fonte: {source_id}")
        
        # Verifica se é hora de sincronizar
        last_sync_time = self.last_sync.get(source_id)
        current_time = time.time()
        
        if last_sync_time and (current_time - last_sync_time) < self.sync_interval:
            logger.info(f"Sincronização recente para {source_id}, pulando")
            return {
                "status": "skipped",
                "reason": "recent_sync",
                "last_sync": datetime.fromtimestamp(last_sync_time).isoformat(),
                "timestamp": datetime.utcnow().isoformat()
            }
        
        # Registra início da sincronização
        self.last_sync[source_id] = current_time
        
        # Determina o tipo de fonte e chama o método apropriado
        source_type = source_config.get("type", "api")
        
        try:
            if source_type == "api":
                result = self._sync_api_source(source_id, source_config)
            elif source_type == "database":
                result = self._sync_database_source(source_id, source_config)
            elif source_type == "file":
                result = self._sync_file_source(source_id, source_config)
            else:
                raise ValueError(f"Tipo de fonte não suportado: {source_type}")
            
            # Atualiza metadados de sincronização
            self._update_sync_metadata(source_id, "success", result.get("records_processed", 0))
            
            logger.info(f"Sincronização da fonte {source_id} concluída com sucesso")
            return {
                "status": "success",
                "records_processed": result.get("records_processed", 0),
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Erro ao sincronizar fonte {source_id}: {str(e)}")
            
            # Atualiza metadados de sincronização
            self._update_sync_metadata(source_id, "error", 0, str(e))
            
            raise
    def _sync_api_source(self, source_id: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sincroniza dados de uma fonte API REST.
        
        Args:
            source_id: Identificador da fonte
            config: Configuração da fonte
            
        Returns:
            Dict[str, Any]: Resultados da sincronização
        """
        base_url = config.get("base_url")
        if not base_url:
            raise ValueError(f"URL base não configurada para fonte {source_id}")
        
        headers = config.get("headers", {})
        auth = None
        
        # Configura autenticação se necessário
        auth_type = config.get("auth_type")
        if auth_type == "basic":
            auth = (config.get("username"), config.get("password"))
        elif auth_type == "token":
            headers["Authorization"] = f"Bearer {config.get('token')}"
        
        # Obtém endpoints para cada tipo de dado
        endpoints = config.get("endpoints", {})
        
        records_processed = 0
        
        # Sincroniza equipamentos
        if "equipment" in endpoints:
            equipment_endpoint = endpoints["equipment"]
            equipment_data = self._fetch_api_data(base_url, equipment_endpoint, headers, auth)
            equipment_mapping = config.get("mappings", {}).get("equipment", {})
            self._process_equipment_data(source_id, equipment_data, equipment_mapping)
            records_processed += len(equipment_data)
        
        # Sincroniza medições
        if "measurements" in endpoints:
            measurements_endpoint = endpoints["measurements"]
            measurements_data = self._fetch_api_data(base_url, measurements_endpoint, headers, auth)
            measurements_mapping = config.get("mappings", {}).get("measurements", {})
            self._process_measurements_data(source_id, measurements_data, measurements_mapping)
            records_processed += len(measurements_data)
        
        # Sincroniza alertas
        if "alerts" in endpoints:
            alerts_endpoint = endpoints["alerts"]
            alerts_data = self._fetch_api_data(base_url, alerts_endpoint, headers, auth)
            alerts_mapping = config.get("mappings", {}).get("alerts", {})
            self._process_alerts_data(source_id, alerts_data, alerts_mapping)
            records_processed += len(alerts_data)
        
        # Sincroniza clientes
        if "clients" in endpoints:
            clients_endpoint = endpoints["clients"]
            clients_data = self._fetch_api_data(base_url, clients_endpoint, headers, auth)
            clients_mapping = config.get("mappings", {}).get("clients", {})
            self._process_clients_data(source_id, clients_data, clients_mapping)
            records_processed += len(clients_data)
        
        return {
            "records_processed": records_processed
        }
    def _sync_database_source(self, source_id: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sincroniza dados de uma fonte de banco de dados.
        
        Args:
            source_id: Identificador da fonte
            config: Configuração da fonte
            
        Returns:
            Dict[str, Any]: Resultados da sincronização
        """
        db_type = config.get("db_type")
        connection_string = config.get("connection_string")
        
        if not db_type or not connection_string:
            raise ValueError(f"Configuração de banco de dados incompleta para fonte {source_id}")
        
        records_processed = 0
        
        try:
            # Implementação específica para cada tipo de banco de dados
            if db_type == "sqlite":
                records_processed = self._sync_sqlite_source(source_id, connection_string, config)
            elif db_type == "mysql":
                records_processed = self._sync_mysql_source(source_id, connection_string, config)
            elif db_type == "postgresql":
                records_processed = self._sync_postgresql_source(source_id, connection_string, config)
            else:
                raise ValueError(f"Tipo de banco de dados não suportado: {db_type}")
            
            return {
                "records_processed": records_processed
            }
            
        except Exception as e:
            logger.error(f"Erro ao sincronizar banco de dados {source_id}: {str(e)}")
            raise
    def _sync_file_source(self, source_id: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sincroniza dados de uma fonte de arquivos.
        
        Args:
            source_id: Identificador da fonte
            config: Configuração da fonte
            
        Returns:
            Dict[str, Any]: Resultados da sincronização
        """
        file_type = config.get("file_type")
        file_path = config.get("file_path")
        
        if not file_type or not file_path:
            raise ValueError(f"Configuração de arquivo incompleta para fonte {source_id}")
        
        records_processed = 0
        
        try:
            # Implementação específica para cada tipo de arquivo
            if file_type == "csv":
                records_processed = self._sync_csv_source(source_id, file_path, config)
            elif file_type == "json":
                records_processed = self._sync_json_source(source_id, file_path, config)
            elif file_type == "excel":
                records_processed = self._sync_excel_source(source_id, file_path, config)
            else:
                raise ValueError(f"Tipo de arquivo não suportado: {file_type}")
            
            return {
                "records_processed": records_processed
            }
            
        except Exception as e:
            logger.error(f"Erro ao sincronizar arquivo {source_id}: {str(e)}")
            raise
    def _fetch_api_data(self, base_url: str, endpoint: str, headers: Dict[str, str] = None, 
                       auth: tuple = None) -> List[Dict[str, Any]]:
        """
        Busca dados de um endpoint de API.
        
        Args:
            base_url: URL base da API
            endpoint: Endpoint específico
            headers: Cabeçalhos HTTP
            auth: Autenticação (usuário, senha)
            
        Returns:
            List[Dict[str, Any]]: Dados obtidos da API
        """
        url = f"{base_url.rstrip('/')}/{endpoint.lstrip('/')}"
        
        try:
            response = requests.get(url, headers=headers, auth=auth, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            
            # Verifica se a resposta é uma lista ou um objeto com uma lista
            if isinstance(data, list):
                return data
            elif isinstance(data, dict):
                # Tenta encontrar a lista de dados no objeto
                for key, value in data.items():
                    if isinstance(value, list) and value:
                        return value
                
                # Se não encontrar uma lista, retorna o objeto em uma lista
                return [data]
            else:
                return []
                
        except Exception as e:
            logger.error(f"Erro ao buscar dados da API {url}: {str(e)}")
            raise
    def _process_equipment_data(self, source_id: str, data: List[Dict[str, Any]], 
                               mapping: Dict[str, str]) -> int:
        """
        Processa e armazena dados de equipamentos.
        
        Args:
            source_id: Identificador da fonte
            data: Dados de equipamentos
            mapping: Mapeamento de campos
            
        Returns:
            int: Número de registros processados
        """
        if not data:
            return 0
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        count = 0
        
        for item in data:
            try:
                # Mapeia campos da fonte para campos unificados
                unified_data = self._map_fields(item, mapping)
                
                # Adiciona campos de metadados
                unified_data["source_id"] = item.get("id") or item.get("equipment_id") or str(count)
                unified_data["source_system"] = source_id
                unified_data["created_at"] = datetime.utcnow().isoformat()
                unified_data["updated_at"] = datetime.utcnow().isoformat()
                unified_data["id"] = f"{source_id}_{unified_data['source_id']}"
                
                # Converte metadados para JSON
                if "metadata" not in unified_data:
                    unified_data["metadata"] = json.dumps(item)
                elif not isinstance(unified_data["metadata"], str):
                    unified_data["metadata"] = json.dumps(unified_data["metadata"])
                
                # Insere ou atualiza no banco de dados
                self._upsert_equipment(cursor, unified_data)
                count += 1
                
            except Exception as e:
                logger.error(f"Erro ao processar equipamento: {str(e)}")
                continue
        
        conn.commit()
        conn.close()
        
        logger.info(f"Processados {count} equipamentos da fonte {source_id}")
        return count
    def _process_measurements_data(self, source_id: str, data: List[Dict[str, Any]], 
                                 mapping: Dict[str, str]) -> int:
        """
        Processa e armazena dados de medições.
        
        Args:
            source_id: Identificador da fonte
            data: Dados de medições
            mapping: Mapeamento de campos
            
        Returns:
            int: Número de registros processados
        """
        if not data:
            return 0
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        count = 0
        
        for item in data:
            try:
                # Mapeia campos da fonte para campos unificados
                unified_data = self._map_fields(item, mapping)
                
                # Adiciona campos de metadados
                unified_data["source_id"] = item.get("id") or item.get("measurement_id") or str(count)
                unified_data["source_system"] = source_id
                unified_data["created_at"] = datetime.utcnow().isoformat()
                
                # Gera ID unificado
                unified_data["id"] = f"{source_id}_measurement_{unified_data['source_id']}"
                
                # Obtém ID do equipamento
                equipment_source_id = item.get("equipment_id")
                if equipment_source_id:
                    unified_data["equipment_id"] = f"{source_id}_{equipment_source_id}"
                
                # Converte metadados para JSON
                if "metadata" not in unified_data:
                    unified_data["metadata"] = json.dumps(item)
                elif not isinstance(unified_data["metadata"], str):
                    unified_data["metadata"] = json.dumps(unified_data["metadata"])
                
                # Insere no banco de dados
                self._insert_measurement(cursor, unified_data)
                count += 1
                
            except Exception as e:
                logger.error(f"Erro ao processar medição: {str(e)}")
                continue
        
        conn.commit()
        conn.close()
        
        logger.info(f"Processadas {count} medições da fonte {source_id}")
        return count
    def _process_alerts_data(self, source_id: str, data: List[Dict[str, Any]], 
                           mapping: Dict[str, str]) -> int:
        """
        Processa e armazena dados de alertas.
        
        Args:
            source_id: Identificador da fonte
            data: Dados de alertas
            mapping: Mapeamento de campos
            
        Returns:
            int: Número de registros processados
        """
        if not data:
            return 0
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        count = 0
        
        for item in data:
            try:
                # Mapeia campos da fonte para campos unificados
                unified_data = self._map_fields(item, mapping)
                
                # Adiciona campos de metadados
                unified_data["source_id"] = item.get("id") or item.get("alert_id") or str(count)
                unified_data["source_system"] = source_id
                unified_data["created_at"] = datetime.utcnow().isoformat()
                unified_data["updated_at"] = datetime.utcnow().isoformat()
                
                # Gera ID unificado
                unified_data["id"] = f"{source_id}_alert_{unified_data['source_id']}"
                
                # Obtém ID do equipamento
                equipment_source_id = item.get("equipment_id")
                if equipment_source_id:
                    unified_data["equipment_id"] = f"{source_id}_{equipment_source_id}"
                
                # Converte metadados para JSON
                if "metadata" not in unified_data:
                    unified_data["metadata"] = json.dumps(item)
                elif not isinstance(unified_data["metadata"], str):
                    unified_data["metadata"] = json.dumps(unified_data["metadata"])
                
                # Insere ou atualiza no banco de dados
                self._upsert_alert(cursor, unified_data)
                count += 1
                
            except Exception as e:
                logger.error(f"Erro ao processar alerta: {str(e)}")
                continue
        
        conn.commit()
        conn.close()
        
        logger.info(f"Processados {count} alertas da fonte {source_id}")
        return count
    def _process_clients_data(self, source_id: str, data: List[Dict[str, Any]], 
                            mapping: Dict[str, str]) -> int:
        """
        Processa e armazena dados de clientes.
        
        Args:
            source_id: Identificador da fonte
            data: Dados de clientes
            mapping: Mapeamento de campos
            
        Returns:
            int: Número de registros processados
        """
        if not data:
            return 0
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        count = 0
        
        for item in data:
            try:
                # Mapeia campos da fonte para campos unificados
                unified_data = self._map_fields(item, mapping)
                
                # Adiciona campos de metadados
                unified_data["source_id"] = item.get("id") or item.get("client_id") or str(count)
                unified_data["source_system"] = source_id
                unified_data["created_at"] = datetime.utcnow().isoformat()
                unified_data["updated_at"] = datetime.utcnow().isoformat()
                
                # Gera ID unificado
                unified_data["id"] = f"{source_id}_client_{unified_data['source_id']}"
                
                # Converte metadados para JSON
                if "metadata" not in unified_data:
                    unified_data["metadata"] = json.dumps(item)
                elif not isinstance(unified_data["metadata"], str):
                    unified_data["metadata"] = json.dumps(unified_data["metadata"])
                
                # Insere ou atualiza no banco de dados
                self._upsert_client(cursor, unified_data)
                count += 1
                
            except Exception as e:
                logger.error(f"Erro ao processar cliente: {str(e)}")
                continue
        
        conn.commit()
        conn.close()
        
        logger.info(f"Processados {count} clientes da fonte {source_id}")
        return count
    def _map_fields(self, source_data: Dict[str, Any], mapping: Dict[str, str]) -> Dict[str, Any]:
        """
        Mapeia campos da fonte para campos unificados.
        
        Args:
            source_data: Dados da fonte
            mapping: Mapeamento de campos
            
        Returns:
            Dict[str, Any]: Dados mapeados
        """
        result = {}
        
        # Se não houver mapeamento, retorna os dados originais
        if not mapping:
            return source_data.copy()
        
        # Mapeia campos conforme configuração
        for target_field, source_field in mapping.items():
            if source_field in source_data:
                result[target_field] = source_data[source_field]
        
        return result
    
    def _upsert_equipment(self, cursor: sqlite3.Cursor, data: Dict[str, Any]) -> None:
        """
        Insere ou atualiza dados de equipamento no banco de dados.
        
        Args:
            cursor: Cursor do banco de dados
            data: Dados do equipamento
        """
        # Prepara campos e valores
        fields = list(data.keys())
        placeholders = ", ".join(["?" for _ in fields])
        values = [data[field] for field in fields]
        
        # Prepara cláusula de atualização
        update_clause = ", ".join([f"{field} = ?" for field in fields if field != "id"])
        update_values = [data[field] for field in fields if field != "id"]
        
        # Monta query
        query = f"""
        INSERT INTO unified_equipment ({", ".join(fields)})
        VALUES ({placeholders})
        ON CONFLICT(id) DO UPDATE SET
        {update_clause}
        """
        
        # Executa query
        cursor.execute(query, values + update_values)
    def _insert_measurement(self, cursor: sqlite3.Cursor, data: Dict[str, Any]) -> None:
        """
        Insere dados de medição no banco de dados.
        
        Args:
            cursor: Cursor do banco de dados
            data: Dados da medição
        """
        # Prepara campos e valores
        fields = list(data.keys())
        placeholders = ", ".join(["?" for _ in fields])
        values = [data[field] for field in fields]
        
        # Monta query
        query = f"""
        INSERT INTO unified_measurements ({", ".join(fields)})
        VALUES ({placeholders})
        """
        
        # Executa query
        cursor.execute(query, values)
    
    def _upsert_alert(self, cursor: sqlite3.Cursor, data: Dict[str, Any]) -> None:
        """
        Insere ou atualiza dados de alerta no banco de dados.
        
        Args:
            cursor: Cursor do banco de dados
            data: Dados do alerta
        """
        # Prepara campos e valores
        fields = list(data.keys())
        placeholders = ", ".join(["?" for _ in fields])
        values = [data[field] for field in fields]
        
        # Prepara cláusula de atualização
        update_clause = ", ".join([f"{field} = ?" for field in fields if field != "id"])
        update_values = [data[field] for field in fields if field != "id"]
        
        # Monta query
        query = f"""
        INSERT INTO unified_alerts ({", ".join(fields)})
        VALUES ({placeholders})
        ON CONFLICT(id) DO UPDATE SET
        {update_clause}
        """
        
        # Executa query
        cursor.execute(query, values + update_values)
    def _upsert_client(self, cursor: sqlite3.Cursor, data: Dict[str, Any]) -> None:
        """
        Insere ou atualiza dados de cliente no banco de dados.
        
        Args:
            cursor: Cursor do banco de dados
            data: Dados do cliente
        """
        # Prepara campos e valores
        fields = list(data.keys())
        placeholders = ", ".join(["?" for _ in fields])
        values = [data[field] for field in fields]
        
        # Prepara cláusula de atualização
        update_clause = ", ".join([f"{field} = ?" for field in fields if field != "id"])
        update_values = [data[field] for field in fields if field != "id"]
        
        # Monta query
        query = f"""
        INSERT INTO unified_clients ({", ".join(fields)})
        VALUES ({placeholders})
        ON CONFLICT(id) DO UPDATE SET
        {update_clause}
        """
        
        # Executa query
        cursor.execute(query, values + update_values)
    
    def _update_sync_metadata(self, source_id: str, status: str, 
                             records_processed: int = 0, 
                             error_message: str = None) -> None:
        """
        Atualiza metadados de sincronização no banco de dados.
        
        Args:
            source_id: Identificador da fonte
            status: Status da sincronização
            records_processed: Número de registros processados
            error_message: Mensagem de erro (se houver)
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        now = datetime.utcnow().isoformat()
        
        # Verifica se já existe registro para esta fonte
        cursor.execute(
            "SELECT source_id FROM sync_metadata WHERE source_id = ?",
            (source_id,)
        )
        
        if cursor.fetchone():
            # Atualiza registro existente
            cursor.execute(
                """
                UPDATE sync_metadata
                SET last_sync = ?, status = ?, records_processed = ?, error_message = ?
                WHERE source_id = ?
                """,
                (now, status, records_processed, error_message, source_id)
            )
        else:
            # Insere novo registro
            cursor.execute(
                """
                INSERT INTO sync_metadata
                (source_id, last_sync, status, records_processed, error_message)
                VALUES (?, ?, ?, ?, ?)
                """,
                (source_id, now, status, records_processed, error_message)
            )
        
        conn.commit()
        conn.close()
