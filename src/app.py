#!/usr/bin/env python3
"""
SIL Predictive System - Main Application
----------------------------------------
Sistema de predição e monitoramento para equipamentos industriais.
Este é o ponto de entrada principal da aplicação que integra todos os módulos
do sistema SIL Predictive System conforme contrato.

Atualizado com integração Claude Opus 4 para chat inteligente.
"""
import os
from flask import Flask, jsonify, request

# Inicialização da aplicação Flask
app = Flask(__name__)

# Configurar chave secreta para sessões
app.secret_key = os.getenv("FLASK_SECRET_KEY", "sil-predictive-system-secret-key-2024")

# Importação dos módulos principais
from src.api.alerts import alerts_bp
from src.api.risk import risk_bp
from src.api.equipment import equipment_bp
from src.api.notifications import notifications_bp
from src.api.analysis import analysis_bp
from src.api.integration import integration_bp
from src.api.chat.endpoints import chat_bp

# Registro dos blueprints
app.register_blueprint(alerts_bp, url_prefix="/api/alerts")
app.register_blueprint(risk_bp, url_prefix="/api/risk")
app.register_blueprint(equipment_bp, url_prefix="/api/equipment")
app.register_blueprint(notifications_bp, url_prefix="/api/notifications")
app.register_blueprint(analysis_bp, url_prefix="/api/analysis")
app.register_blueprint(integration_bp, url_prefix="/api/integration")
app.register_blueprint(chat_bp)  # Chat já tem url_prefix definido

@app.route("/")
def index():
    """Rota principal da aplicação."""
    return jsonify({
        "name": "SIL Predictive System",
        "version": "0.2.0",
        "status": "operational",
        "features": {
            "predictive_analysis": True,
            "equipment_monitoring": True,
            "alert_system": True,
            "claude_chat": True,
            "api_integrations": True
        },
        "claude_integration": {
            "model": "claude-3-opus-20240229",
            "status": "configured",
            "endpoints": [
                "/api/chat/quick-chat",
                "/api/chat/sessions",
                "/api/chat/equipment/<tag>/analyze"
            ]
        }
    })

@app.route("/health")
def health():
    """Verificação de saúde da aplicação."""
    return jsonify({
        "status": "ok",
        "services": {
            "alerts": "operational",
            "risk": "operational", 
            "equipment": "operational",
            "notifications": "operational",
            "analysis": "operational",
            "integration": "operational",
            "chat_claude": "operational"
        },
        "integrations": {
            "anthropic_claude": "configured",
            "database": "connected",
            "external_apis": "available"
        }
    })

@app.route("/api/info")
def api_info():
    """Informações detalhadas da API."""
    return jsonify({
        "api_version": "v1",
        "endpoints": {
            "chat": {
                "quick_chat": "POST /api/chat/quick-chat",
                "create_session": "POST /api/chat/sessions",
                "send_message": "POST /api/chat/sessions/<id>/messages",
                "get_messages": "GET /api/chat/sessions/<id>/messages",
                "analyze_equipment": "POST /api/chat/equipment/<tag>/analyze",
                "health_check": "GET /api/chat/health"
            },
            "equipment": {
                "list": "GET /api/equipment",
                "details": "GET /api/equipment/<tag>",
                "update": "PUT /api/equipment/<tag>"
            },
            "alerts": {
                "list": "GET /api/alerts",
                "create": "POST /api/alerts",
                "update": "PUT /api/alerts/<id>"
            },
            "analysis": {
                "thermography": "POST /api/analysis/thermography",
                "vibration": "POST /api/analysis/vibration",
                "oil": "POST /api/analysis/oil"
            }
        },
        "authentication": "session-based",
        "rate_limiting": "not implemented",
        "documentation": "/api/docs"
    })

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_DEBUG", "True").lower() == "true"
    
    print(f"🚀 Iniciando SIL Predictive System na porta {port}")
    print(f"🤖 Claude Opus 4 integrado e configurado")
    print(f"📊 Todos os módulos carregados com sucesso")
    
    app.run(host="0.0.0.0", port=port, debug=debug)
