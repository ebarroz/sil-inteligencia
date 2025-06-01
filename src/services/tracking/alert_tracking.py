"""
Sistema de Tracking de Alertas - SIL Predictive System
----------------------------------------------------
Este módulo implementa o sistema de visualização geográfica (mapa) e em lista dos alertas,
conforme requisito de "Trackeamento de alertas por mapa ou listas".
"""
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import json
import folium
from folium.plugins import MarkerCluster, HeatMap
import pandas as pd
import numpy as np

# Configuração de logging
logger = logging.getLogger(__name__)

class AlertTracker:
    """Serviço para tracking e visualização de alertas."""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Inicializa o serviço de tracking de alertas.
        
        Args:
            config: Configurações do serviço
        """
        self.config = config
        self.output_dir = config.get("output_dir", "tracking/output")
        self.default_zoom = config.get("default_zoom", 5)
        self.default_center = config.get("default_center", [-15.77972, -47.92972])  # Brasília
        logger.info("Serviço de tracking de alertas inicializado")
    def generate_alert_map(self, alerts: List[Dict[str, Any]], 
                          equipment_list: List[Dict[str, Any]],
                          clients: List[Dict[str, Any]] = None,
                          filter_criteria: Dict[str, Any] = None) -> str:
        """
        Gera um mapa interativo com a localização dos alertas.
        
        Args:
            alerts: Lista de alertas
            equipment_list: Lista de equipamentos
            clients: Lista de clientes (opcional)
            filter_criteria: Critérios de filtragem (opcional)
            
        Returns:
            str: Caminho para o arquivo HTML do mapa
        """
        logger.info(f"Gerando mapa de alertas com {len(alerts)} alertas")
        
        # Filtra alertas conforme critérios
        filtered_alerts = self._filter_alerts(alerts, filter_criteria)
        
        # Cria mapa base
        m = folium.Map(location=self.default_center, zoom_start=self.default_zoom)
        
        # Cria dicionário de equipamentos para acesso rápido
        equipment_dict = {eq.get("id"): eq for eq in equipment_list}
        
        # Cria dicionário de clientes para acesso rápido
        client_dict = {}
        if clients:
            client_dict = {client.get("id"): client for client in clients}
        
        # Agrupa alertas por localização
        location_groups = {}
        
        for alert in filtered_alerts:
            equipment_id = alert.get("equipment_id")
            equipment = equipment_dict.get(equipment_id, {})
            
            # Obtém coordenadas do equipamento
            lat = equipment.get("latitude")
            lng = equipment.get("longitude")
            
            if lat is not None and lng is not None:
                location_key = f"{lat},{lng}"
                
                if location_key not in location_groups:
                    location_groups[location_key] = {
                        "lat": lat,
                        "lng": lng,
                        "alerts": [],
                        "equipment": equipment,
                        "client": None
                    }
                
                location_groups[location_key]["alerts"].append(alert)
                
                # Adiciona informações do cliente se disponível
                if not location_groups[location_key]["client"] and clients:
                    client_id = equipment.get("client_id")
                    if client_id:
                        location_groups[location_key]["client"] = client_dict.get(client_id)
        # Cria cluster de marcadores
        marker_cluster = MarkerCluster().add_to(m)
        
        # Adiciona marcadores para cada localização
        for location_key, location_data in location_groups.items():
            lat = location_data["lat"]
            lng = location_data["lng"]
            alerts = location_data["alerts"]
            equipment = location_data["equipment"]
            client = location_data["client"]
            
            # Determina cor do marcador com base na gravidade mais alta
            color = self._get_marker_color(alerts)
            
            # Cria popup com informações dos alertas
            popup_html = self._create_popup_html(alerts, equipment, client)
            
            # Adiciona marcador ao cluster
            folium.Marker(
                location=[lat, lng],
                popup=folium.Popup(popup_html, max_width=300),
                icon=folium.Icon(color=color, icon="warning", prefix="fa"),
                tooltip=f"{len(alerts)} alertas - {equipment.get('tag', 'Desconhecido')}"
            ).add_to(marker_cluster)
        
        # Adiciona camada de calor se houver muitos alertas
        if len(filtered_alerts) > 10:
            heat_data = []
            
            for location_key, location_data in location_groups.items():
                lat = location_data["lat"]
                lng = location_data["lng"]
                weight = len(location_data["alerts"])
                
                # Ajusta peso com base na gravidade
                for alert in location_data["alerts"]:
                    gravity = alert.get("gravity", "P3")
                    if gravity == "P1":
                        weight += 2
                    elif gravity == "P2":
                        weight += 1
                
                heat_data.append([lat, lng, weight])
            
            # Adiciona camada de calor
            HeatMap(heat_data).add_to(m)
        
        # Adiciona controles de camadas
        folium.LayerControl().add_to(m)
        
        # Salva o mapa como HTML
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        output_filename = f"alert_map_{timestamp}.html"
        output_path = f"{self.output_dir}/{output_filename}"
        
        m.save(output_path)
        
        logger.info(f"Mapa de alertas gerado com sucesso: {output_path}")
        return output_path
    def generate_alert_list(self, alerts: List[Dict[str, Any]], 
                           equipment_list: List[Dict[str, Any]],
                           clients: List[Dict[str, Any]] = None,
                           filter_criteria: Dict[str, Any] = None,
                           output_format: str = "html") -> str:
        """
        Gera uma lista de alertas em formato HTML ou JSON.
        
        Args:
            alerts: Lista de alertas
            equipment_list: Lista de equipamentos
            clients: Lista de clientes (opcional)
            filter_criteria: Critérios de filtragem (opcional)
            output_format: Formato de saída (html ou json)
            
        Returns:
            str: Caminho para o arquivo de saída
        """
        logger.info(f"Gerando lista de alertas com {len(alerts)} alertas")
        
        # Filtra alertas conforme critérios
        filtered_alerts = self._filter_alerts(alerts, filter_criteria)
        
        # Cria dicionário de equipamentos para acesso rápido
        equipment_dict = {eq.get("id"): eq for eq in equipment_list}
        
        # Cria dicionário de clientes para acesso rápido
        client_dict = {}
        if clients:
            client_dict = {client.get("id"): client for client in clients}
        
        # Prepara dados para a lista
        alert_list_data = []
        
        for alert in filtered_alerts:
            equipment_id = alert.get("equipment_id")
            equipment = equipment_dict.get(equipment_id, {})
            
            client_id = equipment.get("client_id")
            client = client_dict.get(client_id, {}) if client_id else {}
            
            # Formata data e hora
            timestamp = alert.get("timestamp")
            formatted_date = ""
            if timestamp:
                try:
                    dt = datetime.fromisoformat(timestamp)
                    formatted_date = dt.strftime("%d/%m/%Y %H:%M:%S")
                except (ValueError, TypeError):
                    formatted_date = timestamp
            
            # Cria item da lista
            list_item = {
                "id": alert.get("id"),
                "timestamp": formatted_date,
                "gravity": alert.get("gravity", "P3"),
                "status": alert.get("status", "NEW"),
                "description": alert.get("description", ""),
                "equipment_tag": equipment.get("tag", ""),
                "equipment_name": equipment.get("name", ""),
                "client_name": client.get("name", ""),
                "location": f"{equipment.get('location', '')}"
            }
            
            alert_list_data.append(list_item)
        # Ordena por gravidade e data
        alert_list_data = sorted(
            alert_list_data, 
            key=lambda x: (
                {"P1": 0, "P2": 1, "P3": 2}.get(x["gravity"], 3),
                x["timestamp"]
            )
        )
        
        # Gera saída no formato solicitado
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        
        if output_format.lower() == "json":
            output_filename = f"alert_list_{timestamp}.json"
            output_path = f"{self.output_dir}/{output_filename}"
            
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(alert_list_data, f, ensure_ascii=False, indent=2)
        else:
            # Gera HTML
            output_filename = f"alert_list_{timestamp}.html"
            output_path = f"{self.output_dir}/{output_filename}"
            
            html_content = self._generate_alert_list_html(alert_list_data)
            
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(html_content)
        
        logger.info(f"Lista de alertas gerada com sucesso: {output_path}")
        return output_path
    def _filter_alerts(self, alerts: List[Dict[str, Any]], 
                      filter_criteria: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """
        Filtra alertas conforme critérios especificados.
        
        Args:
            alerts: Lista de alertas
            filter_criteria: Critérios de filtragem
            
        Returns:
            List[Dict[str, Any]]: Alertas filtrados
        """
        if not filter_criteria:
            return alerts
        
        filtered = alerts.copy()
        
        # Filtra por gravidade
        if "gravity" in filter_criteria:
            gravity_list = filter_criteria["gravity"]
            if not isinstance(gravity_list, list):
                gravity_list = [gravity_list]
            
            filtered = [a for a in filtered if a.get("gravity") in gravity_list]
        
        # Filtra por status
        if "status" in filter_criteria:
            status_list = filter_criteria["status"]
            if not isinstance(status_list, list):
                status_list = [status_list]
            
            filtered = [a for a in filtered if a.get("status") in status_list]
        
        # Filtra por período
        if "start_date" in filter_criteria:
            start_date = filter_criteria["start_date"]
            if isinstance(start_date, str):
                try:
                    start_date = datetime.fromisoformat(start_date)
                except ValueError:
                    start_date = None
            
            if start_date:
                filtered = [
                    a for a in filtered 
                    if a.get("timestamp") and datetime.fromisoformat(a["timestamp"]) >= start_date
                ]
        
        if "end_date" in filter_criteria:
            end_date = filter_criteria["end_date"]
            if isinstance(end_date, str):
                try:
                    end_date = datetime.fromisoformat(end_date)
                except ValueError:
                    end_date = None
            
            if end_date:
                filtered = [
                    a for a in filtered 
                    if a.get("timestamp") and datetime.fromisoformat(a["timestamp"]) <= end_date
                ]
        
        # Filtra por equipamento
        if "equipment_id" in filter_criteria:
            equipment_id_list = filter_criteria["equipment_id"]
            if not isinstance(equipment_id_list, list):
                equipment_id_list = [equipment_id_list]
            
            filtered = [a for a in filtered if a.get("equipment_id") in equipment_id_list]
        
        # Filtra por cliente
        if "client_id" in filter_criteria and "equipment_list" in filter_criteria:
            client_id_list = filter_criteria["client_id"]
            if not isinstance(client_id_list, list):
                client_id_list = [client_id_list]
            
            # Cria lista de equipamentos do cliente
            equipment_list = filter_criteria["equipment_list"]
            client_equipment_ids = [
                eq.get("id") for eq in equipment_list
                if eq.get("client_id") in client_id_list
            ]
            
            filtered = [a for a in filtered if a.get("equipment_id") in client_equipment_ids]
        
        return filtered
    def _get_marker_color(self, alerts: List[Dict[str, Any]]) -> str:
        """
        Determina a cor do marcador com base na gravidade mais alta.
        
        Args:
            alerts: Lista de alertas
            
        Returns:
            str: Cor do marcador
        """
        if any(a.get("gravity") == "P1" for a in alerts):
            return "red"
        elif any(a.get("gravity") == "P2" for a in alerts):
            return "orange"
        else:
            return "blue"
    
    def _create_popup_html(self, alerts: List[Dict[str, Any]], 
                          equipment: Dict[str, Any],
                          client: Dict[str, Any] = None) -> str:
        """
        Cria HTML para o popup do marcador.
        
        Args:
            alerts: Lista de alertas
            equipment: Dados do equipamento
            client: Dados do cliente
            
        Returns:
            str: HTML do popup
        """
        # Conta alertas por gravidade
        p1_count = sum(1 for a in alerts if a.get("gravity") == "P1")
        p2_count = sum(1 for a in alerts if a.get("gravity") == "P2")
        p3_count = sum(1 for a in alerts if a.get("gravity") == "P3")
        
        # Formata HTML
        html = f"""
        <div style="font-family: Arial, sans-serif; max-width: 300px;">
            <h3 style="margin-bottom: 5px;">{equipment.get('tag', 'Equipamento')}</h3>
            <p style="margin-top: 0;">{equipment.get('name', '')}</p>
            
            <p><strong>Cliente:</strong> {client.get('name', 'N/A') if client else 'N/A'}</p>
            <p><strong>Local:</strong> {equipment.get('location', 'N/A')}</p>
            
            <div style="margin: 10px 0; padding: 5px; background-color: #f5f5f5; border-radius: 5px;">
                <p style="margin: 5px 0;"><strong>Alertas:</strong> {len(alerts)}</p>
                <ul style="margin: 5px 0; padding-left: 20px;">
                    <li style="color: red;">P1: {p1_count}</li>
                    <li style="color: orange;">P2: {p2_count}</li>
                    <li style="color: blue;">P3: {p3_count}</li>
                </ul>
            </div>
            
            <h4 style="margin-bottom: 5px;">Últimos alertas:</h4>
            <ul style="margin-top: 0; padding-left: 20px;">
        """
        # Adiciona até 5 alertas mais recentes
        sorted_alerts = sorted(
            alerts, 
            key=lambda x: x.get("timestamp", ""), 
            reverse=True
        )
        
        for i, alert in enumerate(sorted_alerts[:5]):
            gravity = alert.get("gravity", "P3")
            color = "red" if gravity == "P1" else "orange" if gravity == "P2" else "blue"
            
            timestamp = alert.get("timestamp", "")
            if timestamp:
                try:
                    dt = datetime.fromisoformat(timestamp)
                    timestamp = dt.strftime("%d/%m/%Y %H:%M")
                except (ValueError, TypeError):
                    pass
            
            html += f"""
            <li style="margin-bottom: 5px;">
                <span style="color: {color};">[{gravity}]</span> {alert.get('description', 'Sem descrição')}
                <br><small>{timestamp}</small>
            </li>
            """
        
        html += """
            </ul>
        </div>
        """
        
        return html
    def _generate_alert_list_html(self, alert_list_data: List[Dict[str, Any]]) -> str:
        """
        Gera HTML para a lista de alertas.
        
        Args:
            alert_list_data: Dados formatados dos alertas
            
        Returns:
            str: HTML da lista de alertas
        """
        html = """
        <!DOCTYPE html>
        <html lang="pt-BR">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Lista de Alertas - SIL Predictive System</title>
            <style>
                body {
                    font-family: Arial, sans-serif;
                    margin: 0;
                    padding: 20px;
                    background-color: #f5f5f5;
                }
                .container {
                    max-width: 1200px;
                    margin: 0 auto;
                    background-color: white;
                    padding: 20px;
                    border-radius: 5px;
                    box-shadow: 0 2px 5px rgba(0,0,0,0.1);
                }
                h1 {
                    color: #333;
                    margin-top: 0;
                }
                .filters {
                    margin-bottom: 20px;
                    padding: 15px;
                    background-color: #f9f9f9;
                    border-radius: 5px;
                    border: 1px solid #ddd;
                }
                table {
                    width: 100%;
                    border-collapse: collapse;
                }
                th, td {
                    padding: 12px 15px;
                    text-align: left;
                    border-bottom: 1px solid #ddd;
                }
                th {
                    background-color: #f2f2f2;
                    font-weight: bold;
                }
                tr:hover {
                    background-color: #f5f5f5;
                }
                .gravity-p1 {
                    color: white;
                    background-color: #dc3545;
                    padding: 3px 8px;
                    border-radius: 3px;
                    font-weight: bold;
                }
                .gravity-p2 {
                    color: white;
                    background-color: #fd7e14;
                    padding: 3px 8px;
                    border-radius: 3px;
                    font-weight: bold;
                }
                .gravity-p3 {
                    color: white;
                    background-color: #0d6efd;
                    padding: 3px 8px;
                    border-radius: 3px;
                    font-weight: bold;
                }
                .status-new {
                    color: white;
                    background-color: #0dcaf0;
                    padding: 3px 8px;
                    border-radius: 3px;
                }
                .status-acknowledged {
                    color: white;
                    background-color: #6c757d;
                    padding: 3px 8px;
                    border-radius: 3px;
                }
                .status-in-progress {
                    color: white;
                    background-color: #ffc107;
                    padding: 3px 8px;
                    border-radius: 3px;
                }
                .status-resolved {
                    color: white;
                    background-color: #198754;
                    padding: 3px 8px;
                    border-radius: 3px;
                }
                .status-false-positive {
                    color: white;
                    background-color: #6c757d;
                    padding: 3px 8px;
                    border-radius: 3px;
                }
                .timestamp {
                    white-space: nowrap;
                }
                .footer {
                    margin-top: 20px;
                    text-align: center;
                    color: #666;
                    font-size: 0.8em;
                }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>Lista de Alertas - SIL Predictive System</h1>
                
                <div class="filters">
                    <h3>Filtros</h3>
                    <div id="filter-controls">
                        <!-- Controles de filtro seriam adicionados via JavaScript -->
                        <p>Use os controles abaixo para filtrar a lista de alertas.</p>
                    </div>
                </div>
                
                <table>
                    <thead>
                        <tr>
                            <th>Gravidade</th>
                            <th>Status</th>
                            <th>Data/Hora</th>
                            <th>Equipamento</th>
                            <th>Cliente</th>
                            <th>Local</th>
                            <th>Descrição</th>
                        </tr>
                    </thead>
                    <tbody>
        """
        # Adiciona linhas da tabela
        for alert in alert_list_data:
            gravity = alert.get("gravity", "P3")
            gravity_class = f"gravity-{gravity.lower()}"
            
            status = alert.get("status", "NEW")
            status_class = f"status-{status.lower().replace('_', '-')}"
            
            html += f"""
                        <tr>
                            <td><span class="{gravity_class}">{gravity}</span></td>
                            <td><span class="{status_class}">{status}</span></td>
                            <td class="timestamp">{alert.get('timestamp', '')}</td>
                            <td>{alert.get('equipment_tag', '')} - {alert.get('equipment_name', '')}</td>
                            <td>{alert.get('client_name', '')}</td>
                            <td>{alert.get('location', '')}</td>
                            <td>{alert.get('description', '')}</td>
                        </tr>
            """
        
        # Fecha HTML
        timestamp = datetime.utcnow().strftime("%d/%m/%Y %H:%M:%S")
        html += f"""
                    </tbody>
                </table>
                
                <div class="footer">
                    <p>Gerado em {timestamp} | SIL Predictive System</p>
                </div>
            </div>
            
            <script>
                // Aqui seria adicionado JavaScript para filtros interativos
            </script>
        </body>
        </html>
        """
        
        return html
