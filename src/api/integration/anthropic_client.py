"""
Anthropic Claude API Client for SIL Predictive System
-----------------------------------------------------
Cliente especializado para integração com a API da Anthropic Claude Opus 4.
Este módulo fornece funcionalidades específicas para chat inteligente
contextualizado com dados do sistema SIL.
"""
import os
import json
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
import requests
from requests.exceptions import RequestException, Timeout, ConnectionError

# Configure logging
logger = logging.getLogger('sil_anthropic_client')

class AnthropicClient:
    """
    Cliente especializado para API Anthropic Claude Opus 4.
    
    Funcionalidades:
    - Chat contextualizado com dados do sistema SIL
    - Análise de equipamentos e alertas
    - Geração de relatórios inteligentes
    - Suporte a conversas multi-turno
    """
    
    def __init__(
        self,
        api_key: str = None,
        model: str = "claude-3-opus-20240229",
        max_tokens: int = 4096,
        temperature: float = 0.7
    ):
        """
        Inicializa o cliente Anthropic.
        
        Args:
            api_key: Chave da API Anthropic (padrão: variável de ambiente)
            model: Modelo Claude a ser usado
            max_tokens: Número máximo de tokens na resposta
            temperature: Temperatura para controle de criatividade
        """
        self.api_key = api_key or os.getenv('ANTHROPIC_API_KEY')
        self.model = model or os.getenv('ANTHROPIC_MODEL', 'claude-3-opus-20240229')
        self.max_tokens = max_tokens or int(os.getenv('ANTHROPIC_MAX_TOKENS', '4096'))
        self.temperature = temperature or float(os.getenv('ANTHROPIC_TEMPERATURE', '0.7'))
        
        self.base_url = "https://api.anthropic.com/v1"
        self.headers = {
            "Content-Type": "application/json",
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01"
        }
        
        if not self.api_key:
            raise ValueError("API key da Anthropic é obrigatória")
    
    def create_system_prompt(self, context_data: Dict[str, Any] = None) -> str:
        """
        Cria prompt de sistema contextualizado para o SIL Predictive System.
        
        Args:
            context_data: Dados contextuais do sistema (equipamentos, alertas, etc.)
            
        Returns:
            String com prompt de sistema formatado
        """
        base_prompt = """Você é um assistente especializado do SIL Predictive System, um sistema de monitoramento preditivo industrial. 

Suas responsabilidades incluem:
- Análise de dados de termografia, vibração e análise de óleo
- Interpretação de alertas e riscos de equipamentos
- Fornecimento de recomendações de manutenção
- Explicação de dados técnicos de forma clara e objetiva
- Suporte a decisões de manutenção preventiva e preditiva

Sempre responda de forma técnica mas acessível, focando em ações práticas e segurança operacional."""
        
        if context_data:
            context_prompt = "\n\nContexto atual do sistema:\n"
            
            if 'equipment' in context_data:
                context_prompt += f"- Equipamento em foco: {context_data['equipment']}\n"
            
            if 'alerts' in context_data:
                context_prompt += f"- Alertas ativos: {len(context_data['alerts'])}\n"
                for alert in context_data['alerts'][:3]:  # Máximo 3 alertas
                    context_prompt += f"  * {alert.get('severity', 'N/A')}: {alert.get('message', 'N/A')}\n"
            
            if 'recent_data' in context_data:
                context_prompt += f"- Dados recentes disponíveis: {', '.join(context_data['recent_data'])}\n"
            
            base_prompt += context_prompt
        
        return base_prompt
    
    def send_message(
        self,
        message: str,
        context_data: Dict[str, Any] = None,
        conversation_history: List[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Envia mensagem para Claude e retorna resposta.
        
        Args:
            message: Mensagem do usuário
            context_data: Dados contextuais do sistema
            conversation_history: Histórico da conversa
            
        Returns:
            Dicionário com resposta e metadados
        """
        try:
            # Preparar mensagens
            messages = []
            
            # Adicionar histórico se fornecido
            if conversation_history:
                messages.extend(conversation_history)
            
            # Adicionar mensagem atual
            messages.append({
                "role": "user",
                "content": message
            })
            
            # Preparar payload
            payload = {
                "model": self.model,
                "max_tokens": self.max_tokens,
                "temperature": self.temperature,
                "system": self.create_system_prompt(context_data),
                "messages": messages
            }
            
            logger.info(f"Enviando mensagem para Claude: {message[:100]}...")
            
            # Fazer requisição
            response = requests.post(
                f"{self.base_url}/messages",
                headers=self.headers,
                json=payload,
                timeout=30
            )
            
            response.raise_for_status()
            result = response.json()
            
            logger.info("Resposta recebida com sucesso do Claude")
            
            return {
                "success": True,
                "response": result.get("content", [{}])[0].get("text", ""),
                "usage": result.get("usage", {}),
                "model": result.get("model", self.model),
                "timestamp": datetime.now().isoformat()
            }
            
        except RequestException as e:
            logger.error(f"Erro na requisição para Anthropic: {e}")
            return {
                "success": False,
                "error": f"Erro de comunicação: {str(e)}",
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Erro inesperado no cliente Anthropic: {e}")
            return {
                "success": False,
                "error": f"Erro interno: {str(e)}",
                "timestamp": datetime.now().isoformat()
            }
    
    def analyze_equipment_data(
        self,
        equipment_tag: str,
        equipment_data: Dict[str, Any],
        measurement_data: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Analisa dados de equipamento usando Claude.
        
        Args:
            equipment_tag: TAG do equipamento
            equipment_data: Dados básicos do equipamento
            measurement_data: Dados de medições (termografia, vibração, óleo)
            
        Returns:
            Análise detalhada do equipamento
        """
        # Preparar contexto específico
        context = {
            "equipment": equipment_tag,
            "equipment_data": equipment_data,
            "measurement_data": measurement_data or {}
        }
        
        # Criar mensagem de análise
        analysis_message = f"""Analise o equipamento {equipment_tag} com base nos seguintes dados:

Dados do Equipamento:
- Nome: {equipment_data.get('name', 'N/A')}
- Tipo: {equipment_data.get('type', 'N/A')}
- Status: {equipment_data.get('status', 'N/A')}
- Localização: {equipment_data.get('location', 'N/A')}
- Vulnerável: {equipment_data.get('is_vulnerable', 'N/A')}

"""
        
        if measurement_data:
            analysis_message += "Dados de Medições:\n"
            for measurement_type, data in measurement_data.items():
                analysis_message += f"- {measurement_type}: {data}\n"
        
        analysis_message += """
Por favor, forneça:
1. Avaliação do estado atual do equipamento
2. Identificação de possíveis problemas ou riscos
3. Recomendações de manutenção
4. Prioridade de ação (baixa/média/alta/crítica)
"""
        
        return self.send_message(analysis_message, context)
    
    def generate_maintenance_report(
        self,
        equipment_list: List[Dict[str, Any]],
        alert_summary: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Gera relatório de manutenção usando Claude.
        
        Args:
            equipment_list: Lista de equipamentos para análise
            alert_summary: Resumo de alertas do sistema
            
        Returns:
            Relatório de manutenção gerado
        """
        context = {
            "equipment_count": len(equipment_list),
            "alerts": alert_summary.get("alerts", []) if alert_summary else []
        }
        
        report_message = f"""Gere um relatório de manutenção baseado nos seguintes dados:

Total de Equipamentos: {len(equipment_list)}

Equipamentos:
"""
        
        for eq in equipment_list[:10]:  # Limitar a 10 equipamentos
            report_message += f"- {eq.get('tag', 'N/A')}: {eq.get('name', 'N/A')} ({eq.get('status', 'N/A')})\n"
        
        if alert_summary:
            report_message += f"\nAlertas Ativos: {len(alert_summary.get('alerts', []))}\n"
        
        report_message += """
Por favor, gere um relatório que inclua:
1. Resumo executivo do estado geral
2. Equipamentos que requerem atenção imediata
3. Plano de manutenção recomendado
4. Estimativa de custos e recursos necessários
5. Cronograma sugerido de ações
"""
        
        return self.send_message(report_message, context)
    
    def health_check(self) -> Dict[str, Any]:
        """
        Verifica a saúde da conexão com a API Anthropic.
        
        Returns:
            Status da conexão
        """
        try:
            test_response = self.send_message(
                "Teste de conectividade. Responda apenas 'OK' se estiver funcionando.",
                context_data={"test": True}
            )
            
            return {
                "status": "healthy" if test_response.get("success") else "unhealthy",
                "api_key_configured": bool(self.api_key),
                "model": self.model,
                "last_test": datetime.now().isoformat(),
                "response": test_response
            }
            
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "last_test": datetime.now().isoformat()
            }
