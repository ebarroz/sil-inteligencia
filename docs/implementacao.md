# Documentação de Implementação - SIL Predictive System

## Visão Geral

Este documento descreve a implementação da arquitetura do SIL Predictive System, um sistema de inteligência artificial para análise preditiva de manutenção industrial. A implementação inclui:

1. **Clientes de API** para integração com sistemas externos de medição (termografia, óleo e vibração)
2. **Modelos de dados** para representação estruturada das medições
3. **Camada de persistência** para armazenamento em PostgreSQL/TimescaleDB
4. **API REST** para exposição dos dados coletados

## Bibliotecas Utilizadas

A implementação utiliza as seguintes bibliotecas:

- **requests**: Para comunicação HTTP com APIs externas
- **psycopg2**: Para conexão e operações com PostgreSQL
- **FastAPI**: Para criação de endpoints REST
- **Pydantic**: Para validação de dados e serialização/deserialização
- **uuid**: Para geração de identificadores únicos
- **logging**: Para registro de eventos e erros

## Estrutura de Diretórios

```
sil-inteligencia/
├── src/
│   ├── api/
│   │   ├── endpoints.py                # Endpoints REST
│   │   └── integration/
│   │       ├── api_client.py           # Cliente genérico de API
│   │       ├── thermography/
│   │       │   └── client.py           # Cliente específico para termografia
│   │       ├── oil/
│   │       │   └── client.py           # Cliente específico para óleo
│   │       └── vibration/
│   │           └── client.py           # Cliente específico para vibração
│   ├── config/
│   │   └── database.py                 # Configuração e operações de banco de dados
│   └── models/
│       ├── base.py                     # Modelo base para medições
│       ├── thermography/
│       │   └── model.py                # Modelo para medições de termografia
│       ├── oil/
│       │   └── model.py                # Modelo para análises de óleo
│       └── vibration/
│           └── model.py                # Modelo para medições de vibração
└── docs/
    ├── api_integration.md              # Documentação de integração com APIs
    └── mapa_diretorios_sil.md          # Mapa de diretórios do projeto
```

## Componentes Implementados

### 1. Cliente Genérico de API (`src/api/integration/api_client.py`)

Um cliente HTTP genérico que fornece:

- Suporte para diferentes métodos de autenticação (API Key, Bearer Token, OAuth2)
- Retry automático com backoff exponencial
- Controle de rate limiting
- Tratamento de erros abrangente
- Suporte para paginação de resultados
- Filtros por data (since)

### 2. Clientes Específicos de API

Implementações específicas para cada tipo de medição:

- **Termografia** (`src/api/integration/thermography/client.py`): Integração com sistemas de termografia, incluindo dados simulados
- **Óleo** (`src/api/integration/oil/client.py`): Integração com sistemas de análise de óleo, incluindo dados simulados
- **Vibração** (`src/api/integration/vibration/client.py`): Integração com sistemas de medição de vibração, incluindo dados simulados

### 3. Modelos de Dados

Representações estruturadas para cada tipo de medição:

- **Modelo Base** (`src/models/base.py`): Classes e enums comuns a todos os tipos de medição
- **Termografia** (`src/models/thermography/model.py`): Modelo para medições de termografia e pontos de medição
- **Óleo** (`src/models/oil/model.py`): Modelo para análises de óleo e propriedades medidas
- **Vibração** (`src/models/vibration/model.py`): Modelo para medições de vibração, leituras e espectros de frequência

### 4. Camada de Persistência (`src/config/database.py`)

Implementação completa para armazenamento e recuperação de dados:

- **DatabaseManager**: Gerenciador de conexão com PostgreSQL usando pool de conexões
- **MeasurementRepository**: Repositório para operações CRUD com medições
- Suporte para TimescaleDB para armazenamento eficiente de séries temporais
- Métodos específicos para cada tipo de medição
- Consultas otimizadas com índices apropriados

### 5. API REST (`src/api/endpoints.py`)

Endpoints RESTful para acesso aos dados:

- **Equipamentos**: CRUD completo para equipamentos
- **Medições**: Endpoints genéricos para todas as medições
- **Termografia**: Endpoints específicos para medições de termografia
- **Óleo**: Endpoints específicos para análises de óleo
- **Vibração**: Endpoints específicos para medições de vibração
- **Status**: Endpoints para consulta de alertas e avisos
- **Sincronização**: Endpoint para sincronização de dados desde uma data específica

## Como Testar

### 1. Configuração do Ambiente

Certifique-se de ter as dependências instaladas:

```bash
pip install fastapi uvicorn psycopg2-binary requests pydantic
```

### 2. Configuração do Banco de Dados

Crie um banco de dados PostgreSQL e instale a extensão TimescaleDB:

```sql
CREATE DATABASE sil_predictive;
\c sil_predictive
CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;
```

### 3. Inicialização do Esquema

Execute o seguinte código para inicializar o esquema do banco de dados:

```python
from src.config.database import DatabaseManager

db_manager = DatabaseManager(
    host="localhost",
    port=5432,
    database="sil_predictive",
    user="postgres",
    password="postgres"
)

db_manager.initialize_schema()
```

### 4. Execução da API

Crie um arquivo `main.py` na raiz do projeto:

```python
import uvicorn
from fastapi import FastAPI
from src.api.endpoints import router

app = FastAPI(title="SIL Predictive System API")
app.include_router(router)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

Execute a API:

```bash
python main.py
```

Acesse a documentação interativa da API em: http://localhost:8000/docs

### 5. Teste com Dados Simulados

Para testar a integração com dados simulados, execute:

```python
from src.api.integration.thermography.client import ThermographyClient
from src.api.integration.oil.client import OilAnalysisClient
from src.api.integration.vibration.client import VibrationClient

# Criar clientes
thermo_client = ThermographyClient(base_url="https://api.example.com", api_key="test_key")
oil_client = OilAnalysisClient(base_url="https://api.example.com", api_key="test_key")
vibration_client = VibrationClient(base_url="https://api.example.com", api_key="test_key")

# Obter dados simulados
thermo_data = thermo_client.get_measurements(equipment_id="MOTOR-001", limit=5)
oil_data = oil_client.get_measurements(equipment_id="MOTOR-001", limit=5)
vibration_data = vibration_client.get_measurements(equipment_id="MOTOR-001", limit=5)

print(f"Thermography measurements: {len(thermo_data)}")
print(f"Oil analysis measurements: {len(oil_data)}")
print(f"Vibration measurements: {len(vibration_data)}")
```

## Próximos Passos

1. **Integração com APIs Reais**: Substituir os dados simulados por integrações reais quando as especificações das APIs estiverem disponíveis
2. **Autenticação e Autorização**: Implementar sistema de autenticação e autorização para a API REST
3. **Processamento de Alertas**: Desenvolver lógica para processamento automático de alertas
4. **Análise de Causa Raiz**: Implementar algoritmos de análise de causa raiz
5. **Interface de Usuário**: Desenvolver dashboard para visualização dos dados
6. **Testes Automatizados**: Criar testes unitários e de integração
7. **Documentação Adicional**: Expandir a documentação com exemplos de uso e casos de teste

## Conclusão

A implementação atual fornece uma base sólida para o SIL Predictive System, com uma arquitetura modular e extensível que pode ser facilmente adaptada às necessidades específicas do projeto. A separação clara entre camadas (integração, modelos, persistência, API) facilita a manutenção e evolução do sistema.
