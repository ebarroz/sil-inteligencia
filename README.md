# SIL Predictive System

Sistema de monitoramento preditivo industrial integrado com inteligência artificial Claude Opus 4.

## 🚀 Funcionalidades

### Core System
- **Monitoramento Preditivo**: Análise de equipamentos industriais
- **Análise Multi-Modal**: Termografia, vibração e análise de óleo
- **Sistema de Alertas**: Notificações inteligentes de riscos
- **Gestão de Equipamentos**: Controle completo do parque industrial

### 🤖 Integração Claude Opus 4
- **Chat Inteligente**: Conversas contextualizadas com dados do sistema
- **Análise Automática**: Interpretação inteligente de dados de equipamentos
- **Relatórios Dinâmicos**: Geração automática de relatórios de manutenção
- **Recomendações**: Sugestões baseadas em IA para manutenção preventiva

## 📋 Requisitos

- Python 3.8+
- PostgreSQL com TimescaleDB
- Redis (cache)
- Docker e Docker Compose
- Chave da API Anthropic Claude

## 🛠️ Instalação

### 1. Clone o Repositório
```bash
git clone <repository-url>
cd sil-inteligencia
```

### 2. Configuração do Ambiente
```bash
cp .env.example .env
# Edite o arquivo .env com suas configurações
```

### 3. Configurações Obrigatórias

Edite o arquivo `.env`:

```bash
# Banco de Dados
DB_NAME=sil_centro_inteligencia
DB_USER=administrador
DB_PASSWORD=sua_senha_aqui

# Redis
REDIS_PASSWORD=sua_senha_redis

# Anthropic Claude API
ANTHROPIC_API_KEY=sua_chave_anthropic_aqui
ANTHROPIC_MODEL=claude-3-opus-20240229
ANTHROPIC_MAX_TOKENS=4096
ANTHROPIC_TEMPERATURE=0.7

# Flask
FLASK_SECRET_KEY=sua_chave_secreta_flask
```

### 4. Iniciar com Docker
```bash
docker-compose up -d
```

### 5. Executar Aplicação
```bash
python src/app.py
```

## 🔗 Endpoints da API

### Sistema Principal
- `GET /` - Informações do sistema
- `GET /health` - Status de saúde
- `GET /api/info` - Documentação da API

### Chat com Claude
- `POST /api/chat/quick-chat` - Chat rápido
- `POST /api/chat/sessions` - Criar sessão
- `POST /api/chat/sessions/{id}/messages` - Enviar mensagem
- `GET /api/chat/sessions/{id}/messages` - Obter mensagens
- `POST /api/chat/equipment/{tag}/analyze` - Analisar equipamento
- `GET /api/chat/health` - Status do chat

### Equipamentos
- `GET /api/equipment` - Listar equipamentos
- `GET /api/equipment/{tag}` - Detalhes do equipamento
- `PUT /api/equipment/{tag}` - Atualizar equipamento

### Alertas
- `GET /api/alerts` - Listar alertas
- `POST /api/alerts` - Criar alerta
- `PUT /api/alerts/{id}` - Atualizar alerta

## 💬 Exemplos de Uso do Chat

### Chat Rápido
```bash
curl -X POST http://localhost:5000/api/chat/quick-chat \
  -H "Content-Type: application/json" \
  -d {message: Como está o equipamento PUMP-001?}
```

### Análise de Equipamento
```bash
curl -X POST http://localhost:5000/api/chat/equipment/MOTOR-001/analyze \
  -H "Content-Type: application/json"
```

### Criar Sessão de Chat
```bash
curl -X POST http://localhost:5000/api/chat/sessions \
  -H "Content-Type: application/json" \
  -d {session_name: Análise Diária}
```

## 🏗️ Arquitetura

```
src/
├── api/                    # Endpoints da API
│   ├── chat/              # Chat com Claude
│   ├── equipment/         # Gestão de equipamentos
│   ├── alerts/            # Sistema de alertas
│   └── integration/       # Integrações externas
├── services/              # Lógica de negócio
│   └── chat/             # Serviços de chat
├── models/               # Modelos de dados
├── core/                 # Funcionalidades core
└── config/               # Configurações
```

## 🔧 Configuração Avançada

### Variáveis de Ambiente Completas

```bash
# Banco de Dados PostgreSQL
DB_NAME=sil_centro_inteligencia
DB_USER=administrador
DB_PASSWORD=sua_senha
DB_HOST=localhost
DB_PORT=5434

# Cache Redis
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=sua_senha_redis

# Interface pgAdmin
PGADMIN_EMAIL=admin@example.com
PGADMIN_PASSWORD=sua_senha_pgadmin

# Anthropic Claude API
ANTHROPIC_API_KEY=sk-ant-api03-...
ANTHROPIC_MODEL=claude-3-opus-20240229
ANTHROPIC_MAX_TOKENS=4096
ANTHROPIC_TEMPERATURE=0.7

# Configurações da Aplicação
NODE_ENV=production
TZ=America/Sao_Paulo
FLASK_SECRET_KEY=sua-chave-secreta-muito-segura
FLASK_DEBUG=False
PORT=5000
```

## 📊 Monitoramento

### Health Checks
- Sistema principal: `GET /health`
- Chat Claude: `GET /api/chat/health`
- Banco de dados: Verificação automática
- APIs externas: Status em tempo real

### Logs
Os logs são organizados por módulo:
- `sil_anthropic_client` - Cliente Anthropic
- `sil_claude_service` - Serviço de chat
- `sil_chat_api` - API de chat

## 🔒 Segurança

### Autenticação
- Sistema baseado em sessões Flask
- IDs de usuário únicos por sessão
- Isolamento de dados por usuário

### Rate Limiting
- Implementado no cliente Anthropic
- Retry automático com backoff
- Timeout configurável

### Validação
- Validação de entrada em todos endpoints
- Sanitização de dados
- Tratamento seguro de erros

## 🚨 Troubleshooting

### Problemas Comuns

1. **Erro de conexão com Claude**
   ```bash
   # Verificar configuração
   curl -X GET http://localhost:5000/api/chat/health
   ```

2. **Banco de dados não conecta**
   ```bash
   # Verificar containers
   docker-compose ps
   ```

3. **Erro de API Key**
   - Verificar se `ANTHROPIC_API_KEY` está configurada
   - Validar permissões da chave

### Logs de Debug
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## 📈 Performance

### Otimizações Implementadas
- Cache de sessões Redis
- Pool de conexões do banco
- Retry automático para APIs
- Timeout configurável

### Métricas Monitoradas
- Tempo de resposta do Claude
- Taxa de sucesso das requisições
- Uso de tokens da API
- Performance do banco de dados

## 🔄 Atualizações

### Versão 0.2.0 (Atual)
- ✅ Integração completa com Claude Opus 4
- ✅ Sistema de chat contextualizado
- ✅ Análise automática de equipamentos
- ✅ Documentação completa

### Próximas Versões
- [ ] Interface web para chat
- [ ] Relatórios automáticos
- [ ] Integração IoT em tempo real
- [ ] Dashboard analítico

## 📞 Suporte

Para suporte técnico:
1. Consulte os logs do sistema
2. Execute health checks
3. Verifique a documentação da API
4. Consulte o arquivo `docs/claude_integration.md`

## 📄 Licença

Este projeto é propriedade da equipe SIL e está sob licença proprietária.

## 👥 Contribuidores

- Similar
- Enzo Bellissimo
- Arquitetura: Sistema SIL Predictive

---

**Nota**: Este sistema integra tecnologias avançadas de IA para monitoramento industrial. Certifique-se de configurar adequadamente todas as credenciais antes do uso em produção.
