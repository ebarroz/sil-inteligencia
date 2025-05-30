# Mapa de Diretórios do Projeto SIL Predictive System

## Visão Geral da Estrutura

O projeto SIL Predictive System está organizado em uma estrutura modular que segue as melhores práticas de desenvolvimento de software, com separação clara entre camadas de API, modelos de dados, serviços e lógica de negócios. Abaixo está o mapeamento detalhado de cada área do projeto.

## Diretório Principal de Produção

```
/home/enzo/projects/sil-predictive-system/
├── backups/                  # Armazenamento de backups do banco de dados
├── docker/                   # Configurações Docker e scripts de inicialização
├── docs/                     # Documentação do projeto
├── logs/                     # Armazenamento de logs do sistema
└── scripts/                  # Scripts de automação e manutenção
```

## Diretório de Desenvolvimento

```
sil-inteligencia/
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
