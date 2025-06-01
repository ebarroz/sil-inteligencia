"""
API de Chat com Claude Opus 4 - SIL Predictive System
-----------------------------------------------------
Endpoints da API de chat integrados com Claude Opus 4 da Anthropic.
Fornece funcionalidades de chat inteligente contextualizado com dados do sistema.
"""
from flask import Blueprint, request, jsonify, session
import uuid
import logging

from src.services.chat.claude_service import ClaudeChatService
from src.config.database import get_db

logger = logging.getLogger("sil_chat_api")

# Criar blueprint para API de chat
chat_bp = Blueprint("chat", __name__, url_prefix="/api/chat")

@chat_bp.route("/sessions", methods=["POST"])
def create_chat_session():
    """Criar nova sessão de chat"""
    try:
        db = next(get_db())
        chat_service = ClaudeChatService(db)
        
        data = request.json or {}
        
        # Gerar ID de usuário se não estiver presente na sessão
        if "user_id" not in session:
            session["user_id"] = str(uuid.uuid4())[:8]
        
        user_id = session.get("user_id")
        session_name = data.get("session_name")
        
        # Criar sessão
        chat_session = chat_service.create_chat_session(
            user_id=user_id,
            session_name=session_name
        )
        
        return jsonify({
            "success": True,
            "session": chat_session.to_dict()
        })
        
    except Exception as e:
        logger.error(f"Erro ao criar sessão de chat: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@chat_bp.route("/sessions/<session_id>/messages", methods=["POST"])
def send_message(session_id):
    """Enviar mensagem para Claude"""
    try:
        db = next(get_db())
        chat_service = ClaudeChatService(db)
        
        data = request.json
        
        if not data or "content" not in data:
            return jsonify({
                "success": False,
                "error": "Conteúdo da mensagem é obrigatório"
            }), 400
        
        # Verificar se sessão existe
        chat_session = chat_service.get_chat_session(session_id)
        if not chat_session:
            return jsonify({
                "success": False,
                "error": "Sessão de chat não encontrada"
            }), 404
        
        # Processar mensagem
        result = chat_service.process_user_message(
            session_id=session_id,
            user_message=data["content"],
            equipment_tag=data.get("equipment_tag")
        )
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Erro ao processar mensagem: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@chat_bp.route("/sessions/<session_id>/messages", methods=["GET"])
def get_messages(session_id):
    """Obter mensagens de uma sessão"""
    try:
        db = next(get_db())
        chat_service = ClaudeChatService(db)
        
        # Verificar se sessão existe
        chat_session = chat_service.get_chat_session(session_id)
        if not chat_session:
            return jsonify({
                "success": False,
                "error": "Sessão de chat não encontrada"
            }), 404
        
        # Parâmetros opcionais
        limit = request.args.get("limit", 50, type=int)
        
        # Obter mensagens
        messages = chat_session.messages[-limit:] if chat_session.messages else []
        
        return jsonify({
            "success": True,
            "session_id": session_id,
            "messages": [msg.to_dict() for msg in messages]
        })
        
    except Exception as e:
        logger.error(f"Erro ao obter mensagens: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@chat_bp.route("/equipment/<equipment_tag>/analyze", methods=["POST"])
def analyze_equipment(equipment_tag):
    """Analisar equipamento específico usando Claude"""
    try:
        db = next(get_db())
        chat_service = ClaudeChatService(db)
        
        data = request.json or {}
        session_id = data.get("session_id")
        
        # Analisar equipamento
        result = chat_service.analyze_equipment(
            equipment_tag=equipment_tag,
            session_id=session_id
        )
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Erro ao analisar equipamento: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@chat_bp.route("/quick-chat", methods=["POST"])
def quick_chat():
    """Chat rápido sem sessão persistente"""
    try:
        db = next(get_db())
        chat_service = ClaudeChatService(db)
        
        data = request.json
        
        if not data or "message" not in data:
            return jsonify({
                "success": False,
                "error": "Mensagem é obrigatória"
            }), 400
        
        # Gerar ID de usuário temporário
        if "user_id" not in session:
            session["user_id"] = str(uuid.uuid4())[:8]
        
        # Criar sessão temporária
        temp_session = chat_service.create_chat_session(
            user_id=session.get("user_id"),
            session_name="Chat Rápido"
        )
        
        # Processar mensagem
        result = chat_service.process_user_message(
            session_id=temp_session.id,
            user_message=data["message"],
            equipment_tag=data.get("equipment_tag")
        )
        
        # Adicionar ID da sessão ao resultado
        result["session_id"] = temp_session.id
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Erro no chat rápido: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@chat_bp.route("/health", methods=["GET"])
def health_check():
    """Verificar saúde do serviço de chat"""
    try:
        db = next(get_db())
        chat_service = ClaudeChatService(db)
        
        health_status = chat_service.health_check()
        
        return jsonify(health_status)
        
    except Exception as e:
        logger.error(f"Erro no health check: {e}")
        return jsonify({
            "service": "unhealthy",
            "error": str(e)
        }), 500

@chat_bp.route("/sessions", methods=["GET"])
def list_sessions():
    """Listar sessões do usuário"""
    try:
        db = next(get_db())
        
        # Gerar ID de usuário se não estiver presente
        if "user_id" not in session:
            return jsonify({
                "success": True,
                "sessions": []
            })
        
        user_id = session.get("user_id")
        
        # Buscar sessões do usuário
        from src.models.chat import ChatSession
        sessions = db.query(ChatSession).filter(
            ChatSession.user_id == user_id,
            ChatSession.is_active == True
        ).order_by(ChatSession.updated_at.desc()).limit(20).all()
        
        return jsonify({
            "success": True,
            "sessions": [s.to_dict() for s in sessions]
        })
        
    except Exception as e:
        logger.error(f"Erro ao listar sessões: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@chat_bp.route("/sessions/<session_id>", methods=["DELETE"])
def delete_session(session_id):
    """Desativar sessão de chat"""
    try:
        db = next(get_db())
        chat_service = ClaudeChatService(db)
        
        # Verificar se sessão existe
        chat_session = chat_service.get_chat_session(session_id)
        if not chat_session:
            return jsonify({
                "success": False,
                "error": "Sessão não encontrada"
            }), 404
        
        # Desativar sessão
        chat_session.is_active = False
        db.commit()
        
        return jsonify({
            "success": True,
            "message": "Sessão desativada com sucesso"
        })
        
    except Exception as e:
        logger.error(f"Erro ao desativar sessão: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500
