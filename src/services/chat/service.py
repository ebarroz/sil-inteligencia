"""
Serviço de Chat - SIL Predictive System
--------------------------------------------
Este serviço gerencia as operações de chat, integrando com o banco de dados
e fornecendo acesso aos dados de equipamentos e medições.
"""
from datetime import datetime
import uuid
from sqlalchemy.orm import Session
from src.models.chat.model import ChatMessage
from src.models.equipment.equipment import Equipment
from src.models.alerts.model import Alert

class ChatService:
    """Serviço para gerenciar operações de chat no SIL Predictive System"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_all_messages(self, limit=100):
        """Obter todas as mensagens de chat, com limite opcional"""
        return self.db.query(ChatMessage).order_by(ChatMessage.timestamp).limit(limit).all()
    
    def add_message(self, content, user_id=None, is_system=False, equipment_tag=None):
        """Adicionar uma nova mensagem ao chat"""
        message = ChatMessage(
            content=content,
            user_id=user_id,
            is_system=is_system,
            equipment_tag=equipment_tag
        )
        
        self.db.add(message)
        self.db.commit()
        self.db.refresh(message)
        return message
    
    def generate_system_response(self, user_message):
        """Gerar resposta do sistema com base na mensagem do usuário
        
        Esta função analisa o conteúdo da mensagem do usuário e gera uma resposta
        contextual, possivelmente incluindo dados de equipamentos ou medições.
        """
        content = user_message.content.lower()
        
        # Verificar se a mensagem menciona equipamentos
        if "equipamento" in content or "máquina" in content or "tag" in content:
            # Buscar informações de equipamentos
            equipment_count = self.db.query(Equipment).count()
            return self.add_message(
                content=f"Temos {equipment_count} equipamentos cadastrados no sistema. Você pode solicitar informações específicas sobre um equipamento mencionando sua TAG.",
                user_id="system",
                is_system=True
            )
        
        # Verificar se a mensagem menciona alertas
        elif "alerta" in content or "alarme" in content or "falha" in content:
            # Buscar informações de alertas
            alert_count = self.db.query(Alert).count()
            return self.add_message(
                content=f"Existem {alert_count} alertas registrados no sistema. Você pode solicitar detalhes sobre alertas específicos ou filtrar por gravidade (P1, P2, P3).",
                user_id="system",
                is_system=True
            )
        
        # Resposta padrão
        else:
            return self.add_message(
                content=f"Entendi sua mensagem. Como posso ajudar com o monitoramento preditivo? Você pode perguntar sobre equipamentos, alertas, ou relatórios.",
                user_id="system",
                is_system=True
            )
    
    def get_equipment_info(self, tag):
        """Obter informações detalhadas sobre um equipamento específico"""
        equipment = self.db.query(Equipment).filter(Equipment.tag == tag).first()
        if not equipment:
            return None
        
        return equipment
    
    def get_recent_alerts(self, limit=5):
        """Obter alertas recentes do sistema"""
        return self.db.query(Alert).order_by(Alert.created_at.desc()).limit(limit).all()
