#!/usr/bin/env python3
"""
SIL Predictive System - Main Application
----------------------------------------
Sistema de predição e monitoramento para equipamentos industriais.

Este é o ponto de entrada principal da aplicação que integra todos os módulos
do sistema SIL Predictive System conforme contrato.
"""

import os
from flask import Flask, jsonify, request

# Inicialização da aplicação Flask
app = Flask(__name__)

# Importação dos módulos principais
from src.api.alerts import alerts_bp
from src.api.risk import risk_bp
from src.api.equipment import equipment_bp
from src.api.notifications import notifications_bp
from src.api.analysis import analysis_bp
from src.api.integration import integration_bp

# Registro dos blueprints
app.register_blueprint(alerts_bp, url_prefix='/api/alerts')
app.register_blueprint(risk_bp, url_prefix='/api/risk')
app.register_blueprint(equipment_bp, url_prefix='/api/equipment')
app.register_blueprint(notifications_bp, url_prefix='/api/notifications')
app.register_blueprint(analysis_bp, url_prefix='/api/analysis')
app.register_blueprint(integration_bp, url_prefix='/api/integration')

@app.route('/')
def index():
    """Rota principal da aplicação."""
    return jsonify({
        "name": "SIL Predictive System",
        "version": "0.1.0",
        "status": "operational"
    })

@app.route('/health')
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
            "integration": "operational"
        }
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
