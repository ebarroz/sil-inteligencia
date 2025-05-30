# Mapa de Diretórios do Projeto SIL Predictive System

## Visão Geral da Estrutura

O projeto SIL Predictive System está organizado em uma estrutura modular que segue as melhores práticas de desenvolvimento de software, com separação clara entre camadas de API, modelos de dados, serviços e lógica de negócios. Abaixo está o mapeamento detalhado de cada área do projeto.

## Estrutura de Diretórios (Idêntica para Produção e Desenvolvimento)

```
/
├── backups/                  # Armazenamento de backups do banco de dados
├── docker/                   # Configurações Docker e scripts de inicialização
│   └── init-db.sql           # Script SQL para inicialização do banco de dados
├── docs/                     # Documentação do projeto
├── logs/                     # Armazenamento de logs do sistema
├── scripts/                  # Scripts de automação e manutenção
└── src/                      # Código-fonte principal da aplicação
    ├── api/                  # Endpoints da API REST
    │   ├── alerts/           # Endpoints para gerenciamento da Central de Alertas
    │   ├── analysis/         # Endpoints para análise de causa raiz
    │   ├── equipment/        # Endpoints para gerenciamento de equipamentos
    │   ├── integration/      # Endpoints para integração com APIs externas
    │   ├── notifications/    # Endpoints para sistema de notificações
    │   └── risk/             # Endpoints para gerenciamento de perfis de risco
    ├── config/               # Configurações da aplicação
    │   ├── api.py            # Configuração da API REST
    │   └── database.py       # Configuração de conexão com o banco de dados
    ├── core/                 # Lógica de negócios central
    │   ├── alerts/           # Lógica para processamento de alertas
    │   ├── analysis/         # Algoritmos de análise de causa raiz
    │   ├── equipment/        # Lógica para gerenciamento de equipamentos
    │   ├── integration/      # Lógica para integração com sistemas externos
    │   ├── notifications/    # Lógica para envio de notificações
    │   └── risk/             # Lógica para avaliação de risco
    ├── models/               # Modelos de dados e entidades
    │   ├── alerts/           # Modelos para alertas
    │   │   └── alert.py      # Modelo para alertas de manutenção
    │   ├── equipment/        # Modelos para equipamentos
    │   │   └── equipment.py  # Modelo para equipamentos monitorados
    │   ├── risk/             # Modelos para perfis de risco
    │   │   └── risk_profile.py # Modelo para perfis de risco personalizados
    │   └── client.py         # Modelo para clientes/empresas
    ├── services/             # Serviços e integrações externas
    │   ├── alerts/           # Serviços para processamento de alertas
    │   ├── analysis/         # Serviços para análise de dados
    │   │   └── anthropic_service.py # Integração com a API da Anthropic
    │   ├── equipment/        # Serviços para gerenciamento de equipamentos
    │   ├── integration/      # Serviços para integração com APIs heterogêneas
    │   ├── notifications/    # Serviços para envio de notificações
    │   └── risk/             # Serviços para avaliação de risco
    └── utils/                # Utilitários e funções auxiliares
```

## Arquivos de Configuração na Raiz

| Arquivo | Descrição |
|---------|-----------|
| `.env` | Variáveis de ambiente com configurações sensíveis (senhas, chaves de API) |
| `.env.example` | Exemplo de configuração de variáveis de ambiente para referência |
| `docker-compose.yml` | Configuração dos containers Docker (PostgreSQL, Redis, pgAdmin) |
| `README.md` | Documentação principal do projeto |

## Ambientes do Projeto

### Ambiente de Produção
- **Diretório**: `/home/enzo/projects/sil-predictive-system/`
- **Proprietário**: Enzo (Proprietário do Projeto)
- **Finalidade**: Execução do sistema em produção

### Ambiente de Desenvolvimento
- **Diretório**: Repositório `sil-inteligencia` nos diretórios de teste dos usuários
- **Proprietários**: 
  - Manus (Engenheiro de Integrações): `/home/manus/test/sil-inteligencia/`
  - Claude Code (via Docker): Container `claude-ai`
- **Finalidade**: Desenvolvimento e testes de novas funcionalidades

## Fluxos Principais do Sistema

### 1. Fluxo de Alertas
- Dados coletados via APIs heterogêneas (`src/api/integration`)
- Processados e filtrados para remover falsos positivos (`src/core/alerts`)
- Armazenados no banco de dados PostgreSQL
- Exibidos na Central de Alertas para validação humana

### 2. Fluxo de Análise de Causa Raiz
- Alertas validados são analisados pela IA da Anthropic (`src/services/analysis/anthropic_service.py`)
- Padrões recorrentes são identificados
- Relatórios são gerados para os clientes

### 3. Fluxo de Notificações
- Alertas críticos geram notificações automáticas
- Configurável por cliente e nível de gravidade

## Containers Docker

O ambiente de execução é composto por três containers principais:

1. **PostgreSQL com TimescaleDB** (porta 5434)
   - Banco de dados principal com extensão para séries temporais
   - Armazena dados de equipamentos, alertas e métricas

2. **Redis** (porta 6380)
   - Cache para melhorar performance
   - Filas de processamento assíncrono

3. **pgAdmin** (porta 8081)
   - Interface web para administração do banco de dados
   - Facilita consultas e manutenção

## Próximos Passos de Desenvolvimento

1. Implementação completa dos endpoints da API REST
2. Desenvolvimento da interface de usuário
3. Integração com fontes de dados reais
4. Implementação de testes automatizados
5. Configuração de CI/CD para implantação contínua
