# Kritikos API - Documentação Completa

## Visão Geral

A Kritikos API é uma interface RESTful para acesso aos dados do sistema Kritikos de análise parlamentar. Esta API fornece endpoints para consultar informações sobre deputados, gastos parlamentares, emendas, proposições legislativas e rankings de desempenho.

## 🚀 Início Rápido

### Instalação

```bash
# Clonar o repositório
git clone https://github.com/antoniotavarescjr/kritikos.git
cd kritikos/backend

# Instalar dependências
pip install -r requirements_api.txt

# Configurar variáveis de ambiente
cp .env.example .env
# Editar .env com suas configurações
```

### Executar em Desenvolvimento

```bash
# Usando Python
python -m api.main

# Ou usando Uvicorn diretamente
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

### Acessar Documentação

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI JSON**: http://localhost:8000/openapi.json

## 📊 Endpoints Principais

### Deputados
- `GET /api/deputados` - Listar todos os deputados
- `GET /api/deputados/{id}` - Obter deputado específico
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

### Health Checks
- `GET /health` - Status da API
- `GET /health/db` - Status do banco de dados

## 🔧 Configuração

### Variáveis de Ambiente

```bash
# Servidor
HOST=0.0.0.0
PORT=8000
DEBUG=false

# Banco de Dados
DATABASE_URL=postgresql://user:password@localhost:5432/kritikos

# CORS
ALLOWED_HOSTS=["http://localhost:3000", "https://kritikos.com.br"]

# Cache
REDIS_URL=redis://localhost:6379/0
CACHE_TTL=300

# Rate Limiting
RATE_LIMIT_PER_MINUTE=100

# Paginação
DEFAULT_PAGE_SIZE=20
MAX_PAGE_SIZE=100
```

## 📝 Estrutura das Respostas

### Formato Padrão

```json
{
  "data": {...},
  "meta": {
    "total": 100,
    "page": 1,
    "per_page": 20,
    "total_pages": 5
  },
  "links": {
    "self": "/api/deputados?page=1",
    "next": "/api/deputados?page=2",
    "prev": null
  }
}
```

### Formato de Erro

```json
{
  "error": {
    "code": 404,
    "message": "Deputado não encontrado",
    "type": "HTTP_ERROR"
  },
  "meta": {
    "timestamp": 1704637200,
    "path": "/api/deputados/99999"
  }
}
```

## 🔍 Exemplos de Uso

### Buscar Deputado com IDP

```bash
curl -X GET "http://localhost:8000/api/deputados/745" \
  -H "Accept: application/json"
```

```javascript
// JavaScript/React
const response = await fetch('/api/deputados/745');
const data = await response.json();
console.log(data.data);
```

### Buscar Ranking IDP

```bash
curl -X GET "http://localhost:8000/api/ranking/idp?page=1&per_page=10" \
  -H "Accept: application/json"
```

### Buscar Proposições com Filtros

```bash
curl -X GET "http://localhost:8000/api/busca/proposicoes?ementa=educação&tem_analise=true&par_minimo=70" \
  -H "Accept: application/json"
```

## 📊 Métricas e Monitoramento

### Health Checks

A API inclui endpoints de health check para monitoramento:

- `/health` - Verifica se a API está funcionando
- `/health/db` - Verifica conexão com o banco de dados

### Métricas Disponíveis

- Tempo de resposta por endpoint
- Taxa de erro 4xx/5xx
- Uso de memória e CPU
- Conexões ativas no banco

### Logs

A API gera logs estruturados em formato JSON:

```json
{
  "timestamp": "2025-01-07T15:00:00Z",
  "level": "INFO",
  "message": "Request processed",
  "endpoint": "/api/deputados/745",
  "method": "GET",
  "status_code": 200,
  "response_time": 0.045,
  "user_agent": "Mozilla/5.0..."
}
```

## 🧪 Testes

### Executar Testes

```bash
# Instalar dependências de teste
pip install -r requirements_api.txt

# Executar todos os testes
pytest

# Executar com coverage
pytest --cov=api --cov-report=html

# Executar testes específicos
pytest tests/test_deputados.py -v
```

### Estrutura de Testes

```
tests/
├── conft.py              # Configuração geral
├── test_deputados.py     # Testes de deputados
├── test_gastos.py        # Testes de gastos
├── test_emendas.py       # Testes de emendas
├── test_proposicoes.py   # Testes de proposições
├── test_ranking.py       # Testes de ranking
└── test_busca.py         # Testes de busca
```

## 🚀 Deploy

### Docker

```bash
# Construir imagem
docker build -t kritikos-api .

# Executar container
docker run -p 8000:8000 kritikos-api
```

### Docker Compose

```yaml
version: '3.8'
services:
  kritikos-api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://user:pass@db:5432/kritikos
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - db
      - redis
  
  db:
    image: postgres:15
    environment:
      POSTGRES_DB: kritikos
      POSTGRES_USER: user
      POSTGRES_PASSWORD: pass
    volumes:
      - postgres_data:/var/lib/postgresql/data
  
  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data
```

## 📚 Documentação de Referência

### Models Pydantic

Todos os endpoints usam schemas Pydantic para validação:

- `DeputadoResponse` - Dados completos do deputado
- `GastoResponse` - Informações de gastos
- `EmendaResponse` - Dados de emendas
- `ProposicaoResponse` - Proposições e análises
- `IDPRankingResponse` - Ranking por IDP

### Metodologia IDP

O Índice de Desempenho Parlamentar (IDP) é calculado usando:

1. **Desempenho Legislativo** (40%): Baseado em proposições relevantes
2. **Relevância Social** (30%): Média dos scores PAR das proposições
3. **Responsabilidade Fiscal** (30%): Análise de emendas e gastos

### Análises de IA

As proposições são analisadas por agentes de IA especializados:

- **Sumarizer Agent**: Gera resumos automáticos
- **Trivial Filter Agent**: Classifica relevância
- **PAR Analyzer Agent**: Calcula scores de impacto

## 🔒 Segurança

### Rate Limiting

- Limite padrão: 100 requisições/minuto por IP
- Headers: `X-RateLimit-Limit`, `X-RateLimit-Remaining`

### CORS

Configurado para permitir:
- `http://localhost:3000` (React dev)
- `http://localhost:8080` (Vue dev)
- `https://kritikos.com.br` (Produção)

### Validação

- Todos os inputs são validados com Pydantic
- SQL injection prevenido pelo SQLAlchemy
- XSS prevenido por escaping automático

## 🤝 Contribuição

### Desenvolvimento Local

```bash
# Instalar pre-commit hooks
pre-commit install

# Formatar código
black api/
isort api/

# Verificar tipos
mypy api/

# Lint
flake8 api/
```

### Pull Requests

1. Fork o repositório
2. Criar branch feature/nome-da-feature
3. Implementar com testes
4. Submeter PR com descrição detalhada

## 📞 Suporte

- **Issues**: https://github.com/antoniotavarescjr/kritikos/issues
- **Email**: contato@kritikos.com.br
- **Documentação**: https://docs.kritikos.com.br

## 📄 Licença

MIT License - ver arquivo [LICENSE](../../LICENSE) para detalhes.

---

**Última atualização**: 7 de janeiro de 2025
**Versão**: 1.0.0
