"""
Kritikos API - Aplicação principal FastAPI
API RESTful para acesso aos dados do sistema Kritikos de análise parlamentar
"""

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import logging
import time
from typing import Dict, Any

from .config import settings
from routers import deputados, gastos, emendas, proposicoes, ranking, busca
from src.models.database import get_db, get_db_session

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Lifespan da aplicação
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gerenciar eventos de startup e shutdown da API"""
    # Startup
    app.state.start_time = time.time()
    logger.info("🚀 Kritikos API iniciada com sucesso")
    logger.info(f"📚 Documentação disponível em: {settings.DOCS_URL}")
    logger.info(f"📖 ReDoc disponível em: {settings.REDOC_URL}")
    
    yield
    
    # Shutdown
    logger.info("🛑 Kritikos API sendo desligada")

# Criar aplicação FastAPI
app = FastAPI(
    title="Kritikos API",
    description="""
    ## API RESTful para análise parlamentar
    
    Esta API fornece acesso aos dados do sistema Kritikos, incluindo:
    
    ### 📊 Dados de Deputados
    - Informações pessoais e políticas
    - Índice de Desempenho Parlamentar (IDP)
    - Posição no ranking
    
    ### 💰 Gastos Parlamentares
    - Gastos por mês e tipo de despesa
    - Análise de padrões de gastos
    - Comparativos entre deputados
    
    ### 📋 Emendas Parlamentares
    - Emendas propostas e valores
    - Beneficiários e execução financeira
    - Rankings por emendas
    
    ### 📜 Proposições Legislativas
    - Proposições autoria dos deputados
    - Análises com IA (resumos e scores PAR)
    - Classificação de relevância
    
    ### 🏆 Rankings e IDP
    - Ranking geral por IDP
    - Rankings específicos (emendas, gastos)
    - Métricas detalhadas de desempenho
    
    ### 🔍 Busca Avançada
    - Busca textual em proposições
    - Filtros múltiplos
    - Ordenação personalizada
    
    ---
    
    **Metodologia IDP**: O Índice de Desempenho Parlamentar é calculado usando
    uma metodologia adaptada que considera:
    - Desempenho Legislativo (proposições relevantes)
    - Relevância Social (média dos scores PAR)
    - Responsabilidade Fiscal (análise de emendas e gastos)
    
    **Fonte de Dados**: Câmara dos Deputados, Portal da Transparência e análises
    realizadas por agentes de IA especializados.
    """,
    version="1.0.0",
    contact={
        "name": "Kritikos Team",
        "email": "contato@kritikos.com.br",
    },
    license_info={
        "name": "MIT License",
        "url": "https://opensource.org/licenses/MIT",
    },
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan
)

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_HOSTS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Middleware para logging de requisições
@app.middleware("http")
async def log_requests(request, call_next):
    """Middleware para logging de requisições e tempo de resposta"""
    start_time = time.time()
    
    # Log da requisição
    logger.info(
        f"Request: {request.method} {request.url.path} - "
        f"Client: {request.client.host if request.client else 'unknown'}"
    )
    
    # Processar requisição
    response = await call_next(request)
    
    # Calcular tempo de resposta
    process_time = time.time() - start_time
    
    # Log da resposta
    logger.info(
        f"Response: {response.status_code} - "
        f"Time: {process_time:.3f}s - "
        f"Path: {request.url.path}"
    )
    
    # Adicionar header de tempo de processamento
    response.headers["X-Process-Time"] = str(process_time)
    
    return response


# Exception handler personalizado
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Handler personalizado para HTTPExceptions"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.status_code,
                "message": exc.detail,
                "type": "HTTP_ERROR"
            },
            "meta": {
                "timestamp": time.time(),
                "path": request.url.path
            }
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """Handler para exceções genéricas"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": 500,
                "message": "Erro interno do servidor",
                "type": "INTERNAL_ERROR"
            },
            "meta": {
                "timestamp": time.time(),
                "path": request.url.path
            }
        }
    )


# Health checks
@app.get("/health", 
    summary="Health Check da API",
    description="Verifica se a API está funcionando corretamente",
    tags=["Health"],
    responses={
        200: {
            "description": "API saudável",
            "content": {
                "application/json": {
                    "example": {
                        "status": "healthy",
                        "timestamp": "2025-01-07T15:00:00Z",
                        "version": "1.0.0",
                        "uptime": 3600
                    }
                }
            }
        }
    }
)
async def health_check() -> Dict[str, Any]:
    """Health check básico da API"""
    return {
        "status": "healthy",
        "timestamp": time.time(),
        "version": "1.0.0",
        "uptime": time.time() - app.state.start_time if hasattr(app.state, 'start_time') else 0
    }


@app.get("/health/db",
    summary="Health Check do Banco de Dados",
    description="Verifica a conexão com o banco de dados",
    tags=["Health"],
    responses={
        200: {
            "description": "Banco de dados conectado",
            "content": {
                "application/json": {
                    "example": {
                        "status": "healthy",
                        "database": "connected",
                        "timestamp": "2025-01-07T15:00:00Z"
                    }
                }
            }
        },
        503: {
            "description": "Banco de dados indisponível"
        }
    }
)
async def database_health_check() -> Dict[str, Any]:
    """Health check do banco de dados"""
    try:
        session = get_db_session()
        # Testar consulta simples
        session.execute("SELECT 1")
        session.close()
        
        return {
            "status": "healthy",
            "database": "connected",
            "timestamp": time.time()
        }
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        raise HTTPException(
            status_code=503,
            detail="Banco de dados indisponível"
        )


# Endpoint raiz
@app.get("/",
    summary="API Root",
    description="Informações básicas sobre a API",
    tags=["Info"],
    responses={
        200: {
            "description": "Informações da API",
            "content": {
                "application/json": {
                    "example": {
                        "name": "Kritikos API",
                        "version": "1.0.0",
                        "description": "API RESTful para análise parlamentar",
                        "docs_url": "/docs",
                        "redoc_url": "/redoc"
                    }
                }
            }
        }
    }
)
async def root() -> Dict[str, Any]:
    """Endpoint raiz com informações da API"""
    return {
        "name": "Kritikos API",
        "version": "1.0.0",
        "description": "API RESTful para análise parlamentar",
        "docs_url": "/docs",
        "redoc_url": "/redoc",
        "openapi_url": "/openapi.json"
    }


# Incluir routers
app.include_router(
    deputados.router,
    prefix="/api/deputados",
    tags=["Deputados"]
)

app.include_router(
    gastos.router,
    prefix="/api/gastos",
    tags=["Gastos"]
)

app.include_router(
    emendas.router,
    prefix="/api/emendas",
    tags=["Emendas"]
)

app.include_router(
    proposicoes.router,
    prefix="/api/proposicoes",
    tags=["Proposições"]
)

app.include_router(
    ranking.router,
    prefix="/api/ranking",
    tags=["Ranking"]
)

app.include_router(
    busca.router,
    prefix="/api/busca",
    tags=["Busca"]
)


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "api.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level="info"
    )
