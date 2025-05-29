-- Inicialização do banco de dados SIL Centro de Inteligência
-- Criado por: Manus - Engenheiro de Integrações
-- Data: 29 de Maio de 2025

-- Extensões
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "timescaledb";

-- Tabela de clientes
CREATE TABLE IF NOT EXISTS clientes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    nome VARCHAR(255) NOT NULL,
    cnpj VARCHAR(14) UNIQUE NOT NULL,
    email VARCHAR(255) NOT NULL,
    telefone VARCHAR(20),
    nivel_risco_padrao SMALLINT DEFAULT 3,
    data_cadastro TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Tabela de equipamentos
CREATE TABLE IF NOT EXISTS equipamentos (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tag VARCHAR(50) UNIQUE NOT NULL,
    cliente_id UUID NOT NULL REFERENCES clientes(id),
    nome VARCHAR(255) NOT NULL,
    tipo VARCHAR(100) NOT NULL,
    localizacao VARCHAR(255),
    data_instalacao TIMESTAMP WITH TIME ZONE,
    data_cadastro TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Tabela de alertas
CREATE TABLE IF NOT EXISTS alertas (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    equipamento_id UUID NOT NULL REFERENCES equipamentos(id),
    tipo VARCHAR(50) NOT NULL,
    nivel_gravidade SMALLINT NOT NULL,
    mensagem TEXT NOT NULL,
    dados JSONB,
    validado BOOLEAN DEFAULT FALSE,
    falso_positivo BOOLEAN DEFAULT FALSE,
    data_criacao TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    data_validacao TIMESTAMP WITH TIME ZONE
);

-- Índices
CREATE INDEX IF NOT EXISTS idx_equipamentos_cliente_id ON equipamentos(cliente_id);
CREATE INDEX IF NOT EXISTS idx_alertas_equipamento_id ON alertas(equipamento_id);
CREATE INDEX IF NOT EXISTS idx_alertas_nivel_gravidade ON alertas(nivel_gravidade);
CREATE INDEX IF NOT EXISTS idx_alertas_data_criacao ON alertas(data_criacao DESC);

-- Converter tabela de alertas para hypertable (TimescaleDB)
SELECT create_hypertable('alertas', 'data_criacao', if_not_exists => TRUE);

-- Comentários
COMMENT ON TABLE clientes IS 'Empresas clientes do sistema SIL';
COMMENT ON TABLE equipamentos IS 'Equipamentos monitorados pelo sistema';
COMMENT ON TABLE alertas IS 'Alertas gerados pelo sistema de monitoramento';
