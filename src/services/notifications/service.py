"""
Notification service for the SIL Predictive System.

This module handles email and SMS notifications for alerts and reports.
"""

import logging
import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from typing import List, Optional, Dict, Any, Union
from datetime import datetime
import requests
import json

from ..models.clients.model import ContactInfo, NotificationPreference
from ..models.alerts.model import AlertBase, AlertGravity, AlertCriticality

# Configuração de logging
logger = logging.getLogger(__name__)

class NotificationService:
    """Serviço para envio de notificações por e-mail e SMS."""
    
    def __init__(self, config):
        """
        Inicializa o serviço de notificações.
        
        Args:
            config: Configurações do serviço
        """
        self.config = config
        self.email_config = config.get('email', {})
        self.sms_config = config.get('sms', {})
        
        # Validar configurações
        self._validate_config()
        
        logger.info("Serviço de notificações inicializado")
    
    def _validate_config(self):
        """Valida as configurações do serviço."""
        # Validar configurações de e-mail
        required_email_fields = ['smtp_server', 'smtp_port', 'username', 'password', 'from_email']
        for field in required_email_fields:
            if field not in self.email_config:
                logger.warning(f"Campo obrigatório '{field}' não encontrado na configuração de e-mail")
        
        # Validar configurações de SMS
        required_sms_fields = ['api_url', 'api_key']
        for field in required_sms_fields:
            if field not in self.sms_config:
                logger.warning(f"Campo obrigatório '{field}' não encontrado na configuração de SMS")
    
    def send_alert_notification(
        self,
        alert: AlertBase,
        contacts: List[ContactInfo],
        equipment_name: str,
        client_name: str,
        include_report: bool = False,
        report_path: Optional[str] = None
    ) -> Dict[str, bool]:
        """
        Envia notificação de alerta para os contatos especificados.
        
        Args:
            alert: Alerta a ser notificado
            contacts: Lista de contatos para notificação
            equipment_name: Nome do equipamento
            client_name: Nome do cliente
            include_report: Se deve incluir relatório em anexo
            report_path: Caminho para o arquivo de relatório (opcional)
            
        Returns:
            Dicionário com status de envio para cada contato
        """
        results = {}
        
        # Preparar conteúdo da notificação
        subject = f"[{alert.gravity}] Alerta: {equipment_name} - {client_name}"
        
        # Determinar prioridade da mensagem com base na gravidade
        priority = "Alta" if alert.gravity in [AlertGravity.P1, AlertGravity.P2] else "Normal"
        
        # Corpo do e-mail
        email_body = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; }}
                .alert-header {{ background-color: {self._get_color_for_gravity(alert.gravity)}; padding: 10px; color: white; }}
                .alert-content {{ padding: 15px; }}
                .alert-footer {{ background-color: #f0f0f0; padding: 10px; font-size: 0.8em; }}
            </style>
        </head>
        <body>
            <div class="alert-header">
                <h2>Alerta de Manutenção - {alert.gravity}</h2>
                <p>Prioridade: {priority}</p>
            </div>
            <div class="alert-content">
                <p><strong>Cliente:</strong> {client_name}</p>
                <p><strong>Equipamento:</strong> {equipment_name}</p>
                <p><strong>Data/Hora:</strong> {alert.timestamp.strftime('%d/%m/%Y %H:%M:%S')}</p>
                <p><strong>Descrição:</strong> {alert.description}</p>
                <p><strong>Criticidade:</strong> {alert.criticality}</p>
                <p><strong>Status:</strong> {alert.status}</p>
            </div>
            <div class="alert-footer">
                <p>Este é um e-mail automático do Sistema SIL Predictive. Por favor, não responda diretamente a este e-mail.</p>
                <p>Para mais informações, acesse o sistema ou entre em contato com o suporte.</p>
            </div>
        </body>
        </html>
        """
        
        # Corpo do SMS (versão simplificada)
        sms_body = f"SIL Alerta [{alert.gravity}]: {equipment_name} em {client_name}. {alert.description[:100]}{'...' if len(alert.description) > 100 else ''}"
        
        # Enviar notificações para cada contato conforme preferência
        for contact in contacts:
            contact_result = {"email": False, "sms": False}
            
            # Verificar preferência de notificação
            if contact.notification_preference in [NotificationPreference.EMAIL, NotificationPreference.BOTH]:
                # Enviar e-mail
                email_success = self._send_email(
                    to_email=contact.email,
                    subject=subject,
                    body=email_body,
                    is_html=True,
                    attachment_path=report_path if include_report else None
                )
                contact_result["email"] = email_success
            
            if contact.notification_preference in [NotificationPreference.SMS, NotificationPreference.BOTH]:
                # Enviar SMS se o contato tiver telefone
                if contact.phone:
                    sms_success = self._send_sms(
                        phone_number=contact.phone,
                        message=sms_body
                    )
                    contact_result["sms"] = sms_success
            
            results[contact.name] = contact_result
        
        return results
    
    def send_report(
        self,
        contacts: List[ContactInfo],
        subject: str,
        message: str,
        report_path: str,
        client_name: str
    ) -> Dict[str, bool]:
        """
        Envia relatório por e-mail para os contatos especificados.
        
        Args:
            contacts: Lista de contatos para envio
            subject: Assunto do e-mail
            message: Mensagem do e-mail
            report_path: Caminho para o arquivo de relatório
            client_name: Nome do cliente
            
        Returns:
            Dicionário com status de envio para cada contato
        """
        results = {}
        
        # Preparar conteúdo do e-mail
        email_subject = f"{subject} - {client_name}"
        
        # Corpo do e-mail
        email_body = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; }}
                .report-header {{ background-color: #2c3e50; padding: 10px; color: white; }}
                .report-content {{ padding: 15px; }}
                .report-footer {{ background-color: #f0f0f0; padding: 10px; font-size: 0.8em; }}
            </style>
        </head>
        <body>
            <div class="report-header">
                <h2>Relatório SIL Predictive</h2>
                <p>Cliente: {client_name}</p>
            </div>
            <div class="report-content">
                {message}
                <p>O relatório completo está anexado a este e-mail.</p>
            </div>
            <div class="report-footer">
                <p>Este é um e-mail automático do Sistema SIL Predictive. Por favor, não responda diretamente a este e-mail.</p>
                <p>Para mais informações, acesse o sistema ou entre em contato com o suporte.</p>
            </div>
        </body>
        </html>
        """
        
        # Enviar e-mail para cada contato
        for contact in contacts:
            # Enviar apenas para contatos com preferência de e-mail
            if contact.notification_preference in [NotificationPreference.EMAIL, NotificationPreference.BOTH]:
                email_success = self._send_email(
                    to_email=contact.email,
                    subject=email_subject,
                    body=email_body,
                    is_html=True,
                    attachment_path=report_path
                )
                results[contact.name] = email_success
        
        return results
    
    def _send_email(
        self,
        to_email: str,
        subject: str,
        body: str,
        is_html: bool = False,
        attachment_path: Optional[str] = None
    ) -> bool:
        """
        Envia e-mail.
        
        Args:
            to_email: E-mail do destinatário
            subject: Assunto do e-mail
            body: Corpo do e-mail
            is_html: Se o corpo é HTML
            attachment_path: Caminho para arquivo anexo (opcional)
            
        Returns:
            bool: True se o e-mail foi enviado com sucesso, False caso contrário
        """
        try:
            # Criar mensagem
            msg = MIMEMultipart()
            msg['From'] = self.email_config['from_email']
            msg['To'] = to_email
            msg['Subject'] = subject
            
            # Adicionar corpo
            if is_html:
                msg.attach(MIMEText(body, 'html'))
            else:
                msg.attach(MIMEText(body, 'plain'))
            
            # Adicionar anexo, se fornecido
            if attachment_path and os.path.exists(attachment_path):
                with open(attachment_path, 'rb') as file:
                    attachment = MIMEApplication(file.read(), _subtype="pdf")
                    attachment.add_header('Content-Disposition', 'attachment', filename=os.path.basename(attachment_path))
                    msg.attach(attachment)
            
            # Conectar ao servidor SMTP
            server = smtplib.SMTP(self.email_config['smtp_server'], self.email_config['smtp_port'])
            server.starttls()
            server.login(self.email_config['username'], self.email_config['password'])
            
            # Enviar e-mail
            server.send_message(msg)
            server.quit()
            
            logger.info(f"E-mail enviado com sucesso para {to_email}")
            return True
        except Exception as e:
            logger.error(f"Erro ao enviar e-mail para {to_email}: {e}")
            return False
    
    def _send_sms(self, phone_number: str, message: str) -> bool:
        """
        Envia SMS.
        
        Args:
            phone_number: Número de telefone do destinatário
            message: Mensagem SMS
            
        Returns:
            bool: True se o SMS foi enviado com sucesso, False caso contrário
        """
        try:
            # Preparar payload para API de SMS
            payload = {
                "to": phone_number,
                "message": message,
                "api_key": self.sms_config['api_key']
            }
            
            # Adicionar parâmetros adicionais, se configurados
            if 'sender_id' in self.sms_config:
                payload['sender_id'] = self.sms_config['sender_id']
            
            # Enviar requisição para API de SMS
            response = requests.post(
                self.sms_config['api_url'],
                json=payload,
                headers={"Content-Type": "application/json"}
            )
            
            # Verificar resposta
            if response.status_code == 200:
                response_data = response.json()
                if response_data.get('success', False):
                    logger.info(f"SMS enviado com sucesso para {phone_number}")
                    return True
                else:
                    logger.warning(f"Falha ao enviar SMS para {phone_number}: {response_data.get('message', 'Erro desconhecido')}")
                    return False
            else:
                logger.warning(f"Falha ao enviar SMS para {phone_number}: Status {response.status_code}")
                return False
        except Exception as e:
            logger.error(f"Erro ao enviar SMS para {phone_number}: {e}")
            return False
    
    def _get_color_for_gravity(self, gravity: AlertGravity) -> str:
        """
        Retorna a cor correspondente à gravidade do alerta.
        
        Args:
            gravity: Gravidade do alerta
            
        Returns:
            Código de cor HTML
        """
        colors = {
            AlertGravity.P1: "#FF0000",  # Vermelho
            AlertGravity.P2: "#FF8C00",  # Laranja
            AlertGravity.P3: "#FFD700",  # Amarelo
            AlertGravity.P4: "#1E90FF"   # Azul
        }
        
        return colors.get(gravity, "#808080")  # Cinza como padrão

logger.info("Notification service defined.")
"""
