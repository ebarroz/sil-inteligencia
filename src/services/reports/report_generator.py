"""
Gerador de Relatórios - SIL Predictive System
--------------------------------------------
Este módulo implementa a geração automatizada de relatórios para clientes,
conforme requisito #7 (Automatização de envio de relatório diretamente para o Cliente).
"""
import logging
import os
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import jinja2
import pdfkit
import json
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
from io import BytesIO
import base64

# Configuração de logging
logger = logging.getLogger(__name__)

class ReportGenerator:
    """Serviço para geração automatizada de relatórios."""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Inicializa o serviço de geração de relatórios.
        
        Args:
            config: Configurações do serviço
        """
        self.config = config
        self.template_dir = config.get("template_dir", "templates/reports")
        self.output_dir = config.get("output_dir", "reports/output")
        self.logo_path = config.get("logo_path", "static/img/logo.png")
        
        # Configura o ambiente Jinja2 para templates
        self.jinja_env = jinja2.Environment(
            loader=jinja2.FileSystemLoader(self.template_dir),
            autoescape=jinja2.select_autoescape(['html', 'xml'])
        )
        
        # Configura opções do wkhtmltopdf para geração de PDF
        self.pdf_options = {
            'page-size': 'A4',
            'margin-top': '20mm',
            'margin-right': '20mm',
            'margin-bottom': '20mm',
            'margin-left': '20mm',
            'encoding': 'UTF-8',
            'no-outline': None,
            'enable-local-file-access': None
        }
        
        # Garante que o diretório de saída existe
        os.makedirs(self.output_dir, exist_ok=True)
        
        logger.info("Serviço de geração de relatórios inicializado")
    def generate_alert_report(self, alert: Dict[str, Any], equipment: Dict[str, Any], 
                             client: Dict[str, Any], measurements: List[Dict[str, Any]] = None,
                             analysis_results: Dict[str, Any] = None) -> str:
        """
        Gera um relatório detalhado para um alerta específico.
        
        Args:
            alert: Dados do alerta
            equipment: Dados do equipamento
            client: Dados do cliente
            measurements: Dados de medições relacionadas ao alerta (opcional)
            analysis_results: Resultados de análises adicionais (opcional)
            
        Returns:
            str: Caminho para o arquivo PDF gerado
        """
        logger.info(f"Gerando relatório para alerta {alert.get('id')} do equipamento {equipment.get('tag')}")
        
        # Prepara o contexto para o template
        context = {
            "alert": alert,
            "equipment": equipment,
            "client": client,
            "measurements": measurements or [],
            "analysis_results": analysis_results or {},
            "timestamp": datetime.utcnow().strftime("%d/%m/%Y %H:%M:%S"),
            "logo_path": self.logo_path,
            "charts": {}
        }
        
        # Gera gráficos se houver dados de medição
        if measurements:
            context["charts"] = self._generate_charts(measurements, alert)
        
        # Seleciona o template com base na gravidade do alerta
        gravity = alert.get("gravity", "P3")
        template_name = f"alert_report_{gravity.lower()}.html"
        
        try:
            # Renderiza o template HTML
            template = self.jinja_env.get_template(template_name)
            html_content = template.render(**context)
            
            # Define o nome do arquivo de saída
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            alert_id = alert.get("id", "unknown")
            equipment_tag = equipment.get("tag", "unknown")
            
            output_filename = f"alert_{alert_id}_{equipment_tag}_{timestamp}.pdf"
            output_path = os.path.join(self.output_dir, output_filename)
            
            # Gera o PDF
            pdfkit.from_string(html_content, output_path, options=self.pdf_options)
            
            logger.info(f"Relatório gerado com sucesso: {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"Erro ao gerar relatório: {str(e)}")
            raise
    def generate_equipment_report(self, equipment: Dict[str, Any], client: Dict[str, Any],
                                alerts: List[Dict[str, Any]], measurements: Dict[str, List[Dict[str, Any]]],
                                period_days: int = 30) -> str:
        """
        Gera um relatório periódico para um equipamento específico.
        
        Args:
            equipment: Dados do equipamento
            client: Dados do cliente
            alerts: Lista de alertas do período
            measurements: Dicionário com listas de medições por tipo
            period_days: Período em dias para o relatório
            
        Returns:
            str: Caminho para o arquivo PDF gerado
        """
        logger.info(f"Gerando relatório periódico para equipamento {equipment.get('tag')}")
        
        # Calcula estatísticas de alertas
        alert_stats = self._calculate_alert_statistics(alerts)
        
        # Prepara o contexto para o template
        context = {
            "equipment": equipment,
            "client": client,
            "alerts": alerts,
            "alert_stats": alert_stats,
            "measurements": measurements,
            "period_days": period_days,
            "period_start": (datetime.utcnow() - timedelta(days=period_days)).strftime("%d/%m/%Y"),
            "period_end": datetime.utcnow().strftime("%d/%m/%Y"),
            "timestamp": datetime.utcnow().strftime("%d/%m/%Y %H:%M:%S"),
            "logo_path": self.logo_path,
            "charts": {}
        }
        
        # Gera gráficos para cada tipo de medição
        for measurement_type, measurement_data in measurements.items():
            if measurement_data:
                context["charts"][measurement_type] = self._generate_trend_charts(measurement_data, measurement_type)
        
        try:
            # Renderiza o template HTML
            template = self.jinja_env.get_template("equipment_report.html")
            html_content = template.render(**context)
            
            # Define o nome do arquivo de saída
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            equipment_tag = equipment.get("tag", "unknown")
            
            output_filename = f"equipment_{equipment_tag}_{period_days}d_{timestamp}.pdf"
            output_path = os.path.join(self.output_dir, output_filename)
            
            # Gera o PDF
            pdfkit.from_string(html_content, output_path, options=self.pdf_options)
            
            logger.info(f"Relatório periódico gerado com sucesso: {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"Erro ao gerar relatório periódico: {str(e)}")
            raise
    def generate_client_summary_report(self, client: Dict[str, Any], 
                                     equipment_list: List[Dict[str, Any]],
                                     alerts_summary: Dict[str, Any],
                                     period_days: int = 30) -> str:
        """
        Gera um relatório resumido para o cliente com visão geral de todos os equipamentos.
        
        Args:
            client: Dados do cliente
            equipment_list: Lista de equipamentos do cliente
            alerts_summary: Resumo de alertas por equipamento
            period_days: Período em dias para o relatório
            
        Returns:
            str: Caminho para o arquivo PDF gerado
        """
        logger.info(f"Gerando relatório resumido para cliente {client.get('name')}")
        
        # Prepara o contexto para o template
        context = {
            "client": client,
            "equipment_list": equipment_list,
            "alerts_summary": alerts_summary,
            "period_days": period_days,
            "period_start": (datetime.utcnow() - timedelta(days=period_days)).strftime("%d/%m/%Y"),
            "period_end": datetime.utcnow().strftime("%d/%m/%Y"),
            "timestamp": datetime.utcnow().strftime("%d/%m/%Y %H:%M:%S"),
            "logo_path": self.logo_path,
            "charts": self._generate_summary_charts(equipment_list, alerts_summary)
        }
        
        try:
            # Renderiza o template HTML
            template = self.jinja_env.get_template("client_summary_report.html")
            html_content = template.render(**context)
            
            # Define o nome do arquivo de saída
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            client_id = client.get("id", "unknown")
            
            output_filename = f"client_{client_id}_summary_{period_days}d_{timestamp}.pdf"
            output_path = os.path.join(self.output_dir, output_filename)
            
            # Gera o PDF
            pdfkit.from_string(html_content, output_path, options=self.pdf_options)
            
            logger.info(f"Relatório resumido do cliente gerado com sucesso: {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"Erro ao gerar relatório resumido do cliente: {str(e)}")
            raise
    def _generate_charts(self, measurements: List[Dict[str, Any]], 
                        alert: Dict[str, Any]) -> Dict[str, str]:
        """
        Gera gráficos para os dados de medição relacionados ao alerta.
        
        Args:
            measurements: Lista de medições
            alert: Dados do alerta
            
        Returns:
            Dict[str, str]: Dicionário com gráficos em formato base64
        """
        charts = {}
        
        try:
            # Converte medições para DataFrame
            df = pd.DataFrame(measurements)
            
            # Garante que há uma coluna de timestamp
            if "timestamp" in df.columns:
                df["timestamp"] = pd.to_datetime(df["timestamp"])
                df = df.sort_values("timestamp")
                
                # Identifica colunas numéricas para plotagem
                numeric_columns = df.select_dtypes(include=[np.number]).columns.tolist()
                numeric_columns = [col for col in numeric_columns if col not in ["id", "equipment_id"]]
                
                # Gera gráfico de linha para cada coluna numérica
                for column in numeric_columns:
                    plt.figure(figsize=(10, 6))
                    plt.plot(df["timestamp"], df[column], marker='o', linestyle='-')
                    
                    # Adiciona linha vertical no momento do alerta
                    if alert.get("timestamp"):
                        alert_time = pd.to_datetime(alert["timestamp"])
                        if alert_time >= df["timestamp"].min() and alert_time <= df["timestamp"].max():
                            plt.axvline(x=alert_time, color='r', linestyle='--', label='Alerta')
                    
                    plt.title(f"Medições de {column}")
                    plt.xlabel("Data/Hora")
                    plt.ylabel(column)
                    plt.grid(True)
                    plt.xticks(rotation=45)
                    plt.tight_layout()
                    
                    # Converte o gráfico para base64
                    buffer = BytesIO()
                    plt.savefig(buffer, format='png')
                    buffer.seek(0)
                    image_png = buffer.getvalue()
                    buffer.close()
                    
                    chart_base64 = base64.b64encode(image_png).decode('utf-8')
                    charts[column] = f"data:image/png;base64,{chart_base64}"
                    
                    plt.close()
        
        except Exception as e:
            logger.error(f"Erro ao gerar gráficos: {str(e)}")
        
        return charts
    def _generate_trend_charts(self, measurements: List[Dict[str, Any]], 
                             measurement_type: str) -> Dict[str, str]:
        """
        Gera gráficos de tendência para um tipo específico de medição.
        
        Args:
            measurements: Lista de medições
            measurement_type: Tipo de medição (termografia, óleo, vibração, etc.)
            
        Returns:
            Dict[str, str]: Dicionário com gráficos em formato base64
        """
        charts = {}
        
        try:
            # Converte medições para DataFrame
            df = pd.DataFrame(measurements)
            
            # Garante que há uma coluna de timestamp
            if "timestamp" in df.columns and len(df) > 1:
                df["timestamp"] = pd.to_datetime(df["timestamp"])
                df = df.sort_values("timestamp")
                
                # Identifica colunas numéricas para plotagem
                numeric_columns = df.select_dtypes(include=[np.number]).columns.tolist()
                numeric_columns = [col for col in numeric_columns if col not in ["id", "equipment_id"]]
                
                # Gera gráfico de tendência para cada coluna numérica
                for column in numeric_columns:
                    plt.figure(figsize=(10, 6))
                    
                    # Plota os dados
                    plt.plot(df["timestamp"], df[column], marker='o', linestyle='-')
                    
                    # Adiciona linha de tendência
                    if len(df) > 2:
                        x = np.arange(len(df))
                        y = df[column].values
                        z = np.polyfit(x, y, 1)
                        p = np.poly1d(z)
                        plt.plot(df["timestamp"], p(x), "r--", label="Tendência")
                    
                    plt.title(f"Tendência de {column} ({measurement_type})")
                    plt.xlabel("Data/Hora")
                    plt.ylabel(column)
                    plt.grid(True)
                    plt.xticks(rotation=45)
                    plt.legend()
                    plt.tight_layout()
                    
                    # Converte o gráfico para base64
                    buffer = BytesIO()
                    plt.savefig(buffer, format='png')
                    buffer.seek(0)
                    image_png = buffer.getvalue()
                    buffer.close()
                    
                    chart_base64 = base64.b64encode(image_png).decode('utf-8')
                    charts[column] = f"data:image/png;base64,{chart_base64}"
                    
                    plt.close()
        
        except Exception as e:
            logger.error(f"Erro ao gerar gráficos de tendência: {str(e)}")
        
        return charts
    def _generate_summary_charts(self, equipment_list: List[Dict[str, Any]],
                               alerts_summary: Dict[str, Any]) -> Dict[str, str]:
        """
        Gera gráficos resumidos para o relatório do cliente.
        
        Args:
            equipment_list: Lista de equipamentos
            alerts_summary: Resumo de alertas por equipamento
            
        Returns:
            Dict[str, str]: Dicionário com gráficos em formato base64
        """
        charts = {}
        
        try:
            # Gráfico de pizza com distribuição de alertas por gravidade
            gravity_counts = {
                "P1": 0,
                "P2": 0,
                "P3": 0
            }
            
            for equipment_id, summary in alerts_summary.items():
                gravity_counts["P1"] += summary.get("P1", 0)
                gravity_counts["P2"] += summary.get("P2", 0)
                gravity_counts["P3"] += summary.get("P3", 0)
            
            # Gera o gráfico de pizza
            plt.figure(figsize=(8, 8))
            labels = [f"P1 (Crítico): {gravity_counts['P1']}", 
                     f"P2 (Alto): {gravity_counts['P2']}", 
                     f"P3 (Médio): {gravity_counts['P3']}"]
            sizes = [gravity_counts["P1"], gravity_counts["P2"], gravity_counts["P3"]]
            colors = ['#ff6666', '#ffcc66', '#66b3ff']
            
            if sum(sizes) > 0:
                plt.pie(sizes, labels=labels, colors=colors, autopct='%1.1f%%', startangle=90)
                plt.axis('equal')
                plt.title("Distribuição de Alertas por Gravidade")
                
                # Converte o gráfico para base64
                buffer = BytesIO()
                plt.savefig(buffer, format='png')
                buffer.seek(0)
                image_png = buffer.getvalue()
                buffer.close()
                
                chart_base64 = base64.b64encode(image_png).decode('utf-8')
                charts["alerts_by_gravity"] = f"data:image/png;base64,{chart_base64}"
                
                plt.close()
            
            # Gráfico de barras com alertas por equipamento
            if equipment_list and alerts_summary:
                plt.figure(figsize=(12, 6))
                
                equipment_tags = []
                alert_counts = []
                
                for equipment in equipment_list:
                    tag = equipment.get("tag", "")
                    if tag:
                        equipment_tags.append(tag)
                        
                        # Conta total de alertas para este equipamento
                        total_alerts = sum(alerts_summary.get(tag, {}).values())
                        alert_counts.append(total_alerts)
                
                if equipment_tags and alert_counts:
                    # Ordena por número de alertas (decrescente)
                    sorted_indices = np.argsort(alert_counts)[::-1]
                    sorted_tags = [equipment_tags[i] for i in sorted_indices]
                    sorted_counts = [alert_counts[i] for i in sorted_indices]
                    
                    # Limita a 10 equipamentos para melhor visualização
                    if len(sorted_tags) > 10:
                        sorted_tags = sorted_tags[:10]
                        sorted_counts = sorted_counts[:10]
                    
                    plt.bar(sorted_tags, sorted_counts)
                    plt.title("Alertas por Equipamento")
                    plt.xlabel("Equipamento (TAG)")
                    plt.ylabel("Número de Alertas")
                    plt.xticks(rotation=45)
                    plt.tight_layout()
                    
                    # Converte o gráfico para base64
                    buffer = BytesIO()
                    plt.savefig(buffer, format='png')
                    buffer.seek(0)
                    image_png = buffer.getvalue()
                    buffer.close()
                    
                    chart_base64 = base64.b64encode(image_png).decode('utf-8')
                    charts["alerts_by_equipment"] = f"data:image/png;base64,{chart_base64}"
                    
                    plt.close()
        
        except Exception as e:
            logger.error(f"Erro ao gerar gráficos resumidos: {str(e)}")
        
        return charts
    def _calculate_alert_statistics(self, alerts: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Calcula estatísticas sobre os alertas.
        
        Args:
            alerts: Lista de alertas
            
        Returns:
            Dict[str, Any]: Estatísticas calculadas
        """
        stats = {
            "total": len(alerts),
            "by_gravity": {
                "P1": 0,
                "P2": 0,
                "P3": 0
            },
            "by_status": {
                "NEW": 0,
                "ACKNOWLEDGED": 0,
                "IN_PROGRESS": 0,
                "RESOLVED": 0,
                "FALSE_POSITIVE": 0
            },
            "avg_resolution_time": None
        }
        
        resolution_times = []
        
        for alert in alerts:
            # Conta por gravidade
            gravity = alert.get("gravity", "P3")
            stats["by_gravity"][gravity] = stats["by_gravity"].get(gravity, 0) + 1
            
            # Conta por status
            status = alert.get("status", "NEW")
            stats["by_status"][status] = stats["by_status"].get(status, 0) + 1
            
            # Calcula tempo de resolução para alertas resolvidos
            if status == "RESOLVED" and alert.get("created_at") and alert.get("resolved_at"):
                created = datetime.fromisoformat(alert["created_at"])
                resolved = datetime.fromisoformat(alert["resolved_at"])
                resolution_time = (resolved - created).total_seconds() / 3600  # em horas
                resolution_times.append(resolution_time)
        
        # Calcula tempo médio de resolução
        if resolution_times:
            stats["avg_resolution_time"] = sum(resolution_times) / len(resolution_times)
        
        return stats
