"""
API de Chat - SIL Predictive System
--------------------------------------------
Este módulo define os endpoints da API de chat, integrando com o serviço
de chat e o banco de dados para fornecer funcionalidades de chat contextual.
"""
from flask import Blueprint, request, jsonify, session
from sqlalchemy.orm import Session
import uuid

from src.services.chat.service import ChatService
from src.config.database import get_db

# Criar blueprint para API de chat
chat_api = Blueprint('chat_api', __name__, url_prefix='/api/chat')

@chat_api.route('/messages', methods=['GET'])
def get_messages():
    """Obter todas as mensagens de chat"""
    db = next(get_db())
    chat_service = ChatService(db)
    
    # Parâmetro opcional para limitar número de mensagens
    limit = request.args.get('limit', 100, type=int)
    
    messages = chat_service.get_all_messages(limit=limit)
    return jsonify([message.to_dict() for message in messages])

@chat_api.route('/messages', methods=['POST'])
def post_message():
    """Postar uma nova mensagem de chat"""
    db = next(get_db())
    chat_service = ChatService(db)
    
    data = request.json
    
    if not data or 'content' not in data:
        return jsonify({"error": "Conteúdo da mensagem é obrigatório"}), 400
    
    # Gerar ID de usuário se não estiver presente na sessão
    if 'user_id' not in session:
        session['user_id'] = str(uuid.uuid4())[:8]
    
    # Criar mensagem do usuário
    user_message = chat_service.add_message(
        content=data['content'],
        user_id=session.get('user_id'),
        is_system=False,
        equipment_tag=data.get('equipment_tag')  # Tag opcional de equipamento
    )
    
    # Gerar resposta do sistema
    system_response = chat_service.generate_system_response(user_message)
    
    return jsonify([user_message.to_dict(), system_response.to_dict()])

@chat_api.route('/equipment/<tag>', methods=['GET'])
def get_equipment_info(tag):
    """Obter informações de um equipamento específico"""
    db = next(get_db())
    chat_service = ChatService(db)
    
    equipment = chat_service.get_equipment_info(tag)
    if not equipment:
        return jsonify({"error": f"Equipamento com TAG {tag} não encontrado"}), 404
    
    # Adicionar mensagem ao histórico do chat
    if 'user_id' not in session:
        session['user_id'] = str(uuid.uuid4())[:8]
    
    chat_service.add_message(
        content=f"Solicitando informações sobre o equipamento {tag}",
        user_id=session.get('user_id'),
        is_system=False,
        equipment_tag=tag
    )
    
    # Criar resposta com dados do equipamento
    response_data = {
        "tag": equipment.tag,
        "name": equipment.name,
        "type": equipment.type.value if equipment.type else None,
        "status": equipment.status.value if equipment.status else None,
        "location": equipment.location,
        "is_vulnerable": equipment.is_vulnerable,
        "last_maintenance": equipment.last_maintenance.isoformat() if equipment.last_maintenance else None,
        "next_maintenance": equipment.next_maintenance.isoformat() if equipment.next_maintenance else None
    }
    
    return jsonify(response_data)

@chat_api.route('/alerts/recent', methods=['GET'])
def get_recent_alerts():
    """Obter alertas recentes do sistema"""
    db = next(get_db())
    chat_service = ChatService(db)
    
    # Parâmetro opcional para limitar número de alertas
    limit = request.args.get('limit', 5, type=int)
    
    alerts = chat_service.get_recent_alerts(limit=limit)
    
    # Formatar alertas para resposta
    alert_data = []
    for alert in alerts:
        alert_data.append({
            "id": alert.id,
            "equipment_tag": alert.equipment_tag,
            "severity": alert.severity,
            "message": alert.message,
            "created_at": alert.created_at.isoformat() if alert.created_at else None,
            "status": alert.status
        })
    
    return jsonify(alert_data)
