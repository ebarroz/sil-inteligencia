"""
Modelo de Chat - SIL Predictive System
--------------------------------------------
Este módulo define o modelo de dados para mensagens de chat no sistema,
permitindo integração com equipamentos e persistência de dados.
"""
from datetime import datetime
import uuid
from sqlalchemy import Column, String, DateTime, Boolean, Text, ForeignKey
from sqlalchemy.orm import relationship
from src.config.database import Base

class ChatMessage(Base):
    """Modelo de dados para mensagens de chat."""
    __tablename__ = "chat_messages"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(50), nullable=True)
    content = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    is_system = Column(Boolean, default=False)
    
    # Relacionamento opcional com equipamento (quando a mensagem se refere a um equipamento específico)
    equipment_tag = Column(String(50), ForeignKey("equipment.tag"), nullable=True)
    equipment = relationship("Equipment")
    
    def to_dict(self):
        """Convert message to dictionary for serialization"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'content': self.content,
            'timestamp': self.timestamp.isoformat() if isinstance(self.timestamp, datetime) else self.timestamp,
            'is_system': self.is_system,
            'equipment_tag': self.equipment_tag
        }
    
    @classmethod
    def from_dict(cls, data):
        """Create message from dictionary"""
        return cls(
            id=data.get('id', str(uuid.uuid4())),
            content=data.get('content'),
            user_id=data.get('user_id'),
            is_system=data.get('is_system', False),
            timestamp=data.get('timestamp'),
            equipment_tag=data.get('equipment_tag')
        )
    
    def __repr__(self):
        return f"<ChatMessage(id={self.id}, user_id={self.user_id}, is_system={self.is_system})>"
