"""
Configuração de APIs - SIL Predictive System
-------------------------------------------
Este módulo define as configurações para integração com APIs externas
e fornece funções de utilidade para operações de API.
"""

import os
import requests
from typing import Dict, Any, Optional

# Configurações de APIs externas
API_CONFIGS = {
    "vibration": {
        "base_url": os.environ.get("VIBRATION_API_URL", "https://api.vibration-monitor.com/v1"),
        "api_key": os.environ.get("VIBRATION_API_KEY", ""),
        "timeout": 30,
        "retry_attempts": 3
    },
    "thermography": {
        "base_url": os.environ.get("THERMOGRAPHY_API_URL", "https://api.thermo-vision.com/v2"),
        "api_key": os.environ.get("THERMOGRAPHY_API_KEY", ""),
        "timeout": 45,
        "retry_attempts": 2
    },
    "oil_analysis": {
        "base_url": os.environ.get("OIL_API_URL", "https://api.oil-analytics.com/v1"),
        "api_key": os.environ.get("OIL_API_KEY", ""),
        "timeout": 30,
        "retry_attempts": 3
    },
    "anthropic": {
        "base_url": os.environ.get("ANTHROPIC_API_URL", "https://api.anthropic.com/v1"),
        "api_key": os.environ.get("ANTHROPIC_API_KEY", ""),
        "model": os.environ.get("ANTHROPIC_MODEL", "claude-3-opus-20240229"),
        "timeout": 60,
        "max_tokens": 4000
    }
}

def get_api_client(api_name: str):
    """
    Retorna um cliente configurado para a API especificada.
    
    Args:
        api_name: Nome da API (vibration, thermography, oil_analysis, anthropic)
        
    Returns:
        Cliente configurado para a API
    """
    if api_name not in API_CONFIGS:
        raise ValueError(f"API não configurada: {api_name}")
    
    config = API_CONFIGS[api_name]
    
    class APIClient:
        def __init__(self, config):
            self.base_url = config["base_url"]
            self.api_key = config["api_key"]
            self.timeout = config.get("timeout", 30)
            self.retry_attempts = config.get("retry_attempts", 3)
            self.headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
        
        def get(self, endpoint: str, params: Optional[Dict[str, Any]] = None):
            """Executa uma requisição GET para a API."""
            url = f"{self.base_url}/{endpoint}"
            response = requests.get(url, params=params, headers=self.headers, timeout=self.timeout)
            response.raise_for_status()
            return response.json()
        
        def post(self, endpoint: str, data: Dict[str, Any]):
            """Executa uma requisição POST para a API."""
            url = f"{self.base_url}/{endpoint}"
            response = requests.post(url, json=data, headers=self.headers, timeout=self.timeout)
            response.raise_for_status()
            return response.json()
    
    return APIClient(config)
