# Integração Claude Opus 4 - SIL Predictive System

## Visão Geral

Este documento descreve a integração do Claude Opus 4 da Anthropic com o SIL Predictive System, fornecendo capacidades de chat inteligente contextualizado com dados do sistema industrial.

## Arquitetura da Integração

### Componentes Principais

1. **AnthropicClient** (`src/api/integration/anthropic_client.py`)
   - Cliente especializado para comunicação com a API Anthropic
   - Gerencia autenticação, rate limiting e tratamento de erros
   - Fornece métodos específicos para análise de equipamentos

2. **ClaudeChatService** (`src/services/chat/claude_service.py`)
   - Serviço de alto nível que integra Claude com o banco de dados
   - Gerencia sessões de chat e histórico de conversas
   - Contextualiza respostas com dados do sistema SIL

3. **Modelos de Dados** (`src/models/chat.py`)
   - ChatSession: Agrupa mensagens de uma conversa
   - ChatMessage: Mensagens individuais do chat

4. **Endpoints da API** (`src/api/chat/endpoints.py`)
   - Rotas REST para interação com o chat
   - Integração com sistema de sessões Flask

## Configuração

### Variáveis de Ambiente

Adicione as seguintes variáveis ao arquivo `.env`:

```bash
# Configurações da API Anthropic Claude
ANTHROPIC_API_KEY=your_anthropic_api_key_here
ANTHROPIC_MODEL=claude-3-opus-20240229
ANTHROPIC_MAX_TOKENS=4096
ANTHROPIC_TEMPERATURE=0.7
```

### Dependências

O sistema requer as seguintes dependências Python:

- `requests` - Para comunicação HTTP com a API Anthropic
- `flask` - Framework web
- `sqlalchemy` - ORM para banco de dados
- `uuid` - Geração de IDs únicos

## Endpoints da API

### Chat Rápido
```http
POST /api/chat/quick-chat
Content-Type: application/json

{
  "message": "Como está o equipamento PUMP-001?",
  "equipment_tag": "PUMP-001"
}
```

### Criar Sessão de Chat
```http
POST /api/chat/sessions
Content-Type: application/json

{
  "session_name": "Análise de Equipamentos"
}
```

### Enviar Mensagem
```http
POST /api/chat/sessions/{session_id}/messages
Content-Type: application/json

{
  "content": "Analise os dados de vibração do último mês",
  "equipment_tag": "MOTOR-001"
}
```

### Analisar Equipamento
```http
POST /api/chat/equipment/{equipment_tag}/analyze
Content-Type: application/json

{
  "session_id": "optional-session-id"
}
```

### Verificar Saúde
```http
GET /api/chat/health
```

## Funcionalidades

### 1. Chat Contextualizado

O Claude recebe contexto automático sobre:
- Estado atual dos equipamentos
- Alertas ativos no sistema
- Dados recentes de medições
- Histórico da conversa

### 2. Análise de Equipamentos

Capacidades específicas:
- Interpretação de dados de termografia
- Análise de padrões de vibração
- Avaliação de análises de óleo
- Recomendações de manutenção

### 3. Geração de Relatórios

O Claude pode gerar:
- Relatórios de estado de equipamentos
- Planos de manutenção preventiva
- Análises de risco
- Resumos executivos

## Segurança

### Autenticação
- Sistema baseado em sessões Flask
- IDs de usuário gerados automaticamente
- Sessões isoladas por usuário

### Rate Limiting
- Implementado no cliente Anthropic
- Retry automático com backoff exponencial
- Timeout configurável para requisições

### Tratamento de Erros
- Logs detalhados de todas as operações
- Fallback para mensagens de erro amigáveis
- Validação de entrada em todos os endpoints

## Monitoramento

### Health Check
O endpoint `/api/chat/health` verifica:
- Conectividade com a API Anthropic
- Status do banco de dados
- Configuração das credenciais

### Logs
Todos os eventos são registrados com níveis apropriados:
- INFO: Operações normais
- WARNING: Situações de atenção
- ERROR: Falhas e exceções

## Exemplos de Uso

### Consulta Simples
```python
import requests

response = requests.post(http://localhost:5000/api/chat/quick-chat, json={
    message: Qual é o status geral dos equipamentos?
})

print(response.json())
```

### Análise de Equipamento
```python
response = requests.post(http://localhost:5000/api/chat/equipment/PUMP-001/analyze)
analysis = response.json()

if analysis[success]:
    print(f"Análise: {analysis[response]}")
```

## Troubleshooting

### Problemas Comuns

1. **Erro de API Key**
   - Verificar se ANTHROPIC_API_KEY está configurada
   - Validar se a chave tem permissões adequadas

2. **Timeout de Requisição**
   - Verificar conectividade com api.anthropic.com
   - Ajustar timeout nas configurações

3. **Erro de Banco de Dados**
   - Verificar se as tabelas de chat foram criadas
   - Validar conexão com PostgreSQL

### Logs de Debug

Para ativar logs detalhados:
```python
import logging
logging.getLogger(sil_anthropic_client).setLevel(logging.DEBUG)
logging.getLogger(sil_claude_service).setLevel(logging.DEBUG)
```

## Roadmap

### Próximas Funcionalidades
- [ ] Integração com dados de IoT em tempo real
- [ ] Análise preditiva avançada
- [ ] Relatórios automáticos agendados
- [ ] Interface web para chat
- [ ] Integração com sistema de notificações

### Melhorias Planejadas
- [ ] Cache de respostas frequentes
- [ ] Otimização de prompts
- [ ] Suporte a múltiplos idiomas
- [ ] Análise de sentimento
- [ ] Integração com ferramentas de BI

## Suporte

Para suporte técnico ou dúvidas sobre a integração:
- Consulte os logs do sistema
- Verifique a documentação da API Anthropic
- Execute o health check para diagnóstico
