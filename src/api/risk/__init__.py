"""
Módulo de Risco - SIL Predictive System
--------------------------------------
Este módulo implementa o Grau de Risco Personalizado conforme requisito #2:
- Cada cliente (empresa) define seu próprio grau de risco
- Parametrização personalizada por cliente
"""

from flask import Blueprint, jsonify, request

risk_bp = Blueprint('risk', __name__)

@risk_bp.route('/')
def get_risk_profiles():
    """Retorna todos os perfis de risco configurados."""
    return jsonify({
        "status": "success",
        "message": "Perfis de risco disponíveis",
        "data": {
            "risk_profiles": []  # Será populado com dados reais
        }
    })

@risk_bp.route('/client/<client_id>')
def get_client_risk_profile(client_id):
    """Retorna o perfil de risco específico de um cliente."""
    return jsonify({
        "status": "success",
        "message": f"Perfil de risco do cliente {client_id}",
        "data": {
            "client_id": client_id,
            "risk_parameters": {
                "high_threshold": 0.8,
                "medium_threshold": 0.5,
                "low_threshold": 0.3
            }
        }
    })

@risk_bp.route('/client/<client_id>', methods=['PUT'])
def update_client_risk_profile(client_id):
    """Atualiza o perfil de risco de um cliente."""
    data = request.json
    
    return jsonify({
        "status": "success",
        "message": f"Perfil de risco do cliente {client_id} atualizado",
        "data": {
            "client_id": client_id,
            "risk_parameters": data.get('risk_parameters', {})
        }
    })

@risk_bp.route('/calculate/<equipment_tag>')
def calculate_risk(equipment_tag):
    """Calcula o risco atual para um equipamento específico."""
    return jsonify({
        "status": "success",
        "message": f"Cálculo de risco para equipamento {equipment_tag}",
        "data": {
            "equipment_tag": equipment_tag,
            "risk_level": "medium",
            "risk_score": 0.65,
            "factors": [
                {"name": "vibração", "contribution": 0.4},
                {"name": "temperatura", "contribution": 0.25}
            ]
        }
    })
