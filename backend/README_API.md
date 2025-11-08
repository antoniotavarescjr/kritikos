# Kritikos API - FastAPI Backend

API RESTful para acesso aos dados do sistema Kritikos de análise parlamentar.

## 🚀 Quick Start

### 1. Subir os serviços com Docker

```bash
# Na raiz do projeto
docker-compose up -d

# Apenas o banco de dados (se já tiver a API rodando)
docker-compose up -d db redis
```

### 2. Instalar dependências e rodar localmente

```bash
cd backend
pip install -r requirements_api.txt
python -m api.main
```

### 3. Acessar a API

- **API**: http://localhost:8000
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## 📊 Endpoints Principais

### Deputados
- `GET /api/deputados` - Listar deputados
- `GET /api/deputados/{id}` - Dados do deputado
- `GET /api/deputados/{id}/gastos` - Gastos parlamentares
- `GET /api/deputados/{id}/emendas` - Emendas propostas
- `GET /api/deputados/{id}/proposicoes` - Proposições autoria

### Rankings
- `GET /api/ranking/idp` - Ranking por IDP
- `GET /api/ranking/emendas` - Ranking por emendas
- `GET /api/ranking/gastos` - Ranking por gastos
- `GET /api/ranking/proposicoes` - Ranking por proposições

### Busca
- `GET /api/busca/proposicoes` - Buscar proposições
- `GET /api/busca/deputados` - Buscar deputados

### Health
- `GET /health` - Status da API
- `GET /health/db` - Status do banco

## 🧪 Testes

### Testar API localmente

```bash
# Instalar dependências de teste
pip install httpx

# Executar testes automatizados
python test_api_example.py

# Testar API em outro ambiente
python test_api_example.py http://api.kritikos.com.br
```

### Exemplos de requisições

```bash
# Health check
curl http://localhost:8000/health

# Listar deputados
curl "http://localhost:8000/api/deputados?page=1&per_page=5"

# Buscar deputado específico
curl http://localhost:8000/api/deputados/745

# Ranking IDP
curl "http://localhost:8000/api/ranking/idp?page=1&per_page=10"

# Buscar proposições
curl "http://localhost:8000/api/busca/proposicoes?ementa=educação&tem_analise=true"
```

## 🏗️ Estrutura do Projeto

```
backend/
├── api/                    # FastAPI application
│   ├── __init__.py
│   ├── main.py             # Application entry point
│   └── config.py          # Configuration
├── routers/                # API routes
│   ├── __init__.py
│   ├── deputados.py        # Deputados endpoints
│   ├── gastos.py          # Gastos endpoints
│   ├── emendas.py         # Emendas endpoints
│   ├── proposicoes.py     # Proposições endpoints
│   ├── ranking.py         # Ranking endpoints
│   └── busca.py          # Search endpoints
├── schemas/                # Pydantic models
│   ├── __init__.py
│   ├── deputado.py
│   ├── gasto.py
│   ├── emenda.py
│   ├── proposicao.py
│   └── ranking.py
├── services/               # Business logic
│   └── __init__.py
├── src/                   # Existing models and utilities
│   ├── models/           # SQLAlchemy models
│   └── utils/            # Utilities
├── docs/                  # Documentation
├── tests/                  # Test files
├── requirements_api.txt      # API dependencies
├── Dockerfile.api          # Docker image for API
└── test_api_example.py     # API testing script
```

## 🔧 Configuração

### Variáveis de Ambiente

As variáveis estão configuradas no arquivo `.env` na raiz do projeto:

```bash
# Servidor
HOST=0.0.0.0
PORT=8000
DEBUG=false

# Banco de dados
DATABASE_URL=postgresql://user:pass@localhost:5432/kritikos

# Cache
REDIS_URL=redis://localhost:6379/0

# Segurança
SECRET_KEY=your-secret-key

# Rate limiting
RATE_LIMIT_PER_MINUTE=100
```

## 📝 Desenvolvimento

### Formatar código

```bash
# Instalar dependências de desenvolvimento
pip install black isort flake8 mypy

# Formatar
black api/ schemas/ services/ routers/
isort api/ schemas/ services/ routers/

# Verificar tipos
mypy api/

# Lint
flake8 api/
```

### Logs

A API gera logs estruturados em JSON:

```bash
# Ver logs em tempo real
docker-compose logs -f kritikos-api

# Logs no arquivo (se rodando localmente)
tail -f logs/api.log
```

## 🚀 Deploy

### Produção com Docker

```bash
# Build e subir todos os serviços
docker-compose -f docker-compose.yml --env-file .env up -d

# Ver status
docker-compose ps

# Ver logs
docker-compose logs -f kritikos-api
```

### Variáveis de Produção

```bash
# .env de produção
DEBUG=false
LOG_LEVEL=WARNING
SECRET_KEY=production-secret-key
DATABASE_URL=postgresql://user:pass@prod-db:5432/kritikos
```

## 📊 Monitoramento

### Health Checks

- `/health` - Status geral da API
- `/health/db` - Conexão com banco de dados

### Métricas

A API expõe métricas em `/metrics` (se Prometheus habilitado):

- Tempo de resposta por endpoint
- Taxa de erro 4xx/5xx
- Número de requisições
- Uso de memória

## 🔒 Segurança

### Rate Limiting

- Padrão: 100 requisições/minuto por IP
- Headers: `X-RateLimit-Limit`, `X-RateLimit-Remaining`

### CORS

Configurado para permitir:
- `http://localhost:3000` (React dev)
- `http://localhost:8080` (Vue dev)
- `https://kritikos.com.br` (Produção)

### Validação

- Inputs validados com Pydantic
- SQL injection prevenido pelo SQLAlchemy
- XSS prevenido por escaping automático

## 🤝 Contribuição

1. Fork o projeto
2. Criar branch: `feature/nova-funcionalidade`
3. Implementar com testes
4. Submeter PR

## 📞 Suporte

- **Issues**: https://github.com/antoniotavarescjr/kritikos/issues
- **Documentação**: [docs/README.md](docs/README.md)

---

**Versão**: 1.0.0  
**Última atualização**: 7 de janeiro de 2025
