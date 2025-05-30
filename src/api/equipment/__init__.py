"""
Módulo de Equipamentos - SIL Predictive System
---------------------------------------------
Este módulo implementa o sistema de TAG como "RG" do Equipamento conforme requisito #6:
- Cada máquina recebe uma TAG única (identificador)
- TAG é usada em todos os fluxos do sistema
"""

from flask import Blueprint, jsonify, request

equipment_bp = Blueprint('equipment', __name__)

@equipment_bp.route('/')
def get_equipment():
    """Retorna todos os equipamentos cadastrados."""
    return jsonify({
        "status": "success",
        "message": "Equipamentos cadastrados",
        "data": {
            "equipment": []  # Será populado com dados reais
        }
    })

@equipment_bp.route('/<tag>')
def get_equipment_by_tag(tag):
    """Retorna informações de um equipamento específico por TAG."""
    return jsonify({
        "status": "success",
        "message": f"Informações do equipamento {tag}",
        "data": {
            "tag": tag,
            "name": f"Equipamento {tag}",
            "client_id": "client_123",
            "type": "motor",
            "status": "operational",
            "last_maintenance": "2025-04-15T10:30:00Z"
        }
    })

@equipment_bp.route('/', methods=['POST'])
def create_equipment():
    """Cadastra um novo equipamento."""
    data = request.json
    
    return jsonify({
        "status": "success",
        "message": "Equipamento cadastrado com sucesso",
        "data": {
            "tag": data.get('tag'),
            "name": data.get('name'),
            "client_id": data.get('client_id')
        }
    })

@equipment_bp.route('/vulnerability')
def get_vulnerable_equipment():
    """Implementa a detecção de vulnerabilidades (requisito #12)."""
    return jsonify({
        "status": "success",
        "message": "Equipamentos vulneráveis",
        "data": {
            "vulnerable_equipment": [],  # Será populado com dados reais
            "vulnerability_criteria": {
                "no_online_monitoring": True,
                "incomplete_data": True,
                "missing_maintenance": True
            }
        }
    })

@equipment_bp.route('/client/<client_id>')
def get_client_equipment(client_id):
    """Retorna todos os equipamentos de um cliente específico."""
    return jsonify({
        "status": "success",
        "message": f"Equipamentos do cliente {client_id}",
        "data": {
            "client_id": client_id,
            "equipment": []  # Será populado com dados reais
        }
    })
