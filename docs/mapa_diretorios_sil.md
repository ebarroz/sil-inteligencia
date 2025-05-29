# Mapa de Diretórios do Projeto SIL Predictive System

## Visão Geral da Estrutura

O projeto SIL Predictive System está organizado em uma estrutura modular que segue as melhores práticas de desenvolvimento de software, com separação clara entre camadas de API, modelos de dados, serviços e lógica de negócios. Abaixo está o mapeamento detalhado de cada área do projeto.

## Estrutura de Diretórios Principal

```
/home/manus/test/sil-inteligencia/
├── backups/                  # Armazenamento de backups do banco de dados
├── docker/                   # Configurações Docker e scripts de inicialização
├── logs/                     # Armazenamento de logs do sistema
└── src/                      # Código-fonte principal da aplicação
    ├── api/                  # Endpoints da API REST
    ├── config/               # Configurações da aplicação
    ├── core/                 # Lógica de negócios central
    ├── models/               # Modelos de dados e entidades
    ├── services/             # Serviços e integrações externas
    └── utils/                # Utilitários e funções auxiliares
```

## Arquivos de Configuração na Raiz

| Arquivo | Descrição |
|---------|-----------|
| `.env` | Variáveis de ambiente com configurações sensíveis (senhas, chaves de API) |
| `.env.example` | Exemplo de configuração de variáveis de ambiente para referência |
| `docker-compose.yml` | Configuração dos containers Docker (PostgreSQL, Redis, pgAdmin) |
| `README.md` | Documentação principal do projeto |

## Detalhamento das Áreas Principais

### 1. Infraestrutura e Dados (`/docker`, `/backups`, `/logs`)

#### Docker (`/docker`)
Contém configurações e scripts para os containers Docker que fornecem a infraestrutura do sistema.

| Arquivo | Descrição |
|---------|-----------|
| `init-db.sql` | Script SQL para inicialização do banco de dados PostgreSQL |

#### Backups (`/backups`)
Diretório para armazenamento de backups automáticos e manuais do banco de dados.

#### Logs (`/logs`)
Armazenamento centralizado de logs do sistema para monitoramento e diagnóstico.

### 2. Código-Fonte (`/src`)

#### API (`/src/api`)
Endpoints REST que expõem as funcionalidades do sistema para clientes externos.

| Módulo | Descrição |
|--------|-----------|
| `alerts` | Endpoints para gerenciamento da Central de Alertas |
| `analysis` | Endpoints para análise de causa raiz e padrões de falha |
| `equipment` | Endpoints para gerenciamento de equipamentos e TAGs |
| `integration` | Endpoints para integração com APIs externas |
| `notifications` | Endpoints para sistema de notificações |
| `risk` | Endpoints para gerenciamento de perfis de risco |

#### Configuração (`/src/config`)
Configurações centralizadas da aplicação.

| Arquivo | Descrição |
|---------|-----------|
| `database.py` | Configuração de conexão com o banco de dados |
| `api.py` | Configuração da API REST |

#### Core (`/src/core`)
Implementação da lógica de negócios central do sistema.

| Módulo | Descrição |
|--------|-----------|
| `alerts` | Lógica para processamento e filtragem de alertas |
| `analysis` | Algoritmos de análise de causa raiz |
| `equipment` | Lógica para gerenciamento de equipamentos |
| `integration` | Lógica para integração com sistemas externos |
| `notifications` | Lógica para envio de notificações |
| `risk` | Lógica para avaliação de risco |

#### Modelos (`/src/models`)
Definição das entidades e modelos de dados do sistema.

| Arquivo/Módulo | Descrição |
|----------------|-----------|
| `client.py` | Modelo para clientes/empresas |
| `alerts/alert.py` | Modelo para alertas de manutenção |
| `equipment/equipment.py` | Modelo para equipamentos monitorados |
| `risk/risk_profile.py` | Modelo para perfis de risco personalizados |

#### Serviços (`/src/services`)
Serviços que implementam funcionalidades específicas ou integram com sistemas externos.

| Módulo | Descrição |
|--------|-----------|
| `analysis/anthropic_service.py` | Integração com a API da Anthropic para análise de IA |
| `alerts` | Serviços para processamento de alertas |
| `equipment` | Serviços para gerenciamento de equipamentos |
| `integration` | Serviços para integração com APIs heterogêneas |
| `notifications` | Serviços para envio de notificações |
| `risk` | Serviços para avaliação de risco |

#### Utilitários (`/src/utils`)
Funções auxiliares e utilitários usados em todo o sistema.

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
