"""
Chat Models for SIL Predictive System
-------------------------------------
Modelos de banco de dados para funcionalidades de chat integrado com Claude.
"""
from sqlalchemy import Column, String, Text, Boolean, DateTime, Integer, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

Base = declarative_base()

class ChatSession(Base):
    """
    Sessão de chat - agrupa mensagens de uma conversa.
    """
    __tablename__ = "chat_sessions"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(100), nullable=False)
    session_name = Column(String(200))
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    is_active = Column(Boolean, default=True)
    metadata = Column(JSON, default=dict)
    
    # Relacionamento com mensagens
    messages = relationship("ChatMessage", back_populates="session", cascade="all, delete-orphan")
    
    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "session_name": self.session_name,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "is_active": self.is_active,
            "metadata": self.metadata,
            "message_count": len(self.messages) if self.messages else 0
        }

class ChatMessage(Base):
    """
    Mensagem individual do chat.
    """
    __tablename__ = "chat_messages"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = Column(String(36), nullable=False)
    content = Column(Text, nullable=False)
    is_user = Column(Boolean, default=True)  # True para usuário, False para assistente
    equipment_tag = Column(String(50))  # TAG do equipamento relacionado (opcional)
    created_at = Column(DateTime, default=datetime.now)
    metadata = Column(JSON, default=dict)  # Dados adicionais (modelo usado, tokens, etc.)
    
    # Relacionamento com sessão
    session = relationship("ChatSession", back_populates="messages")
    
    def to_dict(self):
        return {
            "id": self.id,
            "session_id": self.session_id,
            "content": self.content,
            "is_user": self.is_user,
            "equipment_tag": self.equipment_tag,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "metadata": self.metadata
        }
