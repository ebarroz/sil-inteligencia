# API Integration for SIL Predictive System

Este documento descreve a estrutura de integração com APIs externas para obtenção de dados de medições de termografia, óleo e vibração para o sistema SIL Predictive.

## Estrutura de Diretórios

```
src/
├── api/
│   └── integration/
│       ├── api_client.py         # Cliente genérico para consumo de APIs
│       ├── thermography/         # Integração com APIs de termografia
│       ├── oil/                  # Integração com APIs de análise de óleo
│       └── vibration/            # Integração com APIs de vibração
└── models/
    ├── base.py                   # Classes base para todos os modelos de medição
    ├── thermography/             # Modelos para dados de termografia
    │   └── model.py
    ├── oil/                      # Modelos para dados de análise de óleo
    │   └── model.py
    └── vibration/                # Modelos para dados de vibração
        └── model.py
```

## Cliente Genérico de API

O arquivo `api_client.py` implementa um cliente genérico para consumo de APIs externas, com suporte para:

- Diferentes métodos de autenticação (API Key, Bearer Token, OAuth2)
- Retry automático com backoff exponencial
- Controle de rate limiting
- Tratamento de erros
- Paginação de resultados
- Filtros por data (since)

### Exemplo de Uso

```python
from src.api.integration.api_client import APIClient

# Inicializar cliente com autenticação por API Key
client = APIClient(
    base_url="https://api.example.com/v1",
    auth_type="api_key",
    auth_credentials={
        "header_name": "X-API-Key",
        "key": "sua-api-key-aqui"
    },
    max_retries=3
)

# Obter dados com paginação automática
measurements = client.get_paginated(
    endpoint="thermography/readings",
    params={"equipment_id": "motor-01"},
    limit=100
)

# Obter dados desde uma data específica
from datetime import datetime, timedelta
yesterday = datetime.utcnow() - timedelta(days=1)
new_measurements = client.get_since(
    endpoint="oil/analysis",
    since_datetime=yesterday,
    datetime_param="after"
)
```

## Modelos de Dados

### Modelo Base

O arquivo `base.py` define classes base para todos os tipos de medição:

- `MeasurementStatus`: Enum para status de medição (NORMAL, WARNING, ALERT, CRITICAL)
- `MeasurementSource`: Enum para fonte de dados (THERMOGRAPHY, OIL_ANALYSIS, VIBRATION)
- `Equipment`: Dataclass para representar equipamentos
- `BaseMeasurement`: Classe base para todas as medições
- `MeasurementThreshold`: Classe para definir limiares de alerta

### Modelo de Termografia

O modelo de termografia (`thermography/model.py`) define:

- `ThermographyPoint`: Representa um ponto de medição em uma imagem termográfica
- `ThermographyMeasurement`: Representa uma sessão de medição termográfica

### Modelo de Análise de Óleo

O modelo de análise de óleo (`oil/model.py`) define:

- `OilSampleType`: Enum para tipos de amostra (NEW, IN_SERVICE, FILTERED, DRAIN)
- `OilProperty`: Representa uma propriedade medida na análise de óleo
- `OilAnalysisMeasurement`: Representa uma análise de óleo completa

### Modelo de Vibração

O modelo de vibração (`vibration/model.py`) define:

- `VibrationAxis`: Enum para eixos de medição (X, Y, Z, RADIAL, AXIAL)
- `VibrationUnit`: Enum para unidades de medição (g, mm/s, μm, Hz)
- `VibrationReading`: Representa uma leitura de vibração
- `FrequencySpectrum`: Representa um espectro de frequência
- `VibrationMeasurement`: Representa uma sessão de medição de vibração

## Exemplo de Uso dos Modelos

```python
from datetime import datetime
from src.models.base import MeasurementStatus, MeasurementSource
from src.models.thermography.model import ThermographyMeasurement, ThermographyPoint

# Criar uma medição de termografia
measurement = ThermographyMeasurement(
    id="thermo-123",
    equipment_id="motor-01",
    timestamp=datetime.utcnow(),
    source=MeasurementSource.THERMOGRAPHY,
    image_url="https://storage.example.com/images/thermo-123.jpg",
    ambient_temperature=25.5,
    humidity=60.0
)

# Adicionar pontos de medição
measurement.points.append(
    ThermographyPoint(
        id="point-1",
        name="Motor Bearing",
        x=150.0,
        y=200.0,
        temperature=85.2
    )
)

# Avaliar status com base nos pontos
status = measurement.evaluate_status()
print(f"Status da medição: {status}")

# Converter para dicionário (para armazenamento ou API)
data = measurement.to_dict()
```

## Bibliotecas Utilizadas

- **requests**: Para comunicação HTTP com APIs externas
- **dataclasses**: Para definição de modelos de dados
- **typing**: Para anotações de tipo
- **datetime**: Para manipulação de datas e timestamps
- **enum**: Para definição de enumerações
- **logging**: Para registro de logs

## Próximos Passos

1. Implementar clientes específicos para cada tipo de API (termografia, óleo, vibração)
2. Adicionar testes unitários para validar a integração
3. Implementar persistência dos dados no banco PostgreSQL
4. Configurar autenticação e credenciais para cada API externa
