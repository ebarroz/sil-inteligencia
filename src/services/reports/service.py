"""
Report generation and delivery service for the SIL Predictive System.

This module handles the creation and sending of alert reports to clients.
"""

import logging
import os
from typing import List, Optional, Dict, Any
from datetime import datetime
from fpdf import FPDF

from ..models.alerts.model import AlertBase, AlertGravity
from ..models.clients.model import ClientBase, ContactInfo
from ..models.equipment.equipment import EquipmentBase
from ..services.notifications.service import NotificationService

# Configuração de logging
logger = logging.getLogger(__name__)

class ReportGenerationService:
    """Serviço para geração e envio de relatórios de alertas."""
    
    def __init__(self, db_manager, notification_service: NotificationService):
        """
        Inicializa o serviço de geração de relatórios.
        
        Args:
            db_manager: Gerenciador de banco de dados
            notification_service: Serviço de notificações
        """
        self.db_manager = db_manager
        self.notification_service = notification_service
        logger.info("Serviço de geração de relatórios inicializado")
    
    def generate_alert_report(
        self,
        client_id: str,
        alert_ids: List[str],
        report_title: str = "Relatório de Alertas de Manutenção",
        output_dir: str = "/tmp"
    ) -> Optional[str]:
        """
        Gera um relatório em PDF contendo detalhes dos alertas especificados.
        
        Args:
            client_id: ID do cliente
            alert_ids: Lista de IDs dos alertas a serem incluídos no relatório
            report_title: Título do relatório
            output_dir: Diretório para salvar o relatório gerado
            
        Returns:
            Caminho para o arquivo PDF gerado ou None em caso de erro
        """
        try:
            # Obter informações do cliente
            client = self._get_client_info(client_id)
            if not client:
                logger.error(f"Cliente {client_id} não encontrado para gerar relatório")
                return None
            
            # Obter detalhes dos alertas
            alerts_data = self._get_alerts_details(alert_ids)
            if not alerts_data:
                logger.warning(f"Nenhum alerta válido encontrado para IDs: {alert_ids}")
                return None
            
            # Criar nome do arquivo
            timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
            file_name = f"Relatorio_Alertas_{client["name"].replace(" ", "_")}_{timestamp_str}.pdf"
            output_path = os.path.join(output_dir, file_name)
            
            # Gerar PDF
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", size=12)
            
            # Cabeçalho
            pdf.set_font("Arial", "B", 16)
            pdf.cell(200, 10, txt=report_title, ln=1, align="C")
            pdf.ln(10)
            
            # Informações do Cliente
            pdf.set_font("Arial", "B", 12)
            pdf.cell(200, 10, txt=f"Cliente: {client["name"]}", ln=1)
            pdf.cell(200, 10, txt=f"Data de Geração: {datetime.now().strftime("%d/%m/%Y %H:%M:%S")}", ln=1)
            pdf.ln(10)
            
            # Detalhes dos Alertas
            pdf.set_font("Arial", "B", 14)
            pdf.cell(200, 10, txt="Detalhes dos Alertas", ln=1)
            pdf.ln(5)
            
            for alert in alerts_data:
                pdf.set_font("Arial", "B", 12)
                pdf.cell(200, 8, txt=f"Alerta ID: {alert["id"]}", ln=1)
                pdf.set_font("Arial", size=10)
                pdf.cell(200, 6, txt=f"  Equipamento: {alert["equipment_name"]} (TAG: {alert["equipment_tag"]})", ln=1)
                pdf.cell(200, 6, txt=f"  Data/Hora: {alert["timestamp"].strftime("%d/%m/%Y %H:%M:%S")}", ln=1)
                pdf.cell(200, 6, txt=f"  Gravidade: {alert["gravity"]}", ln=1)
                pdf.cell(200, 6, txt=f"  Criticidade: {alert["criticality"]}", ln=1)
                pdf.cell(200, 6, txt=f"  Status Atual: {alert["status"]}", ln=1)
                pdf.multi_cell(0, 6, txt=f"  Descrição: {alert["description"]}")
                
                if alert["resolution_details"]:
                    pdf.multi_cell(0, 6, txt=f"  Detalhes da Resolução: {alert["resolution_details"]}")
                
                pdf.ln(5)
            
            # Salvar PDF
            pdf.output(output_path, "F")
            logger.info(f"Relatório gerado com sucesso: {output_path}")
            return output_path
        
        except Exception as e:
            logger.error(f"Erro ao gerar relatório para cliente {client_id}: {e}")
            return None
    
    def send_report_to_client(
        self,
        client_id: str,
        report_path: str,
        subject: str = "Relatório de Alertas de Manutenção SIL Predictive",
        message: str = "Prezados, segue em anexo o relatório de alertas de manutenção gerado pelo sistema SIL Predictive."
    ) -> bool:
        """
        Envia um relatório gerado para os contatos do cliente.
        
        Args:
            client_id: ID do cliente
            report_path: Caminho para o arquivo de relatório PDF
            subject: Assunto do e-mail
            message: Mensagem do corpo do e-mail
            
        Returns:
            bool: True se o envio foi iniciado com sucesso, False caso contrário
        """
        try:
            # Obter informações do cliente e contatos
            client = self._get_client_info(client_id)
            if not client or not client["contacts"]:
                logger.error(f"Cliente {client_id} ou contatos não encontrados para envio de relatório")
                return False
            
            # Filtrar contatos que devem receber e-mail
            email_contacts = [ContactInfo(**contact) for contact in client["contacts"] 
                              if contact.get("notification_preference") in ["EMAIL", "BOTH"]]
            
            if not email_contacts:
                logger.warning(f"Nenhum contato encontrado com preferência de e-mail para cliente {client_id}")
                return False
            
            # Enviar relatório usando o serviço de notificação
            send_results = self.notification_service.send_report(
                contacts=email_contacts,
                subject=subject,
                message=message,
                report_path=report_path,
                client_name=client["name"]
            )
            
            # Verificar se houve sucesso no envio para pelo menos um contato
            success = any(send_results.values())
            if success:
                logger.info(f"Relatório enviado para contatos do cliente {client_id}")
            else:
                logger.warning(f"Falha ao enviar relatório para contatos do cliente {client_id}")
            
            return success
        except Exception as e:
            logger.error(f"Erro ao enviar relatório para cliente {client_id}: {e}")
            return False
    
    def _get_client_info(self, client_id: str) -> Optional[Dict[str, Any]]:
        """
        Obtém informações básicas do cliente.
        
        Args:
            client_id: ID do cliente
            
        Returns:
            Informações do cliente ou None se não encontrado
        """
        try:
            with self.db_manager.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        SELECT id, name, document, contacts
                        FROM clients
                        WHERE id = %s
                        """,
                        (client_id,)
                    )
                    
                    row = cursor.fetchone()
                    if not row:
                        return None
                    
                    return {
                        "id": row[0],
                        "name": row[1],
                        "document": row[2],
                        "contacts": row[3]
                    }
        except Exception as e:
            logger.error(f"Erro ao obter informações do cliente {client_id}: {e}")
            return None
    
    def _get_alerts_details(self, alert_ids: List[str]) -> List[Dict[str, Any]]:
        """
        Obtém detalhes dos alertas especificados.
        
        Args:
            alert_ids: Lista de IDs dos alertas
            
        Returns:
            Lista de dicionários com detalhes dos alertas
        """
        if not alert_ids:
            return []
        
        try:
            with self.db_manager.get_connection() as conn:
                with conn.cursor() as cursor:
                    # Usar placeholder %s para cada ID na lista
                    placeholders = ",".join(["%s"] * len(alert_ids))
                    query = f"""
                    SELECT
                        a.id, a.equipment_id, a.timestamp, a.measurement_id,
                        a.measurement_source, a.description, a.gravity,
                        a.criticality, a.status, a.assigned_to,
                        a.resolution_details, a.is_valid, a.filter_result,
                        e.name as equipment_name, e.tag as equipment_tag
                    FROM alerts a
                    JOIN equipment e ON a.equipment_id = e.id
                    WHERE a.id IN ({placeholders})
                    ORDER BY a.timestamp DESC
                    """
                    
                    cursor.execute(query, alert_ids)
                    
                    alerts = []
                    for row in cursor.fetchall():
                        alerts.append({
                            "id": row[0],
                            "equipment_id": row[1],
                            "timestamp": row[2],
                            "measurement_id": row[3],
                            "measurement_source": row[4],
                            "description": row[5],
                            "gravity": row[6],
                            "criticality": row[7],
                            "status": row[8],
                            "assigned_to": row[9],
                            "resolution_details": row[10],
                            "is_valid": row[11],
                            "filter_result": row[12],
                            "equipment_name": row[13],
                            "equipment_tag": row[14]
                        })
                    
                    return alerts
        except Exception as e:
            logger.error(f"Erro ao obter detalhes dos alertas {alert_ids}: {e}")
            return []

logger.info("Report generation service defined.")
"""
